import xml.etree.ElementTree as ET

from gifts.TAF import Encoder as TE
import gifts.tafDecoder as tD

import gifts.common.xmlConfig as des
import gifts.common.xmlUtilities as deu

reqCodes = [des.WEATHER, des.CLDAMTS, des.CVCTNCLDS]
codes = deu.parseCodeRegistryTables(des.CodesFilePath, reqCodes)

iwxxm = '{http://icao.int/iwxxm/3.0}'
find_iwxxm = './/*%s' % iwxxm
xhref = '{http://www.w3.org/1999/xlink}href'
xtitle = '{http://www.w3.org/1999/xlink}title'

missing = codes[des.NIL][des.MSSG]
nothingOfOperationalSignificance = codes[des.NIL][des.NOOPRSIG]
noSignificantChange = codes[des.NIL][des.NOSIGC]

database = {
    'SBAF': 'AFONSOS ARPT MI|||-22.87 -43.37',
    'VHHH': 'HONG KONG INTERNATIONAL AP|HKG||22.309 113.914 9'}


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


encoder = TE(database)

des.TRANSLATOR = True


def test_tafFailureModes():
    test = """FTCN01 VHHH 151200
"""
    bulletin = encoder.encode(test)
    assert len(bulletin) == test.count('\n') - 1

    for cnt, result in enumerate(bulletin):
        assert result.get('translationFailedTAC') is not None
        assert len(result) == 3
        for child, tag in zip(result, ['issueTime', 'aerodrome', 'validPeriod']):
            assert child.tag == 'iwxxm:%s' % tag

    test = """FTCN01 VHHH 311300
TAF VHHH 31138Z= stops due to bad issue timestamp
TAF SBAF NIL= stops due to no issue timestamp
"""

    bulletin = encoder.encode(test)
    assert len(bulletin) == test.count('\n') - 1

    for cnt, result in enumerate(bulletin):
        assert result.get('translationFailedTAC') is not None
        assert len(result) == 3
        for child, tag in zip(result, ['issueTime', 'aerodrome', 'validPeriod']):
            assert child.tag == 'iwxxm:%s' % tag

    test = """FTCN01 VHHH 311300
TAF VHHH 311338Z COR= stops due to wrong order of elements
"""

    bulletin = encoder.encode(test)
    assert len(bulletin) == test.count('\n') - 1

    for cnt, result in enumerate(bulletin):
        assert result.get('translationFailedTAC') is not None
        assert len(result) == 3
        for child, tag in zip(result, ['issueTime', 'aerodrome', 'validPeriod']):
            assert child.tag == 'iwxxm:%s' % tag

    test = """FTCN01 VHHH 311900
TAF VHHH 311938Z 3120/0202 REMARKS LIKE THIS ONE DO NOT BELONG IN ANNEX 3 TAFS=
                          ^--PARSER HALTS HERE"""

    bulletin = encoder.encode(test)
    assert len(bulletin) == test.count('\n') - 1

    for cnt, result in enumerate(bulletin):
        assert result.get('translationFailedTAC') is not None
        assert len(result) == 3
        for child, tag in zip(result, ['issueTime', 'aerodrome', 'validPeriod']):
            assert child.tag == 'iwxxm:%s' % tag

    test = """FTCN01 VHHH 311900
TAF SBAF 302130Z 3100/3124 15003KT 9000 SHRA FEW015CB SCT018 FM311200 VRB02KT 9999 VCSH SCT022=
"""
    bulletin = encoder.encode(test)
    assert len(bulletin) == test.count('\n') - 1

    for cnt, result in enumerate(bulletin):
        assert result.get('translationFailedTAC') is not None
        assert len(result) == 3
        for child, tag in zip(result, ['issueTime', 'aerodrome', 'validPeriod']):
            assert child.tag == 'iwxxm:%s' % tag


def test_nil():

    test = """FTXX01 LFKJ 072000
TAF SBAF 072000Z NIL=
"""

    bulletin = encoder.encode(test)
    assert len(bulletin) == test.count('\n') - 1

    for cnt, result in enumerate(bulletin):
        assert result.get('translationFailedTAC') is None
        assert len(result) == 3
        for child, tag in zip(result, ['issueTime', 'aerodrome', 'baseForecast']):
            assert child.tag == 'iwxxm:%s' % tag


