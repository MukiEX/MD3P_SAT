import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from retro import *
from montage import montage
W = os.path.join(os.path.dirname(__file__), '..', 'work')
def st(r): return (r.r32(0x608de74), r.r32(0x60b2ac0))
def wait_state(r, s, maxf=2000, press=None):
    f = 0
    while st(r)[0] != s and f < maxf:
        if press and f % 40 == 0: r.press(0, press, 3, 0)
        r.run(5); f += 5
        if r.r32(0x608b4fc) == 0 and st(r)[0] == 3: r.w32(0x608b4fc, 1)
    return st(r)[0] == s
def load(r, name): r.load_state(open(os.path.join(W, name), 'rb').read())
def save(r, name): open(os.path.join(W, name), 'wb').write(r.save_state())
import numpy as np
def find_counter(r, action, n=3, width=4, rng=(0x06080000, 0x06100000)):
    def snap():
        fmt = {4: '>i4', 2: '>i2', 1: 'i1'}[width]
        return np.frombuffer(r.read(rng[0], rng[1] - rng[0]), dtype=fmt).astype(np.int64)
    s = [snap()]
    for i in range(n): action(); s.append(snap())
    d = [s[i + 1] - s[i] for i in range(n)]
    m = np.ones_like(d[0], dtype=bool)
    for x in d[1:]: m &= (x == d[0])
    m &= (d[0] != 0) & (np.abs(d[0]) < 4)
    return [(hex(rng[0] + width * i), [int(x[i]) for x in s]) for i in np.nonzero(m)[0]]

def apply_patch(r, path=os.path.join(W, '..', 'build', '0.BIN')):
    """Write the patched 0.BIN differences into RAM (for savestates made from the original)."""
    new = open(path, 'rb').read(); old = open(os.path.join(W, '0.BIN'), 'rb').read()
    i = 0; n = 0
    while i < len(new):
        if new[i] != old[i]:
            j = i
            while j < len(new) and (new[j] != old[j] or (j + 8 < len(new) and new[j:j+8] != old[j:j+8])): j += 1
            r.write(0x06004000 + i, new[i:j]); n += j - i; i = j
        else: i += 1
    return n

def syms():
    d = {}
    for ln in open(os.path.join(W, '..', 'build', 'symbols.txt')):
        a, n = ln.split(); d[n] = int(a, 16)
    return d
