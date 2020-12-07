import xml.etree.ElementTree as ET

import gifts.VAA as VAAE
from gifts.common import xmlConfig as des
from gifts.common import xmlUtilities as deu

encoder = VAAE.Encoder()

first_siblings = ['issueTime', 'issuingVolcanicAshAdvisoryCentre', 'volcano', 'stateOrRegion', 'summitElevation',
                  'advisoryNumber', 'informationSource', 'colourCode', 'eruptionDetails', 'observation', 'forecast',
                  'forecast', 'forecast', 'remarks', 'nextAdvisoryTime']

aixm = '{http://www.aixm.aero/schema/5.1.1}'
find_aixm = './/*%s' % aixm
gml = '{http://www.opengis.net/gml/3.2}'
find_gml = './/*%s' % gml
iwxxm = '{http://icao.int/iwxxm/3.0}'
find_iwxxm = './/*%s' % iwxxm
xhref = '{http://www.w3.org/1999/xlink}href'


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


codes = deu.parseCodeRegistryTables(des.CodesFilePath, [des.COLOUR_CODES, des.NIL])

des.TRANSLATOR = True


def test_vaaFailureModes():

    import gifts.vaaDecoder as vD
    decoder = vD.Decoder()

    test = """FVXX23 KNES 151247
"""
    result = decoder(test)
    assert 'err_msg' in result

    test = """FVXX01 LFPW 311315 RRA
VA ADVISORY
VAAC: TOULOUSE"""

    bulletin = encoder.encode(test)
    result = bulletin.pop()
    assert len(result) == 2
    for num, child in enumerate(result):
        assert child.tag == first_siblings[num]
    assert len(result.get('translationFailedTAC')) > 0

    test = """FVXX01 LFPW 311315 RRA
VA ADVISORY
DTG: 20191231/1315Z
VAAC: TOULOUSE
<--PARSER HALTS HERE"""

    bulletin = encoder.encode(test)
    result = bulletin.pop()
    assert len(result) == 2
    for num, child in enumerate(result):
        assert child.tag == first_siblings[num]
    assert len(result.get('translationFailedTAC')) > 0


def test_vaaNoWinds():
    import gifts.vaaDecoder as vD

    test = """FVAU03 ADRM 150252
VA ADVISORY
DTG: 20200615/0252Z
VAAC: DARWIN
VOLCANO: SEMERU 263300
PSN: S0806 E11255
AREA: INDONESIA
SUMMIT ELEV: 3676M
ADVISORY NR: 2020/96
INFO SOURCE: CVGHM, HIMAWARI-8
AVIATION COLOUR CODE: ORANGE
ERUPTION DETAILS: GROUND REPORT OF VA ERUPTION TO FL130 AT
15/0237Z
OBS VA DTG: 15/0252Z
OBS VA CLD: VA NOT IDENTIFIABLE FM SATELLITE DATA
FCST VA CLD +6 HR: 15/0852Z NO VA EXP
FCST VA CLD +12 HR: 15/1452Z NO VA EXP
FCST VA CLD +18 HR: 15/2052Z NO VA EXP
RMK: CVGHM VONA REPORTS ERUPTION TO FL130 MOVING TO WEST AT
15/0237Z, HOWEVER VA CANNOT BE IDENTIFIED ON SATELLITE
IMAGERY DUE TO MET CLOUD IN AREA. ADVISORY WILL BE UPDATED
IF NEW INFORMATION IS RECEIVED.
NXT ADVISORY: NO FURTHER ADVISORIES
"""
    decoder = vD.Decoder()
    result = decoder(test)
    assert 'err_msg' in result


def test_vaaWndDirection():

    import gifts.vaaDecoder as vD

    test = """FVAU03 ADRM 150252
VA ADVISORY
DTG: 20200615/0252Z
VAAC: DARWIN
VOLCANO: SEMERU 263300
PSN: S0806 E11255
AREA: INDONESIA
SUMMIT ELEV: 3676M
ADVISORY NR: 2020/96
INFO SOURCE: CVGHM, HIMAWARI-8
AVIATION COLOUR CODE: ORANGE
ERUPTION DETAILS: GROUND REPORT OF VA ERUPTION TO FL130 AT
15/0237Z
OBS VA DTG: 15/0252Z
OBS VA CLD: TOP FL550 N4130 E01415 - N3745 E02145 - N3500 E03015 - N3400 E02930 -
N3845 E01415 - N4030 E01230 - N4130 W01415 MOV NS 5KT
FCST VA CLD +6 HR: 15/0852Z NO VA EXP
FCST VA CLD +12 HR: 15/1452Z NO VA EXP
FCST VA CLD +18 HR: 15/2052Z NO VA EXP
RMK: CVGHM VONA REPORTS ERUPTION TO FL130 MOVING TO WEST AT
15/0237Z, HOWEVER VA CANNOT BE IDENTIFIED ON SATELLITE
IMAGERY DUE TO MET CLOUD IN AREA. ADVISORY WILL BE UPDATED
IF NEW INFORMATION IS RECEIVED.
NXT ADVISORY: NO FURTHER ADVISORIES
"""

    decoder = vD.Decoder()
    result = decoder(test)
    assert 'err_msg' in result


