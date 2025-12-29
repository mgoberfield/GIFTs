import re

from . import tcaDecoder
from . import tcaEncoder
from .common import Encoder as E
#
# Purpose: Accepts ICAO Tropical Cyclone Advisory Traditional Alphanumeric Code form and generates equivalent IWXXM form.
#
# Copyright (C) 2025 Mark Oberfield
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# Contact Info: Mark.Oberfield@gmail.com
#
class Encoder(E.Encoder):
    """Accepts ICAO Tropical Cyclone Advisory Traditional Alphanumeric Code form and generates equivalent IWXXM form

       methods:
         .encode(text, [receiptTime='%Y%m%dT%H:%M:%SZ'])

            text = character string containing entire TAC message (required)
            receiptTime = date/time stamp the TAC message was received at TRANSLATOR centre (optional, see xmlConfig.py)

         returns Bulletin object."""

    def __init__(self):

        super(Encoder, self).__init__()

        self.re_AHL = re.compile(r'FK(?P<aaii>\w\w\d\d)\s+(?P<cccc>\w{4})\s+(?P<yygg>\d{6})(\s+(?P<bbb>[ACR]{2}[A-Z]))?')  # noqa:501
        self.re_TAC = re.compile(r'^TC ADVISORY.+', (re.MULTILINE | re.DOTALL))
        self.T1T2 = 'LK'

        self.decoder = tcaDecoder.Decoder()
        self.encoder = tcaEncoder.Encoder()
