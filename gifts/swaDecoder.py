import itertools
import logging
import os
import re
import time

import skyfield

from skyfield.api import Loader
from skyfield.toposlib import wgs84

from geographiclib.geodesic import Geodesic

from .common import tpg
from .common import xmlConfig as des
from .common import xmlUtilities as deu

# Name: swaDecoder.py
#
# Purpose: To decode, in its entirety, the Space Weather Advisory traditional alphanumeric code
#          as described in the Meteorological Service for International Air Navigation, Annex 3
#          to the Convention on International Civil Aviation.
#
# Author: Mark Oberfield
# Organization: NOAA/NWS/OSTI/MDL/WIAB
#


class Decoder(tpg.Parser):
    r"""
    set lexer = ContextSensitiveLexer
    set lexer_dotall = True

    separator spaces:    '\s+' ;

    token test: 'STATUS:\s*TEST' ;
    token exercise: 'STATUS:\s*EXER\w{0,4}' ;
    token dtg: 'DTG:\s*(?P<date>\d{8})/(?P<time>\d{4})Z' ;
    token centre: 'SWXC:\s*(\w+)' ;
    token effect: 'SWX EFFECT:\s*(RADIATION|GNSS|(HF\s+|SAT)COM)' ;
    token advnum: 'ADVISORY NR:\s*(\d{4}/\d{1,4})' ;
    token prevadvsry: 'NR RPLC:([.\s\d\/]+)' ;
    token init: '(OBS|FCST) SWX:' ;
    token fcsthr: 'FCST SWX \+?(?P<fhr>\d{1,2})\s*HR:' ;
    token timestamp: '\d{2}/\d{4}Z' ;
    token intensity: '(MOD|SEV)' ;
    token day: 'DAYSIDE' ;
    token night: 'NIGHTSIDE' ;
    token lat_band: '(H|M)(N|S)H' ;
    token point: '(N|S)\d{2}\s+(E|W)\d{3}' ;
    token equator: 'EQ(N|S)' ;
    token longitudes: '(E|W)\d{3}\s*-\s*(E|W)\d{3}' ;
    token fltlvls: '(ABV\s+FL\d{3})|(FL\d{3}\s*-\s*(FL)?\d{3})' ;
    token noos: 'NO\s+SWX\s+EXP' ;
    token notavail: 'NOT\s+AVBL' ;
    token rmk: 'RMK:\s*(.+)(?=NXT (MSG|ADVISORY))' ;
    token nextdtg: 'NXT (MSG|ADVISORY):\s*(WILL\s+BE\s+ISSUED\s+BY\s*)?(?P<date>\d{8})/(?P<time>\d{4})Z?' ;
    token noadvisory: 'NXT (MSG|ADVISORY):\s*NO\s+FURTHER\s+ADVISORIES' ;

    START/d -> SWX $ d=self.finish() $ ;

    SWX -> 'SWX ADVISORY' (Test|Exercise)? Body? ;
    Body -> DTG Centre Effect AdvNum Prevadvsry? ObsFcst Fcst+ Rmk (NextDTG|NoAdvisory) ;

    ObsFcst -> Init Timestamp (Noos|(Intensity|Day|Night|Band|Equator|Longitudes|Point|FltLvls|'-')+) ;
    Fcst -> FcstHr Timestamp (Noos|NA|(Intensity|Day|Night|Band|Equator|Longitudes|Point|FltLvls|'-')+) ;

    Test -> test/x $ self.status(x) $ ;
    Exercise -> exercise/x $ self.status(x) $ ;
    DTG -> dtg/x $ self.dtg(x) $ ;
    Centre -> centre/x $ self.centre(x) $ ;
    AdvNum -> advnum/x $ self.advnum(x) $ ;
    Prevadvsry -> prevadvsry/x $ self.advnum(x,'replaced') $ ;
    Effect -> effect/x $ self.effect(x) $ ;

    Init -> init/x $ self.init(x) $ ;
    FcstHr -> fcsthr/x $ self.fcsthr(x) $ ;
    Timestamp -> timestamp/x $ self.timestamp(x) $ ;

    Noos -> noos $ self.noos() $ ;
    NA -> notavail $ self.notavail() $ ;

    Intensity -> intensity/x $ self.newgroup(x) $ ;
    Band -> lat_band/x $ self.lat_band(x) $ ;
    Point -> point/x $ self.point(x) $ ;
    Day -> day/x $ self.day('day') $ ;
    Night -> night/x $ self.day('night') $ ;
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
                                'prevadvsry': 'One or more previous Advisories YYYY/nnnn',
                                'effectn': 'SWX Hazard(s)', 'init': '(OBS|FCST) SWX', 'intensity': '(MOD|SEV)',
                                'timestamp': 'DD/HHmmZ Group', 'noos': 'NO SWX EXP', 'notavail': 'NOT AVBL',
                                'day': 'DAYSIDE', 'night': 'NIGHTSIDE', 'lat_band': '(H|M)(N|S)H',
                                'equator': 'EQ(N|S)', 'longitudes': '(E|W)nnn-(E|W)nnn',
                                'box': 'lat/long bounding box', 'fltlvls': 'ABV FLnnn|FLnnn-nnn',
                                'fcsthr': 'FCST SWX +nn HR', 'rmk': 'RMK:',
                                'nextdtg': 'Next advisory issuance date/time', 'noadvisory': 'NO FURTHER ADVISORIES'}

        self.header = re.compile(r'.*?(?=SWX ADVISORY)', re.DOTALL)

        setattr(self, 'lat_band', self.add_region)
        setattr(self, 'point', self.add_region)
        setattr(self, 'equator', self.add_region)

        self._Logger = logging.getLogger(__name__)
        #
        # Preparing Skyfield
        try:
            load = Loader(os.path.join(skyfield.__path__[0], 'bsp_files'), verbose=False)
            self._ts = load.timescale()
            #
            # Open NAIF/JPL/NASA SPICE Kernel
            planets = load('de421.bsp')
            self._Gaia = planets['earth']
            self._Helios = planets['sun']

        except Exception:
            self._Logger.exception('Unable to load/initialize Skyfield ephemeris file.')
            raise

        return super(Decoder, self).__init__()

    def __call__(self, tac):
        #
        # BBB code unused but needed for bulletin
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

        if prefix == 'advisory':
            self.swa['%sNumber' % prefix] = s.split(':', 1)[1].strip()
        else:
            cstrng = s.split(':', 1)[1].strip()
            self.swa['%sNumber' % prefix] = cstrng.split()

    def init(self, s):

        if s.startswith('OBS'):
            self._affected = {'timeIndicator': 'OBSERVATION'}
        else:
            self._affected = {'timeIndicator': 'FORECAST'}

        self._fcstkey = '0'
        self._boundingBox = BoundingBox()
        self._group = {}

    def newgroup(self, s):
        "If MOD or SEV token is found"

        if self._group:
            boxes = self._boundingBox.getLatLongBoxes()
            if len(boxes):
                self._group['boundingBoxes'] = boxes
            self._affected.setdefault('groups', []).append(self._group)

        self._group = {'intensity': s}

    def fcsthr(self, s):

        if self._group:
            boxes = self._boundingBox.getLatLongBoxes()
            if len(boxes):
                self._group['boundingBoxes'] = boxes

            self._affected.setdefault('groups', []).append(self._group)

        self.swa['fcsts'].update([(self._fcstkey, self._affected)])
        result = self.lexer.tokens[self.lexer.cur_token.name][0].match(s)
        self._fcstkey = result.group('fhr')
        self._affected = {'timeIndicator': 'FORECAST'}
        self._group = {}

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

        self._group.setdefault('regions', []).append(s)
        self._boundingBox.add(s, self.lexer.cur_token.name)

    def day(self, s):
        #
        # Determine solar sub-point on Earth at forecast/observed time.
        fcsttime = self._ts.utc(*self.issueTime[:5])
        subpoint = wgs84.geographic_position_of((self._Helios - self._Gaia).at(fcsttime))
        #
        if s == 'day':
            subpoint = '%s %s' % (round(subpoint.latitude.degrees, 1),
                                  round(subpoint.longitude.degrees, 1))
        else:
            longitude = round(subpoint.longitude.degrees, 1)
            longitude = longitude + 180. if longitude <= 0 else longitude - 180.
            subpoint = '%s %s' % (-(round(subpoint.latitude.degrees, 1)),
                                  (round(longitude, 1)))

        self._group[s] = subpoint
        self._boundingBox.add(subpoint, s)

    def fltlvls(self, s):

        self._group['fltlevels'] = s
        self._boundingBox.add(s, self.lexer.cur_token.name)

    def effect(self, s):

        raw = s.split(':', 1)[1]
        self.swa['effect'] = raw.strip().replace(' ', '_')

    def rmk(self, s):

        self.swa['remarks'] = ' '.join(s[4:].split())

    def nextadvisory(self, s):

        if s is not None:
            self.swa['nextAdvisory'] = self.dtg(s)

    def finish(self):

        try:
            if self._group:
                boxes = self._boundingBox.getLatLongBoxes()
                if len(boxes):
                    self._group['boundingBoxes'] = boxes

                self._affected.setdefault('groups', []).append(self._group)

            self.swa['fcsts'].update([(self._fcstkey, self._affected)])

        except AttributeError:
            pass

        return self.swa


class BoundingBox():
    "Converts text to lat/lng point lists"

    def __init__(self):
        self._latitude_bands = {'HNH': {'neighbors': ['MNH'],
                                        'latitudes': (90, 60)},
                                'MNH': {'neighbors': ['HNH', 'EQN'],
                                        'latitudes': (60, 30)},
                                'EQN': {'neighbors': ['MNH', 'EQS'],
                                        'latitudes': (30, 0)},
                                'EQS': {'neighbors': ['MSH', 'EQN'],
                                        'latitudes': (0, -30)},
                                'MSH': {'neighbors': ['HSH', 'EQS'],
                                        'latitudes': (-30, -60)},
                                'HSH': {'neighbors': ['MSH'],
                                        'latitudes': (-60, -90)}}
        self.regions = []
        self.longitudes = []
        self.polygon = []
        self._band_cnt = 0
        self._fltlvls = ''

        factor = 1000
        if des.TERMINATOR_UOM == '[mi_i]':
            factor = 1609
        try:
            self.Gaia_TRADIUS = float(des.TERMINATOR_RADIUS) * factor
        except ValueError:
            self.Gaia_TRADIUS = 10018000

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
        #
        # (DAY|NIGHT)SIDE modifies the latitude bands
        elif token_name in ['day', 'night']:
            sslat, sslng = new_item.split()
            if len(self.regions):
                self._bands = self.getTerminatedBands(float(sslat), float(sslng))

    def getTerminatedBands(self, sslat, sslng):
        "Generate day or night side latitude bands"

        bands = {'HNH': [], 'MNH': [], 'EQN': [], 'EQS': [], 'MSH': [], 'HSH': []}

        geod = Geodesic.WGS84
        outmask = Geodesic.LATITUDE | Geodesic.LONGITUDE

        bandNames = list(bands)
        nameLoop = bandNames + bandNames[4::-1]
        name = nameLoop.pop(0)
        hi, lo = self._latitude_bands[name]['latitudes']
        segment = []
        #
        # Given the solar sub-point, get lat/lng points on the terminator in CCW fashion
        for bearing in range(0, -360, -des.INCR):

            pt = geod.Direct(sslat, sslng, bearing, self.Gaia_TRADIUS, outmask)
            lat, lng = round(pt['lat2'], 1), round(pt['lon2'], 1)
            # If point is in bounds, append to segment
            if lo <= lat <= hi:
                segment.append((lat, lng))
            else:
                cross = lo if bearing >= -180 else hi
                # Make final point by interpolation and save it
                interp = False
                if cross != segment[-1][0]:
                    # previous point
                    plat, plng = segment[-1]
                    lng = self._unroll(plng, lng)
                    # interpolate new longitude for crossing latitude
                    try:
                        nlng = lng - ((lng-plng)/(lat-plat))*(lat-cross)
                    except ZeroDivisionError:
                        nlng = lng

                    if nlng < -180:
                        nlng += 360
                    elif nlng > 180:
                        nlng -= 360
                    segment.append((cross, round(nlng, 1)))
                    interp = True

                bands[name].append(segment)
                #
                # Start the new segment
                if interp:
                    segment = [(cross, round(nlng, 1))]
                    segment.append((lat, lng))
                else:
                    segment = [(lat, lng)]

                # Get the limits of next latitude band
                name = nameLoop.pop(0)
                hi, lo = self._latitude_bands[name]['latitudes']
        #
        # Extend the last segment with the first, partial, one
        segment += bands[name].pop()
        bands[name] = [segment]
        #
        # Stitch the segments together to form polygons
        for name in bandNames:
            #
            # Get the latitude limits of the bands
            tlat, blat = self._latitude_bands[name]['latitudes']
            if name != 'HNH':
                #
                # Tops of the bands' lat/lng points go westward
                try:
                    tlngs = self._goWest(bands[name][1][-1][1], bands[name][0][0][1])
                except IndexError:
                    tlngs = self._goWest(bands[name][0][-1][1], bands[name][0][0][1])
                segment = [(tlat, x) for x in tlngs]
                segment.append(bands[name][0][0])
                bands[name].append(segment)

            if name != 'HSH':
                #
                # Bottoms of the bands' lat/lng points go eastward
                try:
                    blngs = self._goEast(bands[name][0][-1][1], bands[name][1][0][1])
                except IndexError:
                    blngs = self._goEast(bands[name][0][-1][1], bands[name][0][0][1])
                segment = [(blat, x) for x in blngs]
                if name == 'HNH': segment.append(bands[name][0][0])  # noqa: E701
                bands[name].insert(1, segment)

        return bands

    def getLatLongBoxes(self):
        #
        # If the bands are limited by the Earth's day/night terminator, use them
        boxes = []
        if hasattr(self, '_bands'):

            for region in self.regions:
                numPts, latslngs = self._getBordersOf(region)
                boxes.append((numPts, latslngs, region, None))

            self._reset()
            return boxes

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
            new_uuid = deu.getUUID()
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
            fpolygon = []
            for pnt in self.polygon:
                x, y = pnt.split()
                fpolygon.append((float(x), float(y)))
            try:
                if not deu.isCCW(fpolygon):
                    self.polygon.reverse()

            except ValueError as msg:
                self._Logger.info(msg)

            new_uuid = deu.getUUID()
            boxes.append((str(len(self.polygon)), ' '.join(self.polygon), ['POLYGON'], new_uuid))

        self._reset()
        return boxes

    def _getBordersOf(self, region):
        "Get borders of--possibly combined--latitude bands"

        numBands = len(region)
        #
        # If its just one latitude band, that's simple
        if numBands == 1:
            sides = []
            for side in self._bands[region[0]]:
                sides.extend(list(itertools.chain(side)))
        #
        # For multiple bands, order from N->S            3
        #  first band: save all sides, except bottom,    _
        #  last band: save all sides, except top,    0 |   | 2
        #  other bands: save LHS, RHS only               -
        #                                                1
        else:
            o = list(self._latitude_bands.keys())
            for num, name in enumerate([o[x] for x in sorted([o.index(y) for y in region])]):
                if num == 0:
                    if name != 'HNH':
                        lhs = [self._bands[name][0]]
                        rhs = [self._bands[name][2]]
                        top = [self._bands[name][3]]

                    else:
                        top = [self._bands[name][0]]
                        lhs = []
                        rhs = []

                elif num == numBands-1:
                    if name != 'HSH':
                        lhs.append(self._bands[name][0])
                        btm = [self._bands[name][1]]
                        rhs.insert(0, self._bands[name][2])

                    else:
                        btm = [self._bands[name][0]]

                else:
                    lhs.append(self._bands[name][0])
                    rhs.insert(0, self._bands[name][2])
            #
            # Now stitch together, keeping CCW order: lhs, btm, rhs, top.
            sides = []
            for side in [lhs, btm, rhs, top]:
                sides.extend(list(itertools.chain.from_iterable(side)))

        ssides = [f'{round(float(pt[0]), 1)} {round(float(pt[1]), 1)}' for pt in sides]
        return str(len(ssides)), ' '.join(ssides)

    def _unroll(self, lon1, lon2):
        "Adjust new longitude if it crosses the anti-meridan"
        #
        # If difference in longitude is greater than 180
        if abs(lon2 - lon1) > 180:
            if lon2 > lon1:
                return lon2-360
            else:
                return 360+lon2
        else:
            return lon2

    def _goEast(self, lng1, lng2):
        "Make list of longitudes from west to east"

        lng1 = int(lng1+1)
        lng2 = int(lng2-1)
        if lng1 > 180:
            lng1 -= 360
        if lng2 <= -180:
            lng2 += 360

        easting = [x if x <= 180 else x-360 for x in range(lng1, lng1+360)]
        return easting[0:easting.index(lng2)][::des.INCR]

    def _goWest(self, lng1, lng2):
        "Make list of longitudes from east to west"

        lng1 = int(lng1-1)
        lng2 = int(lng2+1)
        if lng1 < -180:
            lng1 += 360
        if lng2 >= 180:
            lng2 -= 360

        westing = [x if x >= -180 else 360+x for x in range(lng1, lng1-360, -1)]
        return westing[0:westing.index(lng2)][::des.INCR]

    def _reset(self):

        self.regions = []
        self.longitudes = []
        self.polygon = []
        self._fltlvls = ''
        try:
            del self._bands
        except AttributeError:
            pass

    def _convertToFloat(self, string):

        latlong = string.strip()
        dir = latlong[0]
        if dir in ['E', 'W']:
            pos = 4
        else:
            pos = 3

        if dir in ['N', 'E']:
            return int(latlong[1:pos])
        else:
            return -int(latlong[1:pos])
