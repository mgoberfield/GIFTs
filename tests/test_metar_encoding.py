import time
import xml.etree.ElementTree as ET

import gifts.METAR as ME
import gifts.metarDecoder as mD
import gifts.metarEncoder as mE
import gifts.common.xmlConfig as des
import gifts.common.xmlUtilities as deu

reqCodes = [des.WEATHER, des.SEACNDS, des.RWYFRCTN, des.RWYCNTMS, des.RWYDEPST, des.RECENTWX, des.CVCTNCLDS,
            des.CLDAMTS]

codes = deu.parseCodeRegistryTables(des.CodesFilePath, reqCodes)

aixm = './/*{http://www.aixm.aero/schema/5.1.1}'
iwxxm = './/*{http://icao.int/iwxxm/3.0}'
xhref = '{http://www.w3.org/1999/xlink}href'
xtitle = '{http://www.w3.org/1999/xlink}title'

missing = codes[des.NIL][des.MSSG]
inapplicable = codes[des.NIL][des.NA]
notDetectedByAutoSystem = codes[des.NIL][des.NOAUTODEC]
notObservable = codes[des.NIL][des.NOOBSV]
nothingOfOperationalSignificance = codes[des.NIL][des.NOOPRSIG]
noSignificantChange = codes[des.NIL][des.NOSIGC]
unknown = codes[des.NIL][des.UNKNWN]
withheld = codes[des.NIL][des.WTHLD]

database = {
    'BIAR': 'AKUREYRI|AEY|AKI|65.67 -18.07 27',
    'USRR': 'SURGUT|SGC|SURGUT|61.33 73.42  44',
    'USTR': 'TYUMEN/ROSCHINO|TJM||57.17 65.31  115'}

encoder = ME.Encoder(database)

Annex3Decoder = mD.Annex3()
Annex3Encoder = mE.Annex3()

des.TRANSLATOR = True


def test_failModes():

    text = """SAZZ01 XXXX 151200
"""

    result = Annex3Decoder(text)
    assert 'err_msg' in result
    assert result['err_msg'] == 'Unable to find start and end positions of the METAR/SPECI.'
    result['translatedBulletinReceptionTime'] = time.strftime('%Y-%m-%dT%H:%M:%SZ')
    result['translatedBulletinID'] = text.split('\n')[0].replace(' ', '')
    result = Annex3Encoder(result, text)
    assert result.get('translationFailedTAC') is not None

    text = """SAZZ01 XXXX 311300
METAR BAIR 31138Z= stops due to bad issue timestamp"""

    result = Annex3Decoder(text)
    assert 'err_msg' in result
    result['translatedBulletinReceptionTime'] = time.strftime('%Y-%m-%dT%H:%M:%SZ')
    result['translatedBulletinID'] = text.split('\n')[0].replace(' ', '')
    result = Annex3Encoder(result, text)
    assert result.get('translationFailedTAC') is not None

    text = """SAZZ01 XXXX 311300
METAR USTR 311338Z COR= stops due to wrong order of elements"""

    result = Annex3Decoder(text)
    assert 'err_msg' in result
    result['translatedBulletinReceptionTime'] = time.strftime('%Y-%m-%dT%H:%M:%SZ')
    result['translatedBulletinID'] = text.split('\n')[0].replace(' ', '')
    result = Annex3Encoder(result, text)
    assert result.get('translationFailedTAC') is not None
    assert len(result) == 4

    text = """
524
SAXX99 XXXX 311900
METAR USTR 311938Z 36025MPS REMARKS LIKE THIS ONE DO NOT BELONG IN ANNEX 3 METAR/SPECI=
                           ^--PARSER HALTS HERE"""

    result = Annex3Decoder(text)
    assert 'err_msg' in result
    result['translatedBulletinReceptionTime'] = time.strftime('%Y-%m-%dT%H:%M:%SZ')
    result['translatedBulletinID'] = text.split('\n')[2].replace(' ', '')
    result = Annex3Encoder(result, text)
    assert result.get('translationFailedTAC') is not None
    assert len(result) == 4

    des.TRANSLATOR = False

    text = """
524
SPXX99 XXXX 311900
SPECI USTR 311938Z 36025MPS REMARKS LIKE THIS ONE DO NOT BELONG IN ANNEX 3 METAR/SPECI=
                           ^--PARSER HALTS HERE"""

    encoder.encode(text)
    des.TRANSLATOR = True


def test_metarNil():

    text = """SAXX99 XXXX 311300
METAR VHHH 311338Z NIL="""

    result = Annex3Decoder(text)
    assert 'err_msg' not in result
    result['translatedBulletinReceptionTime'] = time.strftime('%Y-%m-%dT%H:%M:%SZ')
    result['translatedBulletinID'] = text.split('\n')[0].replace(' ', '')
    result = Annex3Encoder(result, text)
    assert result.get('translationFailedTAC') is None
    assert len(result) == 4
    assert result[-1].tag == 'iwxxm:observation'


def test_auto():

    test = """SAXX99 XXXX 151200
METAR BIAR 290000Z 33003KT 280V010 3000 VCSH BKN080 OVC120 04/M00 Q1023=
METAR BIAR 290000Z AUTO 33003KT 280V010 3000 VCSH BKN080 04/M00 Q1023="""

    bulletin = encoder.encode(test, time.strftime('%Y-%m-%dT%H:%M:%SZ'))
    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None
    assert result.get('automatedStation') == 'false'
    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None
    assert result.get('automatedStation') == 'true'


def test_cor():

    test = """SAXX99 KXXX 151200
SPECI BIAR 290000Z 33003KT 280V010 CAVOK 04/M00 Q1023=
SPECI COR BIAR 290000Z 33003KT 280V010 CAVOK 04/M00 Q1023=
"""

    bulletin = encoder.encode(test)
    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None
    assert result.get('reportStatus') == 'NORMAL'
    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None
    assert result.get('reportStatus') == 'CORRECTION'


