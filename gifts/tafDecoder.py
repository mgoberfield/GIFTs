#
# Name: TAFDecoder.py
#
# Purpose: To decode, in its entirety, the Terminal Aerodrome Forecast traditional alphanumeric code
#          as described in the Meteorological Service for International Air Navigation, Annex 3
#          to the Convention on International Civil Aviation.
#
# Author: Mark Oberfield
# Organization: NOAA/NWS/OSTI/MDL/WIAB
#
import logging
import re
import time

from .common import tpg
from .common import xmlConfig as des
from .common import xmlUtilities as deu


class CAVOKError(SyntaxError):
    """Called when mandatory values of visibility and sky conditions are missing in a group."""
    pass


class Decoder(tpg.Parser):
    r"""
    set lexer = ContextSensitiveLexer
    set lexer_dotall = True

    separator spaces:    '\s+' ;
    token prefix: 'TAF(\s+(AMD|COR))?' ;
    token ident: '[A-Z]{4}' ;
    token itime: '\d{6}Z' ;
    token nil: 'NIL' ;
    token vtime: '\d{4}/\d{4}' ;
    token cnl: 'CNL' ;
    token ftime: 'FM\d{6}' ;
    token btime: 'BECMG\s+\d{4}/\d{4}' ;
    token ttime: 'TEMPO\s+\d{4}/\d{4}' ;
    token ptime: 'PROB\d{2}\s+(TEMPO\s+)?\d{4}/\d{4}' ;
    token wind: '(VRB|\d{3})P?\d{2,3}(GP?\d{2,3})?(KT|MPS)' ;
    token cavok: 'CAVOK' ;
    token vsby: '\d{4}|P?((?P<whole>\d(?!/))?(?P<fraction>(M|\s+)?\d/\d{1,2})?)SM' ;
    token pcp: 'NSW|[+-]?((DZ|RA|SN|SG|PL|DS|SS|FZ(DZ|RA)){1,3}|(TS|SH)(GR|GS|RA|SN){1,3})' ;
    token obv: '((BC|FZ|MI|PR)?FG|BR|SA|DU|HZ|FU|VA|SQ|PO|FC|TS|BL(DU|SA|SN)|DR(DU|SN))' ;
    token sky: 'NSC|VV[/\d]{3}|(((FEW|SCT|BKN|OVC)\d{3}(CB|TCU)?)(\s+(FEW|SCT|BKN|OVC)\d{3}(CB|TCU)?){0,3})' ;
    token temps: '(T[NX]([M-]?\d{2})\s*/\s*\d{4}Z)' ;

    START/e -> TAF/e $ e=self.finish() $ ;
    TAF -> Prefix Main (BGroup|TGroup|PGroup)? (FGroup|BGroup|TGroup|PGroup)*  ;
    Main -> Ident ITime ( Nil | (VTime ( Cnl | BaseFcst ))) Temps{0,4} $ self.add_group('FM') $ ;

    BaseFcst -> Wind (Cavok|(Vsby (Pcp|Obv){0,3} Sky)) ;

    FGroup -> FTime BaseFcst $ self.add_group('FM') $ ;
    BGroup -> BTime Weather $ self.add_group('BECMG') $ ;
    TGroup -> TTime Weather $ self.add_group('TEMPO') $ ;
    PGroup -> PTime Weather $ self.add_group('PROB') $ ;

    Weather -> Wind? (Cavok|(Vsby? (Pcp|Obv){0,3} Sky?)) ;

    Prefix -> prefix/x $ self.prefix(x) $ ;
    Ident -> ident/x $ self.ident(x) $ ;
    ITime -> itime/x $ self.itime(x) $ ;
    VTime -> vtime/x $ self.vtime(x) $ ;
    FTime -> ftime/x $ self.ftime(x) $ ;
    BTime -> btime/x $ self.ttime(x) $ ;
    TTime -> ttime/x $ self.ttime(x) $ ;
    PTime -> ptime/x $ self.ptime(x) $ ;
    Nil -> nil $ self._nil = True $ ;
    Cnl -> cnl $ self._canceled = True $ ;
    Wind -> wind/x $ self.wind(x) $ ;
    Cavok -> cavok/x $ self.cavok(x) $ ;
    Vsby -> vsby/x $ self.vsby(x) $ ;
    Pcp -> pcp/x $ self.pcp(x) $ ;
    Obv -> obv/x $ self.obv(x) $ ;
    Sky -> sky/x $ self.sky(x) $ ;
    Temps -> temps/x $ self.temps(x) $ ;
    """

    def __init__(self):

        self._tokenInEnglish = {'ident': 'ICAO Identifier', 'itime': 'issuance time ddHHmmZ', 'nil': 'keyword NIL',
                                'vtime': 'valid period', 'cnl': 'keyword CNL', 'ftime': 'FM',
                                'btime': 'BECMG', 'ttime': 'TEMPO', 'ptime': 'PROB TEMPO?',
                                'vsby': 'prevailing visibility', 'pcp': 'precipitation', 'sky': 'sky condition',
                                'obv': 'obstruction-to-vision', 'temps': 'high/low temperatures'}

        self.header = re.compile(r'^TAF(\s+(AMD|COR))?\s+[A-Z]{4}.+?=', (re.MULTILINE | re.DOTALL))
        self.rmkKeyword = re.compile(r'[\s^]RMK[\s$]', re.MULTILINE)

        super(Decoder, self).__init__()
        self._Logger = logging.getLogger(__name__)

    def __call__(self, tac):

        self._taf = {'bbb': '',
                     'translationTime': time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                     'group': []}

        self._group = {'cavok': 'false'}
        self._nil = False
        self._canceled = False
        self._cavokErrors = []

        try:
            result = self.header.search(tac)
            tac = result.group(0)[:-1]

        except AttributeError:
            self._taf['err_msg'] = 'Unable to find start and end positions of the TAF.'
            return self._taf
        #
        # Remove RMK token and everything beyond that. This decoder follows Annex 3 specifications and ignores content
        # beyond the RMK keyword. Any unidentified content in the report renders it invalid.
        #
        rmkResult = self.rmkKeyword.search(tac)
        if rmkResult:
            tac = tac[:rmkResult.start()]

        try:
            self._expected = []
            return super(Decoder, self).__call__(tac)

        except tpg.SyntacticError:

            if len(self._expected):
                err_msg = 'Expecting %s group(s) ' % ' or '.join([self._tokenInEnglish.get(x, x)
                                                                  for x in self._expected])
            else:
                err_msg = 'Unidentified group '

            tacLines = tac.split('\n')
            debugString = '\n%%s\n%%%dc\n%%s' % self.lexer.cur_token.end_column
            errorInTAC = debugString % ('\n'.join(tacLines[:self.lexer.cur_token.end_line]), '^',
                                        '\n'.join(tacLines[self.lexer.cur_token.end_line:]))
            self._Logger.info('%s\n%s' % (errorInTAC, err_msg))

            err_msg += 'at line %d column %d.' % (self.lexer.cur_token.end_line, self.lexer.cur_token.end_column)
            self._taf['err_msg'] = err_msg

            return self.finish(reportCavokErrors=False)

        except CAVOKError:
            #
            # Just the first one is sufficent
            line, position = self._cavokErrors.pop(0)
            err_msg = 'When CAVOK is not present, prevailing visibility and sky conditions must be known.'

            tacLines = tac.split('\n')
            debugString = '\n%%s\n%%%dc\n%%s' % position
            errorInTAC = debugString % ('\n'.join(tacLines[:line]), '^',
                                        '\n'.join(tacLines[line:]))
            self._Logger.info('%s\n%s' % (errorInTAC, err_msg))

            self._taf['err_msg'] = err_msg

            return self._taf

        except Exception:
            self._Logger.exception(tac)
            return self.finish(reportCavokErrors=False)

    def _index(self, pos, token):

        tmp = self.lexer.input[:pos]
        line = tmp.count('\n') + 1
        row = pos - tmp.rfind('\n') - 1
        return ('%d.%d' % (line, row), '%d.%d' % (line, row + len(token)))

    def index(self):

        token = self.lexer.token()
        return self._index(token.start, token.text)

    def eatCSL(self, name):
        'Overrides super definition'
        try:
            value = super(Decoder, self).eatCSL(name)
            self._expected = []
            return value

        except tpg.WrongToken:
            self._expected.append(name)
            raise

    def finish(self, reportCavokErrors=True):
        """Called by the parser at the end of work"""

        if reportCavokErrors and not self.lexer.eof():
            raise tpg.WrongToken()

        if self._nil:
            self._taf['state'] = 'nil'

        elif self._canceled:
            self._taf['state'] = 'canceled'
            self._taf['group'] = []
            self._taf['prevtime'] = self._taf['vtime'].copy()
            self._taf['vtime']['from'] = self._taf['itime']['value']

        else:
            try:
                p = self._taf['group'][-1]
                if p['prevailing']['type'] == 'FM':
                    p['prevailing']['time']['to'] = self._taf['vtime']['to']

            except IndexError:
                pass

        if reportCavokErrors and self._cavokErrors:
            raise CAVOKError

        return self._taf

    def add_group(self, ctype):

        self._group['type'] = ctype
        if not self._nil and not self._canceled:
            if self._group['cavok'] == 'false':
                self.checkCAVOKConditions()

        if ctype in ['FM', 'BECMG']:
            if ctype == 'FM' and self._taf['group']:
                p = self._taf['group'][-1]
                p['prevailing']['time']['to'] = self._group['time']['from']

            self._taf['group'].append({'prevailing': self._group})

        else:
            period = self._taf['group'][-1]
            period.setdefault('ocnl', []).append(self._group)

        self._group = {'cavok': 'false'}

    # Assert that both visibility and sky condition must be present/known in the forecast group if CAVOK is not.
    def checkCAVOKConditions(self):

        try:
            assert 'vsby' in self._group
            assert 'sky' in self._group

        except AssertionError:

            try:
                sky = self._group['sky']
            except KeyError:
                sky = None

            try:
                vsby = self._group['vsby']
            except KeyError:
                vsby = None

            prevailingCnt = len(self._taf['group']) + 1
            #
            # Look back to previous FM/BECMG groups to find vsby and sky conditions.
            # Stop looking if/when cavok becomes 'true'.
            for x in range(-1, -prevailingCnt, -1):
                if self._taf['group'][x]['prevailing']['cavok'] == 'true':
                    break

                if sky is None and 'sky' in self._taf['group'][x]['prevailing']:
                    sky = self._group['sky'] = self._taf['group'][x]['prevailing']['sky']

                if vsby is None and 'vsby' in self._taf['group'][x]['prevailing']:
                    vsby = self._group['vsby'] = self._taf['group'][x]['prevailing']['vsby']
            #
            # This group is implied cavok: just wind forecasts in CAVOK conditions
            if vsby is None and sky is None:
                self._group['cavok'] = 'true'

            elif vsby is None or sky is None:

                line, column = self._group['time']['index'][1].split('.')
                if des.noImpliedCAVOKCondition:
                    self._cavokErrors.append((int(line), int(column)))
                else:
                    icaoID = self._taf['ident']['str']
                    if vsby is None:
                        self.vsby('10000')
                        if des.emitImpliedCAVOKConditionMessage:
                            self._Logger.info('TAF %s: Added >10km visibility to forecast group on line %s, column %s' %
                                              (icaoID, line, column))
                    else:
                        self.sky('NSC')
                        if des.emitImpliedCAVOKConditionMessage:
                            self._Logger.info('TAF %s: Added NSC to forecast group on line %s, column %s' %
                                              (icaoID, line, column))

    ###################################################################
    # Element checks
    def prefix(self, s):

        self._taf['type'] = {'str': s, 'index': self.index()}
        try:
            self._taf['bbb'] = s.split()[1]
        except IndexError:
            pass

    def ident(self, s):

        self._taf['ident'] = {'str': s, 'index': self.index()}

    def itime(self, s):

        self._group['type'] = 'FM'
        d = self._taf['itime'] = {'str': s, 'index': self.index()}
        mday, hour, minute = int(s[: 2]), int(s[2: 4]), int(s[4: 6])
        tms = list(time.gmtime())
        tms[2: 6] = mday, hour, minute, 0
        deu.fix_date(tms)
        d['value'] = time.mktime(tuple(tms))

    def vtime(self, s):

        d = self._group['time'] = {'str': s, 'index': self.index()}

        tms = list(time.gmtime())
        tms[2: 6] = int(s[0: 2]), int(s[2: 4]), 0, 0
        deu.fix_date(tms)

        mday, shour, eday, ehour = int(s[: 2]), int(s[2: 4]), int(s[5: 7]), int(s[7: 9])

        tms[2: 6] = mday, shour, 0, 0
        deu.fix_date(tms)
        d['from'] = time.mktime(tuple(tms))

        tms[2: 6] = eday, ehour, 0, 0
        deu.fix_date(tms)
        d['to'] = time.mktime(tuple(tms))

        self._taf['vtime'] = self._group['time'].copy()
        d['from'] = min(self._taf['vtime']['from'],
                        self._taf['itime']['value'])

    def ftime(self, s):

        d = self._group['time'] = {'str': s, 'index': self.index()}

        mday, hour, minute = int(s[2:4]), int(s[4:6]), int(s[6:8])
        tms = list(time.gmtime(self._taf['vtime']['from']))
        tms[2:5] = mday, hour, minute
        d.update({'from': time.mktime(tuple(tms)), 'to': self._taf['vtime']['to']})

    def ttime(self, s):

        d = self._group['time'] = {'str': s, 'index': self.index()}
        tmp = s.split()[1]
        sday, shour, eday, ehour = int(tmp[:2]), int(tmp[2:4]), int(tmp[5:7]), int(tmp[7:9])

        tms = list(time.gmtime(self._taf['vtime']['from']))
        tms[2:4] = sday, shour
        t = time.mktime(tuple(tms))
        if t < self._taf['vtime']['from']:
            deu.fix_date(tms)

        t = time.mktime(tuple(tms))

        tms[2:4] = eday, ehour
        if eday < sday:
            tms[1] += 1

        d.update({'from': t, 'to': time.mktime(tuple(tms))})

    def ptime(self, s):

        d = self._group['time'] = {'str': s, 'index': self.index()}
        tokens = s.split()
        tmp = tokens[-1]
        sday, shour, eday, ehour = int(tmp[:2]), int(tmp[2:4]), int(tmp[5:7]), int(tmp[7:9])

        tms = list(time.gmtime(self._taf['vtime']['from']))
        tms[2:4] = sday, shour
        t = time.mktime(tuple(tms))
        if t < self._taf['vtime']['from']:
            deu.fix_date(tms)

        t = time.mktime(tuple(tms))
        tms[2:4] = eday, ehour
        if eday < sday:
            tms[1] += 1

        d.update({'from': t, 'to': time.mktime(tuple(tms))})

    def cavok(self, s):

        self._group['cavok'] = 'true'

    def wind(self, s):

        d = self._group['wind'] = {'str': s, 'index': self.index(), 'uom': 'm/s'}
        uompos = -3

        if s.startswith('VRB'):
            d['dd'] = 'VRB'
        else:
            d['dd'] = str(int(s[:3]))

        if s.endswith('KT'):
            d['uom'] = '[kn_i]'
            uompos = -2

        tok = s[3:uompos].split('G', 1)
        speed = tok[0]
        if speed[0] == 'P':
            d['ffplus'] = True
            speed = tok[0][1:]

        d['ff'] = str(int(speed))

        if len(tok) > 1:

            gust = tok[1]
            if gust[0] == 'P':

                d['ggplus'] = True
                gust = tok[1][1:]

            d['gg'] = str(int(gust))

    def vsby(self, s):

        d = self._group['vsby'] = {'str': s, 'index': self.index(), 'uom': 'm'}
        if s.endswith('SM'):

            vis = 0.0
            v = self.lexer.tokens[self.lexer.cur_token.name][0].match(s)
            value = v.groupdict('')

            try:
                vis += float(value.get('whole'))
                if s[0] == 'P':
                    vis += 1.0

            except ValueError:
                pass

            try:
                numerator, denominator = value.get('fraction').split('/', 1)
                vis += float(numerator) / float(denominator)

            except (ValueError, ZeroDivisionError):
                pass

            d['value'] = deu.checkVisibility(str(vis), '[mi_i]')

        else:
            d['value'] = deu.checkVisibility(s, 'm')

    def pcp(self, s):

        try:
            d = self._group['pcp']
            d['index'].append(self.index())
            d['str'] = '%s %s' % (d['str'], s)

        except KeyError:
            self._group['pcp'] = {'str': s, 'index': [self.index()]}

    def obv(self, s):

        try:
            d = self._group['obv']
            d['index'].append(self.index())
            d['str'] = '%s %s' % (d['str'], s)

        except KeyError:
            self._group['obv'] = {'str': s, 'index': [self.index()]}

    def sky(self, s):

        self._group['sky'] = {'str': s, 'index': self.index()}

    def temps(self, s):

        try:
            d = self._group['temps']
            d['index'].append(self.index())
            d['str'] = '%s %s' % (d['str'], s)

        except KeyError:
            d = self._group['temps'] = {'str': s, 'index': [self.index()], 'uom': 'Cel'}

        airtemp, tstamp = map(str.strip, s.split('/'))
        sday, shour = int(tstamp[:2]), int(tstamp[2:4])

        tms = list(time.gmtime(self._taf['vtime']['from']))
        tms[2:4] = sday, shour
        t = time.mktime(tuple(tms))
        if t < self._taf['vtime']['from']:
            deu.fix_date(tms)

        airtemp = airtemp.replace('M', '-')

        if s[1] == 'X':
            d.setdefault('max', []).append({'value': airtemp[2:], 'at': time.mktime(tuple(tms))})
        else:
            d.setdefault('min', []).append({'value': airtemp[2:], 'at': time.mktime(tuple(tms))})
