import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tester', 'build')
from retro import Retro
r=Retro(os.path.join(T, 'Saturn Input Tester.cue'))
r.run(200)
import subprocess
ST=0x06004000+int([l for l in subprocess.check_output([os.environ.get('SH_PREFIX','sh-elf-')+'objdump','-t',os.path.join(T,'tester.o')]).decode().splitlines() if l.endswith(' state')][0].split()[0],16)
a=r.r16(ST); r.run(60); b=r.r16(ST); print('sweep per 60 frames', (b-a)%264)
r.ports[0].buttons={'Y','Z'}; r.run(10); r.ports[0].buttons=set(); r.run(3)
print('yz count', r.r16(ST+6)); assert r.r16(ST+6) == 10
r.ports[0].buttons={'LEFT','RIGHT'}; r.run(10); print('lr', r.r16(ST+4)); assert r.r16(ST+4) == 10
r.ports[0].buttons={'A','B','C','START'}; r.run(3); r.ports[0].buttons=set(); r.run(2)
print('after reset', r.r16(ST+4), r.r16(ST+6))
assert (b - a) % 264 == 60, 'tester loop must advance one column per frame'
assert r.r16(ST + 4) == 0 and r.r16(ST + 6) == 0
print('tester ok')
