import os

try:
    import urllib.request as urlRequest
except ImportError:
    import urllib2 as urlRequest
import xml.etree.ElementTree as ET


def getConcepts(filename, concepts):

    root = ET.parse(filename)
    for x in root.iterfind('.//*{http://www.w3.org/2004/02/skos/core#}Concept'):
        value = x.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about')
        key = value[(value.rfind('/') + 1):]
        concepts.setdefault(key, []).append(value)


def readIgnoredURLs(filename):

    ignoredURLs = []
    with open(filename) as f:
        for raw in f:
            # ignore comment and blank lines
            lne = raw.strip()
            if len(lne) == 0 or lne.startswith('#'):
                continue
            ignoredURLs.append(lne)

    if ignoredURLs:
        print("NOTE: All concepts from the following URLs are ignored/skipped:")
        print('\n\t'.join(ignoredURLs))
        print("")

    return ignoredURLs


def check_GML_references(examplesDirectory, iwxxm_version, internet=False):
    #
    # Find all XML files in directory
    if os.path.isfile(os.path.join(os.getcwd(), 'ignoredURLs.txt')):
        ignoredURLs = readIgnoredURLs(os.path.join(os.getcwd(), 'ignoredURLs.txt'))

    xmlDocs = [os.path.join(examplesDirectory, f) for f in os.listdir(examplesDirectory)
               if os.path.isfile(os.path.join(examplesDirectory, f)) and f.endswith('.xml')]

    count = len(xmlDocs)
    print("Found %d XML files in %s" % (count, examplesDirectory))
    if count == 0:
        print("ERROR: No GML checks.")
        return 1

    if not internet:
        concepts = {}
        file_cache = []
        badCodeListRef = []
        additionalMsg = False

    returnCode = 0
    for docFilename in xmlDocs:

        print("GML Id and XLink checks on %s" % docFilename)
        root = ET.parse(docFilename)
        gmlIds = set([x.get('{http://www.opengis.net/gml/3.2}id')
                      for x in root.iterfind('.//*[@{http://www.opengis.net/gml/3.2}id]')])

        refIds = set([x.get('{http://www.w3.org/1999/xlink}href')[1:]
                      for x in root.iterfind('.//*[@{http://www.w3.org/1999/xlink}href]')
                      if x.get('{http://www.w3.org/1999/xlink}href').startswith('#uuid.')])

        externalRefs = frozenset([x.get('{http://www.w3.org/1999/xlink}href')
                                  for x in root.iterfind('.//*[@{http://www.w3.org/1999/xlink}href]')
                                  if x.get('{http://www.w3.org/1999/xlink}href').startswith('http')])
        #
        # Check to make sure all 'uuid' hrefs are linked to gml:ids
        badHrefs = frozenset(refIds - gmlIds)
        if len(badHrefs):
            returnCode = 1
            for missingIds in badHrefs:
                print("\tERROR: Missing gml ID as xlink:href %s" % missingIds)
            print("")
        #
        # For references to external sources, make sure they exist
        ignoreThis = False
        additionalMsg = False

        for xlinkTarget in externalRefs:

            url = xlinkTarget[:xlinkTarget.rfind('/')]
            for igURL in ignoredURLs:
                if url.startswith(igURL):
                    ignoreThis = True
                    break

            if ignoreThis:
                ignoreThis = False
                continue

            if internet:
                try:
                    response = urlRequest.urlopen(xlinkTarget)
                    if 200 > response.getcode() >= 300:
                        raise Exception
                except Exception:
                    print("\tERROR: xlink:href to '%s' does not resolve to a valid URL" %
                          xlinkTarget)
                    returnCode = 1
            else:
                chopped = xlinkTarget.split('/')
                concept = chopped[-1]
                try:
                    if xlinkTarget not in concepts[concept]:
                        filename = 'schematrons/%s/%s.rdf' % (iwxxm_version, '-'.join(chopped[2:-1]))

                        if filename not in file_cache:
                            raise KeyError
                        else:
                            print("\tERROR: xlink:href to '%s' does not resolve to a valid URL in the RDF files" %
                                  xlinkTarget)
                            returnCode = 1

                except KeyError:

                    filename = 'schematrons/%s/%s.rdf' % (iwxxm_version, '-'.join(chopped[2:-1]))
                    try:
                        getConcepts(filename, concepts)
                        file_cache.append(filename)

                        try:
                            if xlinkTarget not in concepts[concept]:
                                print("\tERROR: xlink:href to '%s' does not resolve to a valid URL in the RDF files" %
                                      xlinkTarget)
                                returnCode = 1
                        except KeyError:
                            print("\tWARNING: Concept %s not found in code list" % concept)

                    except IOError:

                        if filename not in badCodeListRef:
                            badCodeListRef.append(filename)
                            print("\tWARNING: Possible invalid reference to unknown/unapproved code list in document.")
                            print("\t\t Offending code list reference: %s" % xlinkTarget)
                            print("\tIf this reference resides in an <extension> block, this may be permissible.\n")

                        returnCode = 1
                        additionalMsg = True

    if returnCode:
        print("ERROR: Not all URL successfully resolved.")
    else:
        print("SUCCESS: All URL successfully resolved.")

    if additionalMsg:
        print("Examine WARNED references for correctness. If valid, create RDF files for them and place in schematron "
              "directory")

    return returnCode


if __name__ == '__main__':
    import sys
    check_GML_references(sys.argv[1], sys.argv[2], sys.argv[3] == 'True')
