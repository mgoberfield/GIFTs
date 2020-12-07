#
# Name: vaaEncoder.py
# Purpose: To encode Volcanic Ash Advisory information in IWXXM 3.0 XML format.
#
# Author: Mark Oberfield
# Organization: NOAA/NWS/OSTI/Meteorological Development Laboratory
# Contact Info: Mark.Oberfield@noaa.gov
#
import logging
import xml.etree.ElementTree as ET

from .common import xmlConfig as des
from .common import xmlUtilities as deu


class Encoder:
    def __init__(self):
        #
        self._Logger = logging.getLogger(__name__)
        self.NameSpaces = {'aixm': 'http://www.aixm.aero/schema/5.1.1',
                           'gml': 'http://www.opengis.net/gml/3.2',
                           '': des.IWXXM_URI,
                           'xlink': 'http://www.w3.org/1999/xlink',
                           'xsi': 'http://www.w3.org/2001/XMLSchema-instance'}
        #
        # Create dictionaries of the following WMO codes
        neededCodes = [des.COLOUR_CODES]
        try:
            self.codes = deu.parseCodeRegistryTables(des.CodesFilePath, neededCodes, des.PreferredLanguageForTitles)
        except AssertionError as msg:  # pragma: no cover
            self._Logger.warning(msg)

    def __call__(self, decodedVAA, tac):
        #
        self.decodedTAC = decodedVAA
        self.tacString = tac
        self.XMLDocument = None
        self.nilPresent = False

        try:
            self.preamble()
            if not self.nilPresent:
                self.observations()
                self.postContent()

        except Exception:
            self._Logger.exception(tac)

        return self.XMLDocument

    def preamble(self):
        #
        # The root element created here
        self.XMLDocument = ET.Element('VolcanicAshAdvisory')
        #
        for prefix, uri in self.NameSpaces.items():
            if prefix == '':
                self.XMLDocument.set('xmlns', uri)
            else:
                self.XMLDocument.set('xmlns:%s' % prefix, uri)
        #
        self.XMLDocument.set('xsi:schemaLocation', '%s %s' % (des.IWXXM_URI, des.IWXXM_URL))
        #
        # Set its many attributes
        if 'status' in self.decodedTAC:
            self.XMLDocument.set('permissibleUsage', 'NON-OPERATIONAL')
            if self.decodedTAC['status'] == 'TEST':
                self.XMLDocument.set('permissibleUsageReason', 'TEST')
            else:
                self.XMLDocument.set('permissibleUsageReason', 'EXERCISE')
        else:
            self.XMLDocument.set('permissibleUsage', 'OPERATIONAL')
        #
        # bbb code
        self.XMLDocument.set('reportStatus', {'A': 'AMENDMENT', 'C': 'CORRECTION'}.get(
            self.decodedTAC['bbb'], 'NORMAL'))
        #
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
                self.nilPresent = True

        self.XMLDocument.set('gml:id', deu.getUUID())
        #
        # For translation failed messages, no operational content shall be provided in XML
        if self.nilPresent:

            self.issueTime(self.XMLDocument, None)
            self.vaac(self.XMLDocument, None)

        else:
            self.issueTime(self.XMLDocument, self.decodedTAC.get('issueTime', None))
            self.vaac(self.XMLDocument, self.decodedTAC.get('centre', None))

        if not self.nilPresent:
            if 'issueTime' not in self.decodedTAC and self.decodedTAC['status'] == 'TEST':
                self.nilPresent = True

        if self.nilPresent:
            return

        self.volcano(self.XMLDocument)
        #
        child = ET.SubElement(self.XMLDocument, 'stateOrRegion')
        if 'UNKNOWN' not in self.decodedTAC['region']:
            child.text = self.decodedTAC['region']
        else:
            child.set('nilReason', self.codes[des.NIL][des.UNKNWN][0])

        child = ET.SubElement(self.XMLDocument, 'summitElevation')
        if self.decodedTAC['summit']['elevation'].isdigit():
            child.text = self.decodedTAC['summit']['elevation']
            child.set('uom', self.decodedTAC['summit']['uom'])

        elif 'SFC' in self.decodedTAC['summit']['elevation']:
            child.set('nilReason', self.codes[des.NIL][des.NA][0])
        else:
            child.set('nilReason', self.codes[des.NIL][des.UNKNWN][0])

        child = ET.SubElement(self.XMLDocument, 'advisoryNumber')
        child.text = self.decodedTAC['advisoryNumber']

        child = ET.SubElement(self.XMLDocument, 'informationSource')
        child.text = self.decodedTAC['sources']
        #
        try:
            child = ET.Element('colourCode')
            if 'GIVEN' in self.decodedTAC['colourCode']:
                child.set('nilReason', self.codes[des.NIL][des.WTHLD][0])
            elif self.decodedTAC['colourCode'] == 'UNKNOWN':
                child.set('nilReason', self.codes[des.NIL][des.UNKNWN][0])
            elif self.decodedTAC['colourCode'] == 'NIL':
                child.set('nilReason', self.codes[des.NIL][des.MSSG][0])
            else:
                child.set('xlink:href', self.codes[des.COLOUR_CODES][self.decodedTAC['colourCode']][0])

            self.XMLDocument.append(child)

        except KeyError:
            pass

        child = ET.SubElement(self.XMLDocument, 'eruptionDetails')
        if 'UNKNOWN' in self.decodedTAC['details']:
            child.set('nilReason', self.codes[des.NIL][des.UNKNWN][0])
        else:
            child.text = self.decodedTAC['details']

    def issueTime(self, parent, timeStamp):

        indent = ET.SubElement(parent, 'issueTime')
        if timeStamp is None:
            return

        indent1 = ET.SubElement(indent, 'gml:TimeInstant')
        indent1.set('gml:id', deu.getUUID())
        indent2 = ET.SubElement(indent1, 'gml:timePosition')
        indent2.text = timeStamp['str']

    def vaac(self, parent, centre):

        indent = ET.SubElement(parent, 'issuingVolcanicAshAdvisoryCentre')
        if centre is None:
            return

        indent1 = ET.SubElement(indent, 'Unit')
        indent1.set('gml:id', deu.getUUID())
        indent1.set('xmlns', self.NameSpaces['aixm'])
        self._vaacUUID = '#%s' % indent1.get('gml:id')

        indent2 = ET.SubElement(indent1, 'timeSlice')
        indent3 = ET.SubElement(indent2, 'UnitTimeSlice')
        indent3.set('gml:id', deu.getUUID())
        indent4 = ET.SubElement(indent3, 'gml:validTime')
        indent4 = ET.SubElement(indent3, 'interpretation')
        indent4.text = 'SNAPSHOT'
        indent4 = ET.SubElement(indent3, 'name')
        indent4.text = centre
        indent4 = ET.SubElement(indent3, 'type')
        indent4.text = 'OTHER:VAAC'

    def volcano(self, parent):

        indent = ET.SubElement(parent, 'volcano')
        indent1 = ET.SubElement(indent, 'EruptingVolcano')
        indent1.set('xmlns', 'http://def.wmo.int/metce/2013')
        indent1.set('gml:id', deu.getUUID())

        indent2 = ET.SubElement(indent1, 'name')
        indent2.text = self.decodedTAC['volcanoName']

        indent2 = ET.SubElement(indent1, 'position')
        if 'UNKNOWN' in self.decodedTAC['volcanoLocation']:
            indent2.set('nilReason', self.codes[des.NIL][des.UNKNWN][0])
        else:
            indent3 = ET.SubElement(indent2, 'gml:Point')
            indent3.set('axisLabels', des.axisLabels)
            indent3.set('srsName', des.srsName)
            indent3.set('srsDimension', des.srsDimension)
            indent3.set('gml:id', deu.getUUID())
            indent4 = ET.SubElement(indent3, 'gml:pos')
            indent4.text = self.decodedTAC['volcanoLocation']

        indent2 = ET.SubElement(indent1, 'eruptionDate')
        try:
            indent2.text = self.decodedTAC['eruptionDate']
        except KeyError:
            indent2.text = self.decodedTAC['issueTime']['str']

    def observations(self):
        #
        # Order the forecast hours
        fhrs = list(self.decodedTAC['clouds'].keys())
        fhrs.sort(key=int)
        for fhr in fhrs:
            try:
                self.forecast(self.XMLDocument, self.decodedTAC['clouds'][fhr]['cldLyrs'], fhr)
            except Exception:
                self._Logger.exception(self.tacString)

    def observed(self, parent, layers):

        indent = ET.SubElement(parent, 'observation')
        indent1 = ET.SubElement(indent, 'VolcanicAshObservedOrEstimatedConditions')
        if 'nil' in layers[0]:
            indent1.set('status', 'NOT_IDENTIFIABLE')
        else:
            indent1.set('status', 'IDENTIFIABLE')

        indent1.set('isEstimated', str(self.decodedTAC.get('estimated', 'false')).lower())
        indent1.set('gml:id', deu.getUUID())

        self.itime(indent1, self.decodedTAC['clouds']['0']['dtg'])
        if indent1.get('status') == 'IDENTIFIABLE':
            self.doAshClouds(indent1, 'VolcanicAshCloudObservedOrEstimated', layers)
        else:
            self.doWindInLayers(indent1, [x['movement'] for x in layers])

    def doWindInLayers(self, parent, layers):

        for lyr in layers:
            indent1 = ET.SubElement(parent, 'wind')
            indent2 = ET.SubElement(indent1, 'WindObservedOrEstimated')
            indent2.set('gml:id', deu.getUUID())
            indent3 = ET.SubElement(indent2, 'verticalLayer')
            indent4 = ET.SubElement(indent3, 'aixm:AirspaceLayer')
            indent4.set('gml:id', deu.getUUID())
            indent5 = ET.SubElement(indent4, 'aixm:upperLimit')
            indent5.set('uom', 'FL')
            if lyr['top'] is not None:
                indent5.text = lyr['top']
            else:
                indent5.text = lyr['bottom']

            indent5 = ET.SubElement(indent4, 'aixm:upperLimitReference')
            indent5.text = 'STD'

            indent5 = ET.SubElement(indent4, 'aixm:lowerLimit')
            try:
                indent5.text = '%03d' % int(lyr['bottom'])
                indent5.set('uom', 'FL')
                indent5 = ET.SubElement(indent4, 'aixm:lowerLimitReference')
                indent5.text = 'STD'

            except ValueError:
                indent5.text = 'GND'
                indent5 = ET.SubElement(indent4, 'aixm:lowerLimitReference')
                indent5.text = 'SFC'

            if 'VRB' in lyr['dir']:
                indent2.set('variableWindDirection', 'true')
            else:
                indent2.set('variableWindDirection', 'false')
                indent3 = ET.Element('windDirection')
                indent3.text = lyr['dir']
                indent3.set('uom', 'deg')
                indent2.append(indent3)

            indent3 = ET.Element('windSpeed')
            indent3.text = lyr['spd']
            indent3.set('uom', lyr['uom'])
            indent2.append(indent3)

    def forecast(self, parent, layers, fhr):

        if fhr == '0':
            self.observed(parent, layers)
            return

        indent = ET.SubElement(parent, 'forecast')
        indent1 = ET.SubElement(indent, 'VolcanicAshForecastConditions')
        indent1.set('gml:id', deu.getUUID())
        if 'nil' in layers[0]:
            nilType = layers[0]['nil']
            if nilType == 'noashexp':
                indent1.set('status', 'NO_VOLCANIC_ASH_EXPECTED')
            elif nilType == 'notavbl':
                indent1.set('status', 'NOT_AVAILABLE')
            elif nilType == 'notprvd':
                indent1.set('status', 'NOT_PROVIDED')
        else:
            indent1.set('status', 'PROVIDED')

        self.itime(indent1, self.decodedTAC['clouds'][fhr]['dtg'])
        if indent1.get('status') != 'PROVIDED':
            return

        self.doAshClouds(indent1, 'VolcanicAshCloudForecast', layers)

    def doAshClouds(self, parent, elementName, layers):

        for lyr in layers:
            indent1 = ET.SubElement(parent, 'ashCloud')
            indent2 = ET.SubElement(indent1, elementName)
            indent2.set('gml:id', deu.getUUID())
            indent3 = ET.SubElement(indent2, 'ashCloudExtent')
            self.airspaceVolume(indent3, lyr)

            try:
                indent3 = ET.Element('directionOfMotion')
                indent3.text = lyr['movement']['dir']
                indent3.set('uom', 'deg')
                indent2.append(indent3)

                indent3 = ET.Element('speedOfMotion')
                indent3.text = lyr['movement']['spd']
                indent3.set('uom', lyr['movement']['uom'])
                indent2.append(indent3)

            except KeyError:
                pass

    def itime(self, parent, dtg):

        indent = ET.SubElement(parent, 'phenomenonTime')
        indent1 = ET.SubElement(indent, 'gml:TimeInstant')
        indent1.set('gml:id', deu.getUUID())
        indent2 = ET.SubElement(indent1, 'gml:timePosition')
        indent2.text = dtg

    def airspaceVolume(self, parent, lyr):

        indent1 = ET.SubElement(parent, 'aixm:AirspaceVolume')
        indent1.set('gml:id', deu.getUUID())
        indent2 = ET.SubElement(indent1, 'aixm:upperLimit')
        indent2.set('uom', 'FL')
        indent2.text = lyr['top']
        indent2 = ET.SubElement(indent1, 'aixm:upperLimitReference')
        indent2.text = 'STD'

        indent2 = ET.SubElement(indent1, 'aixm:lowerLimit')
        try:
            indent2.text = '%03d' % int(lyr['bottom'])
            indent2.set('uom', 'FL')
            indent2 = ET.SubElement(indent1, 'aixm:lowerLimitReference')
            indent2.text = 'STD'

        except ValueError:
            indent2.text = 'GND'
            indent2 = ET.SubElement(indent1, 'aixm:lowerLimitReference')
            indent2.text = 'SFC'

        except TypeError:
            indent2.set('nilReason', des.MSSG)
            indent2.set('xsi:nil', 'true')

        if 'pnts' in lyr:

            indent2 = ET.SubElement(indent1, 'aixm:horizontalProjection')
            indent3 = ET.SubElement(indent2, 'aixm:Surface')
            indent3.set('gml:id', deu.getUUID())
            indent3.set('axisLabels', des.axisLabels)
            indent3.set('srsName', des.srsName)
            indent3.set('srsDimension', des.srsDimension)

            indent4 = ET.SubElement(indent3, 'gml:patches')
            indent5 = ET.SubElement(indent4, 'gml:PolygonPatch')
            indent6 = ET.SubElement(indent5, 'gml:exterior')
            indent7 = ET.SubElement(indent6, 'gml:LinearRing')
            indent8 = ET.SubElement(indent7, 'gml:posList')
            indent8.set('count', str(len(lyr['pnts'])))
            indent8.text = ' '.join(lyr['pnts'])

    def postContent(self):

        indent = ET.SubElement(self.XMLDocument, 'remarks')
        if self.decodedTAC['remarks']  == 'NIL':
            indent.set('nilReason', self.codes[des.NIL][des.NA][0])
        else:
            indent.text = self.decodedTAC['remarks']

        indent = ET.SubElement(self.XMLDocument, 'nextAdvisoryTime')
        try:
            indent2 = ET.Element('gml:timePosition')
            indent2.text = self.decodedTAC['nextdtg']['str']

            indent1 = ET.SubElement(indent, 'gml:TimeInstant')
            indent1.set('gml:id', deu.getUUID())
            indent1.append(indent2)

            if self.decodedTAC['nextdtg']['cnd'] == 'nst':
                indent2.set('indeterminatePosition', 'before')
            elif self.decodedTAC['nextdtg']['cnd'] == 'nlt':
                indent2.set('indeterminatePosition', 'before')

        except KeyError:
            indent.set('nilReason', self.codes[des.NIL][des.NA][0])
