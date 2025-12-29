import xml.etree.ElementTree as ET

import gifts.VAA as VAAE
from gifts.common import xmlConfig as des
from gifts.common import xmlUtilities as deu

encoder = VAAE.Encoder()

first_siblings = ['issueTime', 'issuingVolcanicAshAdvisoryCentre', 'volcano', 'stateOrRegion', 'sourceElevationAMSL',
                  'advisoryNumber', 'informationSource', 'eruptionDetails', 'observation', 'forecast',
                  'forecast', 'forecast', 'remarks', 'nextAdvisoryTime']

aixm = '{http://www.aixm.aero/schema/5.1.1}'
find_aixm = './/*%s' % aixm
find_gml = './/*{http://www.opengis.net/gml/3.2}'
iwxxm = '{%s}' % des.IWXXM_URI

exercise = """FVAU03 ADRM 150252
VA ADVISORY
STATUS: EXERCISE
DTG: 20251215/0000Z
VAAC: NONE
VOLCANO: UNKNOWN
PSN: UNKNOWN
AREA: UNKNOWN
SOURCE ELEV: UNKNOWN
ADVISORY NR: 0000/0
INFO SOURCE: NONE
ERUPTION DETAILS: NONE
EST VA DTG: NOT PROVIDED
EST VA CLD: NOT PROVIDED
FCST VA CLD +6HR: 15/0600ZNOT PROVIDED
FCST VA CLD +12HR: 15/1200Z NOT AVBL
FCST VA CLD +18HR: 15/1800Z NO VA EXP
RMK: NONE
NXT ADVISORY: NO FURTHER ADVISORIES"""

fuego = """FVXX23 KNES 171857
VA ADVISORY
DTG: 20251217/1857Z
VAAC: WASHINGTON
VOLCANO: FUEGO 342090
PSN: N1428 W09052
AREA: GUATEMALA
SOURCE ELEV: 12346 FT AMSL
ADVISORY NR: 2025/682
INFO SOURCE: GOES-19. NWP MODELS.
ERUPTION DETAILS: ONGOING VA EMS
OBS VA DTG: 17/1830Z
OBS VA CLD: SFC/FL140 N1431 W09105 - N1428 W09052
- N1428 W09052 - N1427 W09105 - N1431 W09105 MOV
W 10KT
FCST VA CLD +6HR: 18/0030Z SFC/FL140 N1432 W09105
- N1428 W09053 - N1428 W09052 - N1426 W09105 -
N1432 W09105
FCST VA CLD +12HR: 18/0630Z SFC/FL140 N1432
W09105 - N1428 W09053 - N1428 W09052 - N1426
W09105 - N1432 W09105
FCST VA CLD +18HR: 18/1230Z SFC/FL140 N1432
W09105 - N1428 W09053 - N1428 W09053 - N1426
W09105 - N1432 W09105
RMK: VA NOT DETECTED ON STLT DUE TO WX CLDS IN
SUMMIT AREA. VA EMS LIKELY CONTINUE GIVEN RECENT
ACTVTY. NO CHG FCST TO MDL WINDS AT FL NXT 18 HR.
...KONON
NXT ADVISORY: WILL BE ISSUED BY 20251218/0115Z"""

semeru = """FVAU03 ADRM 150252
VA ADVISORY
DTG: 20200615/0252Z
VAAC: DARWIN
VOLCANO: SEMERU 263300
PSN: S0806 E11255
AREA: INDONESIA
SOURCE ELEV: 3676M AMSL
ADVISORY NR: 2020/96
INFO SOURCE: CVGHM, HIMAWARI-8
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
NXT ADVISORY: NO FURTHER ADVISORIES"""

#
# Get WMO NIL reason code concepts
codes = deu.parseCodeRegistryTables(des.CodesFilePath, [des.NIL])
des.TRANSLATOR = True


def test_vaaFailureModes():

    import gifts.vaaDecoder as vD
    decoder = vD.Decoder()

    text = """FVXX23 KNES 151247
"""
    result = decoder(text)
    assert 'err_msg' in result

    text = """FVXX01 LFPW 311315 RRA
VA ADVISORY
VAAC: TOULOUSE"""

    bulletin = encoder.encode(text)
    result = bulletin.pop()
    assert len(result) == 2
    for num, child in enumerate(result):
        assert child.tag == first_siblings[num]
    assert len(result.get('translationFailedTAC')) > 0

    text = """FVXX01 LFPW 311315 RRA
VA ADVISORY
DTG: 20191231/1315Z
VAAC: TOULOUSE
<--PARSER HALTS HERE"""

    bulletin = encoder.encode(text)
    result = bulletin.pop()
    assert len(result) == 2
    for num, child in enumerate(result):
        assert child.tag == first_siblings[num]
    assert len(result.get('translationFailedTAC')) > 0


