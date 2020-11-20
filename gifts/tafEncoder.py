#
# tafEncoder.py
#
# Purpose: Encodes a python dictionary consisting of TAF components into a XML
#          document according to the IWXXM 3.0 schema.
#
# Author: Mark Oberfield - MDL/OSTI/NWS/NOAA
#
import logging
import sys
import re
import time
import xml.etree.ElementTree as ET

from .common import Common
from .common import xmlConfig as des
from .common import xmlUtilities as deu

__python_version__ = sys.version_info[0]


class Encoder(Common.Base):

    def __init__(self):
        #
        # Initialize the base class
        super(Encoder, self).__init__()

        self._Logger = logging.getLogger(__name__)

        self._re_cloudLyr = re.compile(r'(?P<AMT>VV|FEW|SCT|BKN|OVC)(?P<HGT>\d{3})?')
        #
        self._changeIndicator = {'BECMG': 'BECOMING', 'TEMPO': 'TEMPORARY_FLUCTUATIONS', 'PROB30': 'PROBABILITY_30',
                                 'PROB40': 'PROBABILITY_40', 'PROB30 TEMPO': 'PROBABILITY_30_TEMPORARY_FLUCTUATIONS',
                                 'PROB40 TEMPO': 'PROBABILITY_40_TEMPORARY_FLUCTUATIONS'}

        self._bbbCodes = {'A': 'AMENDMENT', 'C': 'CORRECTION'}
        #
        # Populate the precipitation/obstruction and other phenomenon dictionary
        #
        # Create dictionaries of the following WMO codes
        neededCodes = [des.CLDAMTS, des.CVCTNCLDS, des.WEATHER]
        try:
            self.codes = deu.parseCodeRegistryTables(des.CodesFilePath, neededCodes, des.PreferredLanguageForTitles)
        except AssertionError as msg:  # pragma: no cover
            self._Logger.warning(msg)

        setattr(self, 'obv', self.pcp)

    def __call__(self, decodedTaf, tac):
        #
        decodingError = 'err_msg' in decodedTaf
        self.decodedTAC = decodedTaf
        self.tacString = tac
        self.nilPresent = False
        self.canceled = False
        #
        # Root element
        self.XMLDocument = ET.Element('iwxxm:TAF')
        #
        for prefix, uri in self.NameSpaces.items():
            if prefix == '':
                self.XMLDocument.set('xmlns', uri)
            else:
                self.XMLDocument.set('xmlns:%s' % prefix, uri)

        self.XMLDocument.set('xsi:schemaLocation', '%s %s' % (des.IWXXM_URI, des.IWXXM_URL))
        try:
            self.XMLDocument.set('reportStatus', self._bbbCodes.get(self.decodedTAC['bbb'][0], 'NORMAL'))
        except IndexError:
            self.XMLDocument.set('reportStatus', 'NORMAL')
        #
        # NIL'd and Cancelled TAFs are recorded in 'state'
        if not decodingError:
            try:
                state = self.decodedTAC['state']
                if state == 'nil':
                    self.nilPresent = True
                elif state == 'canceled':
                    self.canceled = True
                    self.XMLDocument.set('isCancelReport', 'true')

            except KeyError:
                pass

        self.XMLDocument.set('permissibleUsage', 'OPERATIONAL')
        #
        # Additional attributes for root element
        if des.TRANSLATOR:
            #
            self.XMLDocument.set('translationCentreName', des.TranslationCentreName)
            self.XMLDocument.set('translationCentreDesignator', des.TranslationCentreDesignator)
            self.XMLDocument.set('translationTime', self.decodedTAC['translationTime'])
            self.XMLDocument.set('translatedBulletinReceptionTime', self.decodedTAC['translatedBulletinReceptionTime'])
            self.XMLDocument.set('translatedBulletinID', self.decodedTAC['translatedBulletinID'])
            #
            # If there was a decoding problem
            if decodingError:

                self.XMLDocument.set('translationFailedTAC', self.tacString)
                # self.XMLDocument.set('permissibleUsageSupplementary', self.decodedTAC['err_msg'])

        self.XMLDocument.set('gml:id', deu.getUUID())
        self.itime(self.XMLDocument, self.decodedTAC.get('itime', None))
        self.aerodrome(self.XMLDocument, self.decodedTAC.get('ident', None))

        if self.canceled:
            self.vtime(ET.SubElement(self.XMLDocument, 'iwxxm:cancelledReportValidPeriod'), self.decodedTAC['vtime'])
            return self.XMLDocument

        try:
            self.vtime(ET.SubElement(self.XMLDocument, 'iwxxm:validPeriod'), self.decodedTAC['vtime'])
            self.entireValidTimeID = self.validTimeID
        #
        # No valid time for NIL TAF
        except KeyError:
            if self.nilPresent:
                if __python_version__ == 3:
                    killChild = self.XMLDocument.find('iwxxm:validPeriod')
                    self.XMLDocument.remove(killChild)
                else:
                    self.XMLDocument._children.pop()
        #
        # No additional information in the TAC TAF shall be provided in XML when there's a decoding error
        if decodingError:
            return self.XMLDocument
        #
        # Otherwise, fill out the XML document
        try:
            try:
                base = self.decodedTAC['group'].pop(0)
                self.baseFcst(self.XMLDocument, base['prevailing'])
                self.changeGroup(self.XMLDocument, base['ocnl'])

            except (IndexError, KeyError):
                pass
            #
            # Now the rest of the forecast "evolves" from the initial condition
            for group in self.decodedTAC['group']:
                self.changeGroup(self.XMLDocument, group['prevailing'])
                try:
                    self.changeGroup(self.XMLDocument, group['ocnl'])
                except KeyError:
                    pass

        except Exception:
            self._Logger.exception(self.tacString)

        return self.XMLDocument

    def itime(self, parent, token):

        indent1 = ET.SubElement(parent, 'iwxxm:issueTime')
        if token is None:
            return

        indent2 = ET.SubElement(indent1, 'gml:TimeInstant')
        indent2.set('gml:id', deu.getUUID())
        indent3 = ET.SubElement(indent2, 'gml:timePosition')
        indent3.text = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(token['value']))

    def vtime(self, parent, token):

        indent = ET.SubElement(parent, 'gml:TimePeriod')
        indent.set('gml:id', deu.getUUID())

        indent1 = ET.SubElement(indent, 'gml:beginPosition')
        indent1.text = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(token['from']))
        indent1 = ET.SubElement(indent, 'gml:endPosition')
        indent1.text = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(token['to']))

        self.validTimeID = '#%s' % indent.get('gml:id')

    def baseFcst(self, parent, token):

        indent = ET.SubElement(parent, 'iwxxm:baseForecast')
        if self.nilPresent:
            indent.set('nilReason', self.codes[des.NIL][des.MSSG][0])
            return

        indent1 = ET.SubElement(indent, 'iwxxm:MeteorologicalAerodromeForecast')
        indent2 = ET.SubElement(indent1, 'iwxxm:phenomenonTime')
        indent2.set('xlink:href', self.entireValidTimeID)
        #
        # Finally the "base" forecast
        self.result(indent1, token, True)

    def changeGroup(self, parent, fcsts):

        if isinstance(fcsts, dict):
            fcsts = [fcsts]

        for token in fcsts:
            indent = ET.SubElement(parent, 'iwxxm:changeForecast')
            indent1 = ET.SubElement(indent, 'iwxxm:MeteorologicalAerodromeForecast')
            self.vtime(ET.SubElement(indent1, 'iwxxm:phenomenonTime'), token['time'])
            self.result(indent1, token)

    def result(self, parent, token, baseFcst=False):

        parent.set('cloudAndVisibilityOK', token['cavok'])
        if token['cavok'] == 'true':
            self.ForecastResults = ['wind']
        else:
            self.ForecastResults = ['vsby', 'wind', 'pcp', 'obv', 'sky']

        if not baseFcst:
            if token['type'] == 'PROB':
                t = token['time']['str'].split()
                if t[1] == 'TEMPO':
                    changeToken = '%s TEMPO' % t[0]
                else:
                    changeToken = t[0]

                parent.set('changeIndicator', self._changeIndicator.get(changeToken, 'PROBABILITY_30'))
            else:
                parent.set('changeIndicator', self._changeIndicator.get(token['type'], 'FROM'))

        parent.set('gml:id', deu.getUUID())

        for element in self.ForecastResults:
            function = getattr(self, element)
            try:
                function(parent, token[element])
            except KeyError:
                pass

        if baseFcst:
            try:
                self.temps(parent, token['temps'])
            except KeyError:
                pass

    def wind(self, parent, token):

        indent = ET.SubElement(parent, 'iwxxm:surfaceWind')
        indent1 = ET.Element('iwxxm:AerodromeSurfaceWindForecast')
        if token['str'].startswith('VRB'):
            indent1.set('variableWindDirection', 'true')
        else:
            indent1.set('variableWindDirection', 'false')
            indent2 = ET.SubElement(indent1, 'iwxxm:meanWindDirection')
            indent2.text = token['dd']
            indent2.set('uom', 'deg')

        indent2 = ET.SubElement(indent1, 'iwxxm:meanWindSpeed')
        indent2.text = token['ff']
        indent2.set('uom', token['uom'])

        if 'ffplus' in token:

            indent2 = ET.SubElement(indent1, 'iwxxm:meanWindSpeedOperator')
            indent2.text = 'ABOVE'

        try:
            indent2 = ET.Element('iwxxm:windGustSpeed')
            indent2.text = token['gg']
            indent2.set('uom', token['uom'])
            indent1.append(indent2)
            if 'ggplus' in token:

                indent2 = ET.SubElement(indent1, 'iwxxm:windGustSpeedOperator')
                indent2.text = 'ABOVE'

        except (KeyError, ValueError):
            pass

        if len(indent1):
            indent.append(indent1)

    def vsby(self, parent, token):

        indent = ET.SubElement(parent, 'iwxxm:prevailingVisibility')
        indent.set('uom', token['uom'])
        indent.text = token['value']
        if token['value'] == '10000':
            indent = ET.SubElement(parent, 'iwxxm:prevailingVisibilityOperator')
            indent.text = 'ABOVE'

    def pcp(self, parent, token):
        for ww in token['str'].split():
            #
            # Search BUFR table
            try:
                indent = ET.SubElement(parent, 'iwxxm:weather')
                uri, title = self.codes[des.WEATHER][ww]
                indent.set('xlink:href', uri)
                if (des.TITLES & des.Weather):
                    indent.set('xlink:title', title)
            #
            # Weather phenomenon token not matched
            except KeyError:
                if ww == 'NSW':
                    indent.set('nilReason', self.codes[des.NIL][des.NOOPRSIG][0])
                else:
                    indent.set('nilReason', self.codes[des.NIL][des.UNKNWN][0])

    def sky(self, parent, token):

        indent = ET.SubElement(parent, 'iwxxm:cloud')
        for numberLyr, layer in enumerate(token['str'].split()):
            if layer[:2] == 'VV':

                indent1 = ET.SubElement(indent, 'iwxxm:AerodromeCloudForecast')
                indent1.set('gml:id', deu.getUUID())
                indent2 = ET.SubElement(indent1, 'iwxxm:verticalVisibility')

                try:
                    height = int(layer[2:]) * 100
                    indent2.text = str(height)
                    indent2.set('uom', '[ft_i]')

                except ValueError:
                    indent2.set('uom', 'N/A')
                    indent2.set('nilReason', self.codes[des.NIL][des.MSSG][0])
                    indent2.set('xsi:nil', 'true')

            elif layer == 'NSC':
                indent.set('nilReason', self.codes[des.NIL][des.NOOPRSIG][0])

            else:
                if numberLyr == 0:
                    indent1 = ET.SubElement(indent, 'iwxxm:AerodromeCloudForecast')
                    indent1.set('gml:id', deu.getUUID())

                self.doCloudLayer(indent1, layer)

    def doCloudLayer(self, parent, layer):

        indent = ET.SubElement(parent, 'iwxxm:layer')
        indent1 = ET.SubElement(indent, 'iwxxm:CloudLayer')
        desc = self._re_cloudLyr.match(layer)

        amount = desc.group('AMT')
        indent2 = ET.SubElement(indent1, 'iwxxm:amount')
        uri, title = self.codes[des.CLDAMTS][amount]
        indent2.set('xlink:href', uri)
        if (des.TITLES & des.CloudAmt):
            indent2.set('xlink:title', title)

        indent2 = ET.SubElement(indent1, 'iwxxm:base')
        indent2.set('uom', '[ft_i]')
        height = int(desc.group('HGT')) * 100
        indent2.text = str(height)

        if layer.endswith('CB'):
            indent2 = ET.SubElement(indent1, 'iwxxm:cloudType')
            uri, title = self.codes[des.CVCTNCLDS]['CB']
            indent2.set('xlink:href', uri)
            if (des.TITLES & des.CloudType):
                indent2.set('xlink:title', title)

        if layer.endswith('TCU'):
            indent2 = ET.SubElement(indent1, 'iwxxm:cloudType')
            uri, title = self.codes[des.CVCTNCLDS]['TCU']
            indent2.set('xlink:href', uri)
            if (des.TITLES & des.CloudType):
                indent2.set('xlink:title', title)

    def temps(self, parent, token):

        for maxTemp, minTemp in zip(token['max'], token['min']):

            indent = ET.SubElement(parent, 'iwxxm:temperature')
            indent1 = ET.SubElement(indent, 'iwxxm:AerodromeAirTemperatureForecast')

            elementName = 'iwxxm:maximumAirTemperature'
            for xTemp in [maxTemp, minTemp]:

                value = ET.SubElement(indent1, elementName)
                value.text = str(xTemp['value'])
                value.set('uom', 'Cel')

                timeStamp = ET.SubElement(indent1, '%sTime' % elementName)
                timeStamp1 = ET.SubElement(timeStamp, 'gml:TimeInstant')
                timeStamp1.set('gml:id', deu.getUUID())
                timeStamp2 = ET.SubElement(timeStamp1, 'gml:timePosition')
                timeStamp2.text = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(xTemp['at']))

                elementName = 'iwxxm:minimumAirTemperature'
