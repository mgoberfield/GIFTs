#
# Name: tcaDecoder.py
#
# Purpose: To decode, in its entirety, the Tropical Cyclone Advisory traditional alphanumeric code
#          as described in the Meteorological Service for International Air Navigation, Annex 3
#          to the Convention on International Civil Aviation.
#
# Author: Mark Oberfield
# Organization: NOAA/NWS/OSTI/MDL/WIAB
#
import logging
import time
import re

from .common import tpg
from .common import xmlUtilities as deu


class Decoder(tpg.Parser):
    r"""
    set lexer = ContextSensitiveLexer
    set lexer_dotall = True

    separator spaces:    '\s+' ;

    token test: 'STATUS:\s*TEST' ;
    token exercise: 'STATUS:\s*EXER\w{0,4}' ;
    token dtg: 'DTG:\s*(?P<date>\d{8})/(?P<time>\d{4})Z' ;
    token centre: 'TCAC:\s*([^\n]+)' ;
    token cname: 'TC:\s*([^\n]+)' ;
    token advnum: 'ADVISORY\s+NR:\s*\d{4}/\d{1,4}' ;
    token cloc: 'OBS\s+PSN:\s*(?P<day>\d{1,2})/(?P<hhmm>\d{4})Z\s+(?P<pos>[NS]\d{2,4}\s+[EW]\d{3,5})' ;
    token cbnil: 'CB:\s*NIL' ;
    token cbcircle: '(\d{2,3})(KM|NM)\s+OF\s+TC\s+CENT(RE|ER)' ;
    token tops: 'TOPS?\s+(?P<cnd>ABV|BLW)?\s*FL(?P<lvl>\d{3})' ;
    token latlon: '(?P<lat>[NS]\d{2,4})\s+(?P<lon>[EW]\d{3,5})' ;
    token cmov1: 'MOV:\s*(?P<dir>[NEWS]{1,3})\s+(?P<spd>\d{1,2})(?P<uom>K(MH|T))' ;
    token cmov2: 'MOV:\s*STNRY?' ;
    token ichng: 'INTST CHANGE:\s*([^\n]+)' ;
    token cpres: 'C:\s*(\d{3,4})HPA' ;
    token cmaxwnd: 'MAX WIND:\s*(?P<spd>\d{2,3})(?P<uom>MPS|KT)' ;
    token cfpsn: 'FCST PSN\s\+(?P<fhr>\d{1,2})\sHR:\s*(?P<day>\d{1,2})/(?P<hhmm>\d{4})Z\s+(?P<pos>[NS][/\d]{2,4}\s+[EW][/\d]{3,5})' ;  # noqa: E501
    token cfwnd: 'FCST MAX WIND\s+\+\s?\d{1,2}\sHR:\s*(?P<spd>[/\d]{2,3})(?P<uom>MPS|KT)' ;
    token rmk: 'RMK:\s*(.+)(?=NXT MSG)' ;
    token nextdtg: 'NXT MSG:\s+((BFR\s)?(?P<date>\d{8})/(?P<time>\d{4})Z)' ;

    START/d -> TCA $ d=self.finish() $ ;

    TCA -> 'TC ADVISORY' (Test|Exercise)? Body ;
    Body -> DTG Centre CName AdvNum CLoc (CBNIL|CB2|CB3)* (CMov1|CMov2) IChng CPres CMaxWnd (CFPsn CFWnd){4,} Rmk NextDTG? '.*' ;

    CB2 -> 'CB:\s*WI\s+' CBCircle CBTop ;
    CB3 -> 'CB:\s*WI\s+' (LatLon|'-'){5,} CBTop ;

    Exercise -> exercise/x $ self.status(x) $ ;
    Test -> test/x $ self.status(x) $ ;
    Status -> status/x $ self.status(x) $ ;
    DTG -> dtg/x $ self.dtg(x) $ ;
    Centre -> centre/x $ self.centre(x) $ ;
    CName -> cname/x $ self.cname(x) $ ;
    AdvNum -> advnum/x $ self.advnum(x) $ ;
    CLoc -> cloc/x $ self.cfpsn(x) $ ;
    CBNIL -> cbnil/x $ self.cbnil() $ ;
    CBCircle -> cbcircle/x $ self.cbcircle(x) $ ;
    LatLon -> latlon/x $ self.latlon(x) $ ;
    CBTop -> tops/x $ self.tops(x) $ ;
    CMov1 -> cmov1/x $ self.cmov(x) $ ;
    CMov2 -> cmov2/x $ self.cmov(x) $ ;
    IChng -> ichng/x $ self.ichng(x) $ ;
    CPres -> cpres/x $ self.cpres(x) $ ;
    CMaxWnd -> cmaxwnd/x $ self.cmaxwnd(x) $ ;
    CFPsn -> cfpsn/x $ self.cfpsn(x) $ ;
    CFWnd -> cfwnd/x $ self.cfwnd(x) $ ;
    Rmk -> rmk/x $ self.rmk(x) $ ;
    NextDTG -> nextdtg/x $ self.dtg(x) $ ;
    """

    def __init__(self):

        self._tokenInEnglish = {'_tok_1': 'TC ADVISORY line', 'dtg': 'Date/Time Group', 'centre': 'Issuing RSMC',
                                'cname': 'Name of Cyclone', 'vloc': 'Location of Cyclone', 'advnum': 'Advisory Number',
                                'cloc': 'Cyclone Position', 'cmov': 'Cyclone Movement', 'ichng': 'Intensity Change',
                                'cpres': 'Central Pressure', 'cmaxwnd': 'Cyclone Maximum Wind Speed',
                                'cfpsn': 'Forecast Position', 'cfwnd': 'Forecast Maximum Wind Speed', 'rmk': 'Remarks',
                                'nextdtg': 'Next advisory issuance time or NO MSG EXP'}

        self.header = re.compile(r'.*(?=TC ADVISORY)', re.DOTALL)

        self._Logger = logging.getLogger(__name__)
        return super(Decoder, self).__init__()

    def __call__(self, tac):

        self.tca = {'bbb': '',
                    'translationTime': time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'cycloneName': '',
                    'advisoryNumber': '',
                    'minimumPressure': {'value': '', 'uom': 'hPa'},
                    'cbclouds': [],
                    'fcst': {},
                    'remarks': ''}

        self._fcst = self.tca['fcst']

        try:
            result = self.header.search(tac)
            tca = tac[result.end():].replace('=', '')

        except AttributeError:
            self.tca['err_msg'] = 'TC ADVISORY line not found'
            return self.tca

        try:
            self._expected = []
            return super(Decoder, self).__call__(tca)

        except tpg.SyntacticError:
            if not self._is_a_test():
                if len(self._expected):
                    err_msg = 'Expecting %s group(s) ' % ' or '.join(
                        [self._tokenInEnglish.get(x, x) for x in self._expected])
                else:
                    err_msg = 'Unidentified group '

                tacLines = tca.split('\n')
                debugString = '\n%%s\n%%%dc\n%%s' % self.lexer.cur_token.end_column
                errorInTAC = debugString % ('\n'.join(tacLines[:self.lexer.cur_token.end_line]), '^',
                                            '\n'.join(tacLines[self.lexer.cur_token.end_line:]))
                self._Logger.info('%s\n%s' % (errorInTAC, err_msg))

                err_msg += 'at line %d column %d.' % (self.lexer.cur_token.end_line, self.lexer.cur_token.end_column)
                self.tca['err_msg'] = err_msg

        except Exception:
            self._Logger.exception(tca)

        return self.finish()

    def _is_a_test(self):
        return 'status' in self.tca and self.tca['status'] == 'TEST'

    def eatCSL(self, name):
        'Overrides super definition'
        try:
            value = super(Decoder, self).eatCSL(name)
            self._expected = []
            return value

        except tpg.WrongToken:
            self._expected.append(name)
            raise

    def status(self, s):

        self.tca['status'] = s.split(':', 1)[1].strip()

    def dtg(self, s):

        result = self.lexer.tokens[self.lexer.cur_token.name][0].match(s)
        ymd = result.group('date')
        hhmm = result.group('time')
        tms = [0, 0, 0, 0, 0, 0, 0, 0, 0]
        tms[0] = int(ymd[0:4])
        tms[1] = int(ymd[4:6])
        tms[2] = int(ymd[6:8])
        tms[3] = int(hhmm[0:2])
        tms[4] = int(hhmm[2:4])

        if self.lexer.cur_token.name == 'dtg':
            self.issueTime = tms[:]
            self.tca['issueTime'] = {'str': time.strftime('%Y-%m-%dT%H:%M:00Z', tuple(tms)),
                                     'tms': tms}
        else:
            self.tca['nextdtg'] = {'str': time.strftime('%Y-%m-%dT%H:%M:00Z', tuple(tms)),
                                   'before': 'BFR' in s}

    def centre(self, s):

        self.tca['centre'] = s.split(':', 1)[1].strip()

    def cname(self, s):

        self.tca['cycloneName'] = s.split(':', 1)[1].strip()

    def advnum(self, s):

        self.tca['advisoryNumber'] = s.split(':', 1)[1].strip()

    def cbnil(self):

        pass

    def cbcircle(self, s):

        result = self.lexer.tokens[self.lexer.cur_token.name][0].match(s)
        self._cloud = {'type': 'circle', 'radius': result.group(1),
                       'uom': {'KM': 'km', 'NM': '[nm_i]'}.get(result.group(2))}

    def tops(self, s):

        result = self.lexer.tokens[self.lexer.cur_token.name][0].match(s)
        self._cloud['top'] = result.groupdict()
        self.tca['cbclouds'].append(self._cloud.copy())
        del self._cloud

    def cmov(self, s):

        if 'STNR' not in s:
            result = self.lexer.tokens[self.lexer.cur_token.name][0].match(s)
            self._fcst['movement'] = {'dir': deu.CardinalPtsToDegreesS[result.group('dir')],
                                      'spd': str(int(result.group('spd'))),
                                      'uom': {'KMH': 'km/h', 'KT': '[kn_i]'}.get(result.group('uom'))}

    def ichng(self, s):

        self.tca['intstChange'] = s.split(':', 1)[1].strip()

    def cpres(self, s):

        result = self.lexer.tokens[self.lexer.cur_token.name][0].match(s)
        self.tca['minimumPressure']['value'] = str(int(result.group(1)))

    def cmaxwnd(self, s):

        result = self.lexer.tokens[self.lexer.cur_token.name][0].match(s)
        self._fcst['windSpeed'] = {'value': str(int(result.group('spd'))),
                                   'uom': {'MPS': 'm/s', 'KT': '[kn_i]'}.get(result.group('uom'))}

    def cfpsn(self, s):

        result = self.lexer.tokens[self.lexer.cur_token.name][0].match(s)
        try:
            fhr = result.group('fhr')
        except IndexError:
            fhr = '0'

        self._fcst = self.tca['fcst'][fhr] = dict(dtg='', position='')

        tms = self.issueTime[:]
        tms[2], hhmm = int(result.group('day')), result.group('hhmm')
        tms[3], tms[4] = int(hhmm[:2]), int(hhmm[2:])
        #
        # If new month indicated
        if tms[2] < self.issueTime[2]:
            tms[1] += 1
            if tms[1] > 12:
                tms[0] += 1
                tms[1] = 1

        self._fcst['dtg'] = time.strftime('%Y-%m-%dT%H:%M:00Z', tuple(tms))

        try:
            slat, slon = result.group('pos').split()
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

            self._fcst['position'] = '%.3f %.3f' % (lat, lon)

        except ValueError:
            del self._fcst['position']

    def cfwnd(self, s):

        result = self.lexer.tokens[self.lexer.cur_token.name][0].match(s)
        try:
            self._fcst['windSpeed'] = {'value': str(int(result.group('spd'))),
                                       'uom': {'MPS': 'm/s', 'KT': '[kn_i]'}.get(result.group('uom'))}
        except ValueError:
            pass

    def latlon(self, s):

        result = self.lexer.tokens[self.lexer.cur_token.name][0].match(s)
        rlat = result.group('lat')
        try:
            deg, minu = int(rlat[1:3]), int(rlat[3:5])
        except ValueError:
            deg, minu = int(rlat[1:]), 0

        latitude = deg + minu * 0.01667
        if rlat[0] == 'S':
            latitude *= -1.0

        rlon = result.group('lon')
        try:
            deg, minu = int(rlon[1:4]), int(rlon[4:6])
        except ValueError:
            deg, minu = int(rlon[1:]), 0

        longitude = deg + minu * 0.01667
        if rlon[0] == 'W':
            longitude *= -1.0

        try:
            self._cloud['pnts'].append('%.3f %.3f' % (latitude, longitude))
        except AttributeError:
            self._cloud = {'type': 'polygon', 'pnts': ['%.3f %.3f' % (latitude, longitude)]}

    def rmk(self, s):

        self.tca['remarks'] = ' '.join(s[4:].split())

    def finish(self):

        for d in self.tca['cbclouds']:
            if d['type'] == 'polygon':
                if d['pnts'][-1] != d['pnts'][0]:
                    d['pnts'].append(d['pnts'][0])
                #
                # Check to make sure polygon is traversed in CCW fashion
                #
                fpolygon = []
                for pnt in d['pnts']:
                    x, y = pnt.split()
                    fpolygon.append((float(x), float(y)))
                try:
                    if not deu.isCCW(fpolygon):
                        d['pnts'].reverse()

                except ValueError as msg:
                    self._Logger.info(msg)

        return self.tca
