import time
import gifts.SWA as SWAE
import gifts.swaDecoder as SD
import gifts.swaEncoder as SE
import gifts.common.xmlConfig as des

SWAEncoder = SWAE.Encoder()
decoder = SD.Decoder()
encoder = SE.Encoder()

first_siblings = ['issueTime', 'issuingSpaceWeatherCentre', 'advisoryNumber', 'phenomenon', 'phenomenon', 'analysis',
                  'analysis', 'analysis', 'analysis', 'analysis', 'remarks', 'nextAdvisoryTime']


def test_swaFailureModes():

    text = """FNXX01 KWNP 151247
"""
    result = decoder(text)
    assert 'err_msg' in result
    result['translatedBulletinReceptionTime'] = time.strftime('%Y-%m-%dT%H:%M:%SZ')
    result['translatedBulletinID'] = text.split('\n')[0].replace(' ', '')
    result = encoder(result, text)
    assert len(result.get('translationFailedTAC')) > 0

    text = """FNXX01 KWNP 311315
SWX ADVISORY
SWXC: BOULDER"""

    result = decoder(text)
    assert 'err_msg' in result
    result['translatedBulletinReceptionTime'] = time.strftime('%Y-%m-%dT%H:%M:%SZ')
    result['translatedBulletinID'] = text.split('\n')[0].replace(' ', '')
    result = encoder(result, text)
    assert len(result.get('translationFailedTAC')) > 0

    text = """
524
FNXX01 KWNP 311315
SWX ADVISORY
DTG: 20191231/1315Z
SWXC: BOULDER
<--PARSER HALT HERE"""

    result = decoder(text)
    assert 'err_msg' in result
    result['translatedBulletinReceptionTime'] = time.strftime('%Y-%m-%dT%H:%M:%SZ')
    result['translatedBulletinID'] = text.split('\n')[2].replace(' ', '')
    result = encoder(result, text)
    assert len(result.get('translationFailedTAC')) > 0


def test_swaTest():

    text = """FNXX01 KWNP 061006
SWX ADVISORY
STATUS: TEST="""

    result = decoder(text)
    assert 'err_msg' not in result
    assert 'status' in result
    assert result['status'] == 'TEST'

    result['translatedBulletinReceptionTime'] = time.strftime('%Y-%m-%dT%H:%M:%SZ')
    result['translatedBulletinID'] = text.split('\n')[0].replace(' ', '')

    result = encoder(result, text)
    assert len(result) == 2
    for num, child in enumerate(result):
        assert child.tag == first_siblings[num]

    bulletin = SWAEncoder.encode(text)
    assert len(bulletin) == 1

    text = """FNXX01 KWNP 080106
SWX ADVISORY
STATUS:             TEST
DTG:                20161108/0100Z
SWXC:               DONLON
ADVISORY NR:        2016/1
NR RPLC:            2015/325
SWX EFFECT:         HF COM SEV
FCST SWX:           08/0100Z DAYLIGHT SIDE ABV FL400
FCST SWX +6 HR:     08/0700Z DAYLIGHT SIDE FL350-500
FCST SWX +12 HR:    08/1300Z DAYLIGHT SIDE
FCST SWX +18 HR:    08/1900Z S4530 E01545 - S4100 W01300 - S3230 W02530 - S2930 W03715 - S3630 W04630 - S3815 W04445 -
                             S3345 E03800 - S3330 W03230 - S3800 W02330 - S4530 W01545
FCST SWX +24 HR:    09/0100Z N4530 E01545 - N3800 E02330 - N3330 E03230 - N3345 E03800 - N3815 E04445 - N3630 E04630 -
                             N2930 E03715 - N3230 E02530 - N4100 E01300 - N4530 E01545
RMK:                PERIODIC HF COM ABSORPTION OBS AND LIKELY TO CONT IN THE NEAR TERM. CMPL AND PERIODIC LOSS OF HF ON
THE SUNLIT SIDE OF THE EARTH EXP. CONT HF COM DEGRADATION LIKELY OVER THE NXT 7 DAYS. SEE WWW.SPACEWEATHERPROVIDER.WEB
NXT ADVISORY:       20161108/0700Z"""

    result = decoder(text)
    assert 'err_msg' not in result
    assert 'status' in result
    assert result['status'] == 'TEST'

    result['translatedBulletinReceptionTime'] = time.strftime('%Y-%m-%dT%H:%M:%SZ')
    result['translatedBulletinID'] = text.split('\n')[0].replace(' ', '')

    result = encoder(result, text)
    assert len(result) == 12

    save = first_siblings.pop(3)
    first_siblings.insert(3, 'replacedAdvisoryNumber')

    for num, child in enumerate(result):
        assert child.tag == first_siblings[num]

    first_siblings.pop(3)
    first_siblings.insert(3, save)

    bulletin = SWAEncoder.encode(text)
    assert len(bulletin) == 1


