------------------------------------------------------------------------------
# Continuous Integration Status
![Python package](https://github.com/mgoberfield/GIFTs/workflows/Python%20package/badge.svg)

-------------------------------------------------------------------------------
# Generate IWXXM From TAC
This repository hosts software that transforms Annex 3 Traditional Alphanumeric Code (TAC) forms into IWXXM products.

The ICAO Meteorological Information Exchange Model (IWXXM) is a means to report weather information in eXtensible Markup Language (XML). The IWXXM XML schemas, developed and hosted by the WMO in association with ICAO, are used to encode aviation products described in the Meteorological Service for International Air Navigation, Annex 3 to the Convention on International Civil Aviation.

The IWXXM XML schemas describe how METAR, SPECI, TAF, SIGMET, AIRMET, Volcanic Ash Advisory, Tropical Cyclone Advisory, and Space Weather Advisory reports and Significant Weather (SIGWX) are to be encoded in XML.

This repository contains software, written entirely in Python, that transforms the meteorological data in the current TAC form of these reports into IWXXM XML documents. The advantage of the Python language is its popularity, rich functionality, and wide availability under many different computer operating systems.

## Introduction
IWXXM became a WMO standard on 5 November 2020. Met Offices shall disseminate METAR, SPECI, TAF, AIRMET, SIGMET products and Tropical Cyclone, Volcanic Ash and Space Weather Advisories in IWXXM form after that date.

As XML--and creating XML documents--may be unfamiliar technology to those without an IT background, I am providing software to assist those in creating the new XML documents based on IWXXM schemas.

It should be understood that the software provided here is a short-term solution as TAC forms of these products will eventually cease to be a ICAO/WMO standard.

## Prequisites
This software is written entirely in the Python language. Python interpreter v3.9 or better is required.

## Installation
The following instructions assume you are using a computer with a Unix-based operating system. Installing this software on other operating systems may require some adjustments. These instructions install software which decodes the traditional alphanumeric code (TAC) forms of METAR, SPECI, TAF, Space Weather, Tropical Cyclone and Volcanic Ash advisories and encodes them into IWXXM equivalents.

To install the GIFTs<sup>1</sup> package system-wide, use Python's setuptools package and issue the following commands:

	$ cd /path/to/install/directory
	$ git clone https://github.com/NOAA-MDL/GIFTs.git
	$ cd GIFTs
	$ python setup.py install

If you do not have sufficient  permissions to modify your Python's site-packages directory, then update your PATH or PYTHONPATH environmental variable to include the directories where the source code resides.

	$ setenv PATH ${PATH}:/path/to/install/directory/GIFTs/gifts:/path/to/install/directory/GIFTs/gifts/common # C-shell
	% export PATH=${PATH}:/path/to/install/directory/GIFTs/gifts:/path/to/install/directory/GIFTs/gifts/common # Bourne-shell
	
The python files' `import` statements will need to be modified too, if you should use this alternative.

## Configuration

### xmlConfig
While the METAR/SPECI and TAF encoders themselves require minimal setup for use, it is helpful to know how the resulting IWXXM documents can be tweeked. The file [xmlConfig.py](https://github.com/mgoberfield/GIFTs/blob/master/gifts/common/xmlConfig.py) has comments throughout describing the various XML configuration variables: what they're for, and what values they can take on should you want to make changes. The most likely change you will make is whether to provide the altitude of the aerodromes. The vertical datum must be known and provided in order to correctly describe the aerodromes' elevations.

### geoLocations database
The METAR/SPECI and TAF encoders will need an external, user-provided resource that maps the ICAO 4-character identifiers to the aerodromes' location. The `database/` subdirectory contains a simple python script to construct a python dictionary to perform the mapping. Please consult the [README](https://github.com/mgoberfield/GIFTs/tree/master/gifts/database) file in that directory for more details on how to create a simple database that GIFTs can use. Either this technique or setting up a database client using one of Python's database modules is required in order to use the GIFTs encoders. The latter technique is beyond the scope of these instructions.

## Using the software
To illustrate the use of the software, the demo subdirectory contains two simple python programs. Please consult the `demo/` subdirectory [README](https://github.com/mgoberfield/GIFTs/tree/master/demo) file for further details.

## Bulletins
Every GIFTs encoder, after processing a TAC message successfully, returns an object of the class [Bulletin](https://github.com/mgoberfield/GIFTs/blob/master/gifts/common/bulletin.py). The Bulletin object has similarities to a python list object: it has a "length" (the number of IWXXM XML reports); can be indexed; can be iterated; and [ElementTree](https://docs.python.org/3/library/xml.etree.elementtree.html) reports added and removed with the usual python list operations. In addition to the built-in list operations, python's [print()](https://docs.python.org/3/library/functions.html#print) function will nicely format (for human eyes) the bulletin object and write out the complete XML document to a file (default is sys.stdout).

For international distribution, IWXXM reports, due to their increased character length and expanded character set, shall be sent over the Extended ATS Message Handling System (AMHS) as a File Transfer Body Part.<sup>2</sup> The Bulletin class provides a convenient [write()](https://github.com/mgoberfield/GIFTs/blob/master/gifts/common/bulletin.py#L189) method to generate the `<MeterologicalBulletin>`<sup>3</sup> XML document for transmission over the AMHS.

Because of the character length of the `<MeteorologicalBulletin>`, the File Transfer Body Part shall be a compressed file using the gzip protocol. By default, the `.encode()` method of the [Encoder](https://github.com/mgoberfield/GIFTs/blob/master/gifts/common/Encoder.py#L15) class is to generate an uncompressed file when the bulletin.write() method is invoked. To generate a compressed `<MeteorologicalBulletin>` file for transmission over the AMHS is to set the `compress` flag to True in the Bulletin object's write() method, like so:

    bulletin.write(compress=True)  
This will generate a gzip file containing the `<MeteorologicalBulletin>` suitable for transmission over the AMHS.

## Caveats
The decoders were written to follow Annex 3 specifications for the TAC forms. If your observations or forecast products deviate significantly from Annex 3, then this software will likely refuse to encode the data into IWXXM.  Fortunately, solutions can be readily found, ranging from trivial to challenging (see United States METAR/SPECI [reports](https://nws.weather.gov/schemas/iwxxm-us/3.0/examples/metars)).

# IWXXM Validation
It is important that your IWXXM XML documents 'validate' before dissemination. If they don't, they may be rejected by your consumers. Separate from GIFTs, MDL has provided a convienent python script that invokes NCAR's CRUX utility along with IWXXM schemas, schematron and supporting data files to perform this crucial step before disseminating your IWXXM products. The software can be found in the `/validation` subdirectory. Please consult the [README](https://github.com/mgoberfield/GIFTs/blob/master/validation) file for that utility.  You can use this utility to validate the IWXXM XML files created by the `demo1.py` program. 

-------------------
<sup>1</sup>Yes, I know the project name is presumptuous. I apologize.  
<sup>2</sup>_Guidelines for the Implementation of OPMET Data Exchange using IWXXM, Fourth Edition - November 2020_  
<sup>3</sup>_Manual on Codes, International Codes, Volume I.3, Annex II to the WMO Technical Regulations, Part D - Representations derived from data models, 2019 edition_, ref. FM 201-16
