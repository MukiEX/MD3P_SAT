#!/usr/bin/env python3
"""Emit web/patchdata.js: the changed Track 01 sectors (full 2352 bytes) + tuning block location."""
import sys, os, json, base64, zlib, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from iso import Disc
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
o = open(os.path.join(ROOT, 'work', 'track01.bin'), 'rb').read()
n = open(os.path.join(ROOT, 'build', 'track01.bin'), 'rb').read()
S = 2352
secs = [dict(lba=i, crc=zlib.crc32(o[i*S:(i+1)*S]), data=base64.b64encode(n[i*S:(i+1)*S]).decode())
        for i in range(len(o) // S) if o[i*S:(i+1)*S] != n[i*S:(i+1)*S]]
syms = {l.split()[1]: int(l.split()[0], 16) for l in open(os.path.join(ROOT, 'build', 'symbols.txt'))}
lba0, _ = Disc(os.path.join(ROOT, 'work', 'track01.bin')).files()['0.BIN']
off = syms['tune'] - 0x06004000
tune = dict(lba=lba0 + off // 2048, off=off % 2048)
assert off % 2048 + 16 <= 2048, 'tuning block crosses a sector'
P = dict(trackCrc=zlib.crc32(o), trackSectors=len(o) // S, patchedCrc=zlib.crc32(n), sectors=secs, tune=tune)
js = 'var PATCH = ' + json.dumps(P) + ';\nif (typeof module !== "undefined") module.exports = PATCH;\n'
open(os.path.join(ROOT, 'web', 'patchdata.js'), 'w').write(js)
print(len(secs), 'sectors', tune, '%08X -> %08X' % (P['trackCrc'], P['patchedCrc']))
