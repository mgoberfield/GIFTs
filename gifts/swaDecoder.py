#
# Name: swaDecoder.py
#
# Purpose: To decode, in its entirety, the Space Weather Advisory traditional alphanumeric code
#          as described in the Meteorological Service for International Air Navigation, Annex 3
#          to the Convention on International Civil Aviation.
#
# Author: Mark Oberfield
# Organization: NOAA/NWS/OSTI/MDL/WIAB
#
import copy
import itertools
import logging
import os
import re
import time

from skyfield.api import Loader

from .common import tpg
from .common import xmlConfig as des
from .common import xmlUtilities as deu


class Decoder(tpg.Parser):
    r"""
    set lexer = ContextSensitiveLexer
    set lexer_dotall = True

    separator spaces:    '\s+' ;

    token test: 'STATUS:\s*TEST' ;
    token exercise: 'STATUS:\s*EXER\w{0,4}' ;
    token dtg: 'DTG:\s*(?P<date>\d{8})/(?P<time>\d{4})Z' ;
    token centre: 'SWXC:\s*(\w+)' ;
    token advnum: 'ADVISORY NR:\s*(\d{4}/\d{1,4})' ;
    token prevadvsry: 'NR RPLC:\s*(\d{4}/\d{1,4})' ;
    token phenomena: 'SWX EFFECT:\s*(RADIATION|GNSS|(HF\s+|SAT)COM)\s+(MOD|SEV)\s*(AND\s+(RADIATION|GNSS)\s+(MOD|SEV))?' ; # noqa: E501
    token init: '(OBS|FCST) SWX:' ;
    token fcsthr: 'FCST SWX \+?(?P<fhr>\d{1,2})\s*HR:' ;
    token timestamp: '\d{2}/\d{4}Z' ;
    token daylight: 'DAY(LIGHT)?\s+SIDE' ;
    token lat_band: '(H|M)(N|S)H' ;
    token point: '(N|S)\d{2,4}\s+(E|W)\d{3,5}' ;
    token equator: 'EQ(N|S)' ;
    token longitudes: '(E|W)\d{3,5}\s*-\s*(E|W)\d{3,5}' ;
    token fltlvls: '(ABV\s+FL\d{3})|(FL\d{3}\s*-\s*(FL)?\d{3})' ;
    token noos: 'NO\s+SWX\s+EXP' ;
    token notavail: 'NOT\s+AVBL' ;
    token rmk: 'RMK:\s*(.+)(?=NXT (MSG|ADVISORY))' ;
    token nextdtg: 'NXT (MSG|ADVISORY):\s*(WILL\s+BE\s+ISSUED\s+BY\s*)?(?P<date>\d{8})/(?P<time>\d{4})Z?' ;
    token noadvisory: 'NXT (MSG|ADVISORY):\s*NO\s+FURTHER\s+ADVISORIES' ;

    START/d -> SWX $ d=self.finish() $ ;

    SWX -> 'SWX ADVISORY' (Test|Exercise)? Body? ;
    Body -> DTG Centre AdvNum Prevadvsry? Phenomena ObsFcst Fcst+ Rmk (NextDTG|NoAdvisory) ;

    ObsFcst -> Init Timestamp (Noos|(Daylight|Band|Equator|Longitudes|Point|FltLvls|'-')+) ;
    Fcst -> FcstHr Timestamp (Noos|NA|(Daylight|Band|Equator|Longitudes|Point|FltLvls|'-')+) ;

    Test -> test/x $ self.status(x) $ ;
    Exercise -> exercise/x $ self.status(x) $ ;
    DTG -> dtg/x $ self.dtg(x) $ ;
    Centre -> centre/x $ self.centre(x) $ ;
    AdvNum -> advnum/x $ self.advnum(x) $ ;
    Prevadvsry -> prevadvsry/x $ self.advnum(x,'replaced') $ ;
    Phenomena -> phenomena/x $ self.phenomena(x) $ ;

    Init -> init/x $ self.init(x) $ ;
    FcstHr -> fcsthr/x $ self.fcsthr(x) $ ;
    Timestamp -> timestamp/x $ self.timestamp(x) $ ;

    Noos -> noos $ self.noos() $ ;
    NA -> notavail $ self.notavail() $ ;

    Band -> lat_band/x $ self.lat_band(x) $ ;
    Point -> point/x $ self.point(x) $ ;
    Daylight -> daylight $ self.daylight() $ ;
    Equator -> equator/x $ self.equator(x) $ ;
    Longitudes -> longitudes/x $ self.longitudes(x) $ ;

    FltLvls -> fltlvls/x $ self.fltlvls(x) $ ;

    Rmk -> rmk/x $ self.rmk(x) $ ;
    NextDTG -> nextdtg/x $ self.nextadvisory(x) $ ;
    NoAdvisory -> noadvisory $ self.nextadvisory(None) $ ;
    """

    def __init__(self):

        self._tokenInEnglish = {'_tok_1': 'SWX ADVISORY line', 'test': 'STATUS: TEST', 'exercise': 'STATUS: EXER',
                                'dtg': 'Date/Time Group', 'centre': 'Issuing SWX Centre', 'advnum': 'YYYY/nnnn',
                                'prevadvsry': 'Previous Advisory YYYY/nnnn', 'phenomenon': 'SWX Hazard(s)',
                                'init': '(OBS|FCST) SWX', 'timestamp': 'DD/HHmmZ Group', 'noos': 'NO SWX EXP',
                                'notavail': 'NOT AVBL', 'daylight': 'DAY(LIGHT)? SIDE', 'lat_band': '(H|M)(N|S)H',
                                'equator': 'EQ(N|S)', 'longitudes': '(E|W)nnn[nn]-(E|W)nnn[nn]',
                                'box': 'lat/long bounding box', 'fltlvls': 'ABV FLnnn|FLnnn-nnn',
                                'fcsthr': 'FCST SWX +nn HR', 'rmk': 'RMK:',
                                'nextdtg': 'Next advisory issuance date/time', 'noadvisory': 'NO FURTHER ADVISORIES'}

        self.header = re.compile(r'.*(?=SWX ADVISORY)', re.DOTALL)

        setattr(self, 'lat_band', self.add_region)
        setattr(self, 'point', self.add_region)
        setattr(self, 'equator', self.add_region)

        self._Logger = logging.getLogger(__name__)
        #
        # Preparing Skyfield
        try:
            load = Loader(os.path.join(os.path.dirname(__file__), '../data'), verbose=False)
            self._ts = load.timescale()
            #
            # Open NAIF/JPL/NASA SPICE Kernel
            planets = load('de421.bsp')
            self._Gaia = planets['earth']
            self._Helios = planets['sun']

        except Exception:
            self._Logger.exception('Unable to load/initialize Skyfield Module.')
            raise

        return super(Decoder, self).__init__()

    def __call__(self, tac):

        self.swa = {'bbb': '',
                    'translationTime': time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'fcsts': {}}
        try:
            result = self.header.search(tac)
            swa = tac[result.end():].replace('=', '')

        except AttributeError:
            self.swa['err_msg'] = 'SWX ADVISORY line not found'
            return self.swa

        try:
            self._expected = []
            return super(Decoder, self).__call__(swa)

        except tpg.SyntacticError:

            if not self._is_a_test():
                if len(self._expected):
                    err_msg = 'Expecting %s group(s) ' % ' or '.join([self._tokenInEnglish.get(x, x)
                                                                      for x in self._expected])
                else:
                    err_msg = 'Unidentified group '

                tacLines = swa.split('\n')
                debugString = '\n%%s\n%%%dc\n%%s' % self.lexer.cur_token.end_column
                errorInTAC = debugString % ('\n'.join(tacLines[:self.lexer.cur_token.end_line]), '^',
                                            '\n'.join(tacLines[self.lexer.cur_token.end_line:]))
                self._Logger.info('%s\n%s' % (errorInTAC, err_msg))

                err_msg += 'at line %d column %d.' % (self.lexer.cur_token.end_line, self.lexer.cur_token.end_column)
                self.swa['err_msg'] = err_msg

        except Exception:
            self._Logger.exception(swa)

        return self.finish()

    def _is_a_test(self):
        return 'status' in self.swa and self.swa['status'] == 'TEST'

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

        self.swa['status'] = s.split(':', 1)[1].strip()

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
        deu.fix_date(tms)

        if self.lexer.cur_token.name == 'dtg':
            self.issueTime = tms
            self.swa['issueTime'] = {'str': time.strftime('%Y-%m-%dT%H:%M:00Z', tuple(tms)),
                                     'tms': tms}
        else:
            if result.group(2) is None:
                return {'str': time.strftime('%Y-%m-%dT%H:%M:00Z', tuple(tms)),
                        'before': False}
            else:
                return {'str': time.strftime('%Y-%m-%dT%H:%M:00Z', tuple(tms)),
                        'before': True}

    def centre(self, s):

        self.swa['centre'] = s.split(':', 1)[1].strip()

    def advnum(self, s, prefix='advisory'):

        self.swa['%sNumber' % prefix] = s.split(':', 1)[1].strip()

    def init(self, s):

        if s.startswith('OBS'):
            self._affected = {'timeIndicator': 'OBSERVATION'}
        else:
            self._affected = {'timeIndicator': 'FORECAST'}

        self._fcstkey = '0'
        self._boundingBox = BoundingBox()

    def fcsthr(self, s):

        self._affected['boundingBoxes'] = self._boundingBox.getLatLongBoxes()
        self.swa['fcsts'].update([(self._fcstkey, self._affected)])
        result = self.lexer.tokens[self.lexer.cur_token.name][0].match(s)
        self._fcstkey = result.group('fhr')
        self._affected = {'timeIndicator': 'FORECAST'}

    def timestamp(self, s):

        tms = self.issueTime
        tms[2] = int(s[:2])
        tms[3] = int(s[3:5])
        tms[4] = int(s[5:7])
        deu.fix_date(tms)
        self.issueTime = tms
        self._affected['phenomenonTime'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', tuple(tms))

    def noos(self):

        self._affected['noswxexp'] = True

    def notavail(self):

        self._affected['notavail'] = True

    def longitudes(self, s):

        self._boundingBox.add(s, self.lexer.cur_token.name)

    def add_region(self, s):

        self._affected.setdefault('regions', []).append(s)
        self._boundingBox.add(s, self.lexer.cur_token.name)

    def daylight(self):
        #
        # Determine solar sub-point on Earth at forecast/observed time.
        fcsttime = self._ts.utc(*self.issueTime[:5])
        subpoint = (self._Helios - self._Gaia).at(fcsttime).subpoint()
        self._affected['daylight'] = '%s %s' % (round(subpoint.latitude.degrees, 2),
                                                round(subpoint.longitude.degrees, 2))

    def fltlvls(self, s):

        self._affected['fltlevels'] = s
        self._boundingBox.add(s, self.lexer.cur_token.name)

    def phenomena(self, s):

        raw = s.split(':', 1)[1]
        self.swa['phenomenon'] = [x.strip() for x in raw.split('AND')]

    def rmk(self, s):

        self.swa['remarks'] = ' '.join(s[4:].split())

    def nextadvisory(self, s):

        if s is not None:
            self.swa['nextAdvisory'] = self.dtg(s)

    def finish(self):

        try:
            self._affected['boundingBoxes'] = self._boundingBox.getLatLongBoxes()
            self.swa['fcsts'].update([(self._fcstkey, self._affected)])
            #
            # Destroy the uuid cache
            del self._boundingBox

        except AttributeError:
            pass

        return self.swa


class BoundingBox():

    def __init__(self):
        self._latitude_bands = {'HNH': {'neighbors': ['MNH'],
                                        'latitudes': (90.0, 60.0)},
                                'MNH': {'neighbors': ['HNH', 'EQN'],
                                        'latitudes': (60.0, 30.0)},
                                'EQN': {'neighbors': ['MNH', 'EQS'],
                                        'latitudes': (30.0, 0.0)},
                                'EQS': {'neighbors': ['MSH', 'EQN'],
                                        'latitudes': (0.0, -30.0)},
                                'MSH': {'neighbors': ['HSH', 'EQS'],
                                        'latitudes': (-30.0, -60.0)},
                                'HSH': {'neighbors': ['MSH'],
                                        'latitudes': (-60.0, -90.0)}}
        self.regions = []
        self.longitudes = []
        self.polygon = []
        self._band_cnt = 0
        self._fltlvls = ''
        self._uuid_cache = {}

    def add(self, new_item, token_name):

        if token_name in ['lat_band', 'equator']:
            #
            # If no combining is allowed,
            if not des.JOIN_BANDS:
                self.regions.append([new_item])
            else:
                #
                # Look at the list of latitude bands and see if there's an
                # adjacent one or 'neighbor' to link up to.
                #
                self._band_cnt += 1
                combined_region = None

                for region in self.regions:
                    for lat_band in region:
                        if new_item in self._latitude_bands[lat_band]['neighbors']:
                            region.append(new_item)
                            combined_region = region
                            break

                    if combined_region is not None:
                        break
                else:
                    self.regions.append([new_item])
                #
                # If three or more lat_bands have been added with two separate groups,
                # need further analysis for combining groups
                #
                if combined_region is not None and self._band_cnt > 2 and len(self.regions) > 1:

                    remove_region_at = -1
                    for position, region in enumerate(self.regions):
                        if combined_region == region:
                            continue

                        for lat_band in region:
                            if new_item in self._latitude_bands[lat_band]['neighbors']:
                                combined_region.extend(region)
                                remove_region_at = position
                                break

                    if remove_region_at > -1:
                        self.regions.pop(remove_region_at)
        #
        # longitude ranges
        elif token_name == 'longitudes':
            self.longitudes = [self._convertToFloat(x) for x in new_item.split('-')]

        elif token_name == 'point':
            self.polygon.append(' '.join([str(self._convertToFloat(x)) for x in new_item.split()]))

        elif token_name == 'fltlvls':
            self._fltlvls = new_item

    def getLatLongBoxes(self):

        boxes = []
        for region in self.regions:
            alist = [self._latitude_bands[x]['latitudes'] for x in region]
            flattened = list(itertools.chain(*alist))
            n = max(flattened)
            s = min(flattened)

            try:
                w, e = self.longitudes
                if w > e:
                    e, w = w, e

            except ValueError:
                e, w = 180.0, -180.0

            ns = str(n)
            es = str(e)
            ws = str(w)
            ss = str(s)
            #
            aKey = copy.copy(region)
            aKey.extend([es, ws, self._fltlvls])
            uuidKey = frozenset(aKey)
            try:
                new_uuid = self._uuid_cache[uuidKey]
            except KeyError:
                new_uuid = deu.getUUID()
                self._uuid_cache[uuidKey] = '#%s' % new_uuid
            #
            # Start in NW corner and go counter-clockwise, poles are evil places
            if n != 90 and s != -90:
                boxes.append(('5', ' '.join([ns, ws, ss, ws, ss, es, ns, es, ns, ws]), region, new_uuid))
            elif n == 90:
                boxes.append(('4', ' '.join([ns, ws, ss, ws, ss, es, ns, ws]), region, new_uuid))
            elif s == -90:
                boxes.append(('4', ' '.join([ns, ws, ss, ws, ss, es, ns, ws]), region, new_uuid))

        if self.polygon:
            #
            # Check to make sure first == last
            if self.polygon[0] != self.polygon[-1]:
                self.polygon.append(self.polygon[0])
            #
            # Check to make sure polygon is traversed in CCW fashion
            #
            fpolygon = []
            for pnt in self.polygon:
                x, y = pnt.split()
                fpolygon.append((float(x), float(y)))
            try:
                if not deu.isCCW(fpolygon):
                    self.polygon.reverse()

            except ValueError as msg:
                self._Logger.info(msg)

            aKey = copy.copy(self.polygon)
            aKey.append(self._fltlvls)
            uuidKey = frozenset(aKey)
            try:
                new_uuid = self._uuid_cache[uuidKey]
            except KeyError:
                new_uuid = deu.getUUID()
                self._uuid_cache[uuidKey] = '#%s' % new_uuid

            boxes.append((str(len(self.polygon)), ' '.join(self.polygon), ['POLYGON'], new_uuid))

        self._reset()
        return boxes

    def _reset(self):

        self.regions = []
        self.longitudes = []
        self.polygon = []
        self._fltlvls = ''

    def _convertToFloat(self, string):

        latlong = string.strip()
        dir = latlong[0]
        if dir in ['E', 'W']:
            pos = 4
        else:
            pos = 3

        if dir in ['N', 'E']:
            fac = 1.0
        else:
            fac = -1.0

        degrees = int(latlong[1:pos])
        try:
            degrees = int(latlong[pos:]) * 0.0167 + float(degrees)
        except ValueError:
            pass

        degrees *= fac
        return round(degrees, 2)