def test_cnl():

    test = """FTXX01 LFKJ 072000
TAF AMD SBAF 072001Z 0715/0815 CNL=
TAF SBAF 072000Z 0715/0815 CNL=
"""

    bulletin = encoder.encode(test)
    assert len(bulletin) == test.count('\n') - 1

    for cnt, result in enumerate(bulletin):

        assert result.get('translationFailedTAC') is None
        assert len(result) == 3
        assert result.get('isCancelReport') == 'true'
        if cnt == 0:
            assert result.get('reportStatus') == 'AMENDMENT'

        for child, tag in zip(result, ['issueTime', 'aerodrome', 'cancelledReportValidPeriod']):
            assert child.tag == 'iwxxm:%s' % tag


def test_ignoreRmks():

    test = """FTXX01 LFKJ 072000
TAF SBAF 072001Z 0715/0815 00000KT CAVOK RMK IS IGNORED=
"""

    bulletin = encoder.encode(test)
    assert len(bulletin) == test.count('\n') - 1
    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None
    assert len(result) == 4
    for child, tag in zip(result, ['issueTime', 'aerodrome', 'validPeriod', 'baseForecast']):
        assert child.tag == 'iwxxm:%s' % tag


def test_offNominalCase():

    test = """FTXX99 XXXX 260000
TAF SBAF 1118/1224 22010KT CAVOK TEMPO 1209/1218 26010G20KT 9999 FEW030=
"""
    bulletin = encoder.encode(test)
    assert len(bulletin) == test.count('\n') - 1
    result = bulletin.pop()
    assert result.get('translationFailedTAC') is not None
    assert len(result) == 3
    assert result[0].tag == 'iwxxm:issueTime'
    assert result[0].text is None
    assert result[1].tag == 'iwxxm:aerodrome'
    assert result[2].tag == 'iwxxm:validPeriod'
    assert result[2].text is None


def test_wind():

    test = """FTXX01 LFKJ 072000
TAF SBAF 071500Z 0718/0806 VRB06KT 9999 SCT025=
TAF SBAF 071500Z 0718/0806 01006G20KT CAVOK=
TAF SBAF 071500Z 0718/0806 010P50MPS CAVOK=
TAF SBAF 071500Z 0718/0806 010130GP150KT CAVOK=
"""

    bulletin = encoder.encode(test)
    assert len(bulletin) == test.count('\n') - 1
    for cnt, result in enumerate(bulletin):
        assert result.get('translationFailedTAC') is None
        tree = ET.XML(ET.tostring(result))
        wind = tree.find('%sAerodromeSurfaceWindForecast' % find_iwxxm)
        if cnt == 0:
            assert wind.get('variableWindDirection') == 'true'
            assert wind[0].tag == '%smeanWindSpeed' % iwxxm
            assert wind[0].get('uom') == '[kn_i]'
            assert wind[0].text == '6'
        elif cnt == 1:
            assert wind.get('variableWindDirection') == 'false'
            assert wind[0].tag == '%smeanWindDirection' % iwxxm
            assert wind[0].get('uom') == 'deg'
            assert wind[0].text == '10'
            assert wind[1].text == '6'
            assert wind[2].tag == '%swindGustSpeed' % iwxxm
            assert wind[2].get('uom') == '[kn_i]'
            assert wind[2].text == '20'
        elif cnt == 2:
            assert wind[1].get('uom') == 'm/s'
            assert wind[1].text == '50'
            assert wind[2].tag == '%smeanWindSpeedOperator' % iwxxm
            assert wind[2].text == 'ABOVE'
        elif cnt == 3:
            assert wind[1].get('uom') == '[kn_i]'
            assert wind[1].text == '130'
            assert wind[2].tag == '%swindGustSpeed' % iwxxm
            assert wind[2].text == '150'
            assert wind[3].tag == '%swindGustSpeedOperator' % iwxxm
            assert wind[3].text == 'ABOVE'