def test_vaaTest():

    test = """FVXX23 KNES 151247
VA ADVISORY
STATUS: TEST="""

    bulletin = encoder.encode(test)
    result = bulletin.pop()
    assert len(result) == 2
    for num, child in enumerate(result):
        assert child.tag == first_siblings[num]

    assert result.get('permissibleUsage') == 'NON-OPERATIONAL'
    assert result.get('permissibleUsageReason') == 'TEST'

    test = """FVUS01 KNES 312158
VA ADVISORY
STATUS: TEST
DTG: 20191130/2200Z
VAAC: WASHINGTON
VOLCANO: UNNAMED
PSN: UNKNOWN
AREA: CHESAPEAKE BAY
SUMMIT ELEV: 0 FT
ADVISORY NR: 2019/1193
INFO SOURCE: TEST
AVIATION COLOUR CODE: NOT GIVEN
ERUPTION DETAILS: UNKNOWN
EST VA DTG: 30/2200Z
EST VA CLD: VA NOT IDENTIFIABLE FM SATELLITE DATA WIND FL200/300 260/100MPS
FCST VA CLD +6 HR: NOT PROVIDED
FCST VA CLD +12 HR: NOT AVBL
FCST VA CLD +18 HR: NO VA EXP
RMK: NIL
NXT ADVISORY: NO LATER THAN 20191201/0400Z="""

    bulletin = encoder.encode(test)
    result = bulletin.pop()
    assert len(result) == len(first_siblings)
    for num, child in enumerate(result):
        assert child.tag == first_siblings[num]

    assert result.get('permissibleUsage') == 'NON-OPERATIONAL'
    assert result.get('permissibleUsageReason') == 'TEST'

    tree = ET.XML(ET.tostring(result))

    for cnt, element in enumerate(tree):

        if cnt == 0:
            timePosition = element.find('%stimePosition' % find_gml)
            assert timePosition.text == '2019-11-30T22:00:00Z'
        elif cnt == 1:
            name = element.find('%sname' % find_aixm)
            assert name.text == 'WASHINGTON'
            mwotype = element.find('%stype' % find_aixm)
            assert mwotype.text == 'OTHER:VAAC'
        elif cnt == 2:
            name = element.find('.//*{http://def.wmo.int/metce/2013}name')
            assert name.text == 'UNNAMED'
            position = element.find('.//*{http://def.wmo.int/metce/2013}position')
            assert position.get('nilReason') == codes[des.NIL][des.UNKNWN][0]
            edate = element.find('.//*{http://def.wmo.int/metce/2013}eruptionDate')
            assert edate.text == '2019-11-30T22:00:00Z'
        elif cnt == 3:
            assert element.text == 'CHESAPEAKE BAY'
        elif cnt == 4:
            assert element.text == '0'
            assert element.get('uom') == '[ft_i]'
        elif cnt == 5:
            assert element.text == '2019/1193'
        elif cnt == 6:
            assert element.text == 'TEST'
        elif cnt == 7:
            assert element.get('nilReason') == codes[des.NIL][des.WTHLD][0]
        elif cnt == 8:
            assert element.get('nilReason') == codes[des.NIL][des.UNKNWN][0]
        elif cnt == 9:
            assert element[0].get('status') == 'NOT_IDENTIFIABLE'
            assert element[0].get('isEstimated') == 'true'
            timePosition = element.find('%stimePosition' % find_gml)
            assert timePosition.text == '2019-11-30T22:00:00Z'
            wind = element.find('%swind' % find_iwxxm)
            assert wind[0].get('variableWindDirection') == 'false'
            layer = wind.find('%sAirspaceLayer' % find_aixm)
            assert layer[0].tag == '%supperLimit' % aixm
            assert layer[1].tag == '%supperLimitReference' % aixm
            assert layer[2].tag == '%slowerLimit' % aixm
            assert layer[3].tag == '%slowerLimitReference' % aixm
            assert layer[0].text == '300'
            assert layer[1].text == 'STD'
            assert layer[2].text == '200'
            assert layer[3].text == 'STD'
            assert wind[0][1].tag == '%swindDirection' % iwxxm
            assert wind[0][1].text == '260'
            assert wind[0][2].tag == '%swindSpeed' % iwxxm
            assert wind[0][2].text == '100'
            assert wind[0][2].get('uom') == 'm/s'
        elif 9 < cnt < 13:
            timePosition = element.find('%stimePosition' % find_gml)
            if cnt == 10:
                assert element[0].get('status') == 'NOT_PROVIDED'
                assert timePosition.text == '2019-12-01T04:00:00Z'
            elif cnt == 11:
                assert element[0].get('status') == 'NOT_AVAILABLE'
                assert timePosition.text == '2019-12-01T10:00:00Z'
            elif cnt == 12:
                assert element[0].get('status') == 'NO_VOLCANIC_ASH_EXPECTED'
                assert timePosition.text == '2019-12-01T16:00:00Z'
        elif cnt == 13:
            assert element.get('nilReason') == codes[des.NIL][des.NA][0]
        elif cnt == 14:
            timePosition = element.find('%stimePosition' % find_gml)
            assert timePosition.text == '2019-12-01T04:00:00Z'
            assert timePosition.get('indeterminatePosition') == 'before'


