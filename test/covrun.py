"""Accumulate execution coverage over boot + savestates with random input; write work/coverage.bin"""
import sys, os, random; sys.path.insert(0, os.path.dirname(__file__))
from nav import *
import ctypes as C
r = Retro('work/fake.cue')
cov = (C.c_ubyte * 0x80000).in_dll(r.lib, 'dbg_cov')
r.lib.dbg_cov_enable(1)
# boot from scratch
r.run(900); wait_state(r, 4, press=['START'], maxf=3000)
random.seed(1)
BTN = ['A', 'B', 'C', 'X', 'Y', 'Z', 'START', 'UP', 'DOWN', 'LEFT', 'RIGHT', 'L', 'R']
for name in sys.argv[1:]:
    load(r, name)
    for i in range(int(os.environ.get('COVF', '1500')) // 10):
        b = random.choice(BTN + ['A', 'LEFT', 'RIGHT', 'DOWN'])
        if b == 'START' and random.random() < 0.7: b = 'A'
        r.ports[0].buttons = {b}; r.ports[1].buttons = {random.choice(BTN)} if random.random() < .3 else set()
        r.run(4); r.ports[0].buttons = set(); r.ports[1].buttons = set(); r.run(6)
    print(name, 'done', flush=True)
old = bytearray(open('work/coverage.bin', 'rb').read()) if os.path.exists('work/coverage.bin') else bytearray(0x80000)
new = bytes(cov)
open('work/coverage.bin', 'wb').write(bytes(a | b for a, b in zip(old, new)))