def test_vsby():

    test = """FTXX01 LFKJ 072000
TAF SBAF 071500Z 0718/0806 00000KT 9999 FEW025=
TAF SBAF 071500Z 0718/0806 00000KT P6SM FEW025=
TAF SBAF 071500Z 0718/0806 00000KT 0000 FEW025=
TAF SBAF 071500Z 0718/0806 00000KT 0SM FEW025=
TAF SBAF 071500Z 0718/0806 00000KT 21/2SM FEW025=
TAF SBAF 071500Z 0718/0806 00000KT 2 1/2SM FEW025=
TAF SBAF 071500Z 0718/0806 00000KT 1/4SM FEW025=
"""

    bulletin = encoder.encode(test)
    assert len(bulletin) == test.count('\n') - 1
    for cnt, result in enumerate(bulletin):
        assert result.get('translationFailedTAC') is None
        tree = ET.XML(ET.tostring(result))
        vsby = tree.find('%sprevailingVisibility' % find_iwxxm)
        if cnt < 2:
            assert vsby.get('uom') == 'm'
            assert vsby.text == '10000'
            oper = tree.find('%sprevailingVisibilityOperator' % find_iwxxm)
            assert oper is not None
            assert oper.text == 'ABOVE'
        elif cnt < 4:
            assert vsby.get('uom') == 'm'
            assert vsby.text == '0'
            oper = tree.find('%sprevailingVisibilityOperator' % find_iwxxm)
            assert oper is None
        elif cnt < 6:
            assert vsby.get('uom') == 'm'
            assert vsby.text == '4000'
            oper = tree.find('%sprevailingVisibilityOperator' % find_iwxxm)
            assert oper is None
        else:
            assert vsby.get('uom') == 'm'
            assert vsby.text == '400'
            oper = tree.find('%sprevailingVisibilityOperator' % find_iwxxm)
            assert oper is None


def test_pcp():

    test = """FTXX01 LFKJ 072000
TAF SBAF 071500Z 0718/0806 00000KT 9999 -FZRA -SN SHGS FEW025=
TAF SBAF 071500Z 0718/0806 00000KT P6SM -SHRA TS BLDU FEW025=
TAF SBAF 071500Z 0718/0806 00000KT P6SM BLSN BR FEW025=
"""

    des.TITLES = des.Weather
    bulletin = encoder.encode(test)
    assert len(bulletin) == test.count('\n') - 1
    for cnt, result in enumerate(bulletin):
        assert result.get('translationFailedTAC') is None
        tree = ET.XML(ET.tostring(result))
        pcpnList = tree.findall('%sweather' % find_iwxxm)
        if cnt == 0:
            assert len(pcpnList) == 3
            assert pcpnList[0].get(xhref) == codes[des.WEATHER]['-FZRA'][0]
            assert pcpnList[0].get(xtitle) == codes[des.WEATHER]['-FZRA'][1]
            assert pcpnList[1].get(xhref) == codes[des.WEATHER]['-SN'][0]
            assert pcpnList[1].get(xtitle) == codes[des.WEATHER]['-SN'][1]
            assert pcpnList[2].get(xhref) == codes[des.WEATHER]['SHGS'][0]
            assert pcpnList[2].get(xtitle) == codes[des.WEATHER]['SHGS'][1]

        elif cnt == 1:
            assert len(pcpnList) == 3
            assert pcpnList[0].get(xhref) == codes[des.WEATHER]['-SHRA'][0]
            assert pcpnList[1].get(xhref) == codes[des.WEATHER]['TS'][0]
            assert pcpnList[2].get(xhref) == codes[des.WEATHER]['BLDU'][0]

        elif cnt == 2:
            assert len(pcpnList) == 2
            assert pcpnList[0].get(xhref) == codes[des.WEATHER]['BLSN'][0]
            assert pcpnList[1].get(xhref) == codes[des.WEATHER]['BR'][0]


