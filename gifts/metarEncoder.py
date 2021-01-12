#
# Name: metarEncoder.py
# Purpose: To encode METAR/SPECI information in IWXXM 3.0 XML format.
#
# Author: Mark Oberfield
# Organization: NOAA/NWS/OSTI/Meteorological Development Laboratory
# Contact Info: Mark.Oberfield@noaa.gov
#
import logging
import re
import traceback
import sys
import xml.etree.ElementTree as ET

from .common import xmlConfig as des
from .common import xmlUtilities as deu
from .common import Common


class Annex3(Common.Base):

    def __init__(self):
        #
        # Initialize the base class
        super(Annex3, self).__init__()
        #
        self._Logger = logging.getLogger(__name__)
        #
        # Create dictionaries of the following WMO codes
        neededCodes = [des.CLDAMTS, des.WEATHER, des.RECENTWX, des.CVCTNCLDS, des.SEACNDS, des.RWYDEPST, des.RWYCNTMS,
                       des.RWYDEPST, des.RWYFRCTN]
        try:
            self.codes = deu.parseCodeRegistryTables(des.CodesFilePath, neededCodes, des.PreferredLanguageForTitles)
        except AssertionError as msg:  # pragma: no cover
            self._Logger.warning(msg)
        #
        # map several encoder tokens to a single function
        setattr(self, 'obv', self.pcp)
        setattr(self, 'vcnty', self.pcp)

        self.observedTokenList = ['temps', 'altimeter', 'wind', 'vsby', 'rvr', 'pcp', 'obv', 'vcnty',
                                  'sky', 'rewx', 'ws', 'seastate', 'rwystate']

        self.trendTokenList = ['wind', 'pcp', 'obv', 'sky']

        self._re_unknwnPcpn = re.compile(r'(?P<mod>[-+]?)(?P<char>(SH|FZ|TS))')
        self._re_cloudLyr = re.compile(r'(VV|FEW|SCT|BKN|OVC|///|CLR|SKC)([/\d]{3})?(CB|TCU|///)?')
        self._TrendForecast = {'TEMPO': 'TEMPORARY_FLUCTUATIONS', 'BECMG': 'BECOMING'}
        self._RunwayDepositDepths = {'92': '100', '93': '150', '94': '200',
                                     '95': '250', '96': '300', '97': '350', '98': '400'}

    def __call__(self, decodedMetar, tacString):

        self.XMLDocument = None
        self.decodedTAC = decodedMetar
        self.tacString = tacString

        try:
            self.decodingFailure = False
            self.preamble()
            self.observation()
            if not self.decodingFailure:
                self.forecasts()

        except Exception:
            self._Logger.exception(tacString)

        return self.XMLDocument

    def preamble(self):
        #
        # The root element created here
        try:
            self.XMLDocument = ET.Element('iwxxm:%s' % self.decodedTAC['type']['str'])
        except KeyError:
            self.XMLDocument = ET.Element('iwxxm:%s' % 'METAR')
        #
        for prefix, uri in self.NameSpaces.items():
            self.XMLDocument.set('xmlns:%s' % prefix, uri)
        #
        self.XMLDocument.set('xsi:schemaLocation', '%s %s' % (des.IWXXM_URI, des.IWXXM_URL))
        #
        # Set its many attributes
        self.XMLDocument.set('reportStatus', 'NORMAL')
        self.XMLDocument.set('automatedStation', 'false')
        self.nilPresent = 'nil' in self.decodedTAC

        if 'cor' in self.decodedTAC:
            self.XMLDocument.set('reportStatus', 'CORRECTION')

        if 'auto' in self.decodedTAC:
            self.XMLDocument.set('automatedStation', 'true')
        #
        # Additional attributes for root element
        self.XMLDocument.set('permissibleUsage', 'OPERATIONAL')

        if des.TRANSLATOR:

            self.XMLDocument.set('translationCentreName', des.TranslationCentreName)
            self.XMLDocument.set('translationCentreDesignator', des.TranslationCentreDesignator)
            self.XMLDocument.set('translationTime', self.decodedTAC['translationTime'])
            self.XMLDocument.set('translatedBulletinReceptionTime',
                                 self.decodedTAC['translatedBulletinReceptionTime'])
            self.XMLDocument.set('translatedBulletinID', self.decodedTAC['translatedBulletinID'])
            #
            # If TAC translation failed in some way
            if 'err_msg' in self.decodedTAC:

                self.XMLDocument.set('translationFailedTAC', self.tacString)
                # self.XMLDocument.set('permissibleUsageSupplementary', self.decodedTAC.get('err_msg'))
                self.decodingFailure = True

        self.XMLDocument.set('gml:id', deu.getUUID())
        self._issueTimeUUID = None
        self.issueTime(self.XMLDocument, self.decodedTAC.get('itime', None))
        self.aerodrome(self.XMLDocument, self.decodedTAC.get('ident', None))
        self.observationTime()

    def issueTime(self, parent, token):

        indent = ET.SubElement(parent, 'iwxxm:issueTime')
        if token is None:
            return

        self._issueTime = token['value']
        indent1 = ET.SubElement(indent, 'gml:TimeInstant')
        indent1.set('gml:id', deu.getUUID())
        indent2 = ET.SubElement(indent1, 'gml:timePosition')
        indent2.text = self._issueTime
        self._issueTimeUUID = '#%s' % indent1.get('gml:id')

    def observationTime(self):

        try:
            indent = ET.SubElement(self.XMLDocument, 'iwxxm:observationTime')
            if self._issueTimeUUID is not None:
                indent.set('xlink:href', self._issueTimeUUID)

        except AttributeError:
            pass

    def observation(self):

        indent = ET.SubElement(self.XMLDocument, 'iwxxm:observation')
        if self.decodingFailure:
            return

        if self.nilPresent:
            indent.set('nilReason', self.codes[des.NIL][des.MSSG][0])
            return

        self.result(indent)

    def result(self, parent):

        self.runwayDirectionCache = {}
        indent1 = ET.SubElement(parent, 'iwxxm:MeteorologicalAerodromeObservation')
        indent1.set('gml:id', deu.getUUID())
        indent1.set('cloudAndVisibilityOK', str('cavok' in self.decodedTAC).lower())

        for element in self.observedTokenList:
            function = getattr(self, element)
            try:
                function(indent1, self.decodedTAC[element])
            except KeyError:
                #
                # If this error occurred inside one of the functions, report it
                if len(traceback.extract_tb(sys.exc_info()[2])) > 1:  # pragma: no cover
                    self._Logger.exception(self.tacString)
                #
                # Mandatory elements shall be reported missing
                elif element in ['temps', 'altimeter', 'wind']:
                    function(indent1, None)
                #
                # If visibility should be reported but isn't...
                elif 'cavok' not in self.decodedTAC and element in ['vsby', 'rvr']:
                    if element == 'vsby':
                        function(indent1, None)
                    else:
                        try:
                            token = self.decodedTAC['vsby']
                            if int(deu.checkVisibility(token['value'], token['uom'])) < des.RVR_MaximumDistance:
                                function(indent1, None)

                        except (KeyError, ValueError):
                            pass

    def forecasts(self):
        #
        # If no significant changes, "NOSIG", is forecast
        if 'nosig' in self.decodedTAC:

            indent = ET.SubElement(self.XMLDocument, 'iwxxm:trendForecast')
            indent.set('xsi:nil', 'true')
            indent.set('nilReason', self.codes[des.NIL][des.NOSIGC][0])
            return
        #
        # Or if there are any forecast trends
        try:
            self.doTrendForecasts(self.decodedTAC['trendFcsts'])
        except KeyError:
            pass

    def doTrendForecasts(self, events):

        for event in events:

            indent = ET.SubElement(self.XMLDocument, 'iwxxm:trendForecast')
            indent1 = ET.SubElement(indent, 'iwxxm:MeteorologicalAerodromeTrendForecast')
            indent1.set('gml:id', deu.getUUID())
            indent1.set('changeIndicator', self._TrendForecast[event['type']])
            indent1.set('cloudAndVisibilityOK', str('cavok' in event).lower())
            self.trendPhenomenonTime(indent1, event)
            self.trendForecast(indent1, event)

    def trendPhenomenonTime(self, parent, event):

        indent = ET.Element('iwxxm:phenomenonTime')
        indent1 = ET.Element('gml:TimePeriod')
        indent1.set('gml:id', deu.getUUID())
        begin = ET.SubElement(indent1, 'gml:beginPosition')
        end = ET.SubElement(indent1, 'gml:endPosition')
        indicator = ''
        #
        # The event may not have a 'ttime' key. In that case, phenomenonTime is unknown
        try:
            trendFcstPeriod = event['ttime']
            if 'AT' in trendFcstPeriod:
                begin.text = trendFcstPeriod['AT']
                indicator = 'AT'

            elif 'FM' in trendFcstPeriod:
                begin.text = trendFcstPeriod['FM']
                indicator = 'FROM'
                if 'TL' in trendFcstPeriod:
                    end.text = trendFcstPeriod['TL']
                    indicator = 'FROM_UNTIL'

            elif 'TL' in trendFcstPeriod:
                begin.text = self.decodedTAC['itime']['value']
                begin.set('indeterminatePosition', 'after')
                end.text = trendFcstPeriod['TL']
                indicator = 'UNTIL'
            #
            # If only AT or FM is provided
            if end.text is None:
                end.text = begin.text
                end.set('indeterminatePosition', 'after')

            indent.append(indent1)
        #
        # No time range explictly given
        except KeyError:
            indent.set('nilReason', self.codes[des.NIL][des.MSSG][0])

        parent.append(indent)
        if len(indicator) > 0:
            indent = ET.SubElement(parent, 'iwxxm:timeIndicator')
            indent.text = indicator

    def trendForecast(self, parent, forecast):

        try:
            # Always report visibility in meters, per Annex 3 Table A3-5
            uom = forecast['vsby']['uom']
            value = deu.checkVisibility(forecast['vsby']['value'], uom)
            #
            # Visibility in trend forecast is handled as a single element type with no children
            indent = ET.SubElement(parent, 'iwxxm:prevailingVisibility')
            if int(value) >= 10000:
                indent.text = '10000'
                indent.set('uom', 'm')
                indent = ET.SubElement(parent, 'iwxxm:prevailingVisibilityOperator')
                indent.text = 'ABOVE'

            else:
                indent.text = value
                indent.set('uom', 'm')

        except KeyError:
            pass
        #
        # The remaining trend forecast elements are handled similarly to the observed ones
        for element in self.trendTokenList:
            function = getattr(self, element)
            try:
                function(parent, forecast[element], True)
            except KeyError:
                #
                # If this error occurred inside one of the functions, report it
                if len(traceback.extract_tb(sys.exc_info()[2])) > 1:  # pragma: no cover
                    self._Logger.exception(self.tacString)

    def temps(self, parent, token):

        indent = ET.SubElement(parent, 'iwxxm:airTemperature')
        try:
            if deu.is_a_number(token['air']):
                indent.text = token['air']
                indent.set('uom', 'Cel')
            else:
                raise ValueError

        except (TypeError, ValueError):

            indent.set('uom', 'N/A')
            indent.set('nilReason', self.codes[des.NIL][des.NOOBSV][0])
            indent.set('xsi:nil', 'true')

        indent = ET.SubElement(parent, 'iwxxm:dewpointTemperature')
        try:
            if deu.is_a_number(token['dewpoint']):
                indent.text = token['dewpoint']
                indent.set('uom', 'Cel')
            else:
                raise ValueError

        except (AttributeError, TypeError, ValueError):

            indent.set('uom', 'N/A')
            indent.set('nilReason', self.codes[des.NIL][des.NOOBSV][0])
            indent.set('xsi:nil', 'true')

    def altimeter(self, parent, token):

        indent = ET.SubElement(parent, 'iwxxm:qnh')
        #
        # Always report pressure in hPa
        try:
            if token['uom'] == "[in_i'Hg]":
                indent.text = '%.1f' % (float(token['value']) * 33.8639)
            else:
                indent.text = str(int(token['value']))

            indent.set('uom', 'hPa')

        except (TypeError, ValueError):

            indent.set('uom', 'N/A')
            indent.set('nilReason', self.codes[des.NIL][des.NOOBSV][0])
            indent.set('xsi:nil', 'true')

    def wind(self, parent, token, trend=False):

        indent = ET.SubElement(parent, 'iwxxm:surfaceWind')
        if token is None or token['str'].startswith('/////'):
            indent.set('nilReason', self.codes[des.NIL][des.NOOBSV][0])
            indent.set('xsi:nil', 'true')
            return

        if trend:
            indent1 = ET.SubElement(indent, 'iwxxm:AerodromeSurfaceWindTrendForecast')
        else:
            indent1 = ET.SubElement(indent, 'iwxxm:AerodromeSurfaceWind')
            if token['str'].startswith('VRB') or 'ccw' in token:
                indent1.set('variableWindDirection', 'true')
            else:
                indent1.set('variableWindDirection', 'false')

        try:
            indent2 = ET.Element('iwxxm:meanWindDirection')
            indent2.text = str(int(token['dd']))
            indent2.set('uom', 'deg')
            indent1.append(indent2)

        except ValueError:
            if token['dd'] != 'VRB':
                indent2 = ET.Element('iwxxm:meanWindDirection')
                indent2.set('uom', 'N/A')
                indent2.set('nilReason', self.codes[des.NIL][des.NOOBSV][0])
                indent2.set('xsi:nil', 'true')
                indent1.append(indent2)

        indent2 = ET.SubElement(indent1, 'iwxxm:meanWindSpeed')
        try:
            indent2.text = str(int(token['ff']))
            indent2.set('uom', token['uom'])

        except ValueError:
            indent2.set('uom', 'N/A')
            indent2.set('nilReason', self.codes[des.NIL][des.NOOBSV][0])
            indent2.set('xsi:nil', 'true')

        if 'ffplus' in token:

            indent2 = ET.SubElement(indent1, 'iwxxm:meanWindSpeedOperator')
            indent2.text = 'ABOVE'
        #
        # Gusts are optional
        try:
            indent2 = ET.Element('iwxxm:windGustSpeed')
            indent2.text = token['gg']
            indent2.set('uom', token['uom'])
            indent1.append(indent2)

            if 'ggplus' in token:

                indent2 = ET.SubElement(indent1, 'iwxxm:windGustSpeedOperator')
                indent2.text = 'ABOVE'

        except KeyError:
            pass
        #
        # Variable directions are optional
        try:
            indent2 = ET.Element('iwxxm:extremeClockwiseWindDirection')
            indent2.text = str(int(token['cw']))
            indent2.set('uom', 'deg')
            indent1.append(indent2)

            indent2 = ET.Element('iwxxm:extremeCounterClockwiseWindDirection')
            indent2.set('uom', 'deg')
            indent2.text = str(int(token['ccw']))
            indent1.append(indent2)

        except KeyError:
            pass

    def vsby(self, parent, token, trend=False):

        indent = ET.SubElement(parent, 'iwxxm:visibility')
        if token is None or '//' in token['str']:
            indent.set('nilReason', self.codes[des.NIL][des.NOOBSV][0])
            indent.set('xsi:nil', 'true')
            return

        indent1 = ET.SubElement(indent, 'iwxxm:AerodromeHorizontalVisibility')
        indent2 = ET.SubElement(indent1, 'iwxxm:prevailingVisibility')
        #
        # Always report visibility in meters, per Annex 3 Table A3-5
        value = deu.checkVisibility(token['value'], token['uom'])
        uom = 'm'
        indent2.set('uom', uom)

        if int(value) >= 10000:

            indent2.text = '10000'
            indent2 = ET.SubElement(indent1, 'iwxxm:prevailingVisibilityOperator')
            indent2.text = 'ABOVE'

        else:
            indent2.text = value
            try:
                indent2 = ET.Element('iwxxm:prevailingVisibilityOperator')
                indent2.text = {'P': 'ABOVE', 'M': 'BELOW'}[token['oper']]
                indent1.append(indent2)

            except KeyError:
                pass

        try:
            indent2 = ET.Element('iwxxm:minimumVisibility')
            indent2.text = deu.checkVisibility(token['min'])
            indent2.set('uom', 'm')
            indent1.append(indent2)

            if token['bearing'] != '/':

                indent2 = ET.Element('iwxxm:minimumVisibilityDirection')
                indent2.text = token['bearing']
                indent2.set('uom', 'deg')
                indent1.append(indent2)

        except KeyError:
            pass

    def rvr(self, parent, token):

        if token is None:
            indent = ET.SubElement(parent, 'iwxxm:rvr')
            indent.set('nilReason', self.codes[des.NIL][des.MSSG][0])
            indent.set('xsi:nil', 'true')
            return

        for rwy, mean, tend, oper, uom in zip(token['rwy'], token['mean'],
                                              token['tend'], token['oper'],
                                              token['uom']):

            indent = ET.SubElement(parent, 'iwxxm:rvr')
            indent1 = ET.SubElement(indent, 'iwxxm:AerodromeRunwayVisualRange')
            indent1.set('pastTendency', tend)

            indent2 = ET.SubElement(indent1, 'iwxxm:runway')
            self.runwayDirection(indent2, rwy)

            indent2 = ET.SubElement(indent1, 'iwxxm:meanRVR')
            try:
                indent2.text = deu.checkRVR(mean, uom)
                indent2.set('uom', 'm')
                if oper is not None:
                    indent2 = ET.SubElement(indent1, 'iwxxm:meanRVROperator')
                    indent2.text = oper

            except ValueError:
                indent2.set('uom', 'N/A')
                indent2.set('nilReason', self.codes[des.NIL][des.NOOBSV][0])
                indent2.set('xsi:nil', 'true')

    def pcp(self, parent, token, trend=False):

        for ww in token['str']:
            #
            elementName = 'iwxxm:presentWeather'
            if trend:
                elementName = 'iwxxm:weather'

            if ww == '//':
                indent = ET.SubElement(parent, elementName)
                indent.set('nilReason', self.codes[des.NIL][des.NOOBSV][0])
                indent.set('xsi:nil', 'true')
                continue

            if ww == 'NSW':
                indent = ET.SubElement(parent, elementName)
                indent.set('nilReason', self.codes[des.NIL][des.NOOPRSIG][0])
                indent.set('xsi:nil', 'true')
                continue
            #
            # Search WMO Code Registry table
            try:
                uri, title = self.codes[des.WEATHER][ww]
                indent = ET.SubElement(parent, elementName)
                indent.set('xlink:href', uri)
                if (des.TITLES & des.Weather):
                    indent.set('xlink:title', title)
            #
            # Weather phenomenon token not matched
            except KeyError:

                indent = ET.SubElement(parent, elementName)
                result = self._re_unknwnPcpn.match(ww)
                try:
                    up = '%s%sUP' % (result.group('mod'), result.group('char'))
                    uri, title = self.codes[des.WEATHER][up.strip()]

                except AttributeError:
                    uri, title = self.codes[des.WEATHER]['UP']

                indent.set('xlink:href', uri)
                indent.set('xlink:title', '%s: %s' % (title, ww))

    def sky(self, parent, token, trend=False):

        suffix = ''
        if trend:
            suffix = 'Forecast'

        indent = ET.SubElement(parent, 'iwxxm:cloud')
        if token['str'][0] == 'NSC':
            indent.set('nilReason', self.codes[des.NIL][des.NOOPRSIG][0])
            indent.set('xsi:nil', 'true')
            return

        if token['str'][0] == 'NCD':
            indent.set('nilReason', self.codes[des.NIL][des.NOAUTODEC][0])
            indent.set('xsi:nil', 'true')
            self.XMLDocument.set('automatedStation', 'true')
            return

        indent1 = ET.SubElement(indent, 'iwxxm:AerodromeCloud%s' % suffix)
        if trend:
            indent1.set('gml:id', deu.getUUID())

        for lyr in token['str'][:4]:
            if lyr[:3] == '///' and lyr[3:] in ['CB', 'TCU']:
                self.doCloudLayer(indent1, '/', '/', lyr[3:])
            else:
                result = self._re_cloudLyr.match(lyr)
                self.doCloudLayer(indent1, result.group(1), result.group(2), result.group(3))

    def doCloudLayer(self, parent, amount, hgt, typ):
        #
        # Vertical visibility
        if amount == 'VV':
            indent = ET.SubElement(parent, 'iwxxm:verticalVisibility')
            if deu.is_a_number(hgt):
                indent.set('uom', '[ft_i]')
                indent.text = str(int(hgt) * 100)
            else:
                indent.set('uom', 'N/A')
                indent.set('nilReason', self.codes[des.NIL][des.NOOBSV][0])
                indent.set('xsi:nil', 'true')

            return

        indent = ET.SubElement(parent, 'iwxxm:layer')
        if amount == '///' and hgt == '///' and typ is None:
            if self.XMLDocument.get('automatedStation') == 'false':
                indent.set('nilReason', self.codes[des.NIL][des.NOOBSV][0])
            else:
                indent.set('nilReason', self.codes[des.NIL][des.NOAUTODEC][0])

            indent.set('xsi:nil', 'true')
            return

        indent1 = ET.SubElement(indent, 'iwxxm:CloudLayer')
        indent2 = ET.SubElement(indent1, 'iwxxm:amount')
        try:
            uri, title = self.codes[des.CLDAMTS][amount]
            indent2.set('xlink:href', uri)
            if (des.TITLES & des.CloudAmt):
                indent2.set('xlink:title', title)

        except KeyError:

            indent2.set('xsi:nil', 'true')
            if self.XMLDocument.get('automatedStation') == 'false':
                indent2.set('nilReason', self.codes[des.NIL][des.NOOBSV][0])
            else:
                indent2.set('nilReason', self.codes[des.NIL][des.NOAUTODEC][0])

            if amount == 'CLR':
                indent2.set('xlink:title', amount)
        try:
            indent2 = ET.SubElement(indent1, 'iwxxm:base')
            indent2.text = str(int(hgt) * 100)
            indent2.set('uom', '[ft_i]')

        except (TypeError, ValueError):

            if amount == 'SKC':
                indent2.set('nilReason', self.codes[des.NIL][des.NA][0])
            else:
                if self.XMLDocument.get('automatedStation') == 'false':
                    indent2.set('nilReason', self.codes[des.NIL][des.NOOBSV][0])
                else:
                    indent2.set('nilReason', self.codes[des.NIL][des.NOAUTODEC][0])

            indent2.set('xsi:nil', 'true')
            indent2.set('uom', 'N/A')
        #
        # Annex 3 and WMO 306 Manual on Codes specifies only two cloud type in METAR/SPECIs, 'CB' and 'TCU'
        try:
            indent2 = ET.Element('iwxxm:cloudType')
            uri, title = self.codes[des.CVCTNCLDS][typ]
            indent2.set('xlink:href', uri)
            if (des.TITLES & des.CloudType):
                indent2.set('xlink:title', title)
            indent1.append(indent2)

        except KeyError:
            if typ == '///':
                indent2.set('nilReason', self.codes[des.NIL][des.NOOBSV][0])
                indent2.set('xsi:nil', 'true')
                indent1.append(indent2)

    def rewx(self, parent, token):

        for ww in token['str']:

            if ww == '//':
                indent = ET.SubElement(parent, 'iwxxm:recentWeather')
                indent.set('nilReason', self.codes[des.NIL][des.NOOBSV][0])
                indent.set('xsi:nil', 'true')
                continue

            try:
                uri, title = self.codes[des.RECENTWX][ww]
                indent = ET.SubElement(parent, 'iwxxm:recentWeather')
                indent.set('xlink:href', uri)
                if (des.TITLES & des.Weather):
                    indent.set('xlink:title', title)

            except KeyError:
                try:
                    result = self._re_unknwnPcpn.match(ww)
                    up = '%s%sUP' % (result.group('mod'), result.group('char'))
                except AttributeError:
                    up = 'UP'

                uri, title = self.codes[des.RECENTWX][up.strip()]
                indent = ET.SubElement(parent, 'iwxxm:recentWeather')
                indent.set('xlink:href', uri)
                indent.set('xlink:title', '%s: %s' % (title, ww))

    def ws(self, parent, token):

        indent = ET.SubElement(parent, 'iwxxm:windShear')
        indent1 = ET.SubElement(indent, 'iwxxm:AerodromeWindShear')
        if 'ALL' in token['str']:
            indent1.set('allRunways', 'true')
        else:
            indent2 = ET.SubElement(indent1, 'iwxxm:runway')
            self.runwayDirection(indent2, token['rwy'])

    def seastate(self, parent, token):

        indent = ET.SubElement(parent, 'iwxxm:seaCondition')
        indent1 = ET.SubElement(indent, 'iwxxm:AerodromeSeaCondition')
        indent2 = ET.SubElement(indent1, 'iwxxm:seaSurfaceTemperature')
        try:
            indent2.text = str(int(token['seaSurfaceTemperature']))
            indent2.set('uom', 'Cel')

        except ValueError:
            indent2.set('uom', 'N/A')
            indent2.set('nilReason', self.codes[des.NIL][des.NOOBSV][0])
            indent2.set('xsi:nil', 'true')

        try:
            indent2 = ET.Element('iwxxm:significantWaveHeight')
            indent2.text = '%.1f' % (int(token['significantWaveHeight']) * 0.1)
            indent2.set('uom', 'm')
            indent1.append(indent2)

        except ValueError:
            indent2.set('uom', 'N/A')
            indent2.set('xsi:nil', 'true')
            indent2.set('nilReason', self.codes[des.NIL][des.NOOBSV][0])
            indent1.append(indent2)

        except KeyError:
            pass

        try:
            category = token['seaState']
            indent2 = ET.Element('iwxxm:seaState')
            try:
                uri, title = self.codes[des.SEACNDS][category]
                indent2.set('xlink:href', uri)
                if (des.TITLES & des.SeaCondition):
                    indent2.set('xlink:title', title)

            except KeyError:
                indent2.set('xsi:nil', 'true')
                indent2.set('nilReason', self.codes[des.NIL][des.NOOBSV][0])

            indent1.append(indent2)

        except KeyError:
            pass

    def rwystate(self, parent, tokens):

        for token in tokens:

            indent1 = ET.SubElement(parent, 'iwxxm:runwayState')
            if token['state'] == 'SNOCLO':
                indent1.set('nilReason', des.NIL_SNOCLO_URL)
                indent1.set('xsi:nil', 'true')
                continue

            indent2 = ET.SubElement(indent1, 'iwxxm:AerodromeRunwayState')
            indent2.set('allRunways', 'false')
            #
            # Attributes set first
            if len(token['runway']) == 0 or token['runway'] == '88':
                indent2.set('allRunways', 'true')

            if token['runway'] == '99':
                indent2.set('fromPreviousReport', 'true')

            if token['state'][:4] == 'CLRD':
                indent2.set('cleared', 'true')
            #
            # Runway direction
            if indent2.get('allRunways') == 'false':
                indent3 = ET.SubElement(indent2, 'iwxxm:runway')
                if token['runway'] == '99':
                    indent3.set('nilReason', self.codes[des.NIL][des.NA][0])
                else:
                    self.runwayDirection(indent3, token['runway'])
            #
            # Runway deposits
            if token['state'][0].isdigit():
                indent3 = ET.SubElement(indent2, 'iwxxm:depositType')
                uri, title = self.codes[des.RWYDEPST][token['state'][0]]
                indent3.set('xlink:href', uri)
                if (des.TITLES & des.RunwayDeposit):
                    indent3.set('xlink:title', title)
            #
            # Runway contaminates
            if token['state'][1].isdigit():
                indent3 = ET.SubElement(indent2, 'iwxxm:contamination')
                try:
                    uri, title = self.codes[des.RWYCNTMS][token['state'][1]]
                except KeyError:
                    uri, title = self.codes[des.RWYCNTMS]['15']

                indent3.set('xlink:href', uri)
                if (des.TITLES & des.AffectedRunwayCoverage):
                    indent3.set('xlink:title', title)
            #
            # Depth of deposits
            indent3 = ET.Element('iwxxm:depthOfDeposit')
            depth = token['state'][2:4]
            if depth.isdigit():
                if depth != '99':
                    indent3.set('uom', 'mm')
                    indent3.text = self._RunwayDepositDepths.get(depth, depth)
                else:
                    indent3.set('uom', 'N/A')
                    indent3.set('xsi:nil', 'true')
                    indent3.set('nilReason', self.codes[des.NIL][des.UNKNWN][0])

                indent2.append(indent3)

            elif depth == '//':
                indent3.set('uom', 'N/A')
                indent3.set('xsi:nil', 'true')
                indent3.set('nilReason', self.codes[des.NIL][des.NOOPRSIG][0])
                indent2.append(indent3)
            #
            # Runway friction
            friction = token['state'][4:6]
            if friction.isdigit():
                #
                # Remove leading zeros
                friction = str(int(friction))
                indent3 = ET.SubElement(indent2, 'iwxxm:estimatedSurfaceFrictionOrBrakingAction')
                uri, ignored = self.codes[des.RWYFRCTN][friction]
                indent3.set('xlink:href', uri)
                if (des.TITLES & des.RunwayFriction):
                    title = des.RunwayFrictionValues.get(friction, 'Friction coefficient: %.2f' %
                                                         (int(friction) * 0.01))
                    indent3.set('xlink:title', title)

    def runwayDirection(self, parent, rwy):

        uuid = self.runwayDirectionCache.get(rwy, deu.getUUID())
        if uuid[0] == '#':
            parent.set('xlink:href', uuid)
            return

        self.runwayDirectionCache[rwy] = '#%s' % uuid
        indent = ET.SubElement(parent, 'aixm:RunwayDirection')
        indent.set('gml:id', uuid)
        indent1 = ET.SubElement(indent, 'aixm:timeSlice')
        indent2 = ET.SubElement(indent1, 'aixm:RunwayDirectionTimeSlice')
        indent2.set('gml:id', deu.getUUID())
        indent3 = ET.SubElement(indent2, 'gml:validTime')
        indent3 = ET.SubElement(indent2, 'aixm:interpretation')
        indent3.text = 'SNAPSHOT'
        indent3 = ET.SubElement(indent2, 'aixm:designator')
        if rwy == '//':
            indent3.set('nilReason', 'missing')
            indent3.set('xsi:nil', 'true')
        else:
            indent3.text = rwy
