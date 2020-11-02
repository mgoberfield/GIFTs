import xml.etree.ElementTree as ET

import gifts.TCA as TCAE

import gifts.common.xmlConfig as des
import gifts.common.xmlUtilities as deu

encoder = TCAE.Encoder()

first_siblings = ['issueTime', 'issuingTropicalCycloneAdvisoryCentre', 'tropicalCycloneName', 'advisoryNumber',
                  'observation', 'forecast', 'forecast', 'forecast', 'forecast', 'remarks', 'nextAdvisoryTime']

aixm = '{http://www.aixm.aero/schema/5.1.1}'
find_aixm = './/*%s' % aixm
gml = '{http://www.opengis.net/gml/3.2}'
find_gml = './/*%s' % gml
iwxxm = '{http://icao.int/iwxxm/3.0}'
find_iwxxm = './/*%s' % iwxxm
xhref = '{http://www.w3.org/1999/xlink}href'
xtitle = '{http://www.w3.org/1999/xlink}title'


def PP(tree):
    def indent(elem, level=0):
        i = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                indent(elem, level + 1)
                if not elem.tail or not elem.tail.strip():
                    elem.tail = i
            else:
                if level and (not elem.tail or not elem.tail.strip()):
                    elem.tail = i
    indent(tree)
    print(ET.tostring(tree).decode())


codes = deu.parseCodeRegistryTables(des.CodesFilePath, [des.NIL])
missing = codes[des.NIL][des.MSSG]


def test_tcaFailureModes():

    import gifts.tcaDecoder as tD
    decoder = tD.Decoder()

    test = """FKNT23 KNHC 151247
"""
    result = decoder(test)
    assert 'err_msg' in result
    des.TRANSLATOR = True
    test = """FKNT23 KNHC 311315
TC ADVISORY
TCAC: MIAMI"""

    bulletin = encoder.encode(test)
    result = bulletin.pop()
    assert len(result) == 2
    for num, child in enumerate(result):
        assert child.tag == first_siblings[num]
    assert len(result.get('translationFailedTAC')) > 0

    test = """
524
FKNT23 KNHC 311315
TC ADVISORY
DTG: 20191231/1315Z
TCAC: MIAMI
<--PARSER HALT HERE"""

    bulletin = encoder.encode(test)
    result = bulletin.pop()
    assert len(result) == 2
    for num, child in enumerate(result):
        assert child.tag == first_siblings[num]
    assert len(result.get('translationFailedTAC')) > 0


def test_tcaTest():

    test = """FKNT23 KNHC 111800
TC ADVISORY
STATUS: TEST="""

    bulletin = encoder.encode(test)
    result = bulletin.pop()
    assert len(result) == 2
    for num, child in enumerate(result):
        assert child.tag == first_siblings[num]

    assert result.get('permissibleUsage') == 'NON-OPERATIONAL'
    assert result.get('permissibleUsageReason') == 'TEST'