def test_sky():

    test = """FTXX01 LFKJ 072000
TAF SBAF 071500Z 0718/0806 00000KT 9999 FEW025CB SCT030TCU BKN035 OVC040=
TAF SBAF 071500Z 0718/0806 00000KT 9999 VV///=
TAF SBAF 071500Z 0718/0806 00000KT 9999 VV001=
TAF SBAF 071500Z 0718/0806 00000KT 9999 NSC=
"""

    des.TITLES = (des.CloudAmt | des.CloudType)
    bulletin = encoder.encode(test)
    assert len(bulletin) == test.count('\n') - 1
    for cnt, result in enumerate(bulletin):
        assert result.get('translationFailedTAC') is None
        tree = ET.XML(ET.tostring(result))
        cldLyrList = tree.findall('%sCloudLayer' % find_iwxxm)
        if cnt == 0:
            assert len(cldLyrList) == 4

            assert cldLyrList[0][0].tag == '%samount' % iwxxm
            assert cldLyrList[0][1].tag == '%sbase' % iwxxm
            assert cldLyrList[0][2].tag == '%scloudType' % iwxxm
            assert cldLyrList[0][0].get(xhref) == codes[des.CLDAMTS]['FEW'][0]
            assert cldLyrList[0][0].get(xtitle) == codes[des.CLDAMTS]['FEW'][1]
            assert cldLyrList[1][0].get(xhref) == codes[des.CLDAMTS]['SCT'][0]
            assert cldLyrList[1][0].get(xtitle) == codes[des.CLDAMTS]['SCT'][1]
            assert cldLyrList[2][0].get(xhref) == codes[des.CLDAMTS]['BKN'][0]
            assert cldLyrList[2][0].get(xtitle) == codes[des.CLDAMTS]['BKN'][1]
            assert cldLyrList[3][0].get(xhref) == codes[des.CLDAMTS]['OVC'][0]
            assert cldLyrList[3][0].get(xtitle) == codes[des.CLDAMTS]['OVC'][1]
            assert cldLyrList[0][1].get('uom') == '[ft_i]'
            assert cldLyrList[0][1].text == '2500'
            assert cldLyrList[1][1].get('uom') == '[ft_i]'
            assert cldLyrList[1][1].text == '3000'
            assert cldLyrList[2][1].get('uom') == '[ft_i]'
            assert cldLyrList[2][1].text == '3500'
            assert cldLyrList[3][1].get('uom') == '[ft_i]'
            assert cldLyrList[3][1].text == '4000'
            assert cldLyrList[0][2].get(xhref) == codes[des.CVCTNCLDS]['CB'][0]
            assert cldLyrList[0][2].get(xtitle) == codes[des.CVCTNCLDS]['CB'][1]
            assert cldLyrList[1][2].get(xhref) == codes[des.CVCTNCLDS]['TCU'][0]
            assert cldLyrList[1][2].get(xtitle) == codes[des.CVCTNCLDS]['TCU'][1]

        elif cnt == 1:
            assert len(cldLyrList) == 0
            vvFcst = tree.find('%sverticalVisibility' % find_iwxxm)
            assert vvFcst.get('uom') == 'N/A'
            assert vvFcst.get('nilReason') == codes[des.NIL][des.MSSG][0]

        elif cnt == 2:
            assert len(cldLyrList) == 0
            vvFcst = tree.find('%sverticalVisibility' % find_iwxxm)
            assert vvFcst.get('uom') == '[ft_i]'
            assert vvFcst.text == '100'

        elif cnt == 3:
            assert len(cldLyrList) == 0
            nosigCloud = tree.find('%scloud' % find_iwxxm)
            assert nosigCloud.get('nilReason') == codes[des.NIL][des.NOOPRSIG][0]


def test_temps():

    test = """FTXX01 LFKJ 072000
TAF SBAF 301500Z 3018/3106 00000KT CAVOK TX20/3018Z TN15/3106Z=
TAF SBAF 071500Z 0718/0806 00000KT CAVOK TN15/0106Z TX20/3018Z TX21/0817Z TN12/0808Z=
"""

    bulletin = encoder.encode(test)
    assert len(bulletin) == test.count('\n') - 1
    for cnt, result in enumerate(bulletin):
        assert result.get('translationFailedTAC') is None
        tree = ET.XML(ET.tostring(result))
        xTemps = tree.findall('%sAerodromeAirTemperatureForecast' % find_iwxxm)

        if cnt == 0:
            assert len(xTemps) == 1
            assert xTemps[0][0].get('uom') == 'Cel'
            assert xTemps[0][0].text == '20'
            assert xTemps[0][1][0][0].text.endswith('30T18:00:00Z')
            assert xTemps[0][2].get('uom') == 'Cel'
            assert xTemps[0][2].text == '15'
            assert xTemps[0][3][0][0].text.endswith('1T06:00:00Z')

        if cnt == 1:
            assert len(xTemps) == 2
            assert xTemps[0][0].get('uom') == 'Cel'
            assert xTemps[0][0].text == '20'
            assert xTemps[0][1][0][0].text.endswith('30T18:00:00Z')
            assert xTemps[0][2].get('uom') == 'Cel'
            assert xTemps[0][2].text == '15'
            assert xTemps[0][3][0][0].text.endswith('1T06:00:00Z')

            assert xTemps[1][0].get('uom') == 'Cel'
            assert xTemps[1][0].text == '21'
            assert xTemps[1][1][0][0].text.endswith('08T17:00:00Z')
            assert xTemps[1][2].get('uom') == 'Cel'
            assert xTemps[1][2].text == '12'
            assert xTemps[1][3][0][0].text.endswith('08T08:00:00Z')