def test_aerodrome():

    translatedBulletinID = 'SAXX99 KXXX 000000'.replace(' ', '')
    translatedBulletinReceptionTime = time.strftime('%Y-%d-%mT%H:%M:%SZ')

    test = """METAR USRR 290000Z 33003MPS CAVOK 04/M00 Q1013="""

    result = Annex3Decoder(test)
    assert 'err_msg' not in result
    metaData = database[result['ident']['str']]
    fullname, iataID, alternateID, position = metaData.split('|')

    result['ident']['name'] = fullname
    result['ident']['iataID'] = iataID
    result['ident']['alternate'] = alternateID
    result['ident']['position'] = position
    result['translatedBulletinReceptionTime'] = translatedBulletinReceptionTime
    result['translatedBulletinID'] = translatedBulletinID

    des.useElevation = True
    tree = ET.XML(ET.tostring(Annex3Encoder(result, test)))

    assert tree.find('%slocationIndicatorICAO' % aixm).text == result['ident']['str']
    assert tree.find('%sdesignatorIATA' % aixm).text == result['ident']['iataID']
    assert tree.find('%sdesignator' % aixm).text == result['ident']['alternate']
    assert tree.find('%sname' % aixm).text == result['ident']['name']
    assert tree.find('.//*{http://www.opengis.net/gml/3.2}pos').text == ' '.join(result['ident']['position'].split()[:2])  # noqa: E501
    assert tree.find('%selevation' % aixm).text == result['ident']['position'].split()[2]

    result['ident']['position'] = '33.67 -101.82'
    tree = ET.XML(ET.tostring(Annex3Encoder(result, test)))
    assert tree.find('%selevation' % aixm) is None

    des.useElevation = False

    tree = ET.XML(ET.tostring(Annex3Encoder(result, test)))

    assert tree.find('%slocationIndicatorICAO' % aixm).text == result['ident']['str']
    assert tree.find('.//*{http://www.opengis.net/gml/3.2}pos').text == ' '.join(result['ident']['position'].split()[:2])  # noqa: E501
    assert tree.find('%selevation' % aixm) is None


def test_ignoreRMK():

    test = """SAXX99 XXXX 151200
METAR BIAR 290000Z 33003KT 280V010 9999 OVC032 04/M00 Q1023 RMK THIS IS IGNORED=
METAR BIAR 290000Z 33003KT 280V010 9999 OVC032 04/M00 Q1023=
"""
    bulletin = encoder.encode(test)
    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None


def test_missingMandatories():

    test = """SAXX99 XXXX 151200
METAR BIAR 290000Z /////KT //// // ////// ///// Q////=
"""

    bulletin = encoder.encode(test)
    assert len(bulletin) == test.count('\n') - 1
    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None
    tree = ET.XML(ET.tostring(result))

    #  Non-domestic observations are done first
    for element in ['surfaceWind', 'visibility', 'layer', 'presentWeather', 'airTemperature', 'dewpointTemperature',
                    'qnh']:
        fullname = '%s%s' % (iwxxm, element)
        assert tree.find(fullname).get('nilReason') == notObservable[0]


def test_windComponents():

    test = """SAXX99 XXXX 151200
METAR BIAR 290000Z ///10KT //// // ////// ///// Q////=
METAR BIAR 290000Z 260//KT //// // ////// ///// Q////=
METAR BIAR 290000Z VRB03KT //// // ////// ///// Q////=
METAR BIAR 290000Z VRB03G50KT //// // ////// ///// Q////=
METAR BIAR 290000Z 260P10KT //// // ////// ///// Q////=
METAR BIAR 290000Z 260P10G20KT //// // ////// ///// Q////=
METAR BIAR 290000Z 26010GP20KT //// // ////// ///// Q////=
METAR BIAR 290000Z 26010MPS //// // ////// ///// Q////=
METAR BIAR 290000Z 26010MPS 280V010 //// // ////// ///// Q////=
"""

    bulletin = encoder.encode(test)
    assert len(bulletin) == test.count('\n') - 1
    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    assert tree.find('%sAerodromeSurfaceWind' % iwxxm).get('variableWindDirection') == 'false'
    assert tree.find('%smeanWindDirection' % iwxxm).get('nilReason') == notObservable[0]
    assert tree.find('%smeanWindDirection' % iwxxm).get('uom') == 'N/A'
    assert tree.find('%smeanWindSpeed' % iwxxm).text == '10'
    assert tree.find('%smeanWindSpeed' % iwxxm).get('uom') == '[kn_i]'
    assert tree.find('%swindSpeedGust' % iwxxm) is None

    #  METAR BIAR 290000Z 260//KT

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    assert tree.find('%sAerodromeSurfaceWind' % iwxxm).get('variableWindDirection') == 'false'
    assert tree.find('%smeanWindDirection' % iwxxm).text == '260'
    assert tree.find('%smeanWindDirection' % iwxxm).get('uom') == 'deg'
    assert tree.find('%smeanWindSpeed' % iwxxm).get('nilReason') == notObservable[0]
    assert tree.find('%smeanWindSpeed' % iwxxm).get('uom') == 'N/A'
    assert tree.find('%swindSpeedGust' % iwxxm) is None

    #  METAR BIAR 290000Z VRB03KT

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    assert tree.find('%sAerodromeSurfaceWind' % iwxxm).get('variableWindDirection') == 'true'
    assert tree.find('%smeanWindDirection' % iwxxm) is None
    assert tree.find('%smeanWindSpeed' % iwxxm).text == '3'
    assert tree.find('%swindSpeedGust' % iwxxm) is None

    #  METAR BIAR 290000Z VRB03G50KT

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    assert tree.find('%sAerodromeSurfaceWind' % iwxxm).get('variableWindDirection') == 'true'
    assert tree.find('%smeanWindDirection' % iwxxm) is None
    assert tree.find('%smeanWindSpeed' % iwxxm).text == '3'
    assert tree.find('%swindGustSpeed' % iwxxm).text == '50'
    assert tree.find('%swindGustSpeed' % iwxxm).get('uom') == '[kn_i]'

    #  METAR BIAR 290000Z 260P10KT

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    assert tree.find('%smeanWindDirection' % iwxxm).text == '260'
    assert tree.find('%smeanWindSpeed' % iwxxm).text == '10'
    assert tree.find('%smeanWindSpeedOperator' % iwxxm).text == 'ABOVE'
    assert tree.find('%swindGustSpeed' % iwxxm) is None

    #  METAR BIAR 290000Z 260P10G20KT

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    assert tree.find('%smeanWindDirection' % iwxxm).text == '260'
    assert tree.find('%smeanWindSpeed' % iwxxm).text == '10'
    assert tree.find('%smeanWindSpeedOperator' % iwxxm).text == 'ABOVE'
    assert tree.find('%swindGustSpeed' % iwxxm).text == '20'

    #  METAR BIAR 290000Z 26010GP20KT

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    assert tree.find('%smeanWindDirection' % iwxxm).text == '260'
    assert tree.find('%smeanWindSpeed' % iwxxm).text == '10'
    assert tree.find('%swindGustSpeed' % iwxxm).text == '20'
    assert tree.find('%swindGustSpeedOperator' % iwxxm).text == 'ABOVE'

    #  METAR BIAR 290000Z 26010MPS

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    assert tree.find('%smeanWindDirection' % iwxxm).text == '260'
    assert tree.find('%smeanWindSpeed' % iwxxm).text == '10'
    assert tree.find('%smeanWindSpeed' % iwxxm).get('uom') == 'm/s'

    #  METAR BIAR 290000Z 26010MPS 280V010

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    assert tree.find('%sextremeClockwiseWindDirection' % iwxxm).text == '10'
    assert tree.find('%sextremeCounterClockwiseWindDirection' % iwxxm).text == '280'


