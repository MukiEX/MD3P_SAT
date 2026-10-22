"""Regression tests for the Saturn paddle patch (run after tools/build.py).
Uses savestates of the original disc (work/st_*.bin) with the built 0.BIN written into RAM."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from nav import *

P1 = 0x60ae6c0           # player 1 struct in story mode
COL = P1 + 0x18
fails = []
def check(name, cond, info=''):
    print(('PASS ' if cond else 'FAIL ') + name, info); (None if cond else fails.append(name))

r = Retro('work/fake.cue')
S = syms(); PS = S['pstate']; TUNE = S['tune']

def game(dev=DEV_JOYPAD, state='st_f.bin'):
    load(r, state); apply_patch(r)
    for p_ in r.ports: p_.buttons = set(); p_.mbtn = set(); p_.ax = p_.ay = 0
    r.set_device(0, dev); r.run(3)

# ---- normal pad unchanged
game()
c0 = r.r32(COL); r.press(0, ['RIGHT'], 2, 6); c1 = r.r32(COL); r.press(0, ['LEFT'], 2, 6); r.press(0, ['LEFT'], 2, 6)
check('pad d-pad moves one column', c1 == c0 + 1 and r.r32(COL) == c0 - 1, (c0, c1, r.r32(COL)))
r.press(0, ['B'], 2, 30); check('pad B throws', r.r32(P1 + 0x20) == 0)

# ---- mouse
game(DEV_MOUSE)
for i in range(40): r.ports[0].mx = 12; r.run(1)
r.run(10); check('mouse right reaches last column', r.r32(COL) == 6, r.r32(COL))
check('mouse leaves no d-pad bits', r.r16(0x60b3d6c) & 0xF000 == 0)
for i in range(40): r.ports[0].mx = -12; r.run(1)
r.run(10); check('mouse left reaches column 0', r.r32(COL) == 0, r.r32(COL))
# slow: 1 count/frame at x1 = 4 units/frame -> a column every ~32 frames
game(DEV_MOUSE)
c0 = r.r32(COL)
x0 = r.r16(PS + 10)
for i in range(12): r.ports[0].mx = 1; r.run(1)
check('mouse slow motion stays put', r.r32(COL) == c0, (r.r32(COL), (r.r16(PS + 10) - x0) & 0xffff))
for i in range(30): r.ports[0].mx = 1; r.run(1)
check('mouse slow motion steps one column', r.r32(COL) == c0 + 1, r.r32(COL))
r.ports[0].mbtn = {'RIGHT'}; r.run(2); r.ports[0].mbtn = set(); r.run(30)
check('mouse right button throws', r.r32(P1 + 0x20) == 0)
r.ports[0].mbtn = {'LEFT'}; r.run(2); r.ports[0].mbtn = set(); r.run(30)
check('mouse left button catches', r.r32(P1 + 0x20) > 0, r.r32(P1 + 0x20))
# settle: after idle the paddle re-centres in the clown's column
r.run(20); pos = r.r16(PS + 16); check('idle re-centre', pos == r.r32(COL) * 128 + 64, pos)
# speed byte from the tuning block
game(DEV_MOUSE); r.w8(TUNE + 5, 8)
c0 = r.r32(COL)
for i in range(20): r.ports[0].mx = 1; r.run(1)
check('mouse speed x2', r.r32(COL) == c0 + 1, r.r32(COL))

# ---- magnet (off by default): P1 holds colour 3; column 0's lowest balloon is 3, column 1's is 1
game(DEV_MOUSE)
for i in range(40): r.ports[0].mx = -12; r.run(1)
r.run(5); dd = []
for i in range(6):
    a = r.r16(PS + 16); r.ports[0].mx = 2; r.run(1); dd.append(r.r16(PS + 16) - a)
check('magnet off by default', set(dd[2:]) == {8}, dd)
game(DEV_MOUSE); r.w8(TUNE + 13, 3)
for i in range(40): r.ports[0].mx = -12; r.run(1)
r.run(5)
def dpos(n):
    out = []
    for i in range(n):
        a = r.r16(PS + 16); r.ports[0].mx = 2; r.run(1); out.append(r.r16(PS + 16) - a)
    return out
d0 = dpos(8)[2:]; dpos(30); d1 = dpos(6)[2:]
check('magnet half speed only over a matching column', set(d0) == {4} and set(d1) == {8}, (d0, d1, r.r32(COL)))

# ---- glide: aim line x follows the paddle between columns. The aim line's slot in SGL's
# sprite work area depends on what else is on screen, so find it: the word that rises with
# the mouse and holds still when the mouse does.
import numpy as _np
def sprite_words(): return _np.frombuffer(r.read(0x060F0000, 0x1000), dtype='>i2').astype(int)
game(DEV_MOUSE)
snaps = []
for i in range(6):
    r.ports[0].mx = 3; r.run(1); r.ports[0].mx = 0; r.run(2)
    snaps.append(sprite_words())
still = sprite_words(); r.run(2); still2 = sprite_words()
S = _np.array(snaps)
cand = [i for i in range(S.shape[1]) if (_np.diff(S[:, i]) >= 0).all() and len(set(S[:, i])) >= 4 and still[i] == still2[i]]
check('glide moves aim line by pixels', bool(cand), list(S[:, cand[0]]) if cand else None)
r.w8(TUNE + 13, 0)
xs2 = []
for i in range(6):
    r.ports[0].mx = 3; r.run(1); r.ports[0].mx = 0; r.run(2)
    xs2.append(int(sprite_words()[cand[0]]) if cand else None)
check('glide off snaps to columns', bool(cand) and all((b - a) % 16 == 0 for a, b in zip(xs2, xs2[1:])), xs2)

# ---- pulsing target column: VDP1 commands with Gouraud from SGL's ramp (GRDA 0xFFE0..0xFFFF)
import struct as _st
def pulsed():
    v = r.read(0x25C00000, 0x8000); out = []
    for i in range(0, len(v), 32):
        pm, grda = _st.unpack('>H', v[i+4:i+6])[0], _st.unpack('>H', v[i+28:i+30])[0]
        if pm & 7 == 4 and 0xFFE0 <= grda <= 0xFFFF and _st.unpack('>H', v[i:i+2])[0] & 0x8000 == 0: out.append((_st.unpack('>h', v[i+12:i+14])[0], grda))
    return out
game(DEV_MOUSE); r.run(4)
pp = pulsed(); xs = sorted(set(x for x, g in pp))
check('pulse marks one column of P1 balloons', len(pp) >= 1 and len(xs) == 1 and xs[0] == 16 + 16 * r.r32(COL), (pp, r.r32(COL)))
gs = set()
for i in range(12): r.run(4); gs |= set(g for x, g in pulsed())
check('pulse ramps over the cycle', len(gs) >= 5, sorted(hex(g) for g in gs))
for i in range(40): r.ports[0].mx = 12; r.run(1)
r.ports[0].mx = 0; r.run(12)
xs = sorted(set(x for x, g in pulsed())); check('pulse follows the paddle', xs == [16 + 16 * 6], (xs, r.r32(COL)))
game(); r.run(4); check('no pulse for a plain pad', pulsed() == [])
game(DEV_MOUSE); r.w8(TUNE + 13, 1); r.run(4); check('pulse off in the patcher', pulsed() == [])

# ---- wheel
game(DEV_WHEEL)
r.ports[0].ax = -32768; r.run(30); a = r.r32(COL)
r.ports[0].ax = 32767; r.run(30); b = r.r32(COL)
r.ports[0].ax = 0; r.run(30); c = r.r32(COL)
check('wheel absolute', (a, b, c) == (0, 6, 3), (a, b, c))

# ---- 3D pad analog
game(DEV_3DPAD)
r.ports[0].ax = -32768; r.run(30); a = r.r32(COL)
r.ports[0].ax = 0; r.run(30); b = r.r32(COL)
r.press(0, ['RIGHT'], 2, 6); c = r.r32(COL)
check('3D pad stick then d-pad', (a, b, c) == (0, 3, 4), (a, b, c))

# ---- JP3 spinner on the d-pad
game()
seq = [set(), {'LEFT'}, {'LEFT', 'RIGHT'}, {'RIGHT'}]
r.ports[0].buttons = {'LEFT', 'RIGHT'}; r.run(2); ph = 2
for i in range(8): ph = (ph + 1) % 4; r.ports[0].buttons = seq[ph]; r.run(1)
r.run(10); a = r.r32(COL)
for i in range(4): ph = (ph - 1) % 4; r.ports[0].buttons = seq[ph]; r.run(1)
r.run(10); b = r.r32(COL)
check('JP3 4 edges per column', (a, b) == (5, 4), (a, b))
check('JP3 lines never reach the game', r.r16(0x60b3d6c) & 0xC000 == 0)

# ---- JP3 spinner on Y (phase A) / Z (phase B)
game()
seq = [set(), {'Y'}, {'Y', 'Z'}, {'Z'}]
r.ports[0].buttons = {'Y', 'Z'}; r.run(2); ph = 2
for i in range(8): ph = (ph + 1) % 4; r.ports[0].buttons = seq[ph]; r.run(1)
r.run(10); a = r.r32(COL)
for i in range(4): ph = (ph - 1) % 4; r.ports[0].buttons = seq[ph]; r.run(1)
r.run(10); b = r.r32(COL)
check('JP3 on Y/Z', (a, b) == (5, 4), (a, b, r.read(PS, 4).hex()))
check('Y/Z never reach the game', r.r16(0x60b3d6c) & 0x0030 == 0)
r.press(0, ['LEFT'], 2, 6); check('d-pad still works with Y/Z spinner', r.r32(COL) == 3, r.r32(COL))
game(DEV_3DPAD)
r.ports[0].buttons = {'Y', 'Z'}; r.run(2); ph = 2
for i in range(8): ph = (ph + 1) % 4; r.ports[0].buttons = seq[ph]; r.run(1)
r.run(10); check('JP3 on Y/Z of a 3D pad', r.r32(COL) == 5, r.r32(COL))

# ---- X as pull-down (flag bit 2)
def cells(): return sum(1 for b in r.read(P1 + 0x337c, 24 * 7) if b != 36)
game(); r.press(0, ['B'], 2, 30); n0 = r.r32(P1 + 0x20)
r.press(0, ['X'], 2, 30); check('X catches by default', r.r32(P1 + 0x20) > n0, (n0, r.r32(P1 + 0x20)))
# with the option, X does exactly what the native pull-down (L) does, and no longer catches
game(); r.w8(TUNE + 13, 3); r.run(60); snap = r.save_state(); c0 = cells()
r.press(0, ['L'], 2, 40); via_l = (cells(), r.r32(P1 + 0x20), bytes(r.read(P1 + 0x337c, 24 * 7)))
r.load_state(snap); r.w8(TUNE + 13, 3 | 4); n0 = r.r32(P1 + 0x20)
r.press(0, ['X'], 2, 40); via_x = (cells(), r.r32(P1 + 0x20), bytes(r.read(P1 + 0x337c, 24 * 7)))
check('X pull-down option', via_l[0] > c0 and via_x == via_l and via_x[1] == n0, (c0, via_l[:2], via_x[:2], n0))
game(); r.press(0, ['L'], 2, 40)

# ---- menus with a paddle-only mouse (spinner): X alone drives every screen
MODE, DEPTH, CUR_ST, CUR_VS, OPT_ROW, OPT_MUSIC = 0x605a434, 0x6087414, 0x6087384, 0x608738c, 0x60873ec, 0x60873e0
MFLG = PS + 9
def menu(dev=DEV_MOUSE, pad=(), port=0):
    """original-disc mode select, optional pad presses to reach a screen, then the device"""
    load(r, 'st_mode.bin'); apply_patch(r)
    for p_ in r.ports: p_.buttons = set(); p_.mbtn = set(); p_.mx = p_.my = 0
    r.set_device(0, DEV_JOYPAD); r.set_device(1, DEV_JOYPAD); r.run(3)
    for b_, w_ in pad: r.press(0, [b_], 3, w_)
    r.set_device(port, dev); r.run(3)
def spin(n, port=0, per=1):
    """move the mouse until the game-visible X has changed by n counts (the core scales
    negative motion, so count what SGL reports rather than what was sent)"""
    lx = PS + 32 * port + 10; x0 = r.r16(lx)
    for i in range(4 * abs(n)):
        if abs(((r.r16(lx) - x0 + 0x8000) & 0xffff) - 0x8000) >= abs(n): break
        r.ports[port].mx = per if n > 0 else -per; r.run(1)
    r.ports[port].mx = 0; r.run(4)
def spin_back(n, port=0, per=1): spin(-n, port, per)

menu()
m0 = r.r32(MODE); spin(60, per=1); m1 = r.r32(MODE)
check('paddle mouse: X walks the vertical mode list', m1 == (m0 + 3) % 5, (m0, m1))
spin_back(40); check('paddle mouse: -X walks back up', r.r32(MODE) == (m1 - 2) % 5, r.r32(MODE))
m2 = r.r32(MODE)
for i in range(20): r.ports[0].my = 2; r.run(1)
r.ports[0].my = 0; r.run(4)
check('paddle mouse: a little Y is ignored', r.r32(MODE) == m2 and r.r8(MFLG) & 1 == 0, (r.r32(MODE), r.r8(MFLG)))
for i in range(30): r.ports[0].my = 2; r.run(1)
r.ports[0].my = 0; r.run(4)
m3 = r.r32(MODE)
check('real mouse: Y motion switches menus to both axes', r.r8(MFLG) & 1 == 1 and m3 != m2, (m2, m3, r.r8(MFLG)))
spin(60); check('real mouse: X is left/right again (mode list unchanged)', r.r32(MODE) == m3, r.r32(MODE))
r.run(30); ps_ = set(); r.ports[0].mbtn = {'LEFT'}
for i in range(4): r.run(1); ps_.add(r.r16(0x60b3d64))
r.ports[0].mbtn = set()
check('mouse left = A in menus', ps_ == {0, 0x0400}, [hex(x) for x in ps_])
menu(); r.w8(TUNE + 13, 9 | 16)
m0 = r.r32(MODE)
for i in range(60): r.ports[0].my = 3; r.run(1)
r.ports[0].my = 0; r.run(4)
check('pure paddle: Y never used', r.r32(MODE) == m0 and r.r8(MFLG) & 1 == 0, (r.r32(MODE), r.r8(MFLG)))
spin(20); check('pure paddle: X still walks the list', r.r32(MODE) == (m0 + 1) % 5, r.r32(MODE))

# story character select: 2 rows (0..6, 7..15) walked in reading order
menu(pad=[('A', 150), ('A', 150)])
cur = []
for i in range(17): spin(20); cur.append(r.r32(CUR_ST))
check('story grid: X walks both rows in reading order', cur == list(range(1, 16)) + [0, 1], cur)
r.w16(PS + 18, 0); spin_back(40); check('story grid: back across the row ends', r.r32(CUR_ST) == 15, r.r32(CUR_ST))
r.w16(PS + 18, 0); spin(6 * 20)                     # 15 -> 0 .. 5, a top-row slot with one below
hop = [r.r32(CUR_ST)]
for i in range(2):
    r.w16(PS + 18, 0); r.ports[0].mbtn = {'MIDDLE'}; r.run(2); spin(20); r.ports[0].mbtn = set(); r.run(4)
    hop.append(r.r32(CUR_ST))
check('story grid: modifier (middle button) hops rows', hop == [hop[0], hop[0] + 8, hop[0]], hop)

# VS character select: P2 on port 2 walks its own cursor
menu(pad=[('DOWN', 30), ('A', 150), ('A', 150)])
r.press(0, ['A'], 3, 60)                       # P1 picks; P2's turn
r.set_device(1, DEV_MOUSE); r.run(3); c0 = r.r32(CUR_VS + 4)
spin(20, port=1); c1 = r.r32(CUR_VS + 4)
check('VS grid: P2 mouse walks P2 cursor across the row end', (c0, c1) == (6, 7), (c0, c1))
r.set_device(1, DEV_JOYPAD)

# puzzle character select is a single row: X sends LEFT/RIGHT there
menu(pad=[('DOWN', 30), ('DOWN', 30), ('A', 150), ('A', 150)])
taps = set()
for i in range(40):
    r.ports[0].mx = 1; r.run(1)
    if r.r16(0x60b3d64): taps.add(r.r16(0x60b3d64))
r.ports[0].mx = 0; r.run(4)
check('puzzle grid (1 row): X sends RIGHT', taps == {0x8000} and r.r32(DEPTH) == 2, ([hex(t) for t in taps], r.r32(DEPTH)))

# options: rows by X, values with B held; B alone still backs out
menu(pad=[('UP', 30), ('A', 150)])
spin(40); row, mus = r.r32(OPT_ROW), r.r32(OPT_MUSIC)
check('options: X picks rows', row == 2, row)
r.ports[0].mbtn = {'RIGHT'}; r.run(3)
spin(20); held_press = r.r16(0x60b3d64)
r.ports[0].mbtn = set(); r.run(10)
check('options: B held + X changes the value, not the row',
      r.r32(OPT_ROW) == 2 and r.r32(OPT_MUSIC) == mus + 1 and r.r32(DEPTH) == 1, (r.r32(OPT_ROW), r.r32(OPT_MUSIC), r.r32(DEPTH)))
r.ports[0].mbtn = {'RIGHT'}; r.run(3); r.ports[0].mbtn = set(); r.run(60)
check('options: B tap (no spin) is delivered on release', r.r32(DEPTH) == 0, r.r32(DEPTH))

# JP3 (Y/Z wiring) on the mode list
menu(dev=DEV_JOYPAD)
seq = [set(), {'Y'}, {'Y', 'Z'}, {'Z'}]
r.ports[0].buttons = {'Y', 'Z'}; r.run(2); ph = 2; m0 = r.r32(MODE)
for i in range(4): ph = (ph + 1) % 4; r.ports[0].buttons = seq[ph]; r.run(2)
r.ports[0].buttons = seq[ph]; r.run(6)
check('JP3: spinner walks the vertical mode list', r.r32(MODE) == (m0 + 2) % 5, (m0, r.r32(MODE)))
r.ports[0].buttons = set()
load(r, 'st_mode.bin'); apply_patch(r); r.set_device(0, DEV_WHEEL); r.run(3)
r.ports[0].ax = -32768; r.run(10)
taps = []
for i in range(30):
    r.ports[0].ax = int(-32768 + i * 1500); r.run(1)
    if r.r16(0x60b3d64): taps.append(r.r16(0x60b3d64))
check('wheel menu taps', len(taps) >= 3 and set(taps) == {0x8000}, [hex(t) for t in taps])

print('\n%d failures' % len(fails), fails)
sys.exit(1 if fails else 0)
