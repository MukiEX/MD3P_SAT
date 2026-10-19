import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from nav import *
cue, pfx = sys.argv[1], sys.argv[2]
r = Retro(cue)
load(r, pfx + 'mode.bin')
r.press(0,['DOWN'],3,30); r.press(0,['A'],3,120); r.press(0,['A'],3,120)
r.press(1,['START'],3,60); r.press(1,['A'],3,120); r.press(0,['A'],3,120); r.press(1,['A'],3,120)
r.press(0,['A'],3,200); r.press(0,['A'],3,200)
r.ports[0].buttons={'A'}; r.ports[1].buttons={'A'}; r.run(3); r.ports[0].buttons=set(); r.ports[1].buttons=set(); r.run(150)
for i in range(5):
    r.press(0,['A'],3,150)
    if st(r)[0]==6: break
for i in range(12):
    r.run(60); print(i, st(r), hex(r.lib.dbg_pc()), flush=True)
r.screenshot('shots/%svs.png' % pfx)
save(r, pfx + 'vs.bin')