def test_chgGrps():

    test = """FTXX01 LFKJ 072000
TAF SBAF 301500Z 3018/3106 00000KT 4000 -SHRA BR OVC010 FM302200 00000KT CAVOK=
TAF SBAF 301500Z 3018/3106 00000KT 4000 -SHRA BR OVC010 BECMG 3022/3024 9999 NSW=
TAF SBAF 071500Z 0718/0806 00000KT CAVOK TEMPO 0722/0724 3000 OVC040=
TAF SBAF 071500Z 0718/0806 00000KT CAVOK PROB40 0722/0724 3000 OVC040=
TAF SBAF 071500Z 0718/0806 00000KT CAVOK PROB40 TEMPO 0723/0801 3000 OVC040=
TAF SBAF 071500Z 0718/0806 00000KT CAVOK PROB30 0720/0722 3000 OVC040=
TAF SBAF 071500Z 0718/0806 00000KT CAVOK PROB30 TEMPO 0720/0722 3000 OVC040=
"""

    bulletin = encoder.encode(test)
    assert len(bulletin) == test.count('\n') - 1
    for cnt, result in enumerate(bulletin):
        assert result.get('translationFailedTAC') is None
        tree = ET.XML(ET.tostring(result))
        chgFcstList = tree.findall('%sMeteorologicalAerodromeForecast' % find_iwxxm)
        assert len(chgFcstList) == 2
        chgFcstList.pop(0)
        chgFcst = chgFcstList.pop(0)

        if cnt == 0:
            assert chgFcst.get('changeIndicator') == 'FROM'
            assert chgFcst[0][0][0].text.endswith('30T22:00:00Z')
            assert chgFcst[0][0][1].text.endswith('1T06:00:00Z')

        elif cnt == 1:
            assert chgFcst.get('changeIndicator') == 'BECOMING'
            assert chgFcst[0][0][0].text.endswith('30T22:00:00Z')
            assert chgFcst[0][0][1].text.endswith('1T00:00:00Z')

        elif cnt == 2:
            assert chgFcst.get('changeIndicator') == 'TEMPORARY_FLUCTUATIONS'
            assert chgFcst[0][0][0].text.endswith('07T22:00:00Z')
            assert chgFcst[0][0][1].text.endswith('08T00:00:00Z')

        elif cnt == 3:
            assert chgFcst.get('changeIndicator') == 'PROBABILITY_40'
            assert chgFcst[0][0][0].text.endswith('07T22:00:00Z')
            assert chgFcst[0][0][1].text.endswith('08T00:00:00Z')

        elif cnt == 4:
            assert chgFcst.get('changeIndicator') == 'PROBABILITY_40_TEMPORARY_FLUCTUATIONS'
            assert chgFcst[0][0][0].text.endswith('07T23:00:00Z')
            assert chgFcst[0][0][1].text.endswith('08T01:00:00Z')

        elif cnt == 5:
            assert chgFcst.get('changeIndicator') == 'PROBABILITY_30'
            assert chgFcst[0][0][0].text.endswith('07T20:00:00Z')
            assert chgFcst[0][0][1].text.endswith('07T22:00:00Z')

        elif cnt == 6:
            assert chgFcst.get('changeIndicator') == 'PROBABILITY_30_TEMPORARY_FLUCTUATIONS'
            assert chgFcst[0][0][0].text.endswith('07T20:00:00Z')
            assert chgFcst[0][0][1].text.endswith('07T22:00:00Z')