def test_tcaExercise():

    test = """FKPQ30 RJTD 111800
TC ADVISORY
STATUS:               EXER
DTG:                  20180911/1800Z
TCAC:                 TOKYO
TC:                   MANGKHUT
ADVISORY NR:          2018/19
OBS PSN:              11/1800Z N1400 E13725
CB:                   WI 180NM OF TC CENTRE TOP ABV FL450
MOV:                  W 12KT
INTST CHANGE:         INTSF
C:                    905HPA
MAX WIND:             110KT
FCST PSN +6 HR:       12/0000Z N1405 E13620
FCST MAX WIND +6 HR:  110KT
FCST PSN +12 HR:      12/0600Z N1420 E13510
FCST MAX WIND +12 HR: 110KT
FCST PSN +18 HR:      12/1200Z N1430 E134
FCST MAX WIND +18 HR: 110KT
FCST PSN +24 HR:      12/1800Z N1450 E13250
FCST MAX WIND +24 HR: 110KT
RMK:                  NIL
NXT MSG:              BFR 20180912/0000Z=
"""

    bulletin = encoder.encode(test)
    result = bulletin.pop()
    assert len(result) == len(first_siblings)
    for num, child in enumerate(result):
        assert child.tag == first_siblings[num]

    assert result.get('permissibleUsage') == 'NON-OPERATIONAL'
    assert result.get('permissibleUsageReason') == 'EXERCISE'

    tree = ET.XML(ET.tostring(result))

    for num, child in enumerate(first_siblings):
        if num != 5:
            element = tree.find('%s%s' % (iwxxm, child))
        else:
            elementList = tree.findall('%s%s' % (iwxxm, child))

        if num == 0:
            subelement = element.find('.//*{http://www.opengis.net/gml/3.2}timePosition')
            assert subelement.text == '2018-09-11T18:00:00Z'

        elif num == 1:
            subelement = element.find('%sUnitTimeSlice' % find_aixm)
            assert subelement[2].text == 'OTHER:TCAC'
            assert subelement[3].text == 'TOKYO'

        elif num == 2:
            subelement = element.find('{http://def.wmo.int/metce/2013}TropicalCyclone')
            assert subelement[0].text == 'MANGKHUT'

        elif num == 3:
            assert element.text == '2018/19'

        elif num == 4:
            time = element.find('%stimePosition' % find_gml)
            assert time.text == '2018-09-11T18:00:00Z'
            position = element.find('%spos' % find_gml)
            assert position.text == '14.000 137.417'
            uprLimit = element.find('%supperLimit' % find_aixm)
            assert uprLimit.text == '450'
            circle = element.find('%sCircleByCenterPoint' % find_gml)
            assert circle[0].text == '14.000 137.417'
            assert circle[1].text == '180'
            assert circle[1].get('uom') == '[nm_i]'
            movement = element.find('%smovement' % find_iwxxm)
            assert movement.text == 'MOVING'
            movement = element.find('%smovementDirection' % find_iwxxm)
            assert movement.text == '270'
            movement = element.find('%smovementSpeed' % find_iwxxm)
            assert movement.text == '12'
            pressure = element.find('%scentralPressure' % find_iwxxm)
            assert pressure.text == '905'
            maxWSpeed = element.find('%smaximumSurfaceWindSpeed' % find_iwxxm)
            assert maxWSpeed.text == '110'

        elif num == 5:

            for fcnt, forecast in enumerate(elementList):
                time = forecast.find('%stimePosition' % find_gml)
                position = forecast.find('%spos' % find_gml)
                maxWSpeed = forecast.find('%smaximumSurfaceWindSpeed' % find_iwxxm)

                if fcnt == 0:
                    assert time.text == '2018-09-12T00:00:00Z'
                    assert position.text == '14.083 136.333'
                    assert maxWSpeed.text == '110'
                elif fcnt == 1:
                    assert time.text == '2018-09-12T06:00:00Z'
                    assert position.text == '14.333 135.167'
                    assert maxWSpeed.text == '110'
                elif fcnt == 2:
                    assert time.text == '2018-09-12T12:00:00Z'
                    assert position.text == '14.500 134.000'
                    assert maxWSpeed.text == '110'
                elif fcnt == 3:
                    assert time.text == '2018-09-12T18:00:00Z'
                    assert position.text == '14.834 132.833'
                    assert maxWSpeed.text == '110'

        elif num == 9:
            assert element.get('nilReason') == codes[des.NIL][des.NA][0]
        elif num == 10:
            time = element.find('%stimePosition' % find_gml)
            assert time.text == '2018-09-12T00:00:00Z'
            assert time.get('indeterminatePosition') == 'before'


