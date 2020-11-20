#
# Name: metarDecoder.py
#
# Purpose: Annex 3: To decode, in its entirety, the METAR/SPECI traditional alphanumeric code
#          as described in the Meteorological Service for International Air Navigation,
#          Annex 3 to the Convention on International Civil Aviation.
#
# Author: Mark Oberfield
# Organization: NOAA/NWS/OSTI/MDL/WIAB
# Contact Info: Mark.Oberfield@noaa.gov
#
import calendar
import logging
import re
import time

from .common import tpg
from .common import xmlUtilities as deu


class Annex3(tpg.Parser):
    r"""
    set lexer = ContextSensitiveLexer
    set lexer_dotall = True

    separator spaces:    '\s+' ;

    token type:  'METAR|SPECI' ;
    token ident: '[A-Z]{4}' ;
    token itime: '\d{6}Z' ;
    token auto:  'AUTO' ;
    token wind: '(VRB|(\d{3}|///))P?(\d{2,3}|//)(GP?\d{2,3})?(MPS|KT)' ;
    token wind_vrb: '\d{3}V\d{3}' ;
    token vsby1: '((?P<whole>\d{1,3}(?!/))?(?P<fraction>(M|\s+)?\d/\d{1,2})?|/{2,4})SM' ;
    token vsby2: '(?P<vsby>\d{4}|////)\s?(NDV)?' ;
    token minvsby: '\d{4}[NEWS]{0,2}'  ;
    token rvr: 'R(?P<rwy>[/\d]{2}[RCL]?)/(?P<oper>[MP])?(?P<mean>[/\d]{4}(FT)?)/?(?P<tend>[UDN]?)' ;
    token nsw: 'NSW' ;
    token pcp: '//|[+-]?((TS|SH)(GR|GS|RA|SN|UP){1,3}|FZ(DZ|RA|UP){1,2}|(DZ|RA|SN|SG|PL){1,3}|DS|SS|FC|UP)' ;
    token tpcp: '[+]?((TS|SH)(GR|GS|RA|SN){1,3}|FZ(DZ|RA){1,2}|(DZ|RA|SN|SG|PL){1,3}|DS|SS|FC)' ;
    token obv: '(BC|FZ|MI|PR)?FG|BR|(BL|DR)?(SA|DU)|(BL|DR)SN|HZ|FU|VA|SQ|PO|TS' ;
    token vcnty: 'VC(FG|PO|FC|DS|SS|TS|SH|VA|BL(SN|SA|DU))' ;
    token noclouds: 'NSC|NCD' ;
    token vvsby: 'VV(\d{3}|///)' ;
    token sky: '(FEW|SCT|BKN|OVC|///)(\d{3}|///)(CB|TCU|///)?' ;
    token temps: '(?P<air>(M|-)?\d{2}|MM|//)/(?P<dewpoint>(M|-)?\d{2}|MM|//)' ;
    token altimeter: '(Q|A)(\d{3,4}|////)' ;

    token rewx: 'RE(FZ|SH|TS)?(DZ|RASN|RA|(BL)?SN|SG|GR|GS|SS|DS|FC|VA|PL|UP|//)|RETS' ;
    token windshear: 'WS\s+(R(WY)?(?P<rwy>\d{2}[RLC]?)|ALL\s+RWYS?)' ;
    token seastate: 'W(?P<temp>(M|-)?\d\d|//)/(S|H)(?P<value>[/\d]{1,3})' ;
    token rwystate: 'R(\d{0,2}[LCR]?)/([\d/]{6}|SNOCLO|CLRD[/\d]{0,2})' ;
    token trendtype: 'BECMG|TEMPO' ;
    token ftime: '(AT|FM)\d{4}' ;
    token ttime: 'TL\d{4}' ;
    token twind: '\d{3}P?\d{2,3}(GP?\d{2,3})?(MPS|KT)' ;

    START/e -> METAR/e $ e=self.finish() $ ;

    METAR -> Type Cor? Ident ITime (NIL|Report) ;
    Report -> Auto? Main Supplement? TrendFcst? ;
    Main -> Wind VrbDir? (CAVOK|((Vsby1|(Vsby2 MinVsby?)) Rvr{0,4} (Pcp|Obv|Vcnty){0,3} (NoClouds|VVsby|Sky{1,4}))) Temps Altimeter{1,2} ; # noqa: E501
    Supplement -> RecentPcp{0,3} WindShear? SeaState? RunwayState*;
    TrendFcst -> NOSIG|(TrendType (FTime|TTime){0,2} TWind? CAVOK? (Vsby1|Vsby2)? Nsw? (TPcp|Obv){0,3} (NoClouds|VVsby|Sky{0,4}))+ ;

    Type -> type/x $ self.obtype(x) $ ;
    Ident -> ident/x $ self.ident(x) $ ;
    ITime -> itime/x $ self.itime(x) $ ;

    NIL -> 'NIL' $ self.nil() $ ;

    Auto -> auto $ self.auto() $ ;
    Cor ->  'COR' $ self.correction() $ ;
    Wind -> wind/x $ self.wind(x) $ ;
    TWind -> twind/x $ self.wind(x) $ ;
    VrbDir -> wind_vrb/x $ self.wind(x) $ ;
    CAVOK -> 'CAVOK' $ self.cavok() $ ;

    Vsby1 -> vsby1/x $ self.vsby(x,'[mi_i]') $ ;
    Vsby2 -> vsby2/x $ self.vsby(x,'m') $ ;
    MinVsby -> minvsby/x $ self.vsby(x,'m') $ ;
    Rvr -> rvr/x $ self.rvr(x) $ ;
    Pcp -> pcp/x $ self.pcp(x) $ ;
    TPcp -> tpcp/x $ self.pcp(x) $ ;
    Nsw -> nsw/x $ self.pcp(x) $ ;
    Obv -> obv/x $ self.obv(x) $ ;
    Vcnty -> vcnty/x $ self.vcnty(x) $ ;
    NoClouds -> noclouds/x $ self.sky(x) $ ;
    VVsby -> vvsby/x $ self.sky(x) $ ;
    Sky -> sky/x $ self.sky(x) $ ;
    Temps -> temps/x $ self.temps(x) $ ;
    Altimeter -> altimeter/x $ self.altimeter(x) $ ;

    RecentPcp -> rewx/x $ self.rewx(x) $ ;

    WindShear -> windshear/x $ self.windshear(x) $ ;
    SeaState -> seastate/x $ self.seastate(x) $ ;
    RunwayState -> rwystate/x $ self.rwystate(x) $ ;
    NOSIG -> 'NOSIG' $ self.nosig() $ ;

    TrendType -> trendtype/x $ self.trendtype(x) $ ;
    FTime -> ftime/x $ self.timeBoundary(x) $ ;
    TTime -> ttime/x $ self.timeBoundary(x) $ ;
    """

    def __init__(self):

        self._tokenInEnglish = {'_tok_1': 'NIL', '_tok_2': 'COR', '_tok_3': 'CAVOK', '_tok_4': 'NOSIG',
                                'type': 'Keyword METAR or SPECI', 'ident': 'ICAO Identifier',
                                'itime': 'issuance time ddHHmmZ', 'auto': 'AUTO', 'wind': 'wind',
                                'wind_vrb': 'variable wind direction', 'vsby1': 'visibility in statute miles',
                                'vsby2': 'visibility in metres', 'minvsby': 'directional minimum visibility',
                                'rvr': 'runway visual range', 'pcp': 'precipitation',
                                'nsw': 'NSW', 'obv': 'obstruction to vision', 'vcnty': 'precipitation in the vicinity',
                                'noclouds': 'NCD, NSC', 'vvsby': 'vertical visibility', 'sky': 'cloud layer',
                                'temps': 'air and dew-point temperature', 'altimeter': 'altimeter',
                                'rewx': 'recent weather', 'windshear': 'windshear', 'seastate': 'state of the sea',
                                'rwystate': 'state of the runway', 'trendtype': 'trend qualifier',
                                'ftime': 'start of trend time period', 'ttime': 'end of trend time period',
                                'twind': 'wind (VRB not permitted)',
                                'tpcp': 'moderate to heavy precipitation'}

        self.header = re.compile(r'^(METAR|SPECI)(\s+COR)?\s+[A-Z]{4}.+?=', (re.MULTILINE | re.DOTALL))
        self.rmkKeyword = re.compile(r'[\s^]RMK[\s$]', re.MULTILINE)

        super(Annex3, self).__init__()
        self._Logger = logging.getLogger(__name__)

    def __call__(self, tac):

        self._metar = {'bbb': ' ',
                       'translationTime': time.strftime('%Y-%m-%dT%H:%M:%SZ')}
        try:
            result = self.header.search(tac)
            tac = result.group(0)[:-1]

        except AttributeError:
            self._metar['err_msg'] = 'Unable to find start and end positions of the METAR/SPECI.'
            return self._metar

        if self.__class__.__name__ == 'Annex3':
            #
            # Remove RMK token and everything beyond that. This decoder follows Annex 3
            # specifications and ignores content beyond the RMK keyword. Any unidentified
            # content in the report renders it invalid.
            #
            rmkResult = self.rmkKeyword.search(tac)
            if rmkResult:
                tac = tac[:rmkResult.start()]

        try:
            self._expected = []
            return super(Annex3, self).__call__(tac)

        except tpg.SyntacticError:
            try:
                if 'altimeter' in self._metar:
                    self._expected.remove('altimeter')
            except ValueError:
                pass

            if len(self._expected):
                err_msg = 'Expecting %s ' % ' or '.join([self._tokenInEnglish.get(x, x)
                                                         for x in self._expected])
            else:
                err_msg = 'Unidentified group '

            tacLines = tac.split('\n')
            debugString = '\n%%s\n%%%dc\n%%s' % self.lexer.cur_token.end_column
            errorInTAC = debugString % ('\n'.join(tacLines[:self.lexer.cur_token.end_line]), '^',
                                        '\n'.join(tacLines[self.lexer.cur_token.end_line:]))
            self._Logger.info('%s\n%s' % (errorInTAC, err_msg))

            err_msg += 'at line %d column %d.' % (self.lexer.cur_token.end_line, self.lexer.cur_token.end_column)
            self._metar['err_msg'] = err_msg
            return self.finish()

        except Exception:
            self._Logger.exception(tac)
            return self.finish()

    def finish(self):
        #
        # If NIL, no QC checking is required
        if 'nil' in self._metar:
            self._metar
        #
        try:
            self._metar['trendFcsts'].append(self._trend)
            del self._trend
        except (AttributeError, KeyError):
            pass
        #
        # Set boundaries so multiple trend forecasts don't overlap in time
        try:
            for previous, trend in enumerate(self._metar['trendFcsts'][1:]):
                if 'til' not in self._metar['trendFcsts'][previous]['ttime']:
                    self._metar['trendFcsts'][previous]['ttime']['til'] = trend['ttime']['from']
        except KeyError:
            pass

        return self._metar

    def index(self):

        ti = self.lexer.cur_token
        return ('%d.%d' % (ti.line, ti.column - 1),
                '%d.%d' % (ti.end_line, ti.end_column - 1))

    def tokenOK(self, pos=0):
        'Checks whether token ends with a blank'
        try:
            return self.lexer.input[self.lexer.token().stop + pos].isspace()
        except IndexError:
            return True

    def eatCSL(self, name):
        'Overrides super definition'
        try:
            value = super(Annex3, self).eatCSL(name)
            self._expected = []
            return value

        except tpg.WrongToken:
            self._expected.append(name)
            raise

    def updateDictionary(self, key, value, root):

        try:
            d = root[key]
            d['index'].append(self.index())
            d['str'].append(value)

        except KeyError:
            root[key] = {'str': [value], 'index': [self.index()]}

    #######################################################################
    # Methods called by the parser
    def obtype(self, s):

        self._metar['type'] = {'str': s, 'index': self.index()}

    def ident(self, s):

        self._metar['ident'] = {'str': s, 'index': self.index()}

    def itime(self, s):

        d = self._metar['itime'] = {'str': s, 'index': self.index()}
        mday, hour, minute = int(s[:2]), int(s[2:4]), int(s[4:6])

        tms = list(time.gmtime())
        tms[2:6] = mday, hour, minute, 0
        deu.fix_date(tms)
        d['intTime'] = calendar.timegm(tuple(tms))
        d['tuple'] = time.gmtime(d['intTime'])
        d['value'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', d['tuple'])

    def auto(self):

        self._metar['auto'] = {'index': self.index()}

    def correction(self):

        self._metar['cor'] = {'index': self.index()}

    def nil(self):

        self._metar['nil'] = {'index': self.index()}

    def wind(self, s):
        #
        # Wind groups can appear later in the trend section of the report
        try:
            root = getattr(self, '_trend')
        except AttributeError:
            root = getattr(self, '_metar')
        #
        # Handle variable wind direction which always comes after the wind group
        try:
            d = root['wind']
            d['index'] = (d['index'][0], self.index()[1])
            d['str'] = "%s %s" % (d['str'], s)
            ccw, cw = s.split('V')
            d.update({'ccw': ccw, 'cw': cw})
            return

        except KeyError:
            if self.lexer.cur_token.name == 'wind_vrb':
                raise tpg.WrongToken
            pass

        d = root['wind'] = {'str': s, 'index': self.index()}
        dd = s[:3]

        if s[-3:] == 'MPS':
            uom = 'm/s'
            spd = s[3:-3]
        elif s[-2:] == 'KT':
            uom = '[kn_i]'
            spd = s[3:-2]

        try:
            ff, gg = spd.split('G')
            if ff[0] == 'P':
                d['ffplus'] = True
                ff = ff[1:]

            if gg[0] == 'P':
                d['ggplus'] = True
                gg = gg[1:]

            d.update({'dd': dd, 'ff': ff, 'gg': gg, 'uom': uom})

        except ValueError:
            if spd[0] == 'P':
                d['ffplus'] = True
                ff = spd[1:]
            else:
                ff = spd

            d.update({'dd': dd, 'ff': ff, 'uom': uom})

    def cavok(self):

        try:
            root = getattr(self, '_trend')
        except AttributeError:
            root = getattr(self, '_metar')

        root['cavok'] = {'index': self.index()}

    def vsby(self, s, uom):

        vis = 0.0
        oper = None
        v = self.lexer.tokens[self.lexer.cur_token.name][0].match(s)
        if self.lexer.cur_token.name == 'vsby1':
            try:
                vis += float(v.group('whole'))
            except TypeError:
                pass

            try:
                numerator, denominator = v.group('fraction').split('/', 1)
                if numerator[0] == 'M':
                    vis += float(numerator[1:]) / float(denominator)
                    oper = 'M'
                else:
                    vis += float(numerator) / float(denominator)

            except (AttributeError, ZeroDivisionError):
                pass

            value = '%.4f' % vis

        elif self.lexer.cur_token.name == 'vsby2':
            value = v.group('vsby')

        try:
            root = getattr(self, '_trend')
        except AttributeError:
            root = getattr(self, '_metar')

        if 'vsby' in root:
            root['vsby'].update({'min': s[0:4], 'bearing': deu.CardinalPtsToDegreesS.get(s[4:], '/')})
            root['vsby']['index'].append(self.index())
        else:
            root['vsby'] = {'str': s, 'index': [self.index()], 'value': value, 'uom': uom, 'oper': oper}

    def rvr(self, s):

        result = self.lexer.tokens[self.lexer.cur_token.name][0].match(s)
        uom = 'm'
        oper = {'P': 'ABOVE', 'M': 'BELOW'}.get(result.group('oper'), None)
        tend = {'D': 'DOWNWARD', 'N': 'NO_CHANGE', 'U': 'UPWARD'}.get(result.group('tend'), 'MISSING_VALUE')
        mean = result.group('mean')

        if mean[-2:] == 'FT':
            mean = mean[:-2]
            uom = '[ft_i]'

        try:
            d = self._metar['rvr']
            d['str'].append(s)
            d['index'].append(self.index())
            d['rwy'].append(result.group('rwy'))
            d['mean'].append(mean)
            d['oper'].append(oper)
            d['tend'].append(tend)
            d['uom'].append(uom)

        except KeyError:
            self._metar['rvr'] = {'str': [s], 'index': [self.index()], 'rwy': [result.group('rwy')],
                                  'oper': [oper], 'mean': [mean], 'tend': [tend], 'uom': [uom]}

    def obv(self, s):

        if s == '//' and not self.tokenOK():
            raise tpg.WrongToken

        try:
            root = getattr(self, '_trend')
        except AttributeError:
            root = getattr(self, '_metar')

        self.updateDictionary('obv', s, root)

    def pcp(self, s):

        if s == '//' and not self.tokenOK():
            raise tpg.WrongToken

        try:
            root = getattr(self, '_trend')
        except AttributeError:
            root = getattr(self, '_metar')

        self.updateDictionary('pcp', s, root)

    def vcnty(self, s):

        self.updateDictionary('vcnty', s, self._metar)

    def sky(self, s):

        try:
            root = getattr(self, '_trend')
        except AttributeError:
            root = getattr(self, '_metar')

        self.updateDictionary('sky', s, root)

    def temps(self, s):

        d = self._metar['temps'] = {'str': s, 'index': self.index(), 'uom': 'Cel'}

        rePattern = self.lexer.tokens[self.lexer.cur_token.name][0]
        result = rePattern.match(s)

        d.update(result.groupdict())
        try:
            d['air'] = str(int(result.group('air').replace('M', '-')))
        except ValueError:
            pass
        try:
            d['dewpoint'] = str(int(result.group('dewpoint').replace('M', '-')))
        except ValueError:
            pass

    def altimeter(self, s):

        if s[0] == 'Q':
            self._metar['altimeter'] = {'str': s, 'index': self.index(), 'uom': 'hPa', 'value': s[1:]}
        #
        # Add it only if QNH hasn't been found.
        elif 'altimeter' not in self._metar:
            try:
                value = '%.02f' % (int(s[1:]) * 0.01)
            except ValueError:
                value = '////'

            self._metar['altimeter'] = {'str': s, 'index': self.index(), 'uom': "[in_i'Hg]", 'value': value}

    def rewx(self, s):

        self.updateDictionary('rewx', s[2:], self._metar)

    def windshear(self, s):

        rePattern = self.lexer.tokens[self.lexer.cur_token.name][0]
        result = rePattern.match(s)
        self._metar['ws'] = {'str': s, 'index': self.index(), 'rwy': result.group('rwy')}

    def seastate(self, s):

        rePattern = self.lexer.tokens[self.lexer.cur_token.name][0]
        result = rePattern.match(s)

        stateType = {'S': 'seaState', 'H': 'significantWaveHeight'}.get(result.group(3))

        try:
            seatemp = str(int(result.group('temp').replace('M', '-')))
        except ValueError:
            seatemp = result.group('temp')

        self._metar['seastate'] = {'str': s, 'index': self.index(),
                                   'seaSurfaceTemperature': seatemp,
                                   stateType: result.group('value')}

    def rwystate(self, s):  # pragma: no cover

        rePattern = self.lexer.tokens[self.lexer.cur_token.name][0]
        result = rePattern.match(s)
        try:
            self._metar['rwystate'].append({'str': s, 'index': self.index(),
                                            'runway': result.group(1),
                                            'state': result.group(2)})
        except KeyError:
            self._metar['rwystate'] = [{'str': s, 'index': self.index(),
                                        'runway': result.group(1),
                                        'state': result.group(2)}]

    def nosig(self):

        self._metar['nosig'] = {'index': self.index()}

    def trendtype(self, s):

        try:
            self._metar.setdefault('trendFcsts', []).append(getattr(self, '_trend'))
            del self._trend
        except AttributeError:
            pass

        self._trend = {'type': s, 'index': self.index()}

    def timeBoundary(self, s):

        hour, minute = int(s[-4:-2]), int(s[-2:])
        tms = list(self._metar['itime']['tuple'])
        tms[3:6] = hour, minute, 0
        if hour == 24:
            tms[3] = 0
            tms[2] += 1

        deu.fix_date(tms)
        #
        # Cases when forecast crosses midnight UTC.
        if calendar.timegm(tms) < self._metar['itime']['intTime']:
            tms[2] += 1
            deu.fix_date(tms)

        try:
            self._trend['ttime'].update({s[:2]: time.strftime('%Y-%m-%dT%H:%M:%SZ',
                                                              time.gmtime(calendar.timegm(tuple(tms))))})
        except KeyError:
            self._trend.update({'ttime': {s[:2]: time.strftime('%Y-%m-%dT%H:%M:%SZ',
                                                               time.gmtime(calendar.timegm(tuple(tms))))}})
