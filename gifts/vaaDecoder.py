#
# Name: vaaDecoder.py
#
# Purpose: To decode, in its entirety, the Volcanic Ash Advisory traditional alphanumeric code
#          as described in the Meteorological Service for International Air Navigation, Annex 3
#          to the Convention on International Civil Aviation.
#
# Author: Mark Oberfield
# Organization: NOAA/NWS/OSTI/MDL/WIAB
#
import cmath
import logging
import math
import time
import re

from .common import xmlUtilities as deu
from .common import tpg


class MissingAirSpaceWinds(tpg.Error):
    """Not providing wind information when volcanic ash cloud is not observed in satellite imagery
    """
    pass


class Decoder(tpg.Parser):
    r"""
    set lexer = ContextSensitiveLexer
    set lexer_dotall = False

    separator spaces:    '\s+' ;

    token test: 'STATUS:\s*TEST' ;
    token exercise: 'STATUS:\s*EXER\w{0,4}' ;
    token dtg: 'DTG:\s*(?P<date>\d{8})/(?P<time>\d{4})Z' ;
    token centre: 'VAAC:\s*(\w.*)' ;
    token vname: 'VOLCANO:\s*(\w.*)' ;
    token vloc: 'PSN:\s*(([NS]\d{2,4}\s+[EW]\d{3,5})|UNKNOWN)' ;
    token region: 'AREA:\s*(\w.*)' ;
    token summit: 'SUMMIT ELEV:\s*(SFC|UNKNOWN|((?P<elevation>\d{1,5})\s?(?P<uom>M|FT))).*' ;
    token advnum: 'ADVISORY NR:\s*(\d{4}/\d{1,4})' ;
    token source1: 'INFO SOURCE:\s*([\S\s]+)(?=AVIATION COLOU?R CODE:)' ;
    token source2: 'INFO SOURCE:\s*([\S\s]+)(?=ERUPTION DETAILS:)' ;
    token colour: 'AVIATION COLOU?R CODE:\s*(\w.+)' ;
    token details: 'ERUPTION DETAILS:\s*([\S\s]+)(?=(OBS|EST) VA DTG)' ;
    token obsdtg: '(OBS|EST) VA DTG:\s*(?P<day>\d{2})/(?P<time>\d{4})Z' ;
    token opreamble: '(OBS|EST) VA CLD:' ;
    token fpreamble: 'FCST VA CLD \+(?P<fhr>\d{1,2})\s?HR?:' ;
    token dayhour: '\d{2}/\d{4}Z' ;
    token top: 'TOP\s+FL(\d{3})' ;
    token midlyr: 'FL(\d{3}/\d{3})' ;
    token sfc: 'SFC/FL(\d{3})' ;
    token box: '(\d{2,3})(KM|NM)\s+WID\s+LINE\s+BTN' ;
    token latlon: '(?P<lat>[NS]\d{2,4})\s+(?P<lon>[EW]\d{3,5})' ;
    token movement: 'MOV\s+([NEWS]{1,3})\s+(\d{1,3})(-\d{2,3})?(?P<uom>KMH|KT)' ;
    token vanotid: 'VA NOT IDENTIFIABLE[\S\s]+(?=FCST VA CLD \+6)' ;
    token noashexp: 'NO\s+(ASH|VA)\s+EXP' ;
    token notavbl:  'NOT\s+AVBL' ;
    token notprvd:  'NOT\s+PROVIDED' ;
    token rmk: 'RMK:\s*([\S\s]+)(?=NXT ADVIS)' ;
    token nextdtg: 'NXT ADVISORY:\s*((NO FURTHER ADVISORIES)|(((NO LATER THAN )|(WILL BE ISSUED BY ))?(?P<date>\d{8})/(?P<time>\d{4})Z?))' ;  # noqa: E501

    START/d -> VAA $ d=self.finish() $ ;
    VAA -> 'VA ADVISORY' (Test|Exercise)? DTG Centre VName VLoc Region Summit AdvNum Source ColorCode? Details ObsDTG ObsClds FcstClds+ Rmk NextDTG ;  # noqa: E501

    Source -> (Source1|Source2) ;
    ObsClds -> oPreamble (VaNotId|(Volume (Box? (LatLon|'-')+) Movement)+) ;
    FcstClds -> fPreamble DayHour? (Volume? (NoAshExp|NotAvbl|NotPrvd|(Box? (LatLon|'-')+)))* ;
    Volume -> (Sfc|MidLyr|Top)  ;

    Exercise -> exercise/x $ self.status(x) $ ;
    Test -> test/x $ self.status(x) $ ;
    DTG -> dtg/x $ self.dtg(x) $ ;
    Centre -> centre/x $ self.centre(x) $ ;
    VName -> vname/x $ self.vname(x) $ ;
    VLoc -> vloc/x $ self.vloc(x) $ ;
    Region -> region/x $ self.region(x) $ ;
    Summit -> summit/x $ self.summit(x) $ ;
    AdvNum -> advnum/x $ self.advnum(x) $ ;
    Source1 -> source1/x $ self.source(x,'ERUPTION DETAILS:') $ ;
    Source2 -> source2/x $ self.source(x,None) $ ;
    ColorCode -> colour/x $ self.colour(x) $ ;
    Details -> details/x $ self.details(x) $ ;
    ObsDTG -> obsdtg/x $ self.dtg(x) $ ;
    oPreamble -> opreamble/x $ self.preamble(x) $ ;
    fPreamble -> fpreamble/x $ self.preamble(x) $ ;
    DayHour -> dayhour/x $ self.dtg(x) $ ;
    Top -> top/x $ self.top(x) $ ;
    MidLyr -> midlyr/x $ self.midlyr(x) $ ;
    Sfc -> sfc/x $ self.sfc(x) $ ;
    Box -> box/x $ self.box(x) $ ;
    LatLon -> latlon/x $ self.latlon(x) $ ;
    Movement -> movement/x $ self.movement(x) $ ;
    VaNotId -> vanotid/x $ self.vanotid(x) $ ;
    NoAshExp -> noashexp $ self.noash() $ ;
    NotAvbl -> notavbl  $ self.noash() $ ;
    NotPrvd -> notprvd $ self.noash() $ ;
    Rmk -> rmk/x $ self.rmk(x) $ ;
    NextDTG -> nextdtg/x $ self.dtg(x) $ ;
    """

    def __init__(self):

        self._tokenInEnglish = {'_tok_1': 'VA ADVISORY line', 'dtg': 'Date/Time', 'centre': 'Issuing Centre',
                                'vname': 'Name of Volcano', 'vloc': 'Location of Volcano or UNKNOWN',
                                'region': 'Region', 'summit': 'Summit Elevation', 'advnum': 'Advisory Number',
                                'source1': 'Sources', 'colour': 'Color Code', 'details': 'Eruption Details',
                                'obsdtg': 'Observed date/time ', 'opreamble': 'observed ash cloud(s)',
                                'fpreamble': 'forecast ash cloud position(s)', 'dayhour': 'Day/Hour timestamp',
                                'top': 'TOP/FL###', 'midlyr': 'FL###/###', 'sfc': 'SFC/FL###',
                                'box': 'box dimensions', 'latlon': 'latitude/longitude pair',
                                'movement': 'ash cloud movement', 'vanotid': 'VA not identified statement',
                                'notprvd': 'Not Provided statement', 'noashexp': 'No Ash Expected',
                                'rmk': 'Remarks', 'nextdtg': 'Next VAA issuance time',
                                '_tok_2': 'dash character (-)', '_tok_3': 'dash character (-)'}

        self.header = re.compile(r'.*(?=VA ADVISORY)', re.DOTALL)
        self._reWinds = re.compile(r'(WINDS?)?\s+(SFC|FL(?P<bottom>\d{3}))(/((FL)?(?P<top>\d{3})))?\s+(?P<dir>VRB|\d{3})/?(?P<spd>\d{1,3})(-\d{2,3})?(?P<uom>MPS|KT)')  # noqa: E501

        self._detail_date = re.compile(r'[\d/]{4,13}Z')

        self._Logger = logging.getLogger(__name__)
        return super(Decoder, self).__init__()

    def __call__(self, tac):

        self.vaa = {'bbb': '',
                    'translationTime': time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'volcanoName': '',
                    'volcanoLocation': '',
                    'summit': '',
                    'advisoryNumber': '',
                    'sources': '',
                    'details': '',
                    'clouds': {},
                    'remarks': ''}
        try:
            result = self.header.search(tac)
            vaa = tac[result.end():].replace('=', '')

        except AttributeError:

            self.vaa['err_msg'] = 'VA ADVISORY line not found'
            self._Logger.info('%s\n%s' % (tac, self.vaa['err_msg']))
            return self.vaa

        try:
            del self._cloud
        except AttributeError:
            pass

        try:
            self._expected = []
            return super(Decoder, self).__call__(vaa)

        except tpg.SyntacticError:

            if not self._is_a_test():
                if len(self._expected):
                    err_msg = 'Expecting %s ' % ' or '.join([self._tokenInEnglish.get(x, x) for x in self._expected])
                else:
                    err_msg = 'Unidentified group '

                tacLines = vaa.split('\n')
                debugString = '\n%%s\n%%%dc\n%%s' % self.lexer.cur_token.end_column
                errorInTAC = debugString % ('\n'.join(tacLines[:self.lexer.cur_token.end_line]), '^',
                                            '\n'.join(tacLines[self.lexer.cur_token.end_line:]))
                self._Logger.info('%s\n%s' % (errorInTAC, err_msg))

                err_msg += 'at line %d column %d.' % (self.lexer.cur_token.end_line, self.lexer.cur_token.end_column)
                self.vaa['err_msg'] = err_msg

        except MissingAirSpaceWinds as msg:

            if not self._is_a_test():
                tacLines = vaa.split('\n')
                debugString = '\n%%s\n%%%dc\n%%s' % msg.column
                errorInTAC = debugString % ('\n'.join(tacLines[:msg.line]), '^',
                                            '\n'.join(tacLines[msg.line:]))
                self._Logger.info('%s\n%s' % (errorInTAC, msg.msg))
                self.vaa['err_msg'] = msg.msg

        except Exception:  # pragma: no cover
            self._Logger.exception(vaa)

        return self.finish()

    def _is_a_test(self):
        try:
            return self.vaa['status'] == 'TEST'
        except KeyError:
            return False

    def eatCSL(self, name):
        'Overrides super definition'
        try:
            value = super(Decoder, self).eatCSL(name)
            self._expected = []
            return value

        except tpg.WrongToken:
            self._expected.append(name)
            raise

    def preamble(self, s):

        if self.lexer.cur_token.name == 'opreamble':

            self.vaa['estimated'] = s[:3] == 'EST'
            self._fhr = '0'
        else:
            try:
                self.postPolygon(self._cloud)
                self.vaa['clouds'][self._fhr]['cldLyrs'].append(self._cloud.copy())
                del self._cloud

            except AttributeError:
                pass

            result = self.lexer.tokens[self.lexer.cur_token.name][0].match(s)
            self._fhr = result.group('fhr')
            self.vaa['clouds'][self._fhr] = dict(dtg='', cldLyrs=[])
            #
            # In case there's no dtg group following
            secs = time.mktime(time.strptime(self.vaa['clouds']['0']['dtg'], '%Y-%m-%dT%H:%M:00Z'))
            secs += (3600 * int(self._fhr))
            self.vaa['clouds'][self._fhr]['dtg'] = time.strftime('%Y-%m-%dT%H:%M:00Z', time.gmtime(secs))

    def dtg(self, s):

        tokenName = self.lexer.cur_token.name
        result = self.lexer.tokens[self.lexer.cur_token.name][0].match(s)

        if tokenName == 'dtg':

            ymd = result.group('date')
            hhmm = result.group('time')

            tms = list(time.gmtime())
            tms[0] = int(ymd[0:4])
            tms[1] = int(ymd[4:6])
            tms[2] = int(ymd[6:8])
            tms[3] = int(hhmm[0:2])
            tms[4] = int(hhmm[2:4])
            tms[5] = 0
            self.vaa['issueTime'] = {'str': time.strftime('%Y-%m-%dT%H:%M:00Z', tuple(tms)),
                                     'tms': tms}

        elif tokenName == 'obsdtg':

            tms = self.vaa['issueTime']['tms'][:]
            tms[2] = int(result.group('day'))
            if tms[2] > self.vaa['issueTime']['tms'][2]:
                tms[1] -= 1
                if tms[1] == 0:
                    tms[1] = 12
                    tms[0] -= 1

            hhmm = result.group('time')
            tms[3] = int(hhmm[0:2])
            tms[4] = int(hhmm[2:4])
            self.vaa['clouds']['0'] = dict(dtg='', cldLyrs=[])
            self.vaa['clouds']['0']['dtg'] = time.strftime('%Y-%m-%dT%H:%M:00Z', tuple(tms))
            self.vaa['estimated'] = s[:3] == 'EST'

        elif tokenName == 'dayhour':

            tms = self.vaa['issueTime']['tms'][:]
            tms[2] = int(s[0:2])
            if tms[2] < self.vaa['issueTime']['tms'][2]:
                tms[1] += 1
                if tms[1] > 12:
                    tms[1] = 1
                    tms[0] += 1

            tms[3] = int(s[3:5])
            tms[4] = int(s[5:7])
            self.vaa['clouds'][self._fhr]['dtg'] = time.strftime('%Y-%m-%dT%H:%M:00Z', tuple(tms))

        elif tokenName == 'nextdtg':
            try:
                tms = self.vaa['issueTime']['tms'][:]
                ymd = result.group('date')
                hhmm = result.group('time')

                tms[0] = int(ymd[0:4])
                tms[1] = int(ymd[4:6])
                tms[2] = int(ymd[6:8])
                tms[3] = int(hhmm[0:2])
                tms[4] = int(hhmm[2:4])

                self.vaa['nextdtg'] = {'str': time.strftime('%Y-%m-%dT%H:%M:00Z', tuple(tms)), 'cnd': None}
                if result.group(5):
                    self.vaa['nextdtg']['cnd'] = 'nlt'
                elif result.group(6):
                    self.vaa['nextdtg']['cnd'] = 'nst'

            except TypeError:
                pass

    def centre(self, s):

        self.vaa['centre'] = s[5:].strip()

    def vname(self, s):

        self.vaa['volcanoName'] = s[8:].strip()

    def vloc(self, s):
        try:
            strng = s[4:].strip()
            slat, slon = strng.split()
            try:
                deg, minu = int(slat[1:3]), int(slat[3:5])
            except ValueError:
                deg, minu = int(slat[1:3]), 0

            lat = deg + minu * 0.01667
            if slat[0] == 'S':
                lat *= -1.

            try:
                deg, minu = int(slon[1:4]), int(slon[4:6])
            except ValueError:
                deg, minu = int(slon[1:4]), 0

            lon = deg + minu * 0.01667
            if slon[0] == 'W':
                lon *= -1.

            self.vaa['volcanoLocation'] = '%.3f %.3f' % (lat, lon)

        except ValueError:
            self.vaa['volcanoLocation'] = 'UNKNOWN'

    def region(self, s):

        self.vaa['region'] = s[5:].strip()

    def status(self, s):

        self.vaa['status'] = s.split(':', 1)[1].strip()

    def summit(self, s):

        result = self.lexer.tokens[self.lexer.cur_token.name][0].match(s)
        self.vaa['summit'] = result.groupdict(s.split(':', 1)[1].strip())
        self.vaa['summit']['uom'] = {'FT': '[ft_i]'}.get(self.vaa['summit']['uom'], 'm')

    def advnum(self, s):

        result = self.lexer.tokens[self.lexer.cur_token.name][0].match(s)
        self.vaa['advisoryNumber'] = result.group(1)

    def source(self, s, condition):

        self.vaa['sources'] = ' '.join(s[12:].split())

    def colour(self, s):

        result = self.lexer.tokens[self.lexer.cur_token.name][0].match(s)
        self.vaa['colourCode'] = result.group(1)

    def details(self, s):

        details = ' '.join(s[18:].split())
        self.vaa['details'] = details
        #
        # Search for date and/or time of eruption.
        result = self._detail_date.search(details)
        if result is None:
            return
        #
        # Eruption time found.
        tms = self.vaa['issueTime']['tms'][:]
        eruptDate = result.group(0)
        try:
            ymd, hhmm = eruptDate.split('/')
        except ValueError:
            ymd = ''
            hhmm = eruptDate

        if len(ymd) >= 2:
            tms[2] = int(ymd[-2:])
        if len(ymd) >= 4:
            tms[1] = int(ymd[-4:-2])
        if len(ymd) > 5:
            tms[0] = int(ymd[0:4])

        tms[3] = int(hhmm[0:2])
        tms[4] = int(hhmm[2:4])
        #
        # Provide date/time string
        self.vaa['eruptionDate'] = time.strftime('%Y-%m-%dT%H:%M:00Z', tuple(tms))

    def top(self, s):

        try:
            self.postPolygon(self._cloud)
            self.vaa['clouds'][self._fhr]['cldLyrs'].append(self._cloud.copy())
            del self._cloud

        except AttributeError:
            pass

        result = self.lexer.tokens[self.lexer.cur_token.name][0].match(s)
        self._cloud = dict(top=result.group(1), bottom=None, pnts=[])

    def midlyr(self, s):

        try:
            self.postPolygon(self._cloud)
            self.vaa['clouds'][self._fhr]['cldLyrs'].append(self._cloud.copy())
            del self._cloud

        except AttributeError:
            pass

        bottom = int(s[2:5])
        top = int(s[6:9])

        if top < bottom:
            top, bottom = bottom, top

        self._cloud = dict(bottom=str(bottom), top=str(top), pnts=[])

    def sfc(self, s):

        try:
            self.postPolygon(self._cloud)
            self.vaa['clouds'][self._fhr]['cldLyrs'].append(self._cloud.copy())
            del self._cloud

        except AttributeError:
            pass

        self._cloud = dict(top=s[6:9], bottom='SFC', pnts=[])

    def box(self, s):

        result = self.lexer.tokens[self.lexer.cur_token.name][0].match(s)
        self._cloud['box'] = dict(width=result.group(1), uom=result.group(2))

    def latlon(self, s):

        result = self.lexer.tokens[self.lexer.cur_token.name][0].match(s)
        rlat = result.group('lat')
        try:
            deg, minu = int(rlat[1:3]), int(rlat[3:5])
        except ValueError:
            deg, minu = int(rlat[1:3]), 0

        latitude = deg + minu * 0.01667
        if rlat[0] == 'S':
            latitude *= -1.0

        rlon = result.group('lon')
        try:
            deg, minu = int(rlon[1:4]), int(rlon[4:6])
        except ValueError:
            deg, minu = int(rlon[1:4]), 0

        longitude = deg + minu * 0.01667
        if rlon[0] == 'W':
            longitude *= -1.0

        self._cloud['pnts'].append('%.3f %.3f' % (latitude, longitude))

    def movement(self, s):

        result = self.lexer.tokens[self.lexer.cur_token.name][0].match(s)
        try:
            self._cloud['movement'] = {'dir': deu.CardinalPtsToDegreesS[result.group(1)],
                                       'spd': result.group(2),
                                       'uom': {'KT': '[kn_i]', 'KMH': 'km/h'}.get(result.group('uom'))}
        except KeyError:
            raise tpg.WrongToken

    def vanotid(self, s):

        spos = 0
        result = self._reWinds.search(s)

        if result is None:
            token_object = self.lexer.token()
            raise MissingAirSpaceWinds((token_object.line, token_object.column), 'For VA NOT IDENTIFIABLE conditions, '
                                       'wind information shall be provided')

        self._cloud = dict(nil=self.lexer.cur_token.name)
        while result:
            try:
                self._cloud['movement'] = result.groupdict()
                if self._cloud['movement']['bottom'] is None:
                    self._cloud['movement']['bottom'] = result.group(2)
                self._cloud['movement']['uom'] = {'KT': '[kn_i]', 'MPS': 'm/s'}.get(self._cloud['movement']['uom'])

            except AttributeError:
                self._cloud['movement'] = None

            self.vaa['clouds'][self._fhr]['cldLyrs'].append(self._cloud.copy())
            spos += result.end()
            result = self._reWinds.search(s[spos:])

        if len(self.vaa['clouds'][self._fhr]['cldLyrs']) == 0:
            self.vaa['clouds'][self._fhr]['cldLyrs'].append(self._cloud.copy())

        del self._cloud

    def noash(self):

        try:
            if len(self.vaa['clouds'][self._fhr]['cldLyrs']) == 0:
                self.vaa['clouds'][self._fhr]['cldLyrs'].append(dict(nil=self.lexer.cur_token.name))
        except KeyError:
            self.vaa['clouds'][self._fhr] = {'cldLyrs': [dict(nil=self.lexer.cur_token.name)]}

        try:
            del self._cloud
        except AttributeError:
            pass

    def rmk(self, s):

        self.vaa['remarks'] = ' '.join(s[4:].split())
    #
    # Called after new forecast projection, and ash cloud polygon(s)

    def postPolygon(self, cloudInfo):

        if cloudInfo is None:
            return

        if 'box' not in cloudInfo:
            try:
                if cloudInfo['pnts'][0] != cloudInfo['pnts'][-1]:
                    cloudInfo['pnts'].append(cloudInfo['pnts'][0])
            except (KeyError, IndexError):
                pass
        else:
            #
            # Convert box centerline(s) and width(s) to a polygon
            #
            distance = float(cloudInfo['box']['width']) * 0.5
            radius = 6378.
            if cloudInfo['box']['uom'] == 'NM':
                radius = 3440.

            newpolygon = []
            lat2, lon2, v = 0.0, 0.0, 0.0

            for a, b in zip(cloudInfo['pnts'], cloudInfo['pnts'][1:]):
                lat1, lon1 = [float(x) for x in a.split(' ')]
                lat2, lon2 = [float(x) for x in b.split(' ')]
                #
                # Find perpendicular to vector
                v = complex((lon2 - lon1), (lat2 - lat1)) * complex(0.0, 1.0)
                newpolygon.append(deu.computeLatLon(lat1, lon1, math.degrees(cmath.phase(v)), distance, radius))

            newpolygon.append(deu.computeLatLon(lat2, lon2, math.degrees(cmath.phase(v)), distance, radius))
            #
            # Looping back around the central axis
            cloudInfo['pnts'].reverse()
            for a, b in zip(cloudInfo['pnts'], cloudInfo['pnts'][1:]):

                lat1, lon1 = [float(x) for x in a.split(' ')]
                lat2, lon2 = [float(x) for x in b.split(' ')]
                #
                # Find perpendicular to vector
                v = complex((lon2 - lon1), (lat2 - lat1)) * complex(0.0, 1.0)
                newpolygon.append(deu.computeLatLon(lat1, lon1, math.degrees(cmath.phase(v)), distance, radius))

            newpolygon.append(deu.computeLatLon(lat2, lon2, math.degrees(cmath.phase(v)), distance, radius))
            #
            # first == last to close the polygon
            newpolygon.append(newpolygon[0])
            cloudInfo['pnts'] = newpolygon
        #
        # Check to make sure polygon is traversed in CCW fashion
        #
        try:
            fpolygon = []
            for pnt in cloudInfo['pnts']:
                x, y = pnt.split()
                fpolygon.append((float(x), float(y)))

            try:
                if not deu.isCCW(fpolygon):
                    cloudInfo['pnts'].reverse()
                #
                # Convert any longitudes greater than 180 degrees to negative values (signifying west longitudes)
                new_pnts = []
                for pnt in cloudInfo['pnts']:
                    lat, lon = [float(z) for z in pnt.split(' ')]
                    if lon > 180:
                        lon -= 360
                    new_pnts.append(('%.3f %.3f' % (lat, lon)))

                cloudInfo['pnts'] = new_pnts

            except ValueError as msg:
                self._Logger.info(msg)

        except KeyError:
            pass

    def finish(self):

        try:
            self.postPolygon(self._cloud)
            self.vaa['clouds'][self._fhr]['cldLyrs'].append(self._cloud)
            del self._cloud

        except AttributeError:
            pass

        return self.vaa
