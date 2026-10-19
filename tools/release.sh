#!/bin/sh
# Full build: patch code -> 0.BIN -> Track 01 -> patch files + browser patcher
set -e
cd "$(dirname "$0")/.."
XD=${XDELTA:-xdelta3}
python3 tools/build.py
python3 tools/hazards.py
python3 tools/patchdisc.py work/track01.bin build/track01.bin 0.BIN=build/0.BIN
python3 tools/mkpatchdata.py
python3 tools/mkpatcher.py
mkdir -p release
N="Magical Drop III - Toretate Zoukangou (Japan) (2M) (Track 01) [Paddle]"
python3 tools/make_ppf.py work/track01.bin build/track01.bin "release/$N.ppf" "MD3 Saturn Paddle Edition"
$XD -e -9 -f -s work/track01.bin build/track01.bin "release/$N.xdelta"
$XD -d -f -s work/track01.bin "release/$N.xdelta" work/xd_check.bin && cmp work/xd_check.bin build/track01.bin
cp build/MD3SatPaddlePatcher.html release/
python3 -c "import zlib;print('patched Track 01 CRC32 %08X' % zlib.crc32(open('build/track01.bin','rb').read()))"
