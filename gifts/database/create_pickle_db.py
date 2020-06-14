#!/usr/bin/env python
#
import pickle

database = {}
with open('aerodromes.tbl') as _fh:
    for lne in _fh:
        if lne.startswith('#'):
            continue

        try:
            sid, IATAId, alternateId, name, lat, lon, elev = lne.split('|')
        except ValueError:
            continue

        if len(sid) == 4 and sid.isalpha():
            database[sid] = '%s|%s|%s|%.5f %.5f %d' % (name[:60].strip().upper(), IATAId[:3].strip().upper(),
                                                       alternateId[:6].strip().upper(), float(lat), float(lon),
                                                       int(elev))

with open('aerodromes.db', 'wb') as _fh:
    pickle.dump(database, _fh, protocol=pickle.HIGHEST_PROTOCOL)
