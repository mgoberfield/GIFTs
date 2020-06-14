import re

from . import vaaDecoder
from . import vaaEncoder
from .common import Encoder as E


class Encoder(E.Encoder):
    """Accepts Accepts ICAO Volcanic Ash Advisory Traditional Alphanumeric Code form and generates equivalent IWXXM form

       methods:
         .encode(text, [receiptTime='%Y%m%dT%H:%M:%SZ'])

            text = character string containing entire TAC message (required)
            receiptTime = date/time stamp the TAC message was received at TRANSLATOR centre (optional, see xmlConfig.py)

         returns Bulletin object."""

    def __init__(self):

        super(Encoder, self).__init__()

        self.re_AHL = re.compile(r'FV(?P<aaii>\w\w\d\d)\s+(?P<cccc>\w{4})\s+(?P<yygg>\d{6})(\s+(?P<bbb>[ACR]{2}[A-Z]))?')  # noqa:501
        self.re_TAC = re.compile(r'^VA ADVISORY.+', (re.MULTILINE | re.DOTALL))
        self.T1T2 = "LU"

        self.decoder = vaaDecoder.Decoder()
        self.encoder = vaaEncoder.Encoder()
