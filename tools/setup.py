#!/usr/bin/env python3
"""Prepare work/ from your own dump of the game.

usage: tools/setup.py "Magical Drop III - Toretate Zoukangou (Japan) (2M) (Track 01).bin"

Copies Track 01 to work/track01.bin, extracts 0.BIN and IP.BIN from it, and writes the
silent stand-in audio tracks + cue sheets the emulator tests boot from. Nothing from the
game is stored in this repository.
"""
import os, sys, shutil, zlib
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from iso import Disc

EXPECT = 0x97D3B2B2           # Track 01, 5116 sectors (Redump)

def cue(n_audio=29):
    s = 'FILE "track01.bin" BINARY\n  TRACK 01 MODE1/2352\n    INDEX 01 00:00:00\n'
    for t in range(2, 2 + n_audio):
        s += 'FILE "silence.bin" BINARY\n  TRACK %02d AUDIO\n    INDEX 00 00:00:00\n    INDEX 01 00:02:00\n' % t
    return s

def main():
    if len(sys.argv) != 2: sys.exit(__doc__)
    src = sys.argv[1]
    data = open(src, 'rb').read()
    crc = zlib.crc32(data)
    if crc != EXPECT:
        print('warning: CRC32 %08X, expected %08X (Redump Track 01); the build will refuse if 0.BIN differs' % (crc, EXPECT))
    work = os.path.join(ROOT, 'work'); build = os.path.join(ROOT, 'build')
    os.makedirs(work, exist_ok=True); os.makedirs(build, exist_ok=True)
    shutil.copyfile(src, os.path.join(work, 'track01.bin'))
    d = Disc(os.path.join(work, 'track01.bin'))
    open(os.path.join(work, '0.BIN'), 'wb').write(d.read('0.BIN'))
    open(os.path.join(work, 'IP.BIN'), 'wb').write(b''.join(d.sec(i) for i in range(3)))
    silence = bytes(2352 * 75 * 20)
    for dd in (work, build):
        open(os.path.join(dd, 'silence.bin'), 'wb').write(silence)
        open(os.path.join(dd, 'fake.cue'), 'w').write(cue())
    print('work/ ready (0.BIN %d bytes)' % len(d.read('0.BIN')))

if __name__ == '__main__': main()
