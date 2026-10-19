import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tester', 'build')
from retro import Retro, SAT
r=Retro(os.path.join(T, 'Saturn Input Tester.cue'))
r.run(300)
print('pc %08X'%r.lib.dbg_pc())
r.screenshot(os.path.join(T, 's0.png'))
r.ports[0].buttons={'LEFT','A','Y'}
r.ports[1].buttons={'R','START'}
r.run(20)
r.ports[0].buttons={'LEFT','RIGHT','Y','Z'}
r.run(10)
r.ports[0].buttons=set(); r.run(10)
for i in range(6):
  r.ports[0].buttons={'LEFT'} if i%2==0 else {'RIGHT'}; r.run(5)
r.ports[0].buttons={'LEFT','Z'}; r.ports[1].buttons={'X','B','UP'}
r.run(8)
r.screenshot(os.path.join(T, 's1.png'))
print([hex(r.r8(0x20100021+2*i)) for i in range(10)])
from retro import DEV_3DPAD, DEV_MOUSE
r.set_device(1, DEV_3DPAD); r.ports[1].buttons={'C','DOWN'}; r.ports[1].ax=12000
r.run(30); r.screenshot(os.path.join(T, 's2.png'))
r.set_device(1, DEV_MOUSE); r.ports[1].buttons=set(); r.run(30); r.screenshot(os.path.join(T, 's3.png'))
