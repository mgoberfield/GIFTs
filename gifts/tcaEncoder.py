#
# Name: tcaEncoder.py
# Purpose: To encode Tropical Cyclone Advisory information in IWXXM 3.0 XML format.
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

        self._Logger = logging.getLogger(__name__)
        self.NameSpaces = {'aixm': 'http://www.aixm.aero/schema/5.1.1',
                           'gml': 'http://www.opengis.net/gml/3.2',
                           '': des.IWXXM_URI,
                           'xlink': 'http://www.w3.org/1999/xlink',
                           'xsi': 'http://www.w3.org/2001/XMLSchema-instance'}
        #
        # Create dictionaries of the following WMO codes
        neededCodes = [des.NIL]
        try:
            self.codes = deu.parseCodeRegistryTables(des.CodesFilePath, neededCodes, des.PreferredLanguageForTitles)
        except AssertionError as msg:  # pragma: no cover
            self._Logger.warning(msg)

    def __call__(self, decodedTCA, tac):

        self.decodedTAC = decodedTCA
        self.tacString = tac
        self.XMLDocument = None
        self.nilPresent = False
        try:
            self.preamble()
            self.observations()
            self.postContent()

        except Exception:
            self._Logger.exception(tac)

        return self.XMLDocument

    def preamble(self):

        self.XMLDocument = ET.Element('TropicalCycloneAdvisory')
        #
        for prefix, uri in list(self.NameSpaces.items()):
            if prefix == '':
                self.XMLDocument.set('xmlns', uri)
            else:
                self.XMLDocument.set('xmlns:%s' % prefix, uri)
        #
        self.XMLDocument.set('xsi:schemaLocation', '%s %s' % (des.IWXXM_URI, des.IWXXM_URL))
        #
        # Set the root attributes
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

            if 'err_msg' in self.decodedTAC:

                self.XMLDocument.set('translationFailedTAC', ' '.join(self.tacString.split()))
                # self.XMLDocument.set('permissibleUsageSupplementary', self.decodedTAC.get('err_msg'))
                self.nilPresent = True

        self.XMLDocument.set('gml:id', deu.getUUID())
        #
        # For translation failed messages, no operational content shall be provided in XML
        if self.nilPresent:

            self.issueTime(self.XMLDocument, None)
            self.tcac(self.XMLDocument, None)

        else:
            self.issueTime(self.XMLDocument, self.decodedTAC.get('issueTime', None))
            self.tcac(self.XMLDocument, self.decodedTAC.get('centre', None))

        if not self.nilPresent:
            if 'issueTime' not in self.decodedTAC and self.decodedTAC['status'] == 'TEST':
                self.nilPresent = True

        if self.nilPresent:
            return

        child = ET.SubElement(self.XMLDocument, 'tropicalCycloneName')
        indent1 = ET.SubElement(child, 'TropicalCyclone')
        indent1.set('xmlns', 'http://def.wmo.int/metce/2013')
        indent1.set('gml:id', deu.getUUID())
        indent2 = ET.SubElement(indent1, 'name')
        indent2.text = self.decodedTAC['cycloneName']
        #
        child = ET.SubElement(self.XMLDocument, 'advisoryNumber')
        child.text = self.decodedTAC['advisoryNumber']

    def issueTime(self, parent, timeStamp):

        indent = ET.SubElement(parent, 'issueTime')
        if timeStamp is None:
            return

        indent1 = ET.SubElement(indent, 'gml:TimeInstant')
        indent1.set('gml:id', deu.getUUID())
        indent2 = ET.SubElement(indent1, 'gml:timePosition')
        indent2.text = timeStamp['str']

    def tcac(self, parent, centre):

        indent = ET.SubElement(parent, 'issuingTropicalCycloneAdvisoryCentre')
        if centre is None:
            return

        indent1 = ET.SubElement(indent, 'aixm:Unit')
        indent1.set('gml:id', deu.getUUID())

        indent2 = ET.SubElement(indent1, 'aixm:timeSlice')
        indent3 = ET.SubElement(indent2, 'aixm:UnitTimeSlice')
        indent3.set('gml:id', deu.getUUID())
        indent4 = ET.SubElement(indent3, 'gml:validTime')
        indent4 = ET.SubElement(indent3, 'aixm:interpretation')
        indent4.text = 'SNAPSHOT'
        indent4 = ET.SubElement(indent3, 'aixm:type')
        indent4.text = 'OTHER:TCAC'
        indent4 = ET.SubElement(indent3, 'aixm:designator')
        indent4.text = centre

    def observations(self):
        #
        # Order the forecast hours
        fhrs = list(self.decodedTAC['fcst'].keys())
        fhrs.sort(key=int)
        #
        for fhr in fhrs:
            try:
                self.result(self.XMLDocument, self.decodedTAC['fcst'][fhr], fhr)
            except Exception:
                self._Logger.exception(self.tacString)

    def result(self, parent, token, fhr):

        if fhr == '0':
            self.doObservedConditions(ET.SubElement(parent, 'observation'), token)
        else:
            indent = ET.SubElement(parent, 'forecast')
            if 'windSpeed' in token:

                indent1 = ET.Element('TropicalCycloneForecastConditions')
                indent1.set('gml:id', deu.getUUID())
                self.itime(indent1, token['dtg'])
                self.cyclonePosition(indent1, token)

                indent2 = ET.SubElement(indent1, 'maximumSurfaceWindSpeed')
                indent2.set('uom', token['windSpeed']['uom'])
                indent2.text = token['windSpeed']['value']
                indent.append(indent1)

            else:
                indent.set('nilReason', self.codes[des.NIL][des.NOOPRSIG][0])

    def itime(self, parent, dtg):

        indent = ET.SubElement(parent, 'phenomenonTime')
        indent1 = ET.SubElement(indent, 'gml:TimeInstant')
        indent1.set('gml:id', deu.getUUID())
        indent2 = ET.SubElement(indent1, 'gml:timePosition')
        indent2.text = dtg

    def cyclonePosition(self, parent, token):

        indent = ET.SubElement(parent, 'tropicalCyclonePosition')
        if 'position' in token:

            indent1 = ET.SubElement(indent, 'gml:Point')
            indent1.set('gml:id', deu.getUUID())
            indent1.set('axisLabels', des.axisLabels)
            indent1.set('srsName', des.srsName)
            indent1.set('srsDimension', des.srsDimension)
            indent2 = ET.SubElement(indent1, 'gml:pos')
            indent2.text = token['position']

        else:
            indent.set('nilReason', self.codes[des.NIL][des.MSSG][0])

    def doObservedConditions(self, parent, token):

        indent = ET.SubElement(parent, 'TropicalCycloneObservedConditions')
        indent.set('gml:id', deu.getUUID())

        self.itime(indent, token['dtg'])
        self.cyclonePosition(indent, token)
        for cb in self.decodedTAC['cbclouds']:
            indent1 = ET.SubElement(indent, 'cumulonimbusCloudLocation')
            self.airspaceVolume(indent1, cb)

        indent1 = ET.SubElement(indent, 'movement')
        if 'movement' not in token:
            indent1.text = 'STATIONARY'
        else:
            indent1.text = 'MOVING'
            indent1 = ET.SubElement(indent, 'movementDirection')
            indent1.text = token['movement']['dir']
            indent1.set('uom', 'deg')

            indent1 = ET.SubElement(indent, 'movementSpeed')
            indent1.text = token['movement']['spd']
            indent1.set('uom', token['movement']['uom'])

        indent1 = ET.SubElement(indent, 'centralPressure')
        indent1.text = self.decodedTAC['minimumPressure']['value']
        indent1.set('uom', self.decodedTAC['minimumPressure']['uom'])

        indent1 = ET.SubElement(indent, 'maximumSurfaceWindSpeed')
        indent1.text = token['windSpeed']['value']
        indent1.set('uom', token['windSpeed']['uom'])

    def airspaceVolume(self, parent, token):

        indent1 = ET.SubElement(parent, 'aixm:AirspaceVolume')
        indent1.set('gml:id', deu.getUUID())
        indent2 = ET.SubElement(indent1, 'aixm:upperLimit')
        if token['top']['cnd'] == 'BLW':
            indent2.set('nilReason', 'unknown')
            indent2.set('xsi:nil', 'true')
        else:
            indent2.set('uom', 'FL')
            indent2.text = token['top']['lvl']

        indent2 = ET.SubElement(indent1, 'aixm:upperLimitReference')
        indent2.text = 'STD'

        if token['top']['cnd'] == 'BLW':
            indent2 = ET.SubElement(indent1, 'aixm:maximumLimit')
            indent2.set('uom', 'FL')
            indent2.text = token['top']['lvl']
        elif token['top']['cnd'] == 'ABV':
            indent2 = ET.SubElement(indent1, 'aixm:maximumLimit')
            indent2.set('nilReason', 'unknown')
            indent2.set('xsi:nil', 'true')
        else:
            indent2 = ET.SubElement(indent1, 'aixm:lowerLimit')
            indent2.set('uom', 'FL')
            indent2.text = token['top']['lvl']
            indent2 = ET.SubElement(indent1, 'aixm:lowerLimitReference')
            indent2.text = 'STD'

        indent2 = ET.SubElement(indent1, 'aixm:horizontalProjection')
        indent3 = ET.SubElement(indent2, 'aixm:Surface')
        indent3.set('gml:id', deu.getUUID())
        indent3.set('axisLabels', des.axisLabels)
        indent3.set('srsName', des.srsName)
        indent3.set('srsDimension', des.srsDimension)

        if token['type'] == 'polygon':
            indent4 = ET.SubElement(indent3, 'gml:polygonPatches')
            indent5 = ET.SubElement(indent4, 'gml:PolygonPatch')
            indent6 = ET.SubElement(indent5, 'gml:exterior')
            indent7 = ET.SubElement(indent6, 'gml:LinearRing')
            indent8 = ET.SubElement(indent7, 'gml:posList')
            indent8.set('count', str(len(token['pnts'])))
            indent8.text = ' '.join(token['pnts'])
        else:
            indent4 = ET.SubElement(indent3, 'polygonPatches')
            indent4.set('xmlns', self.NameSpaces['gml'])
            indent5 = ET.SubElement(indent4, 'PolygonPatch')
            indent6 = ET.SubElement(indent5, 'exterior')
            indent7 = ET.SubElement(indent6, 'Ring')
            indent8 = ET.SubElement(indent7, 'curveMember')
            indent9 = ET.SubElement(indent8, 'Curve')
            indent9.set('gml:id', deu.getUUID())
            indent10 = ET.SubElement(indent9, 'segments')
            indent11 = ET.SubElement(indent10, 'CircleByCenterPoint')
            indent11.set('numArc', '1')
            indent12 = ET.SubElement(indent11, 'pos')
            indent12.text = self.decodedTAC['fcst']['0']['position']
            indent12 = ET.SubElement(indent11, 'radius')
            indent12.text = token['radius']
            indent12.set('uom', token['uom'])

    def postContent(self):

        if self.nilPresent:
            return

        indent = ET.SubElement(self.XMLDocument, 'remarks')
        if self.decodedTAC['remarks'] == 'NIL':
            indent.set('nilReason', self.codes[des.NIL][des.NA][0])
        else:
            indent.text = self.decodedTAC['remarks']

        indent = ET.SubElement(self.XMLDocument, 'nextAdvisoryTime')
        try:
            indent1 = ET.Element('gml:TimeInstant')
            indent1.set('gml:id', deu.getUUID())
            indent2 = ET.SubElement(indent1, 'gml:timePosition')
            indent2.text = self.decodedTAC['nextdtg']['str']
            if self.decodedTAC['nextdtg']['before']:
                indent2.set('indeterminatePosition', 'before')
            indent.append(indent1)

        except KeyError:
            indent.set('nilReason', self.codes[des.NIL][des.NA][0])
