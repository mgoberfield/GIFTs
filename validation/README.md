# Introduction

This software package can be used to check IWXXM documents for correctly-formed XML, schema and schematron
('business rules') validation. The Java code, CRUX, performs the validation steps. Information on CRUX can
be found at the following URL: https://github.com/NCAR/crux.


Prequisites
-----------

The software consists of Python and Java code.

Python code requires the 'lxml' and 'requests' modules to parse XML documents and retrieve IWXXM schemas and
RDF files for local (and fast) validation. These modules can be obtained via the 'pip' command, if not already
installed.

The version of python must be at least 2.7 or better.

This code has been developed, tested and works on a reasonably up-to-date Linux OS and Windows 10 machine.
For old and/or other operating systems, this code may need some adjustments, but there are no guarantees.
We are not obligated to make this software work on your computers.


Installation
------------

This README file is at the top directory of the installation package.

The package has the following directory tree:

	<TOP_DIR>
    bin  -- Java CRUX utility
    externalSchemas  -- Local copies of schemas. Should be occasionally refreshed from their respective sources.
        schemas.opengis.net
            gml
                3.2.1
            sampling
                2.0
            iso
                19139
                    20070417
                        gmx
                        gco
                        gmd
                        gss
                        gts
                        gsr
            om
                2.0
            samplingSpatial
                2.0
            sweCommon
                2.0
        schemas.wmo.int
            metce
                1.1
                    rule
                1.2
                    rule
                1.0
                    rule
            collect
                1.1
                    rule
                1.2
                    rule
            opm
                1.1
                    rule
                1.2
                    rule
                1.0
                    rule
            saf
                1.1
                    rule
                1.0
                    rule
        aero
            aixm
                5.1.1
                    message
                5.1
                5.1_profiles
                    AIXM_WX
                        5.1a
                            xlink
                            ISO_19136_Schemas
                            message
                            ISO_19139_Schemas
                                gmx
                                gco
                                resources
                                    crs
                                    example
                                    uom
                                    Codelist
                                gmd
                                gss
                                gts
                                gsr
                5.1.1_profiles
                    AIXM_WX
                        5.1.1b
                            message
                        5.1.1a
                            message
        org
            w3c
                1999
                2001

    schemas -- local copies of the IWXXM schemas (created later)
    schematrons -- local copies of the IWXXM schematrons (created later)


IWXXM Validation
----------------

The python script, 'iwxxmValidator.py' requires a single argument, the directory path to the IWXXM XML
documents.

Invoking the script for help with the '-h' or '--help' flag provides the following options:

	usage: iwxxmValidator.py [-h] [-f] [-u] [--noGMLChecks] [-k] [-v VERSION] directory

	Rudimentary validation tool for IWXXM documents

	positional arguments:
  	   directory             directory path containing IWXXM XML documents for
           			 validation (required)

	optional arguments:
	  -h, --help            show this help message and exit
	  -f, --fetch           fetch files from WMO Code Registry and WMO schema site
	  -u, --useInternet     when checking GML links, query WMO Code Registry for
              			validation
	  --noGMLChecks         skip GML link checking
	  -k, --keep            do not delete catalog file when validation finishes
	  -v VERSION, --version VERSION
                        	IWXXM version major.minor number to validate against,
                        	default '3.0'

--version flag
------------------
By default, the validation tool checks IWXXM v3.0 documents. If your IWXXM XML documents are based on a 
different version of IWXXM, provide the appropriate major.minor combination using the '-v' or '--version'
flag.

The script will check for this version's local copy of the IWXXM schemas and schematron, and associated
RDF files from the WMO Code Registry. If a copy is not found, the script will go to the canonical sources,
'http://schemas.wmo.int/iwxxm' and 'http://codes.wmo.int', to download them. Therefore, your machine will
need access to the Internet when running this script the first time, and when switching to new versions.


--fetch flag
----------------
If circumstances require it, you can force the script to download and overwrite the local cache of the 
IWXXM schemas and schematron files with the '-f' or '--fetch' flag. (Default: do not fetch)


--keep flag
---------------
The validator creates an OASIS style Catalog file on-the-fly for local validation which speeds up the
process up considerably. It is normally deleted when the script finishes. (Default: do not keep)

The catalog file can be used in "XML-aware" editors that can perform XML full validation. With this flag
set, the OASIS Catalog file is kept in the top-level directory with the name, 'catalog-<v>.xml' where
<v> is the IWXXM major.minor number.

If a catalog-<v>.xml is already present in the directory, the script will NOT overwrite it, but use it as
is.


--noGMLChecks flag
----------------------
After performing XML validation, a further examination of the internal and external references within each
XML document is done. As a prerequisite, this step requires the XML document to be 'well-formed'. If this
flag is given, this check is skipped. (Default: do GML reference checks)


--useInternet flag
----------------------
If GML checks are enabled, the algorithm has the option to query code registries which requires
Internet connectivity (and can be slow). Or the algorithm can refer to the local copy of the RDF files to
determine valid references to code lists (fast).  (Default: use local copy of RDF files)

To run:
-------

If the python and java interpeters are in your execution PATH, then 

      iwxxmValidator.py <directorypathtoXMLdocuments>

is sufficient.

Notes:
------
This software is not meant to be a subtitute for more sophisticated XML-aware applications. This is a basic, relatively "unfriendly" tool if you are new to XML documents and the technology associated with them. It _can_ help you find errors in your documents but sometimes the error messages from CRUX are cryptic. We make no apologies for that.

When using tool the first time on Windows machines, the user must have the ability to create a symbolic link to a file as it's created as part of downloading files from the WMO Code Registry.  After the initial downloading of files and setup, this particular privilege is no longer needed on subsequent invocations of `iwxxmValidator.py`.

This script can be used to quickly validate IWXXM messages before dissemination in an operational environment.

There are numerous examples of validated IWXXM documents on the Internet.  The canoncial IWXXM source has a few instances in the http://schemas.wmo.int/iwxxm/*version*/examples folders.

Another repository of examples is the WMO-IM GitHub site: http://github.com/wmo-im/iwxxm-translation

However, after genuine effort on your part, you cannot figure out the problem with your XML document, please raise your issue to the CBS TT-AvXML google group for assistance:

https://groups.google.com/a/wmo.int/forum/#!forum/cbs-tt-avxml

There are people on that forum who have probably seen your issue before and can help.

An 'ignoredURLs.txt' file is provided for the case when your IWXXM documents have `<extension>` blocks that
contain references to URLs that are not part of the WMO Code Registry. By adding the URLs in this file,
this will suppress warning messages from the checkGMLReferences routine.

The schematron portion of the CRUX utility will create a directory cache called 'cruxcache' sub-directory
in the directory designated in java.io.tmpdir