def test_temperatures():

    test = """SAXX99 XXXX 151200
METAR BIAR 290000Z /////KT //// // ////// 20/20  Q////=
METAR BIAR 290000Z /////KT //// // ////// M20/// Q////=
METAR BIAR 290000Z /////KT //// // ////// ///M20 Q////=
METAR BIAR 290000Z /////KT //// // ////// -05/-07 Q////=
"""

    bulletin = encoder.encode(test)
    assert len(bulletin) == test.count('\n') - 1
    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    assert tree.find('%sairTemperature' % iwxxm).text == '20'
    assert tree.find('%sdewpointTemperature' % iwxxm).text == '20'

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    assert tree.find('%sairTemperature' % iwxxm).text == '-20'
    assert tree.find('%sdewpointTemperature' % iwxxm).get('nilReason') == notObservable[0]

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    assert tree.find('%sairTemperature' % iwxxm).get('nilReason') == notObservable[0]
    assert tree.find('%sdewpointTemperature' % iwxxm).text == '-20'

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    assert tree.find('%sairTemperature' % iwxxm).text == '-5'
    assert tree.find('%sdewpointTemperature' % iwxxm).text == '-7'


def test_altimeters():

    test = """SAXX99 XXXX 151200
METAR BIAR 290000Z /////KT //// // ////// ///// Q1013=
METAR BIAR 290000Z /////KT //// // ////// ///// A2992=
METAR BIAR 290000Z /////KT //// // ////// ///// A//// Q1013 RMK I HAVE SEEN THIS CASE=
METAR BIAR 290000Z /////KT //// // ////// ///// Q1013 A//// BUT NOT THIS ONE=
"""

    bulletin = encoder.encode(test)
    assert len(bulletin) == test.count('\n') - 1
    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    assert tree.find('%sqnh' % iwxxm).text == '1013'
    assert tree.find('%sqnh' % iwxxm).get('uom') == 'hPa'

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    assert tree.find('%sqnh' % iwxxm).text == '1013.2'
    assert tree.find('%sqnh' % iwxxm).get('uom') == 'hPa'

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    assert tree.find('%sqnh' % iwxxm).text == '1013'
    assert tree.find('%sqnh' % iwxxm).get('uom') == 'hPa'

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is not None


def test_vsbys():

    test = """SAXX99 XXXX 151200
METAR BIAR 290000Z /////KT 9999 // ////// ///// Q////=
METAR BIAR 290000Z /////KT 3000NDV // ////// ///// Q////=
METAR BIAR 290000Z /////KT 4000 0150N // ////// ///// Q////=
METAR BIAR 290000Z /////KT 0400 0050 // ////// ///// Q////=
METAR BIAR 290000Z /////KT 1/16SM // ////// ///// Q////=
METAR BIAR 290000Z /////KT M1/4SM // ////// ///// Q////=
METAR BIAR 290000Z /////KT 1SM // ////// ///// Q////=
METAR BIAR 290000Z /////KT 1 1/2SM // ////// ///// Q////=
METAR BIAR 290000Z /////KT 7SM // ////// ///// Q////=
"""

    bulletin = encoder.encode(test)
    assert len(bulletin) == test.count('\n') - 1
    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    assert tree.find('%sprevailingVisibility' % iwxxm).text == '10000'
    assert tree.find('%sprevailingVisibility' % iwxxm).get('uom') == 'm'
    assert tree.find('%sprevailingVisibilityOperator' % iwxxm).text == 'ABOVE'

    # METAR BIAR 290000Z /////KT 3000NDV // ////// ///// Q////=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    assert tree.find('%sprevailingVisibility' % iwxxm).text == '3000'
    assert tree.find('%sminimumVisibility' % iwxxm) is None

    # METAR BIAR 290000Z /////KT 4000 0150N // ////// ///// Q////=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    assert tree.find('%sprevailingVisibility' % iwxxm).text == '4000'
    assert tree.find('%sminimumVisibility' % iwxxm).text == '150'
    assert tree.find('%sminimumVisibilityDirection' % iwxxm).text == '360'

    # METAR BIAR 290000Z /////KT 0400 0050 // ////// ///// Q////=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    assert tree.find('%sprevailingVisibility' % iwxxm).text == '400'
    assert tree.find('%sminimumVisibility' % iwxxm).text == '50'
    assert tree.find('%sminimumVisibilityDirection' % iwxxm) is None
    assert tree.find('%srvr' % iwxxm).get('nilReason') == missing[0]

    # METAR BIAR 290000Z /////KT 1/16SM // ////// ///// Q////=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    assert tree.find('%sprevailingVisibility' % iwxxm).text == '100'
    assert tree.find('%sprevailingVisibility' % iwxxm).get('uom') == 'm'

    # METAR BIAR 290000Z /////KT M1/4SM // ////// ///// Q////=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    assert tree.find('%sprevailingVisibility' % iwxxm).text == '400'
    assert tree.find('%sprevailingVisibilityOperator' % iwxxm).text == 'BELOW'

    # METAR BIAR 290000Z /////KT 1SM // ////// ///// Q////=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    assert tree.find('%sprevailingVisibility' % iwxxm).text == '1600'
    assert tree.find('%sprevailingVisibility' % iwxxm).get('uom') == 'm'

    # METAR BIAR 290000Z /////KT 1 1/2SM // ////// ///// Q////=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    assert tree.find('%sprevailingVisibility' % iwxxm).text == '2400'

    # METAR BIAR 290000Z /////KT 7SM // ////// ///// Q////=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    assert tree.find('%sprevailingVisibility' % iwxxm).text == '10000'
    assert tree.find('%sprevailingVisibilityOperator' % iwxxm).text == 'ABOVE'


