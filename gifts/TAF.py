import logging
import re

from . import tafDecoder
from . import tafEncoder
from .common import Encoder as E


class Encoder(E.Encoder):
    """Accepts Terminal Aerodrome Forecast Traditional Alphanumeric Code form and generates equivalent IWXXM form

       geoLocationsDB = object containing a get() method to return metadata information based on ICAO Id. Response
                        shall be of the form 'name|IATA_ID|alternate_designator|latitude longitude elevation' (required)

       methods:
         .encode(text, [receiptTime='%Y%m%dT%H:%M:%SZ'])

            text = character string containing entire TAC message (required)
            receiptTime = date/time stamp the TAC message was received at TRANSLATOR centre (optional, see xmlConfig.py)

         returns Bulletin object."""

    def __init__(self, geoLocationsDB):

        super(Encoder, self).__init__()

        self.re_AHL = re.compile(r'FT(?P<aaii>\w\w\d\d)\s+(?P<cccc>\w{4})\s+(?P<yygg>\d{6})(\s+(?P<bbb>[ACR]{2}[A-Z]))?')  # noqa:501
        self.re_TAC = re.compile(r'^TAF(?:\s+(?:AMD|COR|CC[A-Z]|RTD))?\s+[A-Z]{4}.+?=', (re.MULTILINE | re.DOTALL))
        self.T1T2 = "LT"

        self._Logger = logging.getLogger(__name__)
        self.decoder = tafDecoder.Decoder()
        self.encoder = tafEncoder.Encoder()
        self.geoLocationsDB = geoLocationsDB
