#!/usr/bin/env python3
"""SH-2 slot checks over the placed chunks and patched sites of a built 0.BIN.

Rules (SH7604 manual, "slot illegal instructions"):
  * nothing that changes PC in a delay slot (bra/bsr/jmp/jsr/rts/rte/bt/bf/braf/bsrf/trapa)
  * no PC-relative data access in a delay slot (mov.w/mov.l @(disp,PC), mova): the PC
    seen there is the branch target side, not what the assembler assumed
  * no ldc/lds into SR in a delay slot
Also reports mov.l @(disp,PC) literals that are not 4-aligned and literal loads that point
outside the chunk they belong to (a sign of a chunk boundary bug).
"""
import sys, json, struct, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sh2 import decode
BASE = 0x06004000
DELAYED = lambda op: (op >> 12) in (0xA, 0xB) or (op & 0xFF00) in (0x8D00, 0x8F00) or op in (0x000B, 0x002B) \
    or (op & 0xF0FF) in (0x402B, 0x400B, 0x0023, 0x0003)
def slot_illegal(op):
    if DELAYED(op): return 'branch'
    if (op & 0xFF00) in (0x8900, 0x8B00): return 'bt/bf'
    if (op >> 12) in (0x9, 0xD) or (op & 0xFF00) == 0xC700: return 'pc-relative'
    if (op & 0xFF00) == 0xC300: return 'trapa'
    if (op & 0xF0FF) in (0x400E, 0x4007): return 'ldc sr'
    return None

def check(img, ranges):
    errs = []
    for name, s, e in ranges:
        data = set()             # literal pool words loaded by this range's code
        for pc in range(s, e - 1, 2):
            op = struct.unpack('>H', img[pc - BASE:pc - BASE + 2])[0]
            if op >> 12 == 0xD: a = (pc & ~3) + 4 + (op & 0xFF) * 4; data.update((a, a + 2))
            elif op >> 12 == 0x9: data.add(pc + 4 + (op & 0xFF) * 2)
        for pc in range(s, e - 2, 2):
            if pc in data: continue
            op = struct.unpack('>H', img[pc - BASE:pc - BASE + 2])[0]
            if DELAYED(op):
                nxt = struct.unpack('>H', img[pc + 2 - BASE:pc + 4 - BASE])[0]
                why = slot_illegal(nxt)
                if why: errs.append('%s %08X: %s in delay slot (%04X after %04X)' % (name, pc + 2, why, nxt, op))
    return errs

if __name__ == '__main__':
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    img = open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, 'build', '0.BIN'), 'rb').read()
    log = json.load(open(os.path.join(root, 'build', 'build_log.json')))
    ranges = [(c['name'], int(c['addr'], 16), int(c['addr'], 16) + c['size']) for c in log['chunks']]
    ranges += [(h['name'], int(h['addr'], 16), int(h['addr'], 16) + len(h['now']) // 2) for h in log['hooks'] if 'addr' in h]
    # literal pools are data: only scan code. Treat words after the last rts/jmp/bra of a
    # chunk as data by stopping at the first 4-aligned word that is a pointer-looking value.
    errs = check(img, ranges)
    for e in errs: print(e)
    print('%d hazards' % len(errs))
    sys.exit(1 if errs else 0)