def test_vaaExercise():

    test = """FVXX01 LFPW 311315 RRA
VA ADVISORY
STATUS: EXER
DTG: 20191231/1315Z
VAAC: TOULOUSE
VOLCANO: CAMPI FLEGREI 211010
PSN: N40 E014
AREA: ITALY
SUMMIT ELEV: 458M
ADVISORY NR: 2019/1
INFO SOURCE: EXERCISE EXERCISE EXERCISE
AVIATION COLOUR CODE: NIL
ERUPTION DETAILS: ERUPTION AT 20191231/1241Z EXERCISE EXERCISE
EXERCISE
OBS VA DTG: 31/1300Z
OBS VA CLD: SFC/FL100 200KM WID LINE BTN N30 W07530 - N40 W070 MOV N
99KMH
FL100/400 100NM WID LINE BTN S40 E01615 - S3930 E01415 MOV S 99KT
TOP FL550 N4130 E01415 - N3745 E02145 - N3500 E03015 - N3400 E02930 -
N3845 E01415 - N4030 E01230 - N4130 W01415 MOV SE 40KT
FCST VA CLD +6 HR: 31/1800Z NOT AVBL
FCST VA CLD +12 HR: 01/0000Z NO VA EXP
FCST VA CLD +18 HR: 01/0600Z SFC/FL100 N4130 E01715 - N3615 E01830 -
N3645 E01430 - N3230 E01430 - N3245 E00830 - N3700 E00730 - N3945
E00115 - N4530 E00815 - N4700 E01330 - N4300 E01330 - N4130 E01715
FL100/390 N3715 E00645 - N4000 W00545 - N3545 W01415 - N3700 W02130 -
N4130 W02300 - N4330 W01630 - N4115 W01430 - N4300 E00145 - N4615
E00345 - N5215 E02630 - N4930 E03500 - N4630 E03415 - N4715 E02730 -
N4445 E01900 - N3730 E01515 - N3715 E00645  FL390/550 N4530 E01545 -
N3800 E02330 - N3330 E03230 - N3345 E03800 - N3815 E04445 - N3630
E04630 - N2930 E03715 - N3230 E02530 - N41 E013 - N4530 E01545
RMK:  EXERCISE PLEASE DISREGARD EXERCISE EXERCISE
NXT ADVISORY: NO FURTHER ADVISORIES="""

    bulletin = encoder.encode(test)
    result = bulletin.pop()
    assert len(result) == len(first_siblings)
    for num, child in enumerate(result):
        assert child.tag == first_siblings[num]

    assert result.get('permissibleUsage') == 'NON-OPERATIONAL'
    assert result.get('permissibleUsageReason') == 'EXERCISE'

    tree = ET.XML(ET.tostring(result))
    for cnt, element in enumerate(tree):

        if cnt == 0:
            timePosition = element.find('%stimePosition' % find_gml)
            assert timePosition.text == '2019-12-31T13:15:00Z'
        elif cnt == 1:
            name = element.find('%sname' % find_aixm)
            assert name.text == 'TOULOUSE'
            mwotype = element.find('%stype' % find_aixm)
            assert mwotype.text == 'OTHER:VAAC'
        elif cnt == 2:
            name = element[0][0]
            assert name.text == 'CAMPI FLEGREI 211010'
            position = element.find('%spos' % find_gml)
            assert position.text == '40.000 14.000'
            edate = element.find('.//*{http://def.wmo.int/metce/2013}eruptionDate')
            assert edate.text == '2019-12-31T12:41:00Z'
        elif cnt == 3:
            assert element.text == 'ITALY'
        elif cnt == 4:
            assert element.text == '458'
            assert element.get('uom') == 'm'
        elif cnt == 5:
            assert element.text == '2019/1'
        elif cnt == 6:
            assert element.text == 'EXERCISE EXERCISE EXERCISE'
        elif cnt == 7:
            assert element.get('nilReason') == codes[des.NIL][des.MSSG][0]
        elif cnt == 8:
            assert element.text == 'ERUPTION AT 20191231/1241Z EXERCISE EXERCISE EXERCISE'
        elif cnt == 9:
            assert element[0].get('status') == 'IDENTIFIABLE'
            assert element[0].get('isEstimated') == 'false'
            timePosition = element.find('%stimePosition' % find_gml)
            assert timePosition.text == '2019-12-31T13:00:00Z'
            ashCloudList = element.findall('%sashCloud' % find_iwxxm)
            assert len(ashCloudList) == 3

            for acnt, ashCloud in enumerate(ashCloudList):

                volume = ashCloud.find('%sAirspaceVolume' % find_aixm)
                if acnt == 0:

                    assert volume[0].tag == '%supperLimit' % aixm
                    assert volume[1].tag == '%supperLimitReference' % aixm
                    assert volume[2].tag == '%slowerLimit' % aixm
                    assert volume[3].tag == '%slowerLimitReference' % aixm
                    assert volume[0].text == '100'
                    assert volume[1].text == 'STD'
                    assert volume[2].text == 'GND'
                    assert volume[3].text == 'SFC'
                    assert ashCloud[0][1].tag == '%sdirectionOfMotion' % iwxxm
                    assert ashCloud[0][2].tag == '%sspeedOfMotion' % iwxxm
                    assert ashCloud[0][1].text == '360'
                    assert ashCloud[0][2].text == '99'
                    assert ashCloud[0][2].get('uom') == 'km/h'
                    posList = ashCloud.find('%sposList' % find_gml)
                    assert posList.text == '30.433 -76.409 29.567 -74.591 39.567 -68.972 40.433 -71.028 30.433 -76.409'

                elif acnt == 1:

                    assert volume[0].text == '400'
                    assert volume[1].text == 'STD'
                    assert volume[2].text == '100'
                    assert volume[3].text == 'STD'
                    assert ashCloud[0][1].text == '180'
                    assert ashCloud[0][2].text == '99'
                    assert ashCloud[0][2].get('uom') == '[kn_i]'
                    posList = ashCloud.find('%sposList' % find_gml)
                    assert posList.text == '-40.808 15.986 -39.192 16.514 -38.692 14.512 -40.308 13.988 -40.808 15.986'

                elif acnt == 2:
                    assert volume[0].text == '550'
                    assert volume[1].text == 'STD'
                    assert volume[2].get('nilReason') == des.MSSG
                    assert ashCloud[0][1].text == '135'
                    assert ashCloud[0][2].text == '40'
                    assert ashCloud[0][2].get('uom') == '[kn_i]'

        elif 9 < cnt < 13:
            timePosition = element.find('%stimePosition' % find_gml)
            if cnt == 10:
                assert element[0].get('status') == 'NOT_AVAILABLE'
                assert timePosition.text == '2019-12-31T18:00:00Z'
            elif cnt == 11:
                assert element[0].get('status') == 'NO_VOLCANIC_ASH_EXPECTED'
                assert timePosition.text == '2020-01-01T00:00:00Z'
            elif cnt == 12:
                assert element[0].get('status') == 'PROVIDED'
                assert timePosition.text == '2020-01-01T06:00:00Z'
                ashCloudList = element.findall('%sashCloud' % find_iwxxm)
                assert len(ashCloudList) == 3

                for acnt, ashCloud in enumerate(ashCloudList):

                    volume = ashCloud.find('%sAirspaceVolume' % find_aixm)
                    if acnt == 0:
                        assert volume[0].tag == '%supperLimit' % aixm
                        assert volume[1].tag == '%supperLimitReference' % aixm
                        assert volume[2].tag == '%slowerLimit' % aixm
                        assert volume[3].tag == '%slowerLimitReference' % aixm
                        assert volume[0].text == '100'
                        assert volume[1].text == 'STD'
                        assert volume[2].text == 'GND'
                        assert volume[3].text == 'SFC'
                    elif cnt == 1:
                        assert volume[0].text == '390'
                        assert volume[1].text == 'STD'
                        assert volume[2].text == '100'
                        assert volume[3].text == 'STD'
                    elif cnt == 2:
                        assert volume[0].text == '550'
                        assert volume[2].text == '390'

        elif cnt == 13:
            assert element.text == 'EXERCISE PLEASE DISREGARD EXERCISE EXERCISE'
        elif cnt == 14:
            assert element.get('nilReason') == codes[des.NIL][des.NA][0]


