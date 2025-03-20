import re

from . import metarDecoder
from . import metarEncoder
from .common import Encoder as E


class Encoder(E.Encoder):
    """Accepts Meteorological Aerodrome Report Traditional Alphanumeric Code forms based on Annex 3 and generates
       equivalent IWXXM form

       geoLocationsDB = object containing a get() method to return metadata information based on ICAO Id. Response
                        shall be of the form 'name|IATA_ID|alternate_designator|latitude longitude elevation' (required)

       methods:
         .encode(text, [receiptTime='%Y%m%dT%H:%M:%SZ'])

            text = character string containing entire TAC message (required)
            receiptTime = date/time stamp the TAC message was received at TRANSLATOR centre (optional, see xmlConfig.py)

         returns Bulletin object."""

    def __init__(self, geoLocationsDB):
        """Accepts Meteorological Aerodrome Report Traditional Alphanumeric Code forms based on Annex 3 and generates
        equivalent IWXXM form

        geoLocationsDB = object containing a get() method to return metadata information based on ICAO Id. Response
                         shall be of the form 'name|alternate_name|latitude longitude elevation' (required)"""

        super(Encoder, self).__init__()

        self.re_AHL = re.compile(r'S(?P<aaii>(A|P)[A-Z][A-Z]\d\d)\s+(?P<cccc>[A-Z]{4})\s+(?P<yygg>\d{6})(\s+(?P<bbb>[ACR]{2}[A-Z]))?')  # noqa:501
        self.re_TAC = re.compile(r'^(?:METAR|SPECI)\s+(?:COR\s+)?[A-Z][A-Z0-9]{3}\s.+?=', (re.MULTILINE | re.DOTALL))
        self.T1T2 = "L"

        self.decoder = metarDecoder.Annex3()
        self.encoder = metarEncoder.Annex3()
        self.geoLocationsDB = geoLocationsDB