def test_cavok():

    des.noImpliedCAVOKCondition = True

    test = """TAF SBAF 301500Z 3018/3106 00000KT CAVOK BECMG 3020/3022 BKN025=
TAF SBAF 301500Z 3018/3106 00000KT CAVOK BECMG 3020/3022 2000 -SN BR=
TAF SBAF 071938Z 0720/0723 27010KT CAVOK TEMPO 0720/0722 4SM -SHRASN BR OVC015 BECMG 0720/0722 29012G22KT OVC010="""
    decoder = tD.Decoder()

    for taf in test.split('\n'):
        result = decoder(taf)
        assert 'err_msg' in result
        assert result['err_msg'] == 'When CAVOK is not present, prevailing visibility and sky conditions must be known.'

    des.noImpliedCAVOKCondition = False

    test = """FTXX01 LFKJ 072000
TAF SBAF 301500Z 3018/3106 00000KT CAVOK BECMG 3020/3022 BKN025=
TAF SBAF 301500Z 3018/3106 00000KT CAVOK BECMG 3020/3022 2000 -SN BR=
TAF SBAF 071938Z 0720/0723 27010KT CAVOK TEMPO 0720/0722 4SM -SHRASN BR OVC015 BECMG 0720/0722 29012G22KT OVC010=
"""

    bulletin = encoder.encode(test)
    assert len(bulletin) == test.count('\n') - 1
    for cnt, result in enumerate(bulletin):
        assert result.get('translationFailedTAC') is None
        tree = ET.XML(ET.tostring(result))
        chgFcstList = tree.findall('%sMeteorologicalAerodromeForecast' % find_iwxxm)
        if cnt == 0:
            assert len(chgFcstList) == 2
            lastChngGrp = chgFcstList[-1]
            assert lastChngGrp.get('cloudAndVisibilityOK') == 'false'
            assert lastChngGrp[1].tag == '%sprevailingVisibility' % iwxxm
            assert lastChngGrp[1].text == '10000'
            assert lastChngGrp[2].tag == '%sprevailingVisibilityOperator' % iwxxm
            assert lastChngGrp[2].text == 'ABOVE'

        elif cnt == 1:
            assert len(chgFcstList) == 2
            lastChngGrp = chgFcstList[1]
            assert lastChngGrp.get('cloudAndVisibilityOK') == 'false'
            assert lastChngGrp[1].tag == '%sprevailingVisibility' % iwxxm
            assert lastChngGrp[1].text == '2000'
            assert lastChngGrp[4].tag == '%scloud' % iwxxm
            assert lastChngGrp[4].get('nilReason') == codes[des.NIL][des.NOOPRSIG][0]

        elif cnt == 2:
            assert len(chgFcstList) == 3
            lastChngGrp = chgFcstList[-1]
            assert lastChngGrp.get('cloudAndVisibilityOK') == 'false'
            assert lastChngGrp[1].tag == '%sprevailingVisibility' % iwxxm
            assert lastChngGrp[1].text == '10000'
            assert lastChngGrp[2].tag == '%sprevailingVisibilityOperator' % iwxxm
            assert lastChngGrp[2].text == 'ABOVE'

    test = """TAF SBAF 301500Z 3018/3106 00000KT CAVOK BECMG 3020/3022 4000 DZ -SHRA BR BKN025=
TAF SBAF 301500Z 3018/3106 00000KT CAVOK BECMG 3020/3022 2000 SN BR OVC009=
TAF SBAF 071938Z 0720/0723 27010KT CAVOK TEMPO 0720/0722 4SM -SHRASN BR OVC015 BECMG 0720/0722 29012G22KT=
TAF AMD SBAF 111550Z 1115/1212 29010KT CAVOK BECMG 1118/1120 VRB02KT 9999 BECMG 1205/1207 26012G22KT TEMPO 1207/1210 SHRA BKN012 BKN030CB="""  # noqa

    for taf in test.split('\n'):
        result = decoder(taf)
        assert 'err_msg' not in result


if __name__ == '__main__':

    test_tafFailureModes()
    test_nil()
    test_cnl()
    test_ignoreRmks()
    test_offNominalCase()
    test_wind()
    test_vsby()
    test_pcp()
    test_sky()
    test_temps()
    test_chgGrps()
    test_cavok()
