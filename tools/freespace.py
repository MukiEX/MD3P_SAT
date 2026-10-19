"""Static reachability over 0.BIN: find unreachable functions usable as free space.

Roots: entry point + every aligned 32-bit word in the image that points into the image
(conservative: any pointer-looking value may be a function pointer).
Flood-fill follows branches, calls, fall-through and switch tables. Literal pool words and
mova tables touched by reached code are marked as used data.
Free = runs not reached, starting at a function prologue, nothing points inside them from
outside, and at least MINLEN bytes.
"""
import sys, struct, json
sys.path.insert(0, __import__('os').path.dirname(__file__))
from sh2 import Image, decode, plausible, is_prologue

BASE = 0x06004000
MINLEN = 0x40

def analyse(data, extra_roots=(), extra_used=()):
    img = Image(data, BASE)
    n = len(data)
    used = bytearray(n)          # 1 = reached code, 2 = data used by code
    ptrs = {}
    for o in range(0, n - 3, 2):
        v = struct.unpack('>I', data[o:o + 4])[0]
        if BASE <= v < BASE + n:
            ptrs.setdefault(v, []).append(BASE + o)
    roots = [BASE] + [a for a in ptrs if a % 2 == 0] + list(extra_roots)
    work = list(roots); seen = set()
    while work:
        pc = work.pop()
        if pc in seen or not img.inside(pc) or pc & 1: continue
        while img.inside(pc):
            if pc in seen and used[pc - BASE] == 1: break
            seen.add(pc)
            op = img.u16(pc)
            if not plausible(op): break
            used[pc - BASE] = used[pc - BASE + 1] = 1
            kind, info, x = decode(op, pc)
            stop = False
            if kind in ('bra', 'bsr', 'bcc'):
                work.append(info)
                if kind == 'bra': stop = True
            elif kind in ('ret', 'jmp', 'braf'):
                stop = True
            elif kind == 'lit32':
                if img.inside(info + 3):
                    for k in range(4): used[info - BASE + k] |= 2
            elif kind == 'lit16':
                if img.inside(info + 1):
                    for k in range(2): used[info - BASE + k] |= 2
            elif kind == 'mova':
                t = info; mn = 1 << 32; pos = t
                while img.inside(pos + 1) and pos < mn and pos - t < 0x200:
                    e = img.u16(pos); e = e - 0x10000 if e & 0x8000 else e
                    tgt = t + e
                    if not img.inside(tgt) or tgt & 1: break
                    used[pos - BASE] |= 2; used[pos - BASE + 1] |= 2
                    work.append(tgt); mn = min(mn, tgt); pos += 2
            if stop:
                # delay slot
                dpc = pc + 2
                if img.inside(dpc):
                    used[dpc - BASE] = used[dpc - BASE + 1] = 1
                    dk, di, dx = decode(img.u16(dpc), dpc)
                    if dk == 'lit32' and img.inside(di + 3):
                        for k in range(4): used[di - BASE + k] |= 2
                break
            pc += 2
    for a in extra_used:
        used[a - BASE] |= 2
    # gaps
    runs = []; o = 0
    while o < n:
        if used[o] == 0:
            s = o
            while o < n and used[o] == 0: o += 1
            runs.append((BASE + s, BASE + o))
        else: o += 1
    free = []
    for s, e in runs:
        # align start to first prologue in run
        a = s + (s & 1)
        while a < e - 1 and not is_prologue(img.u16(a)): a += 2
        if e - a < MINLEN: continue
        # anything pointing inside from outside?
        inbound = [(t, src) for t in range(a, e) for src in ptrs.get(t, []) if not (a <= src < e)]
        free.append(dict(start=a, end=e, size=e - a, inbound=[(hex(t), hex(src)) for t, src in inbound][:5]))
    return used, free

if __name__ == '__main__' and sys.argv[1:2] != ['--valid']:
    data = open(sys.argv[1], 'rb').read()
    used, free = analyse(data)
    tot = 0
    for f in free:
        flag = '' if not f['inbound'] else ' INBOUND ' + str(f['inbound'])
        print('%08X-%08X %5X%s' % (f['start'], f['end'], f['size'], flag))
        if not f['inbound']: tot += f['size']
    print('total clean free: %X (%d)' % (tot, tot))
    json.dump(free, open(sys.argv[2], 'w'), indent=1) if len(sys.argv) > 2 else None

def validate_run(data, s, e):
    """Flood-fill from every prologue inside [s,e) treating the run as code. Returns fraction
    of run bytes explained by code+literals, and whether anything escaped the run or was implausible."""
    img = Image(data, BASE)
    cov = bytearray(e - s); bad = []
    starts = [a for a in range(s, e - 1, 2) if (img.u16(a) & 0xF00F) == 0x2F06 or img.u16(a) == 0x4F22]
    work = list(starts[:1]); seen = set()
    while work:
        pc = work.pop()
        if pc in seen: continue
        if not (s <= pc < e): bad.append(('escape', hex(pc))); continue
        while s <= pc < e:
            if pc in seen: break
            seen.add(pc); op = img.u16(pc)
            if not plausible(op): bad.append(('implausible', hex(pc))); break
            cov[pc - s] = cov[pc - s + 1] = 1
            kind, info, x = decode(op, pc)
            if kind in ('bra', 'bsr', 'bcc'):
                if kind == 'bsr':
                    if not img.inside(info): bad.append(('bsr-out', hex(pc)))
                else: work.append(info)
                if kind == 'bra': cov[pc + 2 - s:pc + 4 - s] = b'\1\1'; work.append(pc + 2) if False else None; 
                if kind == 'bra':
                    dpc = pc + 2; op2 = img.u16(dpc); k2, i2, _ = decode(op2, dpc)
                    if k2 == 'lit32' and s <= i2 < e: cov[i2 - s:i2 - s + 4] = b'\1' * 4
                    break
            elif kind in ('ret', 'jmp', 'braf'):
                cov[pc + 2 - s:pc + 4 - s] = b'\1\1'
                dpc = pc + 2; op2 = img.u16(dpc); k2, i2, _ = decode(op2, dpc)
                if k2 == 'lit32' and s <= i2 < e: cov[i2 - s:i2 - s + 4] = b'\1' * 4
                break
            elif kind == 'lit32':
                if s <= info < e: cov[info - s:info - s + 4] = b'\1' * 4
                else: bad.append(('lit-out', hex(pc)))
            elif kind == 'lit16':
                if s <= info < e: cov[info - s:info - s + 2] = b'\1' * 2
                else: bad.append(('lit-out', hex(pc)))
            elif kind == 'mova':
                bad.append(('mova', hex(pc)))
            pc += 2
        # next function after this one
        if not work:
            nxt = [a for a in starts if a not in seen and not cov[a - s]]
            if nxt: work.append(nxt[0])
    # zero padding counts as explained
    expl = sum(1 for i in range(e - s) if cov[i] or (data[s - BASE + i] == 0))
    return expl / (e - s), bad

def main_valid(binpath, out):
    data = open(binpath, 'rb').read()
    used, free = analyse(data)
    good = [f for f in free if not f['inbound'] and (lambda fr_bad: fr_bad[0] > 0.85 and not fr_bad[1])(validate_run(data, f['start'], f['end']))]
    json.dump(good, open(out, 'w'), indent=1)
    print('%d holes, %d bytes -> %s' % (len(good), sum(f['size'] for f in good), out))

if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == '--valid':
    main_valid(sys.argv[2], sys.argv[3])
