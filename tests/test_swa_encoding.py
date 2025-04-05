import time
import gifts.SWA as SWAE
import gifts.swaDecoder as SD
import gifts.swaEncoder as SE
import gifts.common.xmlConfig as des

SWAEncoder = SWAE.Encoder()
decoder = SD.Decoder()
encoder = SE.Encoder()
des.TRANSLATOR = True
#
# Very rudimentary tests. More through assertion tests will have to come later.

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

    first_siblings = ['issueTime', 'issuingSpaceWeatherCentre', 'advisoryNumber', 'replacedAdvisoryNumber',
                      'replacedAdvisoryNumber', 'replacedAdvisoryNumber', 'replacedAdvisoryNumber',
                      'replacedAdvisoryNumber','effect', 'analysis', 'analysis', 'analysis', 'analysis',
                      'analysis', 'remarks', 'nextAdvisoryTime']

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
STATUS:             EXER
DTG:                20250405/0100Z
SWXC:               DONLON
SWX EFFECT:         HF COM
ADVISORY NR:        2025/11
NR RPLC:            2025/10 2025/09 2025/08 2025/07 2025/06
FCST SWX:           04/0100Z SEV HNH HSH DAYSIDE MOD HNH HSH NIGHTSIDE
FCST SWX +6 HR:     04/0700Z MOD DAYSIDE
FCST SWX +12 HR:    04/1300Z MOD DAYSIDE
FCST SWX +18 HR:    04/1900Z MOD S45 E015 - S41 W013 - S32 W025 - S29 W037 - S36 W046 - S38 W044 -
                             S33 E038 - S33 W032 - S38 W023 - S45 W015
FCST SWX +24 HR:    09/0100Z MOD N45 E015 - N38 E023 - N33 E032 - N33 E038 - N38 E044 - N36 E046 -
                             N29 E037 - N32 E025 - N41 E013 - N45 E015
RMK:                NIL
NXT ADVISORY:       20250405/0700Z="""

    result = decoder(text)
    assert 'err_msg' not in result
    assert 'status' in result
    assert result['status'] == 'EXER'

    result['translatedBulletinReceptionTime'] = time.strftime('%Y-%m-%dT%H:%M:%SZ')
    result['translatedBulletinID'] = text.split('\n')[0].replace(' ', '')

    result = encoder(result, text)
    assert len(result) == 16

    for num, child in enumerate(result):
        assert child.tag == first_siblings[num]

    bulletin = SWAEncoder.encode(text)
    assert len(bulletin) == 1


def test_swaExercise():

    first_siblings = ['issueTime', 'issuingSpaceWeatherCentre', 'advisoryNumber','effect', 'analysis',
                      'analysis', 'analysis', 'analysis', 'analysis', 'remarks', 'nextAdvisoryTime']

    text = """FNXX01 KWNP 301202
SWX ADVISORY
STATUS:             EXERCISE
DTG:                20200430/1200Z
SWXC:               BOULDER
SWX EFFECT:         GNSS
ADVISORY NR:        2020/1
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

    first_siblings = ['issueTime', 'issuingSpaceWeatherCentre', 'advisoryNumber', 'replacedAdvisoryNumber',
                      'effect', 'analysis', 'analysis', 'analysis', 'analysis', 'analysis', 'remarks',
                      'nextAdvisoryTime']

    text = """FNXX01 KWNP 110100
SWX ADVISORY
DTG:                20161108/0100Z
SWXC:               DONLON
SWX EFFECT:         GNSS
ADVISORY NR:        2016/2
NR RPLC:            2016/1
OBS SWX:            08/0100Z SEV HNH HSH
FCST SWX +6 HR:     08/0700Z MOD HNH HSH W180 - E180
FCST SWX +12 HR:    08/1300Z MOD HNH MNH MSH HSH E180 - W180
FCST SWX +18 HR:    08/1900Z NOT AVBL
FCST SWX +24 HR:    09/0100Z NO SWX EXP
RMK:                NIL
NXT ADVISORY:       WILL BE ISSUED BY 20161108/0100Z"""

    result = decoder(text)
    assert 'err_msg' not in result
    assert 'status' not in result

    result['translatedBulletinReceptionTime'] = time.strftime('%Y-%m-%dT%H:%M:%SZ')
    result['translatedBulletinID'] = text.split('\n')[0].replace(' ', '')
    result = encoder(result, text)

    for num, child in enumerate(result):
        assert child.tag == first_siblings[num]

    des.JOIN_BANDS = True

    text = """FNXX01 KWNP 110100
SWX ADVISORY
DTG:                20161108/0100Z
SWXC:               DONLON
SWX EFFECT:         SATCOM
ADVISORY NR:        2016/2
NR RPLC:            2016/1
OBS SWX:            08/0100Z SEV EQN EQS
FCST SWX +6 HR:     08/0700Z SEV EQN EQS W180 - E180
FCST SWX +12 HR:    08/1300Z MOD HNH MNH MSH HSH
FCST SWX +18 HR:    08/0700Z MOD EQN EQS
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


    test = """FNXX01 KWNP 080106
SWX ADVISORY
STATUS:             TEST
DTG:                20161108/0100Z
SWXC:               DONLON
SWX EFFECT:         RADIATION
ADVISORY NR:        2016/1
NR RPLC:            2015/325
OBS SWX:            08/0100Z SEV DAYSIDE ABV FL400
FCST SWX +6 HR:     08/0700Z SEV DAYSIDE FL350-500
FCST SWX +12 HR:    08/1300Z MOD NIGHTSIDE FL350-500
FCST SWX +18 HR:    08/1900Z MOD S45 E015 - S41 W013 - S32 W025 - S29 W037 - S36 W046 - S38 W044 -
                             S33 E038 - S3330 W032 - S38 W023 - S45 W015
FCST SWX +24 HR:    09/0100Z MOD N45 E015 - N38 E023 - N33 E032 - N33 E038 - N38 E044 - N36 E046 -
                             N29 E037 - N32 E025 - N41 E013 - N45 E015
RMK:                NIL
NXT ADVISORY:       20161108/0700Z="""
    result = decoder(test)
    assert 'err_msg' not in result


if __name__ == '__main__':

    test_swaFailureModes()
    test_swaTest()
    test_swaExercise()
    test_swaNormal()