def test_tcaNormal():

    test = """FKNT23 KNHC 011501
TCANT3

TROPICAL STORM HELENE ICAO ADVISORY NUMBER  01
NWS NATIONAL HURRICANE CENTER MIAMI FL       AL012018
1501 UTC FRI MAY 01 2018

TC ADVISORY
DTG:                      20180501/1501Z
TCAC:                     KNHC
TC:                       HELENE
ADVISORY NR:              2018/01
OBS PSN:                  01/1430Z N3254 W03618
CB:                       WI N3332 W03620-N3406 W03641-N34 W035-
                          N3325 W03617-N3332 W03620 TOP BLW FL350
CB:                       WI N3140 W03525-N3061 W03611-N3030 W03449-
                          N3140 W03525 TOP FL350
MOV:                      STNR
INTST CHANGE:             NC
C:                        0988HPA
MAX WIND:                 060KT
FCST PSN +6 HR:           01/2100Z N3438 W03546
FCST MAX WIND +6 HR:      060KT
FCST PSN +12 HR:          02/0300Z N3613 W03458
FCST MAX WIND +12 HR:     060KT
FCST PSN +18 HR:          02/0900Z N3740 W03355
FCST MAX WIND +18 HR:     055KT
FCST PSN +24 HR:          02/1500Z N3858 W03233
FCST MAX WIND +24 HR:     055KT
RMK:                      NIL
NXT MSG:                  20180912/0000Z="""

    bulletin = encoder.encode(test)
    result = bulletin.pop()
    assert len(result) == len(first_siblings)
    for num, child in enumerate(result):
        assert child.tag == first_siblings[num]

    assert result.get('permissibleUsage') == 'OPERATIONAL'
    assert result.get('permissibleUsageReason') is None

    tree = ET.XML(ET.tostring(result))
    element = tree.find('%sobservation' % iwxxm)
    cblocation = element.find('%scumulonimbusCloudLocation' % find_iwxxm)
    polygon = cblocation.find('%sposList' % find_gml)
    assert polygon.get('count') == '5'
    assert polygon.text == '33.533 -36.333 33.417 -36.283 34.000 -35.000 34.100 -36.683 33.533 -36.333'


