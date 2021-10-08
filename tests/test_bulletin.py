import os
import pytest
import tempfile
import gzip

import gifts.common.bulletin as bulletin
from gifts.TAF import Encoder as TE
from gifts.METAR import Encoder as ME


database = {'SBAF': 'AFONSOS ARPT MI|||-22.87 -43.37'}

tafEncoder = TE(database)
metarEncoder = ME(database)


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

    taf_test = """FTUS43 KBOU 081800
TAF SBAF 101800Z NIL=
"""

    metar_test = """SAUS51 KLWX 081800
METAR SBAF 101800Z NIL=
"""

    collective1 = tafEncoder.encode(taf_test)
    collective2 = metarEncoder.encode(metar_test)

    with pytest.raises(SyntaxError):
        collective1 + collective2

    with pytest.raises(SyntaxError):
        collective1.append(collective2[0])


def test_realize():

    taf_test = """FTUS43 KBOU 081800
TAF SBAF 101800Z NIL=
"""
    collective1 = tafEncoder.encode(taf_test)
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


def test_writes():

    taf_test = """FTUS43 KBOU 081800
TAF SBAF 101800Z NIL=
"""
    collective1 = tafEncoder.encode(taf_test)
    #
    # No filename provided
    collective1.write()
    os.unlink(collective1.get_bulletinIdentifier())

    _fh = open(os.devnull, 'w')
    collective1.write(_fh.write)
    with pytest.raises(SyntaxError):
        collective1.write(_fh)
    _fh.close()
    #
    # Indicate bulletin, when written out, is to be compressed
    collective2 = tafEncoder.encode(taf_test, xml="xml.gz")
    #
    # No filename provided
    collective2.write()
    os.unlink(collective2.get_bulletinIdentifier())
    #
    # This time because external and internal name of the file disagree
    _fh = open(os.devnull, 'wb')
    with pytest.raises(SyntaxError):
        collective2.write(_fh)
    _fh.close()
    #
    # Same.
    with pytest.raises(SyntaxError):
        collective1.write(os.devnull)
    #
    # Passes now because internal and external names agree
    filename = os.path.join(tempfile.gettempdir(), collective2.get_bulletinIdentifier())
    _fh = open(filename, 'wb')
    collective2.write(_fh)
    _fh.close()
    os.unlink(filename)
    #
    collective2.write(filename)
    os.unlink(filename)
    #
    # Pass in a directory
    collective2.write(tempfile.gettempdir())
    os.unlink(filename)
    #
    # Print is normally to stdout, but for testing, route output to /dev/null
    _fh = open(os.devnull, 'w')
    print(collective2, file=_fh)
    _fh.close()


def test_header_option():

    taf_test = """FTUS45 KEKA 081900 CCA
TAF SBAF 081800Z NIL=
"""
    collective = tafEncoder.encode(taf_test)
    #
    # Verify default - no WMO AHL line
    collective.write()
    fn = collective.get_bulletinIdentifier()

    _fh = open(fn, 'r')
    first_line = _fh.readline()
    assert first_line != 'LTUS45 KEKA 081900 CCA\n'
    _fh.close()
    os.unlink(fn)

    filename = os.path.join(tempfile.gettempdir(), fn)
    _fh = open(filename, 'w')
    #
    # Insert WMO AHL line
    collective.write(_fh, header=True)
    _fh.close()

    # Verify first line is the WMO AHL
    _fh = open(filename, 'r')
    first_line = _fh.readline()
    assert first_line == 'LTUS45 KEKA 081900 CCA\n'
    _fh.close()
    os.unlink(filename)

    taf_test = """FTUS41 KCAE 090000 AAB
TAF AMD SBAF 090000Z 0900/1006 CNL="""

    collective = tafEncoder.encode(taf_test)
    #
    # Insert WMO AHL line
    collective.write(header=True)
    fn = collective.get_bulletinIdentifier()

    # Verify first line is the WMO AHL
    _fh = open(fn, 'r')
    first_line = _fh.readline()
    assert first_line == 'LTUS41 KCAE 090000 AAB\n'
    _fh.close()
    os.unlink(fn)


def test_operations():

    taf_test1 = """FTUS43 KBOU 081800
TAF SBAF 101800Z NIL=
"""

    taf_test2 = """FTUS43 KBOU 081800
TAF SBAF 101800Z NIL=
"""

    collective1 = tafEncoder.encode(taf_test1)
    collective2 = tafEncoder.encode(taf_test2)

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


def test_compression():

    taf_test = """FTUS43 KBOU 081800 CCA
TAF SBAF 101800Z NIL=
"""
    collective = tafEncoder.encode(taf_test, xml='xml.gz')
    #
    id = collective.get_bulletinIdentifier()
    assert id[-2:] == 'gz'
    #
    # Verify that compressed file is written and without WMO AHL
    # (header is ignored)
    #
    collective.write(header=True)
    try:
        _fh = gzip.open(id)
    except Exception as exc:
        assert False, f"Attempt to open gzip file failed {exc}"

    first_line = _fh.readline().decode('utf-8')
    assert first_line != 'LTUS43 KBOU 081800 CCA\n'
    _fh.close()
    os.unlink(id)

    taf_test = """FTUS41 KCAE 101200
TAF SBAF 101800Z NIL=
"""
    collective = tafEncoder.encode(taf_test)
    id = collective.get_bulletinIdentifier()
    assert id[-3:] == 'xml'

    collective.write(compress=True)
    nid = collective.get_bulletinIdentifier()
    assert nid[-2:] == 'gz'

    try:
        _fh = gzip.open(nid)
    except Exception as exc:
        assert False, f"Attempt to open gzip file failed {exc}"

    _fh.close()
    os.unlink(nid)
    

if __name__ == '__main__':

    test_empty()
    test_unlike()
    test_realize()
    test_operations()
    test_writes()
    test_header_option()
    test_compression()