def test_rvrs():

    test = """SAXX99 XXXX 151200
METAR BIAR 290000Z /////KT 1000 R///////FT ////// ///// Q////=
METAR BIAR 290000Z /////KT 1000 R01/////FT ////// ///// Q////=
METAR BIAR 290000Z /////KT 1000 R01C/4000FT ////// ///// Q////=
METAR BIAR 290000Z /////KT 1000 R01L/P4000FT ////// ///// Q////=
METAR BIAR 290000Z /////KT 1000 R01R/M0500FT ////// ///// Q////=
METAR BIAR 290000Z /////KT 1000 R36/1000U ////// ///// Q////=
METAR BIAR 290000Z /////KT 1000 R36L/1000D ////// ///// Q////=
METAR BIAR 290000Z /////KT 1000 R36R/1000N ////// ///// Q////=
METAR BIAR 290000Z /////KT 1000 R36C/1000 ////// ///// Q////=
METAR BIAR 290000Z /////KT 1000 R01C/4000FT/U ////// ///// Q////=
METAR BIAR 290000Z /////KT 1000 R01L/P4000FT/D ////// ///// Q////=
METAR BIAR 290000Z /////KT 1000 R01R/M0500FT/N ////// ///// Q////=
"""
    bulletin = encoder.encode(test)
    assert len(bulletin) == test.count('\n') - 1

    #  METAR BIAR 290000Z /////KT 1000 R///////FT ////// ///// Q////=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    runway = tree.find('%sAerodromeRunwayVisualRange' % iwxxm)
    assert runway.get('pastTendency') == 'MISSING_VALUE'
    assert runway.find('%sdesignator' % aixm).get('nilReason') == 'missing'
    assert tree.find('%smeanRVR' % iwxxm).get('nilReason') == notObservable[0]
    assert tree.find('%smeanRVR' % iwxxm).get('uom') == 'N/A'

    #  METAR BIAR 290000Z /////KT 1000 R01/////FT ////// ///// Q////=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    runway = tree.find('%sAerodromeRunwayVisualRange' % iwxxm)
    assert runway.find('%sdesignator' % aixm).text == '01'
    assert tree.find('%smeanRVR' % iwxxm).get('nilReason') == notObservable[0]

    #  METAR BIAR 290000Z /////KT 1000 R01C/4000FT ////// ///// Q////=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    runway = tree.find('%sAerodromeRunwayVisualRange' % iwxxm)
    assert runway.find('%sdesignator' % aixm).text == '01C'
    assert tree.find('%smeanRVR' % iwxxm).text == '1200'
    assert tree.find('%smeanRVR' % iwxxm).get('uom') == 'm'

    #  METAR BIAR 290000Z /////KT 1000 R01L/P4000FT ////// ///// Q////=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    runway = tree.find('%sAerodromeRunwayVisualRange' % iwxxm)
    assert runway.get('pastTendency') == 'MISSING_VALUE'
    assert runway.find('%sdesignator' % aixm).text == '01L'
    assert tree.find('%smeanRVR' % iwxxm).text == '1200'
    assert tree.find('%smeanRVR' % iwxxm).get('uom') == 'm'
    assert tree.find('%smeanRVROperator' % iwxxm).text == 'ABOVE'

    #  METAR BIAR 290000Z /////KT 1000 R01R/M0500FT ////// ///// Q////=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    runway = tree.find('%sAerodromeRunwayVisualRange' % iwxxm)
    assert runway.get('pastTendency') == 'MISSING_VALUE'
    assert runway.find('%sdesignator' % aixm).text == '01R'
    assert tree.find('%smeanRVR' % iwxxm).text == '150'
    assert tree.find('%smeanRVR' % iwxxm).get('uom') == 'm'
    assert tree.find('%smeanRVROperator' % iwxxm).text == 'BELOW'

    #  METAR BIAR 290000Z /////KT 1000 R36/1000U ////// ///// Q////=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    runway = tree.find('%sAerodromeRunwayVisualRange' % iwxxm)
    assert runway.get('pastTendency') == 'UPWARD'
    assert runway.find('%sdesignator' % aixm).text == '36'
    assert tree.find('%smeanRVR' % iwxxm).text == '1000'
    assert tree.find('%smeanRVR' % iwxxm).get('uom') == 'm'

    #  METAR BIAR 290000Z /////KT 1000 R36L/1000D ////// ///// Q////=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    runway = tree.find('%sAerodromeRunwayVisualRange' % iwxxm)
    assert runway.get('pastTendency') == 'DOWNWARD'
    assert runway.find('%sdesignator' % aixm).text == '36L'

    #  METAR BIAR 290000Z /////KT 1000 R36R/1000N////// ///// Q////=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    runway = tree.find('%sAerodromeRunwayVisualRange' % iwxxm)
    assert runway.get('pastTendency') == 'NO_CHANGE'
    assert runway.find('%sdesignator' % aixm).text == '36R'

    #  METAR BIAR 290000Z /////KT 1000 R36C/1000 ////// ///// Q////=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    runway = tree.find('%sAerodromeRunwayVisualRange' % iwxxm)
    assert runway.get('pastTendency') == 'MISSING_VALUE'
    assert runway.find('%sdesignator' % aixm).text == '36C'

    #  METAR BIAR 290000Z /////KT 1000 R01C/4000FT/U ////// ///// Q////=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    runway = tree.find('%sAerodromeRunwayVisualRange' % iwxxm)
    assert runway.get('pastTendency') == 'UPWARD'
    assert runway.find('%sdesignator' % aixm).text == '01C'

    #  METAR BIAR 290000Z /////KT 1000 R01L/4000FT/D ////// ///// Q////=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    runway = tree.find('%sAerodromeRunwayVisualRange' % iwxxm)
    assert runway.get('pastTendency') == 'DOWNWARD'
    assert runway.find('%sdesignator' % aixm).text == '01L'

    #  METAR BIAR 290000Z /////KT 1000 R01R/P4000FT/N ////// ///// Q////=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    runway = tree.find('%sAerodromeRunwayVisualRange' % iwxxm)
    assert runway.get('pastTendency') == 'NO_CHANGE'
    assert runway.find('%sdesignator' % aixm).text == '01R'

    test = """SAXX99 XXXX 151200
METAR BIAR 290000Z /////KT 1000 R01/1000N R02/1000D R03/1000U R04/1000 ////// ///// Q////="""

    bulletin = encoder.encode(test)
    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))

    rvrs = tree.findall('%srvr' % iwxxm)
    assert len(rvrs) == 4

    for rvr in rvrs:
        rwy = rvr.find('%sdesignator' % aixm).text
        if rwy == '01':
            rvr[0].get('pastTendency') == 'NO_CHANGE'
        elif rwy == '02':
            rvr[0].get('pastTendency') == 'DOWNWARD'
        elif rwy == '03':
            rvr[0].get('pastTendency') == 'UPWARD'
        elif rwy == '04':
            rvr[0].get('pastTendency') == 'MISSING_VALUE'
        else:
            assert True is False

        assert tree.find('%smeanRVR' % iwxxm).text == '1000'
        assert tree.find('%smeanRVR' % iwxxm).get('uom') == 'm'