def test_nonOperationalMessages():

    text = """FVXX23 KNES 151247
VA ADVISORY
STATUS: TEST"""

    bulletin = encoder.encode(text)
    result = bulletin.pop()
    assert len(result) == 2
    for num, child in enumerate(result):
        assert child.tag == first_siblings[num]

    assert result.get('permissibleUsage') == 'NON-OPERATIONAL'
    assert result.get('permissibleUsageReason') == 'TEST'

    text = exercise

    bulletin = encoder.encode(text)
    result = bulletin.pop()

    assert result.get('permissibleUsage') == 'NON-OPERATIONAL'
    assert result.get('permissibleUsageReason') == 'EXERCISE'

    tree = ET.XML(ET.tostring(result))
    #
    # Check all mandatory items
    for cnt, child in enumerate(result):
        assert child.tag == first_siblings[cnt]
    #
    # Look at each child element in detail
    for cnt, element in enumerate(tree):
        #
        # issueTime
        if cnt == 0:
            timePosition = element.find('%stimePosition' % find_gml)
            assert timePosition.text == '2025-12-15T00:00:00Z'
        #
        # issuing centre
        elif cnt == 1:
            name = element.find('%sname' % find_aixm)
            assert name.text == 'NONE'
            mwotype = element.find('%stype' % find_aixm)
            assert mwotype.text == 'OTHER:VAAC'
        #
        # volcano details
        elif cnt == 2:
            volcano = element.find('{http://def.wmo.int/metce/2013}Volcano')
            assert volcano is not None

            name = element.find('*{http://def.wmo.int/metce/2013}name')
            assert name.text == 'UNKNOWN'

            position = element.find('*{http://def.wmo.int/metce/2013}position')
            assert position.get('nilReason') == codes[des.NIL][des.UNKNWN][0]

            edate = element.find('*{http://def.wmo.int/metce/2013}eruptionDate')
            assert edate is None
        #
        # stateOrRegion element
        elif cnt == 3:
            assert element.get('nilReason') == codes[des.NIL][des.UNKNWN][0]
        #
        # sourceElevation element
        elif cnt == 4:
            assert element.get('nilReason') == codes[des.NIL][des.UNKNWN][0]
        #
        # advisory no.
        elif cnt == 5:
            assert element.text == '0000/0'
        #
        # source and eruption details free text
        elif 5 < cnt < 8:
            assert element.text == 'NONE'
        #
        # observation
        elif cnt == 8:
            assert len(element) == 1
            # conditions estimated
            conditions = element.find('%sVolcanicAshObservedOrEstimatedConditions' % iwxxm)
            assert conditions.get('status') == 'NOT_PROVIDED'
            assert conditions.get('isEstimated') == 'true'
        #
        # forecasts
        elif 8 < cnt < 12:
            condition = element.find('%sVolcanicAshForecastConditions' % iwxxm)
            timePosition = element.find('%stimePosition' % find_gml)
            if cnt == 9:
                assert condition.get('status') == 'NOT_PROVIDED'
                assert timePosition.text == '2025-12-15T06:00:00Z'
            elif cnt == 10:
                assert condition.get('status') == 'NOT_AVAILABLE'
                assert timePosition.text == '2025-12-15T12:00:00Z'
            elif cnt == 11:
                assert condition.get('status') == 'NO_VOLCANIC_ASH_EXPECTED'
                assert timePosition.text == '2025-12-15T18:00:00Z'

        elif cnt == 12:
            # remarks
            assert element.text == 'NONE'
        elif cnt == 13:
            # NO FURTHER ADVISORIES
            assert element.get('nilReason') == codes[des.NIL][des.NA][0]

    text2 = text.replace('EST VA CLD: NOT PROVIDED', 'OBS VA CLD: NOT AVBL')
    bulletin = encoder.encode(text2)
    result = bulletin.pop()

    assert result[8][0].get('isEstimated') == 'false'
    assert result[8][0].get('status') == 'NOT_AVAILABLE'


def test_sourceElevation():

    text = fuego
    bulletin = encoder.encode(text)
    result = bulletin.pop()

    assert result.get('permissibleUsage') == 'OPERATIONAL'
    assert result.get('reportStatus') == 'NORMAL'
    #
    # Check all mandatory items
    for cnt, child in enumerate(result):
        assert child.tag == first_siblings[cnt]
    #
    # Source elevation
    sourceElevation = result[4]
    assert sourceElevation.text == '12346'
    assert sourceElevation.get('uom', '[ft_i]')

    text = fuego.replace('12346 FT', '3763M')
    bulletin = encoder.encode(text)
    result = bulletin.pop()

    sourceElevation = result[4]
    assert sourceElevation.text == '3763'
    assert sourceElevation.get('uom', 'm')

    text = fuego.replace('12346 FT AMSL', '10M BLW MSL')
    bulletin = encoder.encode(text)
    result = bulletin.pop()

    sourceElevation = result[4]
    assert sourceElevation.text == '-10'
    assert sourceElevation.get('uom', 'm')

    text = fuego.replace('12346 FT AMSL', '0M')
    bulletin = encoder.encode(text)
    result = bulletin.pop()

    sourceElevation = result[4]
    assert sourceElevation.text == '0'
    assert sourceElevation.get('uom', 'm')


