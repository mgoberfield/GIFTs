#!/usr/bin/env python

import argparse
import sys
import os
import checkGMLReferences
import codeListsToSchematron as codeLists


def main(cmdargs):

    cwd = os.getcwd()
    if not os.path.isfile(os.path.join(cwd, 'bin', 'crux-1.3-all.jar')) or \
       not os.path.isdir(os.path.join(cwd, 'externalSchemas')):
        print("This script must be run from the top-level of the install directory and contain:")
        print("  the 'bin' subdirectory,")
        print("  the 'externalSchemas' subdirectory.")
        sys.exit(1)

    # obtain WMO schema and codes registry content
    if cmdargs.fetch:
        print("Getting version %s of IWXXM schemas, schematron and associated RDF files" % cmdargs.version)
        codeLists.run(cmdargs)
    else:
        #
        # Check to make sure the schemas are there . . .
        cwd = os.getcwd()
        schemaPath = os.path.join(cwd, 'schemas', cmdargs.version)
        schematronPath = os.path.join(cwd, 'schematrons', cmdargs.version)
        if not os.path.isfile(os.path.join(schemaPath, 'iwxxm.xsd')) or \
           not os.path.isfile(os.path.join(schematronPath, 'iwxxm.sch')):
            print("Missing required %s files. Fetching them and running GML checks" % cmdargs.version)
            codeLists.run(cmdargs)
            cmdargs.noGMLCheck = False

    returnCode = validate_xml_files(cmdargs)
    if returnCode > 0:
        print("========= Validation FAILED on %s =========" % cmdargs.directory)
    else:
        print("========= Validation SUCCESSFUL on %s =========" % cmdargs.directory)
    sys.exit(returnCode)


def validate_xml_files(cmdargs):

    cwd = os.getcwd()
    schemaDirectory = os.path.join(cwd, 'schemas', cmdargs.version)
    schematronFile = os.path.join(cwd, 'schematrons', cmdargs.version, 'iwxxm.sch')

    catalogTemplate = os.path.join(cwd, 'catalog.template.xml')
    thisCatalogFile = catalogTemplate.replace('.template', '-%s' % cmdargs.version)

    # replace ${INSTALL_DIR}, ${IWXXM_VERSION}, and ${IWXXM_VERSION_DIR} with appropriate values in the catalog.xml file
    if not os.path.exists(thisCatalogFile):
        with open(catalogTemplate) as templateFhandle:
            with open(thisCatalogFile, 'w') as catalogFhandle:
                catalogText = templateFhandle.read()
                catalogText = catalogText.replace("${INSTALL_DIR}", cwd)
                catalogText = catalogText.replace("${IWXXM_VERSION}", cmdargs.version)
                catalogText = catalogText.replace("${IWXXM_VERSION_DIR}", schemaDirectory)
                catalogFhandle.write(catalogText)
    else:
        print("Catalog file version %s already exists in directory. Using it for validation." % cmdargs.version)
        cmdargs.keep = True

    print('Validating all XML files in %s with IWXXM XML schemas and schematron (version: %s)' % (cmdargs.directory,
                                                                                                  cmdargs.version))
    javacmd = 'java -jar %s -c %s -s %s %s%c*.xml' % (os.path.join(cwd, 'bin', 'crux-1.3-all.jar'), thisCatalogFile,
                                                      schematronFile, cmdargs.directory, os.path.sep)
    validationResult = os.system(javacmd)
    if validationResult > 0:
        print('FAILED validation.  Continuing . . .')
    else:
        print('SUCCESSFUL validation')

    # remove the modified catalog file
    if not cmdargs.keep:
        os.remove(thisCatalogFile)

    if not cmdargs.noGMLChecks:
        print('CHECKING GML correctness')
        checkResult = checkGMLReferences.check_GML_references(cmdargs.directory, cmdargs.version, cmdargs.useInternet)
        if checkResult > 0:
            print('CHECKING GML correctness finished, some files are not correct!!!')
        else:
            print('CHECKING GML correctness finished successfuly')
    else:
        checkResult = 0

    # this can return status codes of 256, which is an undefined value sometimes interpreted as 0.
    # Force it to a valid value
    if validationResult != 0:
        validationResult = 1

    return validationResult | checkResult


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Rudimentary validation tool for IWXXM documents")
    parser.add_argument("-f", "--fetch", help="fetch files from WMO Code Registry and WMO schema site",
                        action="store_true", default=False)
    parser.add_argument("-u", "--useInternet", help="when checking GML links, query WMO Code Registry for validation",
                        action="store_true", default=False)
    parser.add_argument("--noGMLChecks", help="skip GML link checking", action="store_true", default=False)
    parser.add_argument("-k", "--keep", help="do not delete catalog file when validation finishes",
                        action="store_true", default=False)
    parser.add_argument("-v", "--version", help="IWXXM version major.minor number to validate against, default '3.0'",
                        type=str, default="3.0")
    parser.add_argument("directory", help="directory path containing IWXXM XML documents for validation", type=str)
    cmdargs = parser.parse_args()

    main(cmdargs)