def test_wx_phenomena():
    #
    # Not necessary to test every permutation, just enough for code coverage
    test = """SAXX99 XXXX 151200
METAR BIAR 290000Z /////KT //// -TSRA ////// ///// Q////=
METAR BIAR 290000Z /////KT //// VCFG  ////// ///// Q////=
METAR BIAR 290000Z /////KT //// +SS   ////// ///// Q////=
METAR BIAR 290000Z /////KT //// UP    ////// ///// Q////=
METAR BIAR 290000Z /////KT //// +SHUP ////// ///// Q////=
METAR BIAR 290000Z /////KT //// TS    ////// ///// Q////=
"""
    des.TITLES = des.Weather

    bulletin = encoder.encode(test)
    assert len(bulletin) == test.count('\n') - 1

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    wx = tree.find('%spresentWeather' % iwxxm)
    url, title = codes[des.WEATHER]['-TSRA']
    assert wx.get(xhref) == url
    assert wx.get(xtitle) == title

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    wx = tree.find('%spresentWeather' % iwxxm)
    url, title = codes[des.WEATHER]['VCFG']
    assert wx.get(xhref) == url
    assert wx.get(xtitle) == title

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    wx = tree.find('%spresentWeather' % iwxxm)
    url, title = codes[des.WEATHER]['+SS']
    assert wx.get(xhref) == url
    assert wx.get(xtitle) == title

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    wx = tree.find('%spresentWeather' % iwxxm)
    url, title = codes[des.WEATHER]['UP']
    assert wx.get(xhref) == url
    assert wx.get(xtitle) == title

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    wx = tree.find('%spresentWeather' % iwxxm)
    url, title = codes[des.WEATHER]['+SHUP']
    assert wx.get(xhref) == url
    assert wx.get(xtitle) == title

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    wx = tree.find('%spresentWeather' % iwxxm)
    url, title = codes[des.WEATHER]['TS']
    assert wx.get(xhref) == url
    assert wx.get(xtitle) == title

    test = """SAXX99 XXXX 151200
METAR BIAR 290000Z /////KT //// ////// ///// Q//// RE// RETS RERASN=
"""
    des.TITLES = 0

    bulletin = encoder.encode(test)
    assert len(bulletin) == test.count('\n') - 1
    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    wxrs = tree.findall('%srecentWeather' % iwxxm)
    assert len(wxrs) == 3

    for cnt, wx in enumerate(wxrs):
        if cnt == 0:
            assert wx.get('nilReason') == notObservable[0]
        elif cnt == 1:
            assert wx.get(xhref) == codes[des.WEATHER]['TS'][0]
        elif cnt == 2:
            assert wx.get(xhref) == codes[des.WEATHER]['RASN'][0]

    test = """SAXX99 XXXX 151200
METAR BIAR 290000Z /////KT //// ////// ///// Q//// NOSIG=
METAR BIAR 290000Z /////KT //// ////// ///// Q//// BECMG 21015MPS CAVOK=
METAR BIAR 290000Z /////KT //// ////// ///// Q//// TEMPO MIFG=
"""
    des.TITLES = 0

    bulletin = encoder.encode(test)
    assert len(bulletin) == test.count('\n') - 1
    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    assert tree[-1].tag == '{http://icao.int/iwxxm/3.0}trendForecast'
    assert tree[-1].get('nilReason') == noSignificantChange[0]

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    element = tree.find('%sMeteorologicalAerodromeTrendForecast' % iwxxm)
    assert element.get('changeIndicator') == 'BECOMING'
    assert element.get('cloudAndVisibilityOK') == 'true'
    assert element[1][0].tag == '{http://icao.int/iwxxm/3.0}AerodromeSurfaceWindTrendForecast'
    assert element[1][0][0].tag == '{http://icao.int/iwxxm/3.0}meanWindDirection'
    assert element[1][0][0].text == '210'
    assert element[1][0][0].get('uom') == 'deg'
    assert element[1][0][1].tag == '{http://icao.int/iwxxm/3.0}meanWindSpeed'
    assert element[1][0][1].text == '15'
    assert element[1][0][1].get('uom') == 'm/s'

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    element = tree.find('%sMeteorologicalAerodromeTrendForecast' % iwxxm)

    assert element.get('changeIndicator') == 'TEMPORARY_FLUCTUATIONS'
    assert element.get('cloudAndVisibilityOK') == 'false'
    assert element[-1].get(xhref) == codes[des.WEATHER]['MIFG'][0]