def test_volcanoInfo():

    text = fuego
    bulletin = encoder.encode(text)
    result = bulletin.pop()

    volcano = result[2][0]
    assert len(volcano) == 2
    assert volcano.tag == 'Volcano'
    assert volcano[0].text == 'FUEGO 342090'
    assert volcano[1][0][0].text == '14.467 -90.867'

    text = fuego.replace('ONGOING VA EMS', 'ERUPTION AT 0530Z')
    bulletin = encoder.encode(text)
    result = bulletin.pop()

    volcano = result[2][0]
    assert len(volcano) == 3
    assert volcano.tag == 'EruptingVolcano'
    assert volcano[2].text == '2025-12-17T05:30:00Z'


def test_centreName():

    text = fuego
    bulletin = encoder.encode(text)
    result = bulletin.pop()
    #
    # AIXM padding
    centre = result[1][0][0][0][2]
    assert centre.text == 'WASHINGTON'


def test_stateOrRegion():

    text = fuego
    bulletin = encoder.encode(text)
    result = bulletin.pop()

    state = result[3]
    assert state.text == 'GUATEMALA'


def test_advisoryNumber():

    text = fuego
    bulletin = encoder.encode(text)
    result = bulletin.pop()

    state = result[5]
    assert state.text == '2025/682'


def test_infoSource():

    text = fuego
    bulletin = encoder.encode(text)
    result = bulletin.pop()

    infoSource = result[6]
    assert infoSource.text == 'GOES-19. NWP MODELS.'


def test_eruptionDetails():

    text = fuego
    bulletin = encoder.encode(text)
    result = bulletin.pop()

    infoSource = result[7]
    assert infoSource.text == 'ONGOING VA EMS'


def test_remarks():

    text = fuego
    bulletin = encoder.encode(text)
    result = bulletin.pop()

    remarks = result[12]
    assert remarks.text == ' '.join(['VA NOT DETECTED ON STLT DUE TO WX CLDS IN SUMMIT AREA.',
                                     'VA EMS LIKELY CONTINUE GIVEN RECENT ACTVTY.',
                                     'NO CHG FCST TO MDL WINDS AT FL NXT 18 HR.', '...KONON'])


def test_nextTime():

    text = fuego
    bulletin = encoder.encode(text)
    result = bulletin.pop()

    nextTime = result[13][0][0]

    assert nextTime.text == '2025-12-18T01:15:00Z'
    assert nextTime.get('indeterminatePosition') == 'before'

    text = fuego.replace('WILL BE ISSUED BY', 'NO LATER THAN')
    bulletin = encoder.encode(text)
    result = bulletin.pop()

    nextTime = result[13][0][0]
    assert nextTime.get('indeterminatePosition') == 'before'

    text = fuego.replace('WILL BE ISSUED BY', '')
    bulletin = encoder.encode(text)
    result = bulletin.pop()

    nextTime = result[13][0][0]
    assert nextTime.get('indeterminatePosition') is None