def test_vaaNormal():

    test = """FVFE01 RJTD 111803
VA ADVISORY
DTG: 20200511/1803Z
VAAC: TOKYO
VOLCANO: ASOSAN 282110
PSN: N3253 E13106
AREA: JAPAN
SUMMIT ELEV: 1592M
ADVISORY NR: 2020/547
INFO SOURCE: HIMAWARI-8 JMA
AVIATION COLOUR CODE: UNKNOWN
ERUPTION DETAILS: ACTIVITY CONT. VA AT 20200511/1800Z FL050 EXTD N
OBS VA DTG: 11/1750Z
OBS VA CLD: VA NOT IDENTIFIABLE FM SATELLITE DATA WIND SFC/FL050 VRB10MPS
FCST VA CLD +6 HR: NOT AVBL
FCST VA CLD +12 HR: NOT AVBL
FCST VA CLD +18 HR: NOT AVBL
RMK: WE WILL ISSUE FURTHER ADVISORY IF VA IS DETECTED IN SATELLITE
IMAGERY.
NXT ADVISORY: NO FURTHER ADVISORIES="""

    bulletin = encoder.encode(test)
    result = bulletin.pop()
    assert len(result) == len(first_siblings)
    for num, child in enumerate(result):
        assert child.tag == first_siblings[num]

    assert result.get('permissibleUsage') == 'OPERATIONAL'
    assert result.get('permissibleUsageReason') is None

    tree = ET.XML(ET.tostring(result))

    for cnt, element in enumerate(tree):

        if cnt == 0:
            timePosition = element.find('%stimePosition' % find_gml)
            assert timePosition.text == '2020-05-11T18:03:00Z'
        elif cnt == 1:
            name = element.find('%sname' % find_aixm)
            assert name.text == 'TOKYO'
        elif cnt == 2:
            name = element.find('.//*{http://def.wmo.int/metce/2013}name')
            assert name.text == 'ASOSAN 282110'
            position = element.find('%spos' % find_gml)
            assert position.text == '32.884 131.100'
            edate = element.find('.//*{http://def.wmo.int/metce/2013}eruptionDate')
            assert edate.text == '2020-05-11T18:00:00Z'
        elif cnt == 3:
            assert element.text == 'JAPAN'
        elif cnt == 4:
            assert element.text == '1592'
            assert element.get('uom') == 'm'
        elif cnt == 5:
            assert element.text == '2020/547'
        elif cnt == 6:
            assert element.text == 'HIMAWARI-8 JMA'
        elif cnt == 7:
            assert element.get('nilReason') == codes[des.NIL][des.UNKNWN][0]
        elif cnt == 8:
            assert element.text == 'ACTIVITY CONT. VA AT 20200511/1800Z FL050 EXTD N'
        elif cnt == 9:
            assert element[0].get('status') == 'NOT_IDENTIFIABLE'
            assert element[0].get('isEstimated') == 'false'
            timePosition = element.find('%stimePosition' % find_gml)
            assert timePosition.text == '2020-05-11T17:50:00Z'
            wind = element.find('%swind' % find_iwxxm)
            assert wind[0].get('variableWindDirection') == 'true'
            layer = wind.find('%sAirspaceLayer' % find_aixm)
            assert layer[0].tag == '%supperLimit' % aixm
            assert layer[1].tag == '%supperLimitReference' % aixm
            assert layer[2].tag == '%slowerLimit' % aixm
            assert layer[3].tag == '%slowerLimitReference' % aixm
            assert layer[0].text == '050'
            assert layer[1].text == 'STD'
            assert layer[2].text == 'GND'
            assert layer[3].text == 'SFC'
            assert wind[0][1].tag == '%swindSpeed' % iwxxm
            assert wind[0][1].text == '10'
            assert wind[0][1].get('uom') == 'm/s'
        elif 9 < cnt < 13:
            assert element[0].get('status') == 'NOT_AVAILABLE'
            timePosition = element.find('%stimePosition' % find_gml)
            if cnt == 10:
                assert timePosition.text == '2020-05-11T23:50:00Z'
            elif cnt == 11:
                assert timePosition.text == '2020-05-12T05:50:00Z'
            elif cnt == 12:
                assert timePosition.text == '2020-05-12T11:50:00Z'
        elif cnt == 13:
            assert element.text == 'WE WILL ISSUE FURTHER ADVISORY IF VA IS DETECTED IN SATELLITE IMAGERY.'
        elif cnt == 14:
            assert element.get('nilReason') == codes[des.NIL][des.NA][0]

    test = """FVAU01 ADRM 312158
VA ADVISORY
DTG: 20191130/2200Z
VAAC: DARWIN
VOLCANO: DUKONO 268010
PSN: N0141 E12753
AREA: INDONESIA
SUMMIT ELEV: 4380FT
ADVISORY NR: 2019/1193
INFO SOURCE: HIMAWARI-8
AVIATION COLOUR CODE: ORANGE
ERUPTION DETAILS: CONTINUOUS VA ERUPTION OBS TO FL070 EXT W
        AT 30/2130Z.
OBS VA DTG: 30/2200Z
OBS VA CLD: SFC/FL070 N0140 E12754 - N0146 E12802 - N0149
        E12756 - N0145 E12736 - N0138 E12742 MOV W 5KT
FCST VA CLD +6 HR: 01/0400Z SFC/FL070 N0128 E12758 - N0131
        E12732 - N0147 E12735 - N0204 E12805 - N0143 E12826
FCST VA CLD +12 HR: 01/1000Z SFC/FL070 N0127 E12749 - N0135
        E12813 - N0205 E12820 - N0201 E12747 - N0130 E12725
FCST VA CLD +18 HR: 01/1600Z SFC/FL070 N0124 E12750 - N0133
        E12724 - N0203 E12739 - N0152 E12812 - N0132 E12809
RMK: VA OBS EXT TO W ON LATEST SAT IMAGERY. HOWEVER, PARTLY
        OBSCURED BY MET CLOUD. HEIGHT AND FORECAST BASED ON
        HIMAWARI-8, MENADO 13/1200Z SOUNDING AND MODEL GUIDANCE. LOW
        CONFIDENCE IN FORECAST DUE TO LIGHT AND VARIABLE WINDS.
NXT ADVISORY: WILL BE ISSUED BY 20191201/0400Z="""

    bulletin = encoder.encode(test)
    result = bulletin.pop()
    assert len(result) == len(first_siblings)
    for num, child in enumerate(result):
        assert child.tag == first_siblings[num]

    assert result.get('permissibleUsage') == 'OPERATIONAL'
    assert result.get('permissibleUsageReason') is None
    tree = ET.XML(ET.tostring(result))

    for cnt, element in enumerate(tree):

        if cnt == 0:
            timePosition = element.find('%stimePosition' % find_gml)
            assert timePosition.text == '2019-11-30T22:00:00Z'
        elif cnt == 1:
            name = element.find('%sname' % find_aixm)
            assert name.text == 'DARWIN'
        elif cnt == 2:
            name = element.find('.//*{http://def.wmo.int/metce/2013}name')
            assert name.text == 'DUKONO 268010'
            position = element.find('%spos' % find_gml)
            assert position.text == '1.683 127.884'
            edate = element.find('.//*{http://def.wmo.int/metce/2013}eruptionDate')
            assert edate.text == '2019-11-30T21:30:00Z'
        elif cnt == 3:
            assert element.text == 'INDONESIA'
        elif cnt == 4:
            assert element.text == '4380'
            assert element.get('uom') == '[ft_i]'
        elif cnt == 5:
            assert element.text == '2019/1193'
        elif cnt == 6:
            assert element.text == 'HIMAWARI-8'
        elif cnt == 7:
            assert element.get(xhref) == codes[des.COLOUR_CODES]['ORANGE'][0]
        elif cnt == 8:
            assert element.text == 'CONTINUOUS VA ERUPTION OBS TO FL070 EXT W AT 30/2130Z.'
        elif cnt == 9:

            assert element[0].get('status') == 'IDENTIFIABLE'
            assert element[0].get('isEstimated') == 'false'
            timePosition = element.find('%stimePosition' % find_gml)
            assert timePosition.text == '2019-11-30T22:00:00Z'
            ashCloudList = element.findall('%sashCloud' % find_iwxxm)
            assert len(ashCloudList) == 1

            for acnt, ashCloud in enumerate(ashCloudList):

                volume = ashCloud.find('%sAirspaceVolume' % find_aixm)
                if acnt == 0:
                    assert volume[0].tag == '%supperLimit' % aixm
                    assert volume[1].tag == '%supperLimitReference' % aixm
                    assert volume[2].tag == '%slowerLimit' % aixm
                    assert volume[3].tag == '%slowerLimitReference' % aixm
                    assert volume[0].text == '070'
                    assert volume[1].text == 'STD'
                    assert volume[2].text == 'GND'
                    assert volume[3].text == 'SFC'
                    assert ashCloud[0][1].tag == '%sdirectionOfMotion' % iwxxm
                    assert ashCloud[0][2].tag == '%sspeedOfMotion' % iwxxm
                    assert ashCloud[0][1].text == '270'
                    assert ashCloud[0][2].text == '5'
                    assert ashCloud[0][2].get('uom') == '[kn_i]'

        elif 9 < cnt < 13:
            timePosition = element.find('%stimePosition' % find_gml)
            assert element[0].get('status') == 'PROVIDED'
            ashCloud = element.find('%sashCloud' % find_iwxxm)
            volume = ashCloud.find('%sAirspaceVolume' % find_aixm)
            assert volume[0].tag == '%supperLimit' % aixm
            assert volume[1].tag == '%supperLimitReference' % aixm
            assert volume[2].tag == '%slowerLimit' % aixm
            assert volume[3].tag == '%slowerLimitReference' % aixm
            assert volume[0].text == '070'
            assert volume[1].text == 'STD'
            assert volume[2].text == 'GND'
            assert volume[3].text == 'SFC'

            if cnt == 10:
                assert timePosition.text == '2019-12-01T04:00:00Z'
            elif cnt == 11:
                assert timePosition.text == '2019-12-01T10:00:00Z'
            elif cnt == 12:
                assert timePosition.text == '2019-12-01T16:00:00Z'

        elif cnt == 13:
            assert len(element.text) > 220
        elif cnt == 14:
            timePosition = element.find('%stimePosition' % find_gml)
            assert timePosition.text == '2019-12-01T04:00:00Z'
            assert timePosition.get('indeterminatePosition') == 'before'

    test = """
FVAG01 SABM 290615
VA ADVISORY
DTG: 20200529/0615Z

VAAC: BUENOS AIRES

VOLCANO: SABANCAYA 354006
PSN: S1547 W07150

AREA: PERU

SUMMIT ELEV: 19576 FT (5967 M)

ADVISORY NR: 2020/635

INFO SOURCE: GOES-E. GFS. WEBCAM.

AVIATION COLOUR CODE: PURPLE

ERUPTION DETAILS: CONTINUOUS EMISSION

OBS VA DTG: 29/0510Z

OBS VA CLD: SFC/FL240 S1546 W07151 - S1552 W07131
- S1558 W07137 - S1546 W07151 MOV SE 20KT

FCST VA CLD +6 HR: 29/1100Z SFC/FL240 S1547 W07151
- S1602 W07113 - S1621 W07134 - S1547 W07151

FCST VA CLD +12 HR: 29/1700Z SFC/FL240 S1547
W07151 - S1604 W07110 - S1625 W07134 - S1547
W07151

FCST VA CLD +18 HR: 29/2300Z SFC/FL240 S1547
W07151 - S1602 W07100 - S1630 W07128 - S1547
W07151

RMK: VA PLUME IS DETECTED IN STLT IMAGERY MOV SE
EST FL240. THERMAL WEBCAM SHOWS A CONTINUOUS
EMISSION WITH INTERMITTENT PUFFS...SMN

NXT ADVISORY: WILL BE ISSUED BY 20200529/1215Z="""
    colorCode = first_siblings.index('colourCode')
    first_siblings.pop(colorCode)
    bulletin = encoder.encode(test)
    result = bulletin.pop()

    assert len(result) == len(first_siblings)
    for num, child in enumerate(result):
        assert child.tag == first_siblings[num]

    first_siblings.insert(colorCode, 'colorCode')

    assert result.get('permissibleUsage') == 'OPERATIONAL'
    assert result.get('permissibleUsageReason') is None
    tree = ET.XML(ET.tostring(result))

    for cnt, element in enumerate(tree):

        if cnt == 0:
            timePosition = element.find('%stimePosition' % find_gml)
            assert timePosition.text == '2020-05-29T06:15:00Z'
        elif cnt == 1:
            name = element.find('%sname' % find_aixm)
            assert name.text == 'BUENOS AIRES'
        elif cnt == 2:
            name = element.find('.//*{http://def.wmo.int/metce/2013}name')
            assert name.text == 'SABANCAYA 354006'
            position = element.find('%spos' % find_gml)
            assert position.text == '-15.783 -71.834'
            edate = element.find('.//*{http://def.wmo.int/metce/2013}eruptionDate')
            assert edate.text == '2020-05-29T06:15:00Z'
        elif cnt == 3:
            assert element.text == 'PERU'
        elif cnt == 4:
            assert element.text == '19576'
            assert element.get('uom') == '[ft_i]'
        elif cnt == 5:
            assert element.text == '2020/635'
        elif cnt == 6:
            assert element.text == 'GOES-E. GFS. WEBCAM.'
        elif cnt == -7:
            assert element.get('nilReason') == codes[des.NIL][des.WTHLD][0]
        elif cnt == 7:
            assert element.text == 'CONTINUOUS EMISSION'
        elif cnt == 8:

            assert element[0].get('status') == 'IDENTIFIABLE'
            assert element[0].get('isEstimated') == 'false'
            timePosition = element.find('%stimePosition' % find_gml)
            assert timePosition.text == '2020-05-29T05:10:00Z'
            ashCloudList = element.findall('%sashCloud' % find_iwxxm)
            assert len(ashCloudList) == 1

            for acnt, ashCloud in enumerate(ashCloudList):

                volume = ashCloud.find('%sAirspaceVolume' % find_aixm)
                if acnt == 0:
                    assert volume[0].tag == '%supperLimit' % aixm
                    assert volume[1].tag == '%supperLimitReference' % aixm
                    assert volume[2].tag == '%slowerLimit' % aixm
                    assert volume[3].tag == '%slowerLimitReference' % aixm
                    assert volume[0].text == '240'
                    assert volume[1].text == 'STD'
                    assert volume[2].text == 'GND'
                    assert volume[3].text == 'SFC'
                    assert ashCloud[0][1].tag == '%sdirectionOfMotion' % iwxxm
                    assert ashCloud[0][2].tag == '%sspeedOfMotion' % iwxxm
                    assert ashCloud[0][1].text == '135'
                    assert ashCloud[0][2].text == '20'
                    assert ashCloud[0][2].get('uom') == '[kn_i]'

        elif 8 < cnt < 12:
            timePosition = element.find('%stimePosition' % find_gml)
            assert element[0].get('status') == 'PROVIDED'
            ashCloud = element.find('%sashCloud' % find_iwxxm)
            volume = ashCloud.find('%sAirspaceVolume' % find_aixm)
            assert volume[0].tag == '%supperLimit' % aixm
            assert volume[1].tag == '%supperLimitReference' % aixm
            assert volume[2].tag == '%slowerLimit' % aixm
            assert volume[3].tag == '%slowerLimitReference' % aixm
            assert volume[0].text == '240'
            assert volume[1].text == 'STD'
            assert volume[2].text == 'GND'
            assert volume[3].text == 'SFC'

            if cnt == 9:
                assert timePosition.text == '2020-05-29T11:00:00Z'
            elif cnt == 10:
                assert timePosition.text == '2020-05-29T17:00:00Z'
            elif cnt == 11:
                assert timePosition.text == '2020-05-29T23:00:00Z'

        elif cnt == 12:
            assert len(element.text) > 80
        elif cnt == 13:
            timePosition = element.find('%stimePosition' % find_gml)
            assert timePosition.text == '2020-05-29T12:15:00Z'
            assert timePosition.get('indeterminatePosition') == 'before'