def test_sky_conditions():

    test = """SAXX99 XXXX 151200
METAR BIAR 290000Z /////KT //// NSC ///// Q////=
METAR BIAR 290000Z /////KT //// NCD ///// Q////=
METAR BIAR 290000Z AUTO /////KT //// NCD ///// Q////=
METAR BIAR 290000Z /////KT //// ///050 BKN/// //////CB //////TCU ///// Q////=
METAR BIAR 290000Z /////KT //// VV/// ///// Q////=
METAR BIAR 290000Z /////KT //// VV001 ///// Q////=
METAR BIAR 290000Z /////KT //// FEW050 SCT100 BKN110CB OVC120/// ///// Q////=
"""
    des.TITLES = des.CloudType

    bulletin = encoder.encode(test)
    assert len(bulletin) == test.count('\n') - 1
    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    element = tree.find('%scloud' % iwxxm)
    assert element.get('nilReason') == nothingOfOperationalSignificance[0]
    assert tree.get('automatedStation') == 'false'

    # METAR BIAR 290000Z /////KT //// NCD ///// Q////=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    element = tree.find('%scloud' % iwxxm)
    assert element.get('nilReason') == notDetectedByAutoSystem[0]
    assert tree.get('automatedStation') == 'true'

    # METAR BIAR 290000Z AUTO /////KT //// NCD ///// Q////=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    element = tree.find('%scloud' % iwxxm)
    assert element.get('nilReason') == notDetectedByAutoSystem[0]

    # METAR BIAR 290000Z /////KT //// ///050 BKN/// //////CB //////TCU ///// Q////=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    layers = tree.findall('%sCloudLayer' % iwxxm)
    assert len(layers) == 4

    for cnt, layer in enumerate(layers):
        if cnt == 0:
            assert layer[0].get('nilReason') == notObservable[0]
            assert layer[1].text == '5000'
            assert layer[1].get('uom') == '[ft_i]'

        elif cnt == 1:
            assert layer[0].get(xhref) == codes[des.CLDAMTS]['BKN'][0]
            assert layer[1].get('nilReason') == notObservable[0]
            assert layer[1].get('uom') == 'N/A'

        elif cnt == 2:
            assert layer[0].get('nilReason') == notObservable[0]
            assert layer[1].get('nilReason') == notObservable[0]
            url, title = codes[des.CVCTNCLDS]['CB']
            assert layer[2].get(xhref) == url
            assert layer[2].get(xtitle) == title

        elif cnt == 3:
            assert layer[0].get('nilReason') == notObservable[0]
            assert layer[1].get('nilReason') == notObservable[0]
            url, title = codes[des.CVCTNCLDS]['TCU']
            assert layer[2].get(xhref) == url
            assert layer[2].get(xtitle) == title

    # METAR BIAR 290000Z /////KT //// VV/// ///// Q////=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    layer = tree.find('%sverticalVisibility' % iwxxm)
    assert layer.get('nilReason') == notObservable[0]
    assert layer.get('uom') == 'N/A'

    # METAR BIAR 290000Z /////KT //// VV001 ///// Q////=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    layer = tree.find('%sverticalVisibility' % iwxxm)
    assert layer.text == '100'
    assert layer.get('uom') == '[ft_i]'

    # METAR BIAR 290000Z /////KT //// FEW050 SCT100 BKN110CB OVC120/// ///// Q////=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    layers = tree.findall('%sCloudLayer' % iwxxm)
    assert len(layers) == 4

    for cnt, layer in enumerate(layers):
        if cnt == 0:
            assert layer[0].get(xhref) == codes[des.CLDAMTS]['FEW'][0]
            assert layer[1].text == '5000'
            assert layer[1].get('uom') == '[ft_i]'

        elif cnt == 1:
            assert layer[0].get(xhref) == codes[des.CLDAMTS]['SCT'][0]
            assert layer[1].text == '10000'
            assert layer[1].get('uom') == '[ft_i]'

        elif cnt == 2:
            assert layer[0].get(xhref) == codes[des.CLDAMTS]['BKN'][0]
            assert layer[1].text == '11000'
            assert layer[1].get('uom') == '[ft_i]'
            url, title = codes[des.CVCTNCLDS]['CB']
            assert layer[2].get(xhref) == url
            assert layer[2].get(xtitle) == title

        elif cnt == 3:
            assert layer[0].get(xhref) == codes[des.CLDAMTS]['OVC'][0]
            assert layer[1].text == '12000'
            assert layer[1].get('uom') == '[ft_i]'
            assert layer[2].tag == '{http://icao.int/iwxxm/3.0}cloudType'
            assert layer[2].get('nilReason') == notObservable[0]

    test = """SAXX99 XXXX 151200
METAR BIAR 290000Z AUTO /////KT //// // ////// ///// Q////=
METAR BIAR 290000Z AUTO /////KT //// ///050 BKN/// //////CB //////TCU ///// Q////=
METAR BIAR 290000Z AUTO /////KT //// ///015/// ///// Q////=
"""
    des.TITLES = 0

    bulletin = encoder.encode(test)
    assert len(bulletin) == test.count('\n') - 1

    #  METAR BIAR 290000Z AUTO /////KT //// // ////// ///// Q////=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    assert tree.get('automatedStation') == 'true'
    assert tree.find('%slayer' % iwxxm).get('nilReason') == notDetectedByAutoSystem[0]

    #  METAR BIAR 290000Z AUTO /////KT //// ///050 BKN/// //////CB //////TCU ///// Q////="""

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    assert tree.get('automatedStation') == 'true'
    layers = tree.findall('%sCloudLayer' % iwxxm)
    assert len(layers) == 4

    for cnt, layer in enumerate(layers):
        if cnt == 0:
            assert layer[0].get('nilReason') == notDetectedByAutoSystem[0]
            assert layer[1].text == '5000'
            assert layer[1].get('uom') == '[ft_i]'

        elif cnt == 1:
            assert layer[0].get(xhref) == codes[des.CLDAMTS]['BKN'][0]
            assert layer[1].get('nilReason') == notDetectedByAutoSystem[0]
            assert layer[1].get('uom') == 'N/A'

        elif cnt == 2:
            assert layer[0].get('nilReason') == notDetectedByAutoSystem[0]
            assert layer[1].get('nilReason') == notDetectedByAutoSystem[0]
            assert layer[2].get(xhref) == codes[des.CVCTNCLDS]['CB'][0]
            assert layer[2].get(xtitle) is None

        elif cnt == 3:
            assert layer[0].get('nilReason') == notDetectedByAutoSystem[0]
            assert layer[1].get('nilReason') == notDetectedByAutoSystem[0]
            assert layer[2].get(xhref) == codes[des.CVCTNCLDS]['TCU'][0]
            assert layer[2].get(xtitle) is None

    # METAR BIAR 290000Z AUTO /////KT //// ///015/// ///// Q////=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    layers = tree.findall('%sCloudLayer' % iwxxm)
    assert len(layers) == 1

    for cnt, layer in enumerate(layers):
        if cnt == 0:
            assert layer[0].get('nilReason') == notDetectedByAutoSystem[0]
            assert layer[1].text == '1500'
            assert layer[1].get('uom') == '[ft_i]'
            assert layer[2].get('nilReason') == notObservable[0]


def test_windshears():

    test = """SAXX99 XXXX 151200
METAR BIAR 290000Z /////KT //// // ////// ///// Q//// WS ALL RWY=
METAR BIAR 290000Z /////KT //// // ////// ///// Q//// WS R01C=
"""
    bulletin = encoder.encode(test)
    assert len(bulletin) == test.count('\n') - 1

    #  METAR BIAR 290000Z /////KT //// // ////// ///// Q//// WS ALL RWY=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    assert len(tree.find('%sAerodromeWindShear' % iwxxm)) == 0
    assert tree.find('%sAerodromeWindShear' % iwxxm).get('allRunways') == 'true'

    #  METAR BIAR 290000Z /////KT //// // ////// ///// Q//// WS R01C=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    ws = tree.find('%sAerodromeWindShear' % iwxxm)
    assert ws.find('%sdesignator' % aixm).text == '01C'