def test_observedCloudVerticalExtent():

    text = fuego
    bulletin = encoder.encode(text)
    result = bulletin.pop()

    observation = result[8][0]

    assert observation.get('isEstimated') == 'false'
    assert observation.get('status') == 'PROVIDED'
    assert observation[0][0][0].text == '2025-12-17T18:30:00Z'

    obsAshCloud = observation[1][0][0][0]
    assert obsAshCloud[0].tag == 'aixm:upperLimit'
    assert obsAshCloud[0].get('uom') == 'FL'
    assert obsAshCloud[0].text == '140'
    assert obsAshCloud[1].tag == 'aixm:upperLimitReference'
    assert obsAshCloud[1].text == 'STD'

    assert obsAshCloud[2].tag == 'aixm:lowerLimit'
    assert obsAshCloud[2].get('uom') is None
    assert obsAshCloud[2].text == 'GND'
    assert obsAshCloud[3].tag == 'aixm:lowerLimitReference'
    assert obsAshCloud[3].text == 'SFC'

    text = fuego.replace('OBS VA CLD: SFC/FL140', 'OBS VA CLD: TOP FL500')
    bulletin = encoder.encode(text)
    result = bulletin.pop()

    obsAshCloud = result[8][0][1][0][0][0]
    assert obsAshCloud[0].tag == 'aixm:upperLimit'
    assert obsAshCloud[0].get('uom') == 'FL'
    assert obsAshCloud[0].text == '500'
    assert obsAshCloud[1].tag == 'aixm:upperLimitReference'
    assert obsAshCloud[1].text == 'STD'

    assert obsAshCloud[2].tag == 'aixm:lowerLimit'
    assert obsAshCloud[2].get('nilReason') == des.MSSG

    text = fuego.replace('OBS VA CLD: SFC/FL140', 'OBS VA CLD: FL050/250')
    bulletin = encoder.encode(text)
    result = bulletin.pop()

    obsAshCloud = result[8][0][1][0][0][0]
    assert obsAshCloud[0].tag == 'aixm:upperLimit'
    assert obsAshCloud[0].get('uom') == 'FL'
    assert obsAshCloud[0].text == '250'
    assert obsAshCloud[1].tag == 'aixm:upperLimitReference'
    assert obsAshCloud[1].text == 'STD'

    assert obsAshCloud[2].tag == 'aixm:lowerLimit'
    assert obsAshCloud[2].get('uom') == 'FL'
    assert obsAshCloud[2].text == '50'
    assert obsAshCloud[3].tag == 'aixm:lowerLimitReference'
    assert obsAshCloud[3].text == 'STD'


def test_observedAshCloudMotions():

    text = fuego
    bulletin = encoder.encode(text)
    result = bulletin.pop()

    obsMovementDir = result[8][0][1][0][1]
    assert obsMovementDir.get('uom') == 'deg'
    assert obsMovementDir.text == '270'
    obsMovementSpd = result[8][0][1][0][2]
    assert obsMovementSpd.get('uom') == '[kn_i]'
    assert obsMovementSpd.text == '10'

    text = fuego.replace('W 10KT', 'SE 40KMH')
    bulletin = encoder.encode(text)
    result = bulletin.pop()

    obsMovementDir = result[8][0][1][0][1]
    assert obsMovementDir.text == '135'
    obsMovementSpd = result[8][0][1][0][2]
    assert obsMovementSpd.get('uom') == 'km/h'
    assert obsMovementSpd.text == '40'


def test_observedCloudHorizontalExtent():

    text = fuego
    bulletin = encoder.encode(text)
    result = bulletin.pop()

    observation = result[8][0]
    obsAshCloud = observation[1][0][0][0]

    aixmHProj = obsAshCloud[4]
    assert aixmHProj.tag == 'aixm:horizontalProjection'

    polygonCoords = aixmHProj[0][0][0][0][0][0]
    assert polygonCoords.get('count') == '5'

    latlongpairs = polygonCoords.text
    assert latlongpairs[:14] == latlongpairs[-14:]


def test_vaCldNotFound():

    text = semeru
    bulletin = encoder.encode(text)
    result = bulletin.pop()

    observation = result[8][0]
    assert observation.get('status') == 'NOT_IDENTIFIABLE'
    assert len(observation) == 1
    assert observation[0].tag == 'phenomenonTime'

    text = semeru.replace('DATA', 'DATA WIND FL005/010 000/00MPS')
    bulletin = encoder.encode(text)
    result = bulletin.pop()
    observation = result[8][0]
    assert len(observation) == 2
    wind = observation[1]

    assert wind.tag == 'wind'
    assert wind[0].tag == 'WindObservedOrEstimated'
    assert wind[0].get('variableWindDirection') == 'false'
    assert wind[0][0].tag == 'verticalLayer'
    assert wind[0][1].tag == 'windDirection'
    assert wind[0][1].text == '000'
    assert wind[0][1].get('uom') == 'deg'
    assert wind[0][2].tag == 'windSpeed'
    assert wind[0][2].text == '00'
    assert wind[0][2].get('uom') == 'm/s'

    text = semeru.replace('DATA', 'DATA WIND FL005/010 VRB12KT')
    bulletin = encoder.encode(text)
    result = bulletin.pop()
    observation = result[8][0][1][0]
    assert observation.get('variableWindDirection') == 'true'
    assert len(observation) == 2
    assert observation[0].tag == 'verticalLayer'
    assert observation[1].tag == 'windSpeed'
    assert observation[1].text == '12'
    assert observation[1].get('uom') == '[kn_i]'


if __name__ == '__main__':

    test_vaaFailureModes()
    test_nonOperationalMessages()
    test_sourceElevation()
    test_volcanoInfo()
    test_centreName()
    test_stateOrRegion()
    test_advisoryNumber()
    test_infoSource()
    test_eruptionDetails()
    test_remarks()
    test_nextTime()
    test_observedCloudVerticalExtent()
    test_observedAshCloudMotions()
    test_observedCloudHorizontalExtent()
    test_vaCldNotFound()
