"""Build savestates from a clean boot of the patched disc (build/fake.cue)."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from nav import *
CUE = os.environ.get('CUE', 'build/fake.cue'); PFX = os.environ.get('PFX', 'p_')
os.makedirs('shots', exist_ok=True)
r = Retro(CUE)
r.run(900)
assert wait_state(r, 4, press=['START'], maxf=4000); r.run(120); save(r, PFX + 'title.bin')
r.press(0, ['START'], 3, 0); assert wait_state(r, 5); r.run(200); save(r, PFX + 'mode.bin')
r.screenshot('shots/%smode.png' % PFX)
# endless (puzzle) mode
for i in range(2): r.press(0, ['DOWN'], 3, 30)
r.press(0, ['A'], 3, 120); r.screenshot('shots/%send1.png' % PFX)
r.press(0, ['A'], 3, 120); r.screenshot('shots/%send2.png' % PFX)
r.press(0, ['A'], 3, 200); r.screenshot('shots/%send3.png' % PFX)
r.press(0, ['A'], 3, 200); r.screenshot('shots/%send4.png' % PFX)
save(r, PFX + 'endless.bin')
print('state', st(r))
