"""
Search all IWXXM schemas for vocabulary/codelist entries and download each entry in RDF format.
For use with iwxxm.sch which has schematron rules derived from the IWXXM UML model that ensure
a codelist element's xlink:href is a member of the corresponding codelist.
"""

import os
import sys
from os.path import isfile, join
# lxml is used instead of ElementTree because it tracks parent relationships
from lxml import etree
import requests

import argparse


def run(cmdargs):

    if sys.version_info.major == 2 and os.name == "nt":
        os.symlink = symlink_ms
    #
    # Check for presence of desired version of schemas and schematron directories and files
    fetchSchemaFiles = False
    fetchSchematronFile = False
    #
    cwd = os.getcwd()
    schemaPath = os.path.join(cwd, 'schemas')
    if not os.path.exists(schemaPath):
        os.mkdir(schemaPath)
        fetchSchemaFiles = True

    schemaPath = os.path.join(cwd, 'schemas', cmdargs.version)
    if not os.path.exists(schemaPath):
        os.mkdir(schemaPath)
        fetchSchemaFiles = True
    #
    # Check for presence of schema files
    if not os.path.isfile(os.path.join(schemaPath, 'iwxxm.xsd')):
        fetchSchemaFiles = True

    schematronPath = os.path.join(cwd, 'schematrons')
    if not os.path.exists(schematronPath):
        os.mkdir(schematronPath)
        fetchSchematronFile = True

    schematronPath = os.path.join(cwd, 'schematrons', cmdargs.version)
    if not os.path.exists(schematronPath):
        os.mkdir(schematronPath)
        fetchSchematronFile = True

    if not os.path.isfile(os.path.join(schematronPath, 'iwxxm.sch')):
        fetchSchematronFile = True

    if not os.path.isdir(schemaPath) or not os.path.isdir(schematronPath):
        print('ERROR: %s and %s must be existing directories' % (schemaPath, schematronPath))
        sys.exit(1)

    if fetchSchemaFiles:
        source = 'http://schemas.wmo.int/iwxxm/%s' % cmdargs.version
        suffix = 'xsd'
        fetchLocalCopy(source, suffix, schemaPath)

    if fetchSchematronFile:
        source = 'http://schemas.wmo.int/iwxxm/%s/rule' % cmdargs.version
        suffix = 'sch'
        fetchLocalCopy(source, suffix, schematronPath)

    ns = {'xs': 'http://www.w3.org/2001/XMLSchema'}
    sn = {}
    # insert all values as keys as well so the lookups can go both ways
    for key, value in ns.items():
        sn[value] = key
    ns.update(sn)

    xsdfiles = [join(schemaPath, f) for f in os.listdir(schemaPath)
                if f.endswith(".xsd") and isfile(join(schemaPath, f))]

    # dictionary mapping from XSD Type names such as 'AerodromeRecentWeatherType' to the path on codes.wmo.int
    # such as 'http://codes.wmo.int/49-2/AerodromeRecentWeather'
    typeToCodeList = {}

    # first go through the XSD files and find all types with a vocabulary/codelist
    # we walk through the XSD files twice because XSD Types are imported and used in other XSD files which means
    # we need to search all files for elements corresponding to XSD Types
    for xsdFile in xsdfiles:
        print('Parsing %s for vocabularies/code lists' % xsdFile)
        tree = etree.parse(xsdFile)
        root = tree.getroot()

        for complexType in root.findall('xs:complexType', ns):
            # print "Found complexType: "+str(complexType)
            for vocabularyElem in complexType.findall('xs:annotation/xs:appinfo/xs:vocabulary', ns):
                codeListPath = vocabularyElem.text
                # for example, WeatherCausingVisibilityReductionType
                complexTypeName = complexType.attrib['name']

                typeToCodeList[complexTypeName] = codeListPath

                # Download the RDF representation of this vocabulary
                download_codelist(codeListPath, schematronPath)
    # Also download http://codes.wmo.int/common/nil for nilReason instances, not referenced by an xsd
    # see https://github.com/wmo-im/iwxxm/issues/193
    download_codelist('http://codes.wmo.int/common/nil', schematronPath)
    #
    # For local validation of GML href links, the 'http://codes.wmo.int/49-2/AerodromePresentOrForecastWeather'
    # code list is a _very_ large subset of WMO No. 306 Vol 1 code-table 4678 (399 entries verses 402)
    #
    if 'http://codes.wmo.int/49-2/AerodromePresentOrForecastWeather' in typeToCodeList.values():
        srcfile = parseLocalCodeListFile('http://codes.wmo.int/49-2/AerodromePresentOrForecastWeather')
        deslink = parseLocalCodeListFile('http://codes.wmo.int/306/4678')
        if os.path.isfile(os.path.join(schematronPath, deslink)) == False:
            try:
                os.symlink(os.path.join(schematronPath, srcfile), os.path.join(schematronPath, deslink))
            except Exception as msg:
                print('Unable to create symbolic link. Reason: %s' % msg)


def fetchLocalCopy(source, suffix, destinationDirectory):

    response = requests.get(source)
    if response.status_code != 200:
        print('ERROR: Unable to access %s' % source)
        return

    table = etree.HTML(response.text).find('body/table')
    for schemaFile in [a.get('href') for a in table.iterfind(".//a[@href]") if a.get('href').endswith(suffix)]:
        schemaContents = requests.get('%s/%s' % (source, schemaFile))
        if schemaContents.status_code == 200:
            with open(os.path.join(destinationDirectory, schemaFile), 'w') as _fh:
                try:
                    _fh.write(schemaContents.text)
                except UnicodeEncodeError:
                    _fh.write(schemaContents.text.encode('utf-8'))
        else:
            print('Unable to write %s in %s (%s)' % (schemaFile, destinationDirectory, schemaContents.status_code))


def download_codelist(codeListPath, schematronPath):
    '''Download the RDF representation of this vocabulary'''
    headers = {"Accept": "application/rdf+xml"}
    print('\tDownloading %s in RDF format' % codeListPath)

    r = requests.get(codeListPath, headers=headers)
    localCodeListFile = os.path.join(schematronPath, parseLocalCodeListFile(codeListPath))
    if r.status_code == 200:
        with open(localCodeListFile, 'w') as _fh:
            try:
                _fh.write(r.text)
            except UnicodeEncodeError:
                _fh.write(r.text.encode('utf-8'))
    else:
        print('ERROR: Could not load code list at %s!' % codeListPath)


def parseLocalCodeListFile(codeListHttpPath):

    filename = codeListHttpPath.replace('http://', '').replace('/', '-')  # remove slashes and 'http://'
    return '%s.rdf' % filename


def symlink_ms(source, link_name):

    import ctypes
    csl = ctypes.windll.kernel32.CreateSymbolicLinkW
    csl.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32)
    csl.restype = ctypes.c_ubyte
    flags = 1 if os.path.isdir(source) else 0
    if csl(link_name, source.replace('/', '\\'), flags) == 0:
        raise ctypes.WinError()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument("--version", "-v", help="IWXXM version major.minor number to validate against", type=str,
                        default="3.0")
    cmdargs = parser.parse_args()

    run(cmdargs)
