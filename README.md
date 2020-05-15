This repository is a scientific product and is not official communication of the National Oceanic and Atmospheric Administration (NOAA), or the United States Department of Commerce (DOC). All NOAA GitHub project code is provided on an ‘as is’ basis and the user assumes responsibility for its use. Any claims against the Department of Commerce or Department of Commerce bureaus stemming from the use of this GitHub project will be governed by all applicable Federal law. Any reference to specific commercial products, processes, or services by service mark, trademark, manufacturer, or otherwise, does not constitute or imply their endorsement, recommendation or favoring by the Department of Commerce. The Department of Commerce seal and logo, or the seal and logo of a DOC bureau, shall not be used in any manner to imply endorsement of any commercial product or activity by DOC or the United States Government.

# GIFTS - Generate IWXXM From TAC Software
This repository hosts software provided by the United States' National Weather Service that transforms Annex 3 Traditional Alphanumeric Code (TAC) forms into IWXXM format.

The ICAO Meteorological Information Exchange Model (IWXXM) is a format for reporting weather information in eXtensible Markup Language (XML). The IWXXM XML schemas, developed and hosted by the WMO in association with ICAO, are used to encode aviation products described in the Meteorological Service for International Air Navigation, Annex 3 to the Convention on International Civil Aviation.

Version 3.0 of the IWXXM XML schemas encode METAR, SPECI, TAF, SIGMET, AIRMET, Volcanic Ash Advisory, Tropical Cyclone Advisory, and Space Weather Advisory reports.

This repository contains software, written exclusively in the Python language, that transforms the current TAC form of these reports into IWXXM XML documents. The advantage of the Python language is its popularity, rich functionality and wide availiability under many different computer operating systems.