def test_tcaMetric():

    test = """FKPQ30 RJTD 111800
TC ADVISORY
DTG:                  20180911/1800Z
TCAC:                 TOKYO
TC:                   MANGKHUT
ADVISORY NR:          2018/19
OBS PSN:              11/1800Z N1400 E13725
CB:                   WI 180KM OF TC CENTRE TOP ABV FL450
MOV:                  W 20KMH
INTST CHANGE:         NC
C:                    905HPA
MAX WIND:             150MPS
FCST PSN +6 HR:       12/0000Z N14 E13620
FCST MAX WIND +6 HR:  50MPS
FCST PSN +12 HR:      12/0600Z N1420 E13510
FCST MAX WIND +12 HR: 50MPS
FCST PSN +18 HR:      12/1200Z N1430 E134
FCST MAX WIND +18 HR: 50MPS
FCST PSN +24 HR:      12/1800Z N1450 E13250
FCST MAX WIND +24 HR: 50MPS
RMK:                  NIL
NXT MSG:              20180912/0000Z =
"""

    bulletin = encoder.encode(test)
    result = bulletin.pop()
    assert len(result) == len(first_siblings)
    for num, child in enumerate(result):
        assert child.tag == first_siblings[num]

    assert result.get('permissibleUsage') == 'OPERATIONAL'
    assert result.get('permissibleUsageReason') is None

    tree = ET.XML(ET.tostring(result))

    for num, child in enumerate(first_siblings):
        if num != 5:
            element = tree.find('%s%s' % (iwxxm, child))
        else:
            elementList = tree.findall('%s%s' % (iwxxm, child))

        if num == 0:
            subelement = element.find('.//*{http://www.opengis.net/gml/3.2}timePosition')
            assert subelement.text == '2018-09-11T18:00:00Z'

        elif num == 1:
            subelement = element.find('%sUnitTimeSlice' % find_aixm)
            assert subelement[2].text == 'OTHER:TCAC'
            assert subelement[3].text == 'TOKYO'

        elif num == 2:
            subelement = element.find('{http://def.wmo.int/metce/2013}TropicalCyclone')
            assert subelement[0].text == 'MANGKHUT'

        elif num == 3:
            assert element.text == '2018/19'

        elif num == 4:
            time = element.find('%stimePosition' % find_gml)
            assert time.text == '2018-09-11T18:00:00Z'
            position = element.find('%spos' % find_gml)
            assert position.text == '14.000 137.417'
            uprLimit = element.find('%supperLimit' % find_aixm)
            assert uprLimit.text == '450'
            circle = element.find('%sCircleByCenterPoint' % find_gml)
            assert circle[0].text == '14.000 137.417'
            assert circle[1].text == '180'
            assert circle[1].get('uom') == 'km'
            movement = element.find('%smovement' % find_iwxxm)
            assert movement.text == 'MOVING'
            movement = element.find('%smovementDirection' % find_iwxxm)
            assert movement.text == '270'
            movement = element.find('%smovementSpeed' % find_iwxxm)
            assert movement.text == '20'
            pressure = element.find('%scentralPressure' % find_iwxxm)
            assert pressure.text == '905'
            maxWSpeed = element.find('%smaximumSurfaceWindSpeed' % find_iwxxm)
            assert maxWSpeed.text == '150'
            assert maxWSpeed.get('uom') == 'm/s'

        elif num == 5:

            for fcnt, forecast in enumerate(elementList):
                time = forecast.find('%stimePosition' % find_gml)
                position = forecast.find('%spos' % find_gml)
                maxWSpeed = forecast.find('%smaximumSurfaceWindSpeed' % find_iwxxm)

                assert maxWSpeed.text == '50'
                assert maxWSpeed.get('uom') == 'm/s'

                if fcnt == 0:
                    assert time.text == '2018-09-12T00:00:00Z'
                    assert position.text == '14.000 136.333'
                elif fcnt == 1:
                    assert time.text == '2018-09-12T06:00:00Z'
                    assert position.text == '14.333 135.167'
                elif fcnt == 2:
                    assert time.text == '2018-09-12T12:00:00Z'
                    assert position.text == '14.500 134.000'
                elif fcnt == 3:
                    assert time.text == '2018-09-12T18:00:00Z'
                    assert position.text == '14.834 132.833'

        elif num == 9:
            assert element.get('nilReason') == codes[des.NIL][des.NA][0]
        elif num == 10:
            time = element.find('%stimePosition' % find_gml)
            assert time.text == '2018-09-12T00:00:00Z'