def test_seastates():

    test = """SAXX99 XXXX 151200
METAR BIAR 290000Z /////KT //// // ////// ///// Q//// WM02/S2=
METAR BIAR 290000Z /////KT //// // ////// ///// Q//// W22/H75=
"""
    des.TITLES = des.SeaCondition
    bulletin = encoder.encode(test)
    assert len(bulletin) == test.count('\n') - 1

    #  METAR BIAR 290000Z /////KT //// // ////// ///// Q//// WM02/S2=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    assert tree.find('%sseaSurfaceTemperature' % iwxxm).text == '-2'
    ss = tree.find('%sseaState' % iwxxm)
    url, title = codes[des.SEACNDS]['2']
    assert ss.get(xhref) == url
    assert ss.get(xtitle) == title

    #  METAR BIAR 290000Z /////KT //// // ////// ///// Q//// W22/H75=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    assert tree.find('%sseaSurfaceTemperature' % iwxxm).text == '22'
    wh = tree.find('%ssignificantWaveHeight' % iwxxm)
    assert wh.text == '7.5'
    assert wh.get('uom') == 'm'

    des.TITLES = 0

    test = """SAXX99 XXXX 151200
METAR BIAR 290000Z /////KT //// // ////// ///// Q//// W///S/=
METAR BIAR 290000Z /////KT //// // ////// ///// Q//// W///H//=
"""
    bulletin = encoder.encode(test)
    assert len(bulletin) == test.count('\n') - 1

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    assert tree.find('%sseaSurfaceTemperature' % iwxxm).get('nilReason') == notObservable[0]
    ss = tree.find('%sseaState' % iwxxm)
    assert ss.get('nilReason') == notObservable[0]

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    wh = tree.find('%ssignificantWaveHeight' % iwxxm)
    assert wh.get('nilReason') == notObservable[0]


def test_runwaystates():
    #
    # Runway states depreciated, discontinued Nov 2021. Tests are not exhaustive.
    #
    test = """SAXX99 XXXX 151200
METAR BIAR 290000Z /////KT //// // ////// ///// Q//// R/SNOCLO=
METAR BIAR 290000Z /////KT //// // ////// ///// Q//// R/CLRD//=
METAR BIAR 290000Z /////KT //// // ////// ///// Q//// R01///////=
METAR BIAR 290000Z /////KT //// // ////// ///// Q//// R02/999491=
METAR BIAR 290000Z /////KT //// // ////// ///// Q//// R88/CLRD//=
METAR BIAR 290000Z /////KT //// // ////// ///// Q//// R99/CLRD//=
"""
    bulletin = encoder.encode(test)
    assert len(bulletin) == test.count('\n') - 1

    #  METAR BIAR 290000Z /////KT //// // ////// ///// Q//// R/SNOCLO=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    assert tree.find('%srunwayState' % iwxxm).get('nilReason') == des.NIL_SNOCLO_URL

    #  METAR BIAR 290000Z /////KT //// // ////// ///// Q//// R/CLRD//=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    rs = tree.find('%srunwayState' % iwxxm)
    assert rs[0].get('allRunways') == 'true'
    assert rs[0].get('cleared') == 'true'

    #  METAR BIAR 290000Z /////KT //// // ////// ///// Q//// R01///////=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    rs = tree.find('%srunwayState' % iwxxm)
    assert rs[0].get('allRunways') == 'false'
    assert rs.find('%sdesignator' % aixm).text == '01'
    assert rs.find('%sdepositType' % iwxxm) is None
    assert rs.find('%scontamination' % iwxxm) is None
    assert rs.find('%sdepthOfDeposit' % iwxxm).get('nilReason') == nothingOfOperationalSignificance[0]
    assert rs.find('%sestimatedSurfaceFrictionOrBrakingAction' % iwxxm) is None

    #  METAR BIAR 290000Z /////KT //// // ////// ///// Q//// R02/999491=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    rs = tree.find('%srunwayState' % iwxxm)
    assert rs[0].get('allRunways') == 'false'
    assert rs.find('%sdesignator' % aixm).text == '02'
    assert rs.find('%sdepositType' % iwxxm).get(xhref) == codes[des.RWYDEPST]['9'][0]
    assert rs.find('%scontamination' % iwxxm).get(xhref) == codes[des.RWYCNTMS]['9'][0]
    assert rs.find('%sdepthOfDeposit' % iwxxm).text == '200'
    assert rs.find('%sdepthOfDeposit' % iwxxm).get('uom') == 'mm'
    friction = rs.find('%sestimatedSurfaceFrictionOrBrakingAction' % iwxxm)
    assert friction.get(xhref) == codes[des.RWYFRCTN]['91'][0]

    #  METAR BIAR 290000Z /////KT //// // ////// ///// Q//// R88/CLRD//=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    rs = tree.find('%srunwayState' % iwxxm)
    assert rs[0].get('allRunways') == 'true'
    assert rs[0].get('cleared') == 'true'

    #  METAR BIAR 290000Z /////KT //// // ////// ///// Q//// R99/CLRD//=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    rs = tree.find('%srunwayState' % iwxxm)
    assert rs[0].get('fromPreviousReport') == 'true'
    assert rs[0].get('cleared') == 'true'


