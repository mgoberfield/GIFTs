Introduction
------------

This sub-directory, `/database`, contains a very simple table, aerodromes.tbl which is converted into a 'pickled'
python dictionary.

This dictionary serves as a means to map ICAO identifiers to name and place which is needed for METAR, SPECI
and TAF IWXXM documents. The demo software provided in this repository uses a pickled database file for
illustration purposes. You can either enlarge this flat file, aerodromes.tbl, to include your aerodromes or set
up database client interface that the GIFTs python software can use to access the geo-spatial information.

The database, aerodromes.tbl
----------------------------
This flat file consists of the following fields, separated by '|' characters:

1. ICAO identfier of the aerodrome.  Matches the following regular expression `[A-Z]{4}` (required)
2. IATA identifier/designator of the aerodrome. Matches the following regular expression: `[A-Z]{3}` (optional)
3. Alternate identifier (not ICAO nor IATA). Matches the following regular expression: `[A-Z0-9]{3,6}` (optional) 
4. Full name of the aerodrome, up to 60 characters. (optional)
5. Latitude of aerodrome in degrees.  Matches the following regular expression: `[-]?\d{1,2}\.\d{0,5}` (South is negative) (required)
6. Longitude of aerodrome in degrees.  Matches the following regular expression: `[-]?\d{1,3}\.\d{0,5}` (West is negative) (required)
7. Elevation of aerodrome in metres. (required)

Leading and trailing whitespace characters from field entries are removed. All letters are promoted to upper-case
in the IWXXM document.

The script, create_pickle_db.py
--------------------------------
A simple python script to read the aerodromes.tbl file, create a dictionary and 'pickle it' as a binary file
for later use.  The input and output file names are "aerodromes.tbl" and "aerodromes.db", respectively.

If your python interpreter is in your PATH, then

   $ create_pickle_db.py

is sufficient.  Otherwise, provide the full path to your python interpreter followed by create_pickle_db.py:

   $ /path/to/python/interpreter/python create_pickle_db.py