def test_developing():

    test = """FKAU02 ADRM 090112
TC ADVISORY
DTG:                  20200109/0000Z
TCAC:                 DARWIN
TC:                   DEVELOPING TROPICAL LOW
ADVISORY NR:          2020/2
OBS PSN:              09/0000Z S1212 E13406
CB:                   WI 60NM OF TC CENTRE TOP FL600
MOV:                  SW 06KT
INTST CHANGE:         WKN
C:                    999HPA
MAX WIND:             30KT
FCST PSN +6 HR:       09/0600Z S1224 E13342
FCST MAX WIND +6 HR:  30KT
FCST PSN +12 HR:      09/1200Z S1236 E13306
FCST MAX WIND +12 HR: 30KT
FCST PSN +18 HR:      09/1800Z S1236 E13248
FCST MAX WIND +18 HR: 30KT
FCST PSN +24 HR:      10/0000Z S1224 E13142
FCST MAX WIND +24 HR: 30KT
RMK:                  NIL
NXT MSG:              NO MSG EXP"""

    bulletin = encoder.encode(test)
    result = bulletin.pop()
    assert len(result) == len(first_siblings)
    for num, child in enumerate(result):
        assert child.tag == first_siblings[num]

    assert result.get('permissibleUsage') == 'OPERATIONAL'
    assert result.get('permissibleUsageReason') is None

    tree = ET.XML(ET.tostring(result))

    for num, child in enumerate(first_siblings):
        if num != 5:
            element = tree.find('%s%s' % (iwxxm, child))
        else:
            elementList = tree.findall('%s%s' % (iwxxm, child))

        if num == 0:
            subelement = element.find('.//*{http://www.opengis.net/gml/3.2}timePosition')
            assert subelement.text == '2020-01-09T00:00:00Z'

        elif num == 1:
            subelement = element.find('%sUnitTimeSlice' % find_aixm)
            assert subelement[2].text == 'OTHER:TCAC'
            assert subelement[3].text == 'DARWIN'

        elif num == 2:
            subelement = element.find('{http://def.wmo.int/metce/2013}TropicalCyclone')
            assert subelement[0].text == 'DEVELOPING TROPICAL LOW'

        elif num == 3:
            assert element.text == '2020/2'

        elif num == 4:
            time = element.find('%stimePosition' % find_gml)
            assert time.text == '2020-01-09T00:00:00Z'
            position = element.find('%spos' % find_gml)
            assert position.text == '-12.200 134.100'
            uprLimit = element.find('%supperLimit' % find_aixm)
            assert uprLimit.text == '600'
            circle = element.find('%sCircleByCenterPoint' % find_gml)
            assert circle[0].text == '-12.200 134.100'
            assert circle[1].text == '60'
            assert circle[1].get('uom') == '[nm_i]'
            movement = element.find('%smovement' % find_iwxxm)
            assert movement.text == 'MOVING'
            movement = element.find('%smovementDirection' % find_iwxxm)
            assert movement.text == '225'
            movement = element.find('%smovementSpeed' % find_iwxxm)
            assert movement.text == '6'
            pressure = element.find('%scentralPressure' % find_iwxxm)
            assert pressure.text == '999'
            maxWSpeed = element.find('%smaximumSurfaceWindSpeed' % find_iwxxm)
            assert maxWSpeed.text == '30'

        elif num == 5:

            for fcnt, forecast in enumerate(elementList):
                time = forecast.find('%stimePosition' % find_gml)
                position = forecast.find('%spos' % find_gml)
                maxWSpeed = forecast.find('%smaximumSurfaceWindSpeed' % find_iwxxm)

                if fcnt == 0:
                    assert time.text == '2020-01-09T06:00:00Z'
                    assert position.text == '-12.400 133.700'
                    assert maxWSpeed.text == '30'
                elif fcnt == 1:
                    assert time.text == '2020-01-09T12:00:00Z'
                    assert position.text == '-12.600 133.100'
                    assert maxWSpeed.text == '30'
                elif fcnt == 2:
                    assert time.text == '2020-01-09T18:00:00Z'
                    assert position.text == '-12.600 132.800'
                    assert maxWSpeed.text == '30'
                elif fcnt == 3:
                    assert time.text == '2020-01-10T00:00:00Z'
                    assert position.text == '-12.400 131.700'
                    assert maxWSpeed.text == '30'

        elif num == 9:
            assert element.get('nilReason') == codes[des.NIL][des.NA][0]
        elif num == 10:
            assert element.get('nilReason') == codes[des.NIL][des.NA][0]