def test_trendTiming():

    test = """SAXX99 XXXX 151200
METAR BIAR 302351Z /////KT //// ////// ///// Q//// BECMG 9999 NSW=
METAR BIAR 302351Z /////KT //// ////// ///// Q//// BECMG FM0000 TL0030 1/16SM FG=
METAR BIAR 302351Z /////KT //// ////// ///// Q//// BECMG TL0030 CAVOK=
METAR BIAR 302351Z /////KT //// ////// ///// Q//// BECMG FM0000 CAVOK=
METAR BIAR 302351Z /////KT //// ////// ///// Q//// BECMG AT0000 CAVOK=
"""
    bulletin = encoder.encode(test)
    assert len(bulletin) == test.count('\n') - 1

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    element = tree.find('%sMeteorologicalAerodromeTrendForecast' % iwxxm)

    #  METAR BIAR 302351Z /////KT //// ////// ///// Q//// BECMG 9999 NSW=

    assert element.get('changeIndicator') == 'BECOMING'
    assert element[0].tag == '{http://icao.int/iwxxm/3.0}phenomenonTime'
    assert element[0].get('nilReason') == missing[0]
    vis = tree.find('%sprevailingVisibility' % iwxxm)
    assert vis.text == '10000'
    assert vis.get('uom') == 'm'
    oper = tree.find('%sprevailingVisibilityOperator' % iwxxm)
    oper.text = 'ABOVE'

    #  METAR BIAR 302351Z /////KT //// ////// ///// Q//// BECMG FM0000 TL0030 1/16SM FG=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    vis = tree.find('%sprevailingVisibility' % iwxxm)
    assert vis.text == '100'
    assert vis.get('uom') == 'm'

    element = tree.find('%sMeteorologicalAerodromeTrendForecast' % iwxxm)
    assert element.get('changeIndicator') == 'BECOMING'
    assert element[0].tag == '{http://icao.int/iwxxm/3.0}phenomenonTime'
    assert element[1].tag == '{http://icao.int/iwxxm/3.0}timeIndicator'
    assert element[1].text == 'FROM_UNTIL'

    #  METAR BIAR 302351Z /////KT //// ////// ///// Q//// BECMG TL0030 CAVOK=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    element = tree.find('%sMeteorologicalAerodromeTrendForecast' % iwxxm)
    assert element.get('changeIndicator') == 'BECOMING'
    assert element[0].tag == '{http://icao.int/iwxxm/3.0}phenomenonTime'
    assert element[1].tag == '{http://icao.int/iwxxm/3.0}timeIndicator'
    assert element[1].text == 'UNTIL'

    #  METAR BIAR 302351Z /////KT //// ////// ///// Q//// BECMG FM0000 CAVOK=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    element = tree.find('%sMeteorologicalAerodromeTrendForecast' % iwxxm)
    assert element.get('changeIndicator') == 'BECOMING'
    assert element[0].tag == '{http://icao.int/iwxxm/3.0}phenomenonTime'
    assert element[1].tag == '{http://icao.int/iwxxm/3.0}timeIndicator'
    assert element[1].text == 'FROM'

    #  METAR BIAR 302351Z /////KT //// ////// ///// Q//// BECMG AT0000 CAVOK=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    element = tree.find('%sMeteorologicalAerodromeTrendForecast' % iwxxm)
    assert element.get('changeIndicator') == 'BECOMING'
    assert element[0].tag == '{http://icao.int/iwxxm/3.0}phenomenonTime'
    assert element[1].tag == '{http://icao.int/iwxxm/3.0}timeIndicator'
    assert element[1].text == 'AT'

    test = """SAXX99 XXXX 151200
METAR BIAR 302351Z /////KT //// ////// ///// Q//// TEMPO FC=
METAR BIAR 302351Z /////KT //// ////// ///// Q//// TEMPO FM0000 TL0030 FC=
METAR BIAR 302351Z /////KT //// ////// ///// Q//// TEMPO TL0030 FC=
METAR BIAR 302351Z /////KT //// ////// ///// Q//// TEMPO FM0000 FC=
"""

    bulletin = encoder.encode(test)
    assert len(bulletin) == test.count('\n') - 1

    #  METAR BIAR 302351Z /////KT //// ////// ///// Q//// TEMPO FC=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    element = tree.find('%sMeteorologicalAerodromeTrendForecast' % iwxxm)
    assert element.get('changeIndicator') == 'TEMPORARY_FLUCTUATIONS'
    assert element[0].tag == '{http://icao.int/iwxxm/3.0}phenomenonTime'
    assert element[0].get('nilReason') == missing[0]

    #  METAR BIAR 302351Z /////KT //// ////// ///// Q//// TEMPO FM0000 TL030 +FC=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    element = tree.find('%sMeteorologicalAerodromeTrendForecast' % iwxxm)
    assert element.get('changeIndicator') == 'TEMPORARY_FLUCTUATIONS'
    assert element[0].tag == '{http://icao.int/iwxxm/3.0}phenomenonTime'
    assert element[1].tag == '{http://icao.int/iwxxm/3.0}timeIndicator'
    assert element[1].text == 'FROM_UNTIL'

    #  METAR BIAR 302351Z /////KT //// ////// ///// Q//// TEMPO TL0030 +FC=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    element = tree.find('%sMeteorologicalAerodromeTrendForecast' % iwxxm)
    assert element.get('changeIndicator') == 'TEMPORARY_FLUCTUATIONS'
    assert element[0].tag == '{http://icao.int/iwxxm/3.0}phenomenonTime'
    assert element[1].tag == '{http://icao.int/iwxxm/3.0}timeIndicator'
    assert element[1].text == 'UNTIL'

    #  METAR BIAR 302351Z /////KT //// ////// ///// Q//// TEMPO FM0000 +FC=

    result = bulletin.pop()
    assert result.get('translationFailedTAC') is None

    tree = ET.XML(ET.tostring(result))
    element = tree.find('%sMeteorologicalAerodromeTrendForecast' % iwxxm)
    assert element.get('changeIndicator') == 'TEMPORARY_FLUCTUATIONS'
    assert element[0].tag == '{http://icao.int/iwxxm/3.0}phenomenonTime'
    assert element[1].tag == '{http://icao.int/iwxxm/3.0}timeIndicator'
    assert element[1].text == 'FROM'


def test_commonRunway():

    test = """SAXX99 KXXX 151200
METAR BIAR 290000Z /////MPS //// R01C/2000 ////// ///// Q//// WS R01C R01C/999491=
"""
    bulletin = encoder.encode(test)
    assert len(bulletin) == test.count('\n') - 1

    tree = ET.XML(ET.tostring(bulletin.pop()))
    runways = tree.findall('%srunway' % iwxxm)
    assert len(runways) == 3
    #
    # First runway shall have the id that is shared with the rest
    runwayID = None
    for rwy in runways:
        if len(rwy) == 0:
            if runwayID is None:
                runwayID = rwy.get(xhref)[1:]
            else:
                assert runwayID == rwy.get(xhref)[1:]
        else:
            if runwayID is None:
                runwayID = rwy[0].get('{http://www.opengis.net/gml/3.2}id')
            else:
                assert runwayID == rwy[0].get('{http://www.opengis.net/gml/3.2}id')


def test_misc():

    test = """SAXX99 KXXX 151200
METAR BIAR 312000Z 00000KT CAVOK 19/16 Q1019=
METAR BIAR 31200Z 00000KT CAVOK 19/16 Q1019=
"""

    bulletin = encoder.encode(test)
    assert len(bulletin) == test.count('\n') - 1

    tree = ET.XML(ET.tostring(bulletin.pop()))
    assert tree.get('translationFailedTAC') is None
    obTime = tree.find('{http://icao.int/iwxxm/3.0}observationTime')
    assert obTime.get(xhref) is not None

    tree = ET.XML(ET.tostring(bulletin.pop()))
    assert tree.get('translationFailedTAC') is not None
    obTime = tree.find('{http://icao.int/iwxxm/3.0}observationTime')
    assert obTime.get(xhref) is None


if __name__ == '__main__':

    test_failModes()
    test_metarNil()
    test_auto()
    test_cor()
    test_aerodrome()
    test_missingMandatories()
    test_windComponents()
    test_temperatures()
    test_altimeters()
    test_vsbys()
    test_rvrs()
    test_wx_phenomena()
    test_sky_conditions()
    test_windshears()
    test_seastates()
    test_runwaystates()
    test_trendTiming()
    test_commonRunway()
    test_misc()