def test_swaExercise():

    text = """FNXX01 KWNP 301202
SWX ADVISORY
STATUS:             EXERCISE
DTG:                20200430/1200Z
SWXC:               BOULDER
ADVISORY NR:        2020/1
SWX EFFECT:         HF COM MOD AND GNSS MOD
OBS SWX:            30/1200Z NO SWX EXP
FCST SWX +6 HR:     30/1800Z NOT AVBL
FCST SWX +12 HR:    01/0000Z NOT AVBL
FCST SWX +18 HR:    01/0600Z NO SWX EXP
FCST SWX +24 HR:    01/1200Z NO SWX EXP
RMK:                NIL
NXT ADVISORY:       NO FURTHER ADVISORIES=
"""

    result = decoder(text)
    assert 'err_msg' not in result
    assert 'status' in result
    assert result['status'] == 'EXERCISE'

    result['translatedBulletinReceptionTime'] = time.strftime('%Y-%m-%dT%H:%M:%SZ')
    result['translatedBulletinID'] = text.split('\n')[0].replace(' ', '')
    result = encoder(result, text)

    for num, child in enumerate(result):
        assert child.tag == first_siblings[num]

    bulletin = SWAEncoder.encode(text)
    assert len(bulletin) == 1


def test_swaNormal():

    text = """FNXX01 KWNP 110100
SWX ADVISORY
DTG:                20161108/0100Z
SWXC:               DONLON
ADVISORY NR:        2016/2
NR RPLC:            2016/1
SWX EFFECT:         HF COM MOD AND GNSS MOD
OBS SWX:            08/0100Z HNH HSH E18000 - W18000
FCST SWX +6 HR:     08/0700Z HNH HSH W18000 - E18000
FCST SWX +12 HR:    08/1300Z HNH MNH MSH HSH E18000 - W18000
FCST SWX +18 HR:    08/1900Z NOT AVBL
FCST SWX +24 HR:    09/0100Z NO SWX EXP
RMK:                LOW LVL GEOMAGNETIC STORMING CAUSING INCREASED AURORAL ACT AND SUBSEQUENT MOD DEGRADATION OF GNSS
AND HF COM AVBL IN THE AURORAL ZONE. THIS STORMING EXP TO SUBSIDE IN THE FCST PERIOD. SEE WWW.SPACEWEATHERPROVIDER.WEB
NXT ADVISORY:       WILL BE ISSUED BY 20161108/0100Z"""

    result = decoder(text)
    assert 'err_msg' not in result
    assert 'status' not in result

    result['translatedBulletinReceptionTime'] = time.strftime('%Y-%m-%dT%H:%M:%SZ')
    result['translatedBulletinID'] = text.split('\n')[0].replace(' ', '')
    result = encoder(result, text)

    first_siblings.insert(3, 'replacedAdvisoryNumber')

    for num, child in enumerate(result):
        assert child.tag == first_siblings[num]

    des.JOIN_BANDS = True

    text = """FNXX01 KWNP 110100
SWX ADVISORY
DTG:                20161108/0100Z
SWXC:               DONLON
ADVISORY NR:        2016/2
NR RPLC:            2016/1
SWX EFFECT:         HF COM MOD AND GNSS MOD
OBS SWX:            08/0100Z HNH HSH E18000 - W18000
FCST SWX +6 HR:     08/0700Z EQN EQS W18000 - E18000
FCST SWX +12 HR:    08/1300Z HNH MNH MSH HSH E18000 - W18000
FCST SWX +18 HR:    08/0700Z EQN EQS W18000 - E18000
FCST SWX +24 HR:    09/0100Z NO SWX EXP
RMK:                LOW LVL GEOMAGNETIC STORMING CAUSING INCREASED AURORAL ACT AND SUBSEQUENT MOD DEGRADATION OF GNSS
AND HF COM AVBL IN THE AURORAL ZONE. THIS STORMING EXP TO SUBSIDE IN THE FCST PERIOD. SEE WWW.SPACEWEATHERPROVIDER.WEB
NXT ADVISORY:       WILL BE ISSUED BY 20161108/0100Z"""

    result = decoder(text)
    assert 'err_msg' not in result
    assert 'status' not in result

    result['translatedBulletinReceptionTime'] = time.strftime('%Y-%m-%dT%H:%M:%SZ')
    result['translatedBulletinID'] = text.split('\n')[0].replace(' ', '')
    result = encoder(result, text)

    for num, child in enumerate(result):
        assert child.tag == first_siblings[num]

    bulletin = SWAEncoder.encode(text)
    assert len(bulletin) == 1


if __name__ == '__main__':

    test_swaFailureModes()
    test_swaTest()
    test_swaExercise()
    test_swaNormal()
