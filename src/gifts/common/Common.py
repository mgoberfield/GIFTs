import re
import xml.etree.ElementTree as ET

from . import xmlConfig as des
from . import xmlUtilities as deu


class Base(object):

    def __init__(self):

        self._re_ICAO_ID = re.compile(r'[A-Z]{4}')
        self._re_IATA_ID = re.compile(r'[A-Z]{3}')
        self._re_Alternate_ID = re.compile(r'[A-Z0-9]{3,6}')

        self.NameSpaces = {'aixm': 'http://www.aixm.aero/schema/5.1.1',
                           'iwxxm': des.IWXXM_URI,
                           'gml': 'http://www.opengis.net/gml/3.2',
                           'xlink': 'http://www.w3.org/1999/xlink',
                           'xsi': 'http://www.w3.org/2001/XMLSchema-instance'}

    def aerodrome(self, parent, token):

        indent = ET.SubElement(parent, 'iwxxm:aerodrome')
        if token is None:
            return

        indent1 = ET.SubElement(indent, 'aixm:AirportHeliport')
        indent1.set('gml:id', deu.getUUID())

        indent2 = ET.SubElement(indent1, 'aixm:timeSlice')
        indent3 = ET.SubElement(indent2, 'aixm:AirportHeliportTimeSlice')
        indent3.set('gml:id', deu.getUUID())

        indent4 = ET.SubElement(indent3, 'gml:validTime')
        indent4 = ET.SubElement(indent3, 'aixm:interpretation')
        indent4.text = 'SNAPSHOT'

        try:
            designator = token['alternate']
            if self._re_Alternate_ID.match(designator) is not None:
                indent4 = ET.SubElement(indent3, 'aixm:designator')
                indent4.text = designator

        except KeyError:
            pass

        try:
            indent4 = ET.Element('aixm:name')
            indent4.text = token['name']
            if len(indent4.text):
                indent3.append(indent4)

        except KeyError:
            pass
        #
        # ICAO identifier shall only match [A-Z]{4}
        designator = token['str']
        if self._re_ICAO_ID.match(designator) is not None:
            indent4 = ET.SubElement(indent3, 'aixm:locationIndicatorICAO')
            indent4.text = designator
        #
        # If IATA identifier is provided
        try:
            designator = token['iataID']
            if self._re_IATA_ID.match(designator) is not None:
                indent4 = ET.SubElement(indent3, 'aixm:designatorIATA')
                indent4.text = designator

        except KeyError:
            pass

        try:
            indent4 = ET.Element('aixm:ARP')
            indent5 = ET.SubElement(indent4, 'aixm:ElevatedPoint')
            indent6 = ET.SubElement(indent5, 'gml:pos')
            dim_int = int(des.srsDimension)
            indent6.text = ' '.join(token['position'].split()[:dim_int])
            indent5.set('srsDimension', des.srsDimension)
            indent5.set('srsName', des.srsName)
            indent5.set('axisLabels', des.axisLabels)
            indent5.set('gml:id', deu.getUUID())
            #
            # If vertical datum information is known, then use it.
            if des.useElevation:
                try:
                    indent6 = ET.Element('aixm:elevation')
                    indent6.text = token['position'].split()[dim_int]
                    indent6.set('uom', des.elevationUOM)
                    indent5.append(indent6)

                    indent6 = ET.SubElement(indent5, 'aixm:verticalDatum')
                    indent6.text = des.verticalDatum

                except IndexError:
                    pass

            indent3.append(indent4)

        except KeyError:
            pass