def test_unknowns():

    test = """FVAU03 ADRM 150252
VA ADVISORY
DTG: 20200615/0252Z
VAAC: DARWIN
VOLCANO: SEMERU 263300
PSN: S0806 E11255
AREA: UNKNOWN
SUMMIT ELEV: UNKNOWN
ADVISORY NR: 2020/96
INFO SOURCE: CVGHM, HIMAWARI-8
AVIATION COLOUR CODE: ORANGE
ERUPTION DETAILS: NO ERUPTION - RE-SUSPENDED ASH
OBS VA DTG: 15/0252Z
OBS VA CLD: VA NOT IDENTIFIABLE FM SATELLITE DATA WIND SFC/FL050 090/10MPS
FCST VA CLD +6 HR: 15/0852Z NO VA EXP
FCST VA CLD +12 HR: 15/1452Z NO VA EXP
FCST VA CLD +18 HR: 15/2052Z NO VA EXP
RMK: RE-SUSPENDED ASH
NXT ADVISORY: NO FURTHER ADVISORIES
"""
    bulletin = encoder.encode(test)
    result = bulletin.pop()
    tree = ET.XML(ET.tostring(result))

    element = tree.find('%sstateOrRegion' % iwxxm)
    assert element.get('nilReason') == codes[des.NIL][des.UNKNWN][0]
    element = tree.find('%ssummitElevation' % iwxxm)
    assert element.get('nilReason') == codes[des.NIL][des.UNKNWN][0]

    test = """FVAU03 ADRM 150252
VA ADVISORY
DTG: 20200615/0252Z
VAAC: DARWIN
VOLCANO: SEMERU 263300
PSN: S0806 E11255
AREA: INDONESIA
SUMMIT ELEV: SFC
ADVISORY NR: 2020/96
INFO SOURCE: CVGHM, HIMAWARI-8
AVIATION COLOUR CODE: ORANGE
ERUPTION DETAILS: GROUND REPORT OF VA ERUPTION TO FL130 AT
15/0237Z
OBS VA DTG: 15/0252Z
OBS VA CLD: VA NOT IDENTIFIABLE FM SATELLITE DATA WIND SFC/FL050 VRB10MPS
FCST VA CLD +6 HR: 15/0852Z NO VA EXP
FCST VA CLD +12 HR: 15/1452Z NO VA EXP
FCST VA CLD +18 HR: 15/2052Z NO VA EXP
RMK: CVGHM VONA REPORTS ERUPTION TO FL130 MOVING TO WEST AT
15/0237Z, HOWEVER VA CANNOT BE IDENTIFIED ON SATELLITE
IMAGERY DUE TO MET CLOUD IN AREA. ADVISORY WILL BE UPDATED
IF NEW INFORMATION IS RECEIVED.
NXT ADVISORY: NO FURTHER ADVISORIES
"""
    bulletin = encoder.encode(test)
    result = bulletin.pop()
    tree = ET.XML(ET.tostring(result))

    element = tree.find('%ssummitElevation' % iwxxm)
    assert element.get('nilReason') == codes[des.NIL][des.NA][0]


