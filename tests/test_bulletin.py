import os
import pytest
import tempfile
import gzip

import gifts.common.bulletin as bulletin
from gifts.TCA import Encoder as TE
from gifts.SWA import Encoder as SE

tcaEncoder = TE()
swaEncoder = SE()


def test_empty():

    collective1 = bulletin.Bulletin()
    assert collective1.what_kind() is None
    assert len(collective1) == 0

    with pytest.raises(SyntaxError):
        collective1.export()

    with pytest.raises(IndexError):
        collective1[0]

    collective2 = bulletin.Bulletin()

    with pytest.raises(SyntaxError):
        collective1 + collective2


def test_unlike():

    tca_test = """FKNT23 KNHC 111800
TC ADVISORY
STATUS: TEST=
"""

    swa_test = """FNXX01 KWNP 141901
SWX ADVISORY
STATUS: TEST=
"""

    collective1 = tcaEncoder.encode(tca_test)
    collective2 = swaEncoder.encode(swa_test)

    with pytest.raises(SyntaxError):
        collective1 + collective2

    with pytest.raises(SyntaxError):
        collective1.append(collective2[0])


def test_realize():

    test = """FKNT23 KNHC 111800
TC ADVISORY
STATUS: TEST="""

    collective1 = tcaEncoder.encode(test)
    metBulletin = collective1.export()
    #
    # For test message the iwxxm message (parent) only has two children
    assert len(metBulletin) == 2
    #
    # Erase the <MeteorologicalInformation> bulletin by adding a child after bulletin
    # was created.
    collective1.append(collective1.pop())
    #
    # Create empty bulletin, add a child, then attempt
    # tp create a met bulletin without setting the id.
    #
    collective2 = bulletin.Bulletin()
    collective2.append(collective1[0])

    with pytest.raises(SyntaxError):
        collective2.export()


def test_operations():

    test1 = """FKNT23 KNHC 111800
TC ADVISORY
STATUS: TEST="""

    test2 = """FKNT21 KNHC 111800
TC ADVISORY
STATUS: TEST="""

    collective1 = tcaEncoder.encode(test1)
    collective2 = tcaEncoder.encode(test2)

    assert len(collective1) == 1
    assert len(collective2) == 1

    assert collective1.what_kind() == collective2.what_kind()
    #
    # Like children (iwxxm documents) can be added to a bulletin
    collective1.append(collective2[0])
    assert len(collective1) == 2
    #
    # bulletins can be collected into a single one
    collective3 = collective1 + collective2
    assert len(collective3) == 3
    #
    # Children can be viewed
    document1 = collective3[0]
    document2 = collective1[0]
    #
    # And compared.
    assert document2.get('gml:id') == document1.get('gml:id')
    #
    # And children removed
    document3 = collective3.pop()
    assert document3.get('gml:id') == document1.get('gml:id')
    assert len(collective3) == 2


def test_writes():

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
    collective1 = tcaEncoder.encode(test)
    #
    # No filename provided
    fn = collective1.write()
    assert os.path.isfile(fn)
    assert fn[-3:] == 'xml'
    os.unlink(fn)
    #
    # Pass write method -- doesn't matter what the name is.
    _fh = open(os.devnull, 'w')
    fn = collective1.write(_fh.write)
    assert fn is None
    #
    # Indicate bulletin, when written out, is to be compressed
    collective2 = tcaEncoder.encode(test)
    #
    # No filename provided
    fn = collective2.write(compress=True)
    assert fn[-2:] == 'gz'
    os.unlink(fn)
    #
    # Pass in a directory
    fn = collective2.write(tempfile.gettempdir())
    assert os.path.isfile(fn)
    os.unlink(fn)


def test_header_option():

    test = """FKNT22 KNHC 151436
TCANT2

TROPICAL STORM BILL ICAO ADVISORY NUMBER   5
NWS NATIONAL HURRICANE CENTER MIAMI FL       AL022021
1500 UTC TUE JUN 15 2021

TC ADVISORY
DTG:                      20210615/1500Z
TCAC:                     KNHC
TC:                       BILL
ADVISORY NR:              2021/005
OBS PSN:                  15/1500Z N4030 W06200
MOV:                      NE 33KT
INTST CHANGE:             NC
C:                        0998HPA
MAX WIND:                 050KT
FCST PSN +3 HR:           15/1800Z N4225 W05939
FCST MAX WIND +3 HR:      050KT
FCST PSN +9 HR:           16/0000Z N4425 W05722
FCST MAX WIND +9 HR:      050KT
FCST PSN +15 HR:          16/0600Z N4628 W05507
FCST MAX WIND +15 HR:     045KT
FCST PSN +21 HR:          16/1200Z N//// W/////
FCST MAX WIND +21 HR:     ///KT
FCST PSN +27 HR:          16/1800Z N//// W/////
FCST MAX WIND +27 HR:     ///KT
RMK:                      SOME FORECAST INFORMATION IN
                          THIS PRODUCT IS INTERPOLATED FROM
                          OFFICIAL FORECAST DATA.
NXT MSG:                  20210615/2100Z
$$
"""
    collective = tcaEncoder.encode(test)
    #
    # Verify default - no WMO AHL line
    fn = collective.write()
    _fh = open(fn, 'r')
    first_line = _fh.readline()
    assert first_line != 'LKNT22 KNHC 151436\n'
    _fh.close()
    os.unlink(fn)
    #
    # Insert WMO AHL line
    filename = os.path.join(tempfile.gettempdir(), 'asdfas.txt')
    _fh = open(filename, 'w')
    collective.write(_fh.write, header=True)
    _fh.close()

    # Verify first line is the WMO AHL
    _fh = open(filename, 'r')
    first_line = _fh.readline()
    assert first_line == 'LKNT22 KNHC 151436\n'
    _fh.close()
    os.unlink(filename)

    collective2 = tcaEncoder.encode(test)
    fn = collective2.write(header=True)
    assert fn[-4:] == '.txt'
    #
    # Although the external file has the extension 'txt', the internal bulletinIdentifier in the
    # XML document is still 'xml'
    assert collective2._internalBulletinId[-4:] == '.xml'

    _fh = open(fn, 'r')
    first_line = _fh.readline()
    assert first_line == 'LKNT22 KNHC 151436\n'
    _fh.close()
    os.unlink(fn)


def test_compression():

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
    collective = tcaEncoder.encode(test)
    #
    # Verify that compressed file is written and without WMO AHL
    # (header is ignored)
    #
    fn = collective.write(header=True, compress=True)
    assert fn[-7:] == '.xml.gz'
    assert collective._internalBulletinId[-7:] == '.xml.gz'

    assert os.path.basename(fn) == collective._internalBulletinId

    try:
        _fh = gzip.open(fn)
    except Exception as exc:
        assert False, "Attempt to open gzip file failed: %s" % str(exc)

    first_line = _fh.readline().decode('utf-8')
    assert first_line != 'LKNT23 KNHC 231458\n'
    _fh.close()
    os.unlink(fn)


if __name__ == '__main__':

    test_empty()
    test_unlike()
    test_realize()
    test_operations()
    test_writes()
    test_header_option()
    test_compression()
