#!/usr/bin/env python3
"""Write patched files back into the Track 01 image in place (same size, same LBAs).
Only sectors whose user data changed are rewritten, with fresh Mode 1 EDC/ECC.

usage: patchdisc.py in_track01.bin out_track01.bin NAME=path [NAME=path ...]
"""
import sys, os, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from iso import Disc
from cdsec import fix_mode1

def patch(src, dst, files):
    d = Disc(src); fs = d.files()
    img = bytearray(d.d); changed = 0
    for name, path in files.items():
        lba, size = fs[name]
        new = open(path, 'rb').read()
        if len(new) != size: sys.exit('%s: size %d != %d' % (name, len(new), size))
        for i in range((size + 2047) // 2048):
            o = (lba + i) * 2352
            chunk = new[i * 2048:(i + 1) * 2048]
            if img[o + 16:o + 16 + len(chunk)] != chunk:
                sec = bytearray(img[o:o + 2352])
                assert sec[15] == 1, 'not a mode 1 sector'
                sec[16:16 + len(chunk)] = chunk
                img[o:o + 2352] = fix_mode1(sec); changed += 1
    open(dst, 'wb').write(img)
    return changed, zlib.crc32(img)

if __name__ == '__main__':
    files = dict(a.split('=', 1) for a in sys.argv[3:])
    n, crc = patch(sys.argv[1], sys.argv[2], files)
    print('%d sectors rewritten, CRC32 %08X' % (n, crc))