def test_resuspendedash():

    test = """FVAU03 ADRM 150252
VA ADVISORY
DTG: 20200615/0252Z
VAAC: DARWIN
VOLCANO: SEMERU 263300
PSN: S0806 E11255
AREA: UNKNOWN
SUMMIT ELEV: SFC
ADVISORY NR: 2020/96
INFO SOURCE: CVGHM, HIMAWARI-8
AVIATION COLOUR CODE: ORANGE
ERUPTION DETAILS: NO ERUPTION - RE-SUSPENDED ASH
OBS VA DTG: 15/0252Z
OBS VA CLD: VA NOT IDENTIFIABLE FM SATELLITE DATA WIND SFC/FL050 090/10MPS
FCST VA CLD +6 HR: 15/0852Z NO VA EXP
FCST VA CLD +12 HR: 15/1452Z NO VA EXP
FCST VA CLD +18 HR: 15/2052Z NO VA EXP
RMK: RE-SUSPENDED ASH
NXT ADVISORY: NO FURTHER ADVISORIES
"""
    bulletin = encoder.encode(test)
    result = bulletin.pop()
    tree = ET.XML(ET.tostring(result))

    element = tree.find('%sstateOrRegion' % iwxxm)
    assert element.get('nilReason') == codes[des.NIL][des.UNKNWN][0]
    element = tree.find('%ssummitElevation' % iwxxm)
    assert element.get('nilReason') == codes[des.NIL][des.NA][0]


if __name__ == '__main__':

    test_vaaFailureModes()
    test_vaaNoWinds()
    test_vaaWndDirection()
    test_vaaTest()
    test_vaaExercise()
    test_vaaNormal()
    test_unknowns()
    test_resuspendedash()
