"""Savestates of the ORIGINAL disc for test/devtest.py: work/st_mode.bin (mode select) and
work/st_f.bin (1P vs CPU, 7 columns, in play). Run after tools/setup.py."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nav import *
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
r = Retro(os.path.join(ROOT, 'work', 'fake.cue'))
def cdda():
    if r.r32(0x608b4fc) == 0: r.w32(0x608b4fc, 1)   # no real CD-DA: release the music-start wait
if sys.argv[1:] != ['--play']:
    r.run(900)
    assert wait_state(r, 4, press=['START'], maxf=4000); r.run(120)
    r.press(0, ['START'], 3, 0); assert wait_state(r, 5); r.run(200); save(r, 'st_mode.bin')
    # the core's CD-DA state after the boot path is not in savestates and stalls the match
    # start, so the rest runs in a fresh process from st_mode.bin (as devtest does)
    import subprocess; sys.exit(subprocess.call([sys.executable, os.path.abspath(__file__), '--play']))
load(r, 'st_mode.bin'); r.run(5)
# first mode (1P vs CPU, 7 columns): confirm through the menus until play starts
r.press(0, ['A'], 3, 150); r.press(0, ['A'], 3, 150)     # level, character
for i in range(80):                                         # story text until the match starts
    if st(r)[0] == 6: break
    r.press(0, ['A'], 3, 0)
    for k in range(12):
        if st(r)[0] == 6: break
        cdda(); r.run(5)
# find the first frame where the d-pad moves the clown; save just before it
COL = 0x60ae6c0 + 0x18
def live():                                  # RIGHT moves the clown one column further than no input
    snap = r.save_state()
    r.run(8); idle = r.r32(COL); r.load_state(snap)
    r.press(0, ['RIGHT'], 2, 6); moved = r.r32(COL); r.load_state(snap)
    return moved == idle + 1
back = None
for k in range(200):                         # coarse: 30-frame steps
    if live(): break
    back = r.save_state(); r.run(30)
assert live(), 'play never became live'
if back:                                     # fine: first live frame
    r.load_state(back)
    for k in range(31):
        if live(): break
        r.run(1)
assert r.r32(0x0605A474) == 7, ('not a 7-column game', st(r))
# The checks expect a fixed field: P1 holding one colour-3 balloon, column 0's lowest balloon
# colour 3 and column 1's colour 1 (magnet), room for a pull-down. Lay that field out directly.
P1 = 0x60ae6c0
FIELD = [[2, 2, 12, 14, 2, 0, 0],
         [2, 2, 12, 12, 2, 0, 0],
         [3, 3, 0, 0, 1, 1, 3],
         [3, 1, 0, 36, 2, 1, 3]]
cells = bytearray([36] * (24 * 7))
for y, row in enumerate(FIELD): cells[y * 7:y * 7 + 7] = bytes(row)
r.write(P1 + 0x337c, bytes(cells))
r.w8(P1 + 0x1c, 3); r.w32(P1 + 0x20, 1)
r.run(2)
save(r, 'st_f.bin')
print('saved st_mode.bin, st_f.bin; state', st(r))