def test_dissipation():

    test = """FKNT23 KNHC 231458
TCANT3

REMNANTS OF THREE ICAO ADVISORY NUMBER   4
NWS NATIONAL HURRICANE CENTER MIAMI FL       AL032019
1500 UTC TUE JUL 23 2019

TC ADVISORY
DTG:                      20190723/1500Z
TCAC:                     KNHC
TC:                       THREE
ADVISORY NR:              2019/004
OBS PSN:                  23/1500Z N29 W080
MOV:                      NNE 15KT
INTST CHANGE:             WKN
C:                        1014HPA
MAX WIND:                 030KT
FCST PSN +6 HR:           23/2100Z N2955 W07839
FCST MAX WIND +6 HR:      030KT
FCST PSN +12 HR:          24/0300Z N3325 W07230
FCST MAX WIND +12 HR:     025KT
FCST PSN +18 HR:          24/0900Z N//// W/////
FCST MAX WIND +18 HR:     025KT
FCST PSN +24 HR:          24/1500Z N4530 W05505
FCST MAX WIND +24 HR:     ///KT
RMK:                      THE FORECAST POSITION INFORMATION IN
                          THIS PRODUCT IS INTERPOLATED FROM
                          OFFICIAL FORECAST DATA VALID AT 0000...
                          0600...1200...AND 1800Z.
NXT MSG:                  NO MSG EXP
"""
    bulletin = encoder.encode(test)
    result = bulletin.pop()
    assert len(result) == len(first_siblings)
    for num, child in enumerate(result):
        assert child.tag == first_siblings[num]

    assert result.get('permissibleUsage') == 'OPERATIONAL'
    assert result.get('permissibleUsageReason') is None

    tree = ET.XML(ET.tostring(result))

    for num, child in enumerate(first_siblings):
        if num != 5:
            element = tree.find('%s%s' % (iwxxm, child))
        else:
            elementList = tree.findall('%s%s' % (iwxxm, child))

        if num == 0:
            subelement = element.find('.//*{http://www.opengis.net/gml/3.2}timePosition')
            assert subelement.text == '2019-07-23T15:00:00Z'

        elif num == 1:
            subelement = element.find('%sUnitTimeSlice' % find_aixm)
            assert subelement[2].text == 'OTHER:TCAC'
            assert subelement[3].text == 'KNHC'

        elif num == 2:
            subelement = element.find('{http://def.wmo.int/metce/2013}TropicalCyclone')
            assert subelement[0].text == 'THREE'

        elif num == 3:
            assert element.text == '2019/004'

        elif num == 4:
            time = element.find('%stimePosition' % find_gml)
            assert time.text == '2019-07-23T15:00:00Z'
            position = element.find('%spos' % find_gml)
            assert position.text == '29.000 -80.000'
            movement = element.find('%smovement' % find_iwxxm)
            assert movement.text == 'MOVING'
            movement = element.find('%smovementDirection' % find_iwxxm)
            assert movement.text == '22.5'
            movement = element.find('%smovementSpeed' % find_iwxxm)
            assert movement.text == '15'
            pressure = element.find('%scentralPressure' % find_iwxxm)
            assert pressure.text == '1014'
            maxWSpeed = element.find('%smaximumSurfaceWindSpeed' % find_iwxxm)
            assert maxWSpeed.text == '30'

        elif num == 5:
            for fcnt, forecast in enumerate(elementList):
                time = forecast.find('%stimePosition' % find_gml)
                position = forecast.find('%spos' % find_gml)
                maxWSpeed = forecast.find('%smaximumSurfaceWindSpeed' % find_iwxxm)

                if fcnt == 0:
                    assert time.text == '2019-07-23T21:00:00Z'
                    assert position.text == '29.917 -78.650'
                    assert maxWSpeed.text == '30'
                elif fcnt == 1:
                    assert time.text == '2019-07-24T03:00:00Z'
                    assert position.text == '33.417 -72.500'
                    assert maxWSpeed.text == '25'
                elif fcnt == 2:
                    assert time.text == '2019-07-24T09:00:00Z'
                    assert position is None
                    assert maxWSpeed.text == '25'
                elif fcnt == 3:
                    assert forecast.get('nilReason') == codes[des.NIL][des.NOOPRSIG][0]

        elif num == 9:
            assert len(element.text) > 0
        elif num == 10:
            assert element.get('nilReason') == codes[des.NIL][des.NA][0]


if __name__ == '__main__':

    test_tcaFailureModes()
    test_tcaTest()
    test_tcaExercise()
    test_tcaNormal()
    test_tcaMetric()
    test_developing()
    test_dissipation()
