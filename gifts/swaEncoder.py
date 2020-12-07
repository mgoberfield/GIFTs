#
# Name: swaEncoder.py
# Purpose: To encode Space Weather Advisory information in IWXXM 3.0 XML format.
#
# Author: Mark Oberfield
# Organization: NOAA/NWS/OSTI/Meteorological Development Laboratory
# Contact Info: Mark.Oberfield@noaa.gov
#
import logging
import re
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

        self._fltLvls = re.compile(r'(ABV\s+FL(?P<abv>\d{3}))|(FL(?P<lwr>\d{3})\s*-\s*(FL)?(?P<upr>\d{3}))')
        #
        # Create dictionaries of the following WMO codes
        neededCodes = [des.SWX_PHENOMENA, des.SWX_LOCATION]
        try:
            self.codes = deu.parseCodeRegistryTables(des.CodesFilePath, neededCodes, des.PreferredLanguageForTitles)
        except AssertionError as msg:  # pragma: no cover
            self._Logger.warning(msg)

    def __call__(self, decodedSWA, tac):
        #
        self.decodedTAC = decodedSWA
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
        #
        self.XMLDocument = ET.Element('SpaceWeatherAdvisory')
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
            self.swac(self.XMLDocument, None)

        else:
            self.issueTime(self.XMLDocument, self.decodedTAC.get('issueTime', None))
            self.swac(self.XMLDocument, self.decodedTAC.get('centre', None))

        if not self.nilPresent:
            if 'issueTime' not in self.decodedTAC and self.decodedTAC['status'] == 'TEST':
                self.nilPresent = True

        if self.nilPresent:
            return

        child = ET.SubElement(self.XMLDocument, 'advisoryNumber')
        child.text = self.decodedTAC['advisoryNumber']
        try:
            child = ET.Element('replacedAdvisoryNumber')
            child.text = self.decodedTAC['replacedNumber']
            self.XMLDocument.append(child)

        except KeyError:
            pass
        #
        # Space Weather Hazards
        for hazard in self.decodedTAC['phenomenon']:

            child = ET.SubElement(self.XMLDocument, 'phenomenon')
            child.set('xlink:href', self.codes[des.SWX_PHENOMENA]['_'.join(hazard.split())][0])

    def issueTime(self, parent, timeStamp):

        indent = ET.SubElement(parent, 'issueTime')
        if timeStamp is None:
            return

        indent1 = ET.SubElement(indent, 'gml:TimeInstant')
        indent1.set('gml:id', deu.getUUID())
        indent2 = ET.SubElement(indent1, 'gml:timePosition')
        indent2.text = timeStamp['str']

    def swac(self, parent, centre):

        indent = ET.SubElement(parent, 'issuingSpaceWeatherCentre')
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
        indent4.text = 'OTHER:SWXC'
        indent4 = ET.SubElement(indent3, 'aixm:designator')
        indent4.text = centre

    def observations(self):
        #
        # Order the forecast hours
        fhrs = list(self.decodedTAC['fcsts'].keys())
        fhrs.sort(key=int)
        #
        for fhr in fhrs:
            try:
                self.result(self.XMLDocument, self.decodedTAC['fcsts'][fhr])
            except Exception:
                self._Logger.exception(self.tacString)

    def result(self, parent, token):

        indent = ET.SubElement(parent, 'analysis')
        indent1 = ET.SubElement(indent, 'SpaceWeatherAnalysis')
        indent1.set('gml:id', deu.getUUID())
        indent1.set('timeIndicator', token['timeIndicator'])
        self.itime(indent1, token['phenomenonTime'])

        if 'noswxexp' in token:

            indent2 = ET.SubElement(indent1, 'region')
            indent2.set('nilReason', self.codes[des.NIL][des.NOOPRSIG][0])

        elif 'notavail' in token:

            indent2 = ET.SubElement(indent1, 'region')
            indent2.set('nilReason', self.codes[des.NIL][des.MSSG][0])

        elif 'daylight' in token:

            indent2 = ET.SubElement(indent1, 'region')
            indent3 = ET.SubElement(indent2, 'SpaceWeatherRegion')
            indent3.set('gml:id', deu.getUUID())
            indent4 = ET.SubElement(indent3, 'location')
            try:
                result = self._fltLvls.match(token['fltlevels'])
                self.airspaceVolume(indent4, token, result.groupdict())

            except KeyError:
                self.airspaceVolume(indent4, token)

            indent4 = ET.SubElement(indent3, 'locationIndicator')
            indent4.set('xlink:href', self.codes[des.SWX_LOCATION][des.DAYLIGHTSIDE][0])

        for affectedRegion in token.get('boundingBoxes', []):

            indent2 = ET.SubElement(indent1, 'region')
            regions, uuidString = affectedRegion[-2:]

            if uuidString[0] == '#':
                indent2.set('xlink:href', uuidString)
                continue

            indent3 = ET.SubElement(indent2, 'SpaceWeatherRegion')
            indent4 = ET.SubElement(indent3, 'location')
            indent3.set('gml:id', uuidString)

            try:
                result = self._fltLvls.match(token['fltlevels'])
                self.airspaceVolume(indent4, affectedRegion, result.groupdict())

            except KeyError:
                self.airspaceVolume(indent4, affectedRegion)

            for band in regions:
                indent4 = ET.SubElement(indent3, 'locationIndicator')
                try:
                    indent4.set('xlink:href', self.codes[des.SWX_LOCATION][band][0])
                except KeyError:
                    indent4.set('xlink:href', self.codes[des.NIL][des.NA][0])

    def airspaceVolume(self, parent, token, fltlvls=None):

        indent1 = ET.SubElement(parent, 'AirspaceVolume')
        indent1.set('xmlns', self.NameSpaces['aixm'])
        indent1.set('gml:id', deu.getUUID())
        indent2 = ET.Element('upperLimit')
        indent2.set('uom', 'FL')
        #
        # If flight levels were set
        try:
            indent2.text = fltlvls['abv'] or fltlvls['upr']

            if indent2.text is not None:

                indent1.append(indent2)
                indent2 = ET.SubElement(indent1, 'upperLimitReference')
                indent2.text = 'STD'

            if fltlvls['abv']:

                indent2 = ET.SubElement(indent1, 'maximumLimit')
                indent2.set('nilReason', 'unknown')
                indent2.set('xsi:nil', 'true')

            elif fltlvls['lwr'] is not None:

                indent2 = ET.SubElement(indent1, 'lowerLimit')
                indent2.set('uom', 'FL')
                indent2.text = fltlvls['lwr']
                indent2 = ET.SubElement(indent1, 'lowerLimitReference')
                indent2.text = 'STD'

        except TypeError:
            pass

        indent2 = ET.SubElement(indent1, 'horizontalProjection')
        indent3 = ET.SubElement(indent2, 'Surface')
        indent3.set('srsDimension', des.srsDimension)
        indent3.set('srsName', des.srsName)
        indent3.set('axisLabels', des.axisLabels)
        indent3.set('gml:id', deu.getUUID())
        indent4 = ET.SubElement(indent3, 'polygonPatches')
        indent4.set('xmlns', self.NameSpaces['gml'])
        indent5 = ET.SubElement(indent4, 'PolygonPatch')
        indent6 = ET.SubElement(indent5, 'exterior')

        if 'daylight' in token:
            indent7 = ET.SubElement(indent6, 'Ring')
            indent8 = ET.SubElement(indent7, 'curveMember')
            indent9 = ET.SubElement(indent8, 'Curve')
            indent9.set('gml:id', deu.getUUID())
            indent10 = ET.SubElement(indent9, 'segments')
            indent11 = ET.SubElement(indent10, 'CircleByCenterPoint')
            indent11.set('numArc', '1')
            indent12 = ET.SubElement(indent11, 'pos')
            indent12.text = token['daylight']
            indent12 = ET.SubElement(indent11, 'radius')
            indent12.text = des.DAYLIGHTSIDE_RADIUS
            indent12.set('uom', des.DAYLIGHTSIDE_UOM)

        else:
            indent7 = ET.SubElement(indent6, 'LinearRing')
            indent8 = ET.SubElement(indent7, 'posList')
            indent8.set('count', token[0])
            indent8.text = token[1]

    def itime(self, parent, dtg):

        indent = ET.SubElement(parent, 'phenomenonTime')
        indent1 = ET.SubElement(indent, 'gml:TimeInstant')
        indent1.set('gml:id', deu.getUUID())
        indent2 = ET.SubElement(indent1, 'gml:timePosition')
        indent2.text = dtg

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
            indent2.text = self.decodedTAC['nextAdvisory']['str']
            if self.decodedTAC['nextAdvisory']['before']:
                indent2.set('indeterminatePosition', 'before')
            indent.append(indent1)

        except KeyError:
            indent.set('nilReason', self.codes[des.NIL][des.NA][0])
