#!/usr/bin/env python3
"""Build the Saturn paddle patch into 0.BIN.

1. Split src/*.s into chunks ('!@chunk name'); the text before the first chunk is a header
   included in every chunk.
2. Assemble each chunk with gas at offset 0 (foreign global labels as .equ 0) to measure it.
3. Pack chunks into proven free space (static reachability + emulator coverage), 4-aligned,
   best fit largest first, backtracking if that fails.
4. Re-assemble with every foreign label defined absolutely; refuse any relocation.
5. Write chunks + hook patches into a copy of 0.BIN, verifying original bytes first.
"""
import os, re, sys, json, struct, subprocess, tempfile, argparse
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
SH = os.environ.get('SH_PREFIX', 'sh-elf-')   # binutils for SH (gas, objcopy, objdump)
AS = SH + 'as'; OBJCOPY = SH + 'objcopy'; OBJDUMP = SH + 'objdump'
BASE = 0x06004000

def split_chunks(src):
    lines = open(src).read().split('\n')
    header = []; chunks = []; cur = None
    for ln in lines:
        m = re.match(r'^!@chunk\s+(\w+)', ln)
        if m:
            cur = dict(name=m.group(1), lines=[]); chunks.append(cur); continue
        (cur['lines'] if cur else header).append(ln)
    for c in chunks:
        c['labels'] = [m.group(1) for ln in c['lines'] for m in [re.match(r'^([A-Za-z_]\w*):', ln)] if m]
    return '\n'.join(header), chunks

def assemble(header, chunk, syms, tmp):
    own = set(chunk['labels'])
    eq = '\n'.join('\t.equ\t%s, 0x%08X' % (k, v) for k, v in syms.items() if k not in own)
    src = header + '\n' + eq + '\n\t.text\n' + '\n'.join(chunk['lines']) + '\n'
    s = os.path.join(tmp, chunk['name'] + '.s'); o = s[:-2] + '.o'; b = s[:-2] + '.bin'
    open(s, 'w').write(src)
    r = subprocess.run([AS, '-big', '--isa=sh2', '-o', o, s], capture_output=True, text=True)
    if r.returncode: sys.exit('assembler failed for %s:\n%s' % (chunk['name'], r.stderr))
    rel = subprocess.run([OBJDUMP, '-r', o], capture_output=True, text=True).stdout
    relocs = [ln for ln in rel.split('\n') if re.match(r'^[0-9a-f]{8} ', ln)]
    subprocess.run([OBJCOPY, '-O', 'binary', '-j', '.text', o, b], check=True)
    data = open(b, 'rb').read() if os.path.exists(b) else b''
    nm = subprocess.run([OBJDUMP, '-t', o], capture_output=True, text=True).stdout
    offs = {}
    for ln in nm.split('\n'):
        p = ln.split()
        if len(p) >= 5 and p[-2] != '*ABS*' and '.text' in ln and p[-1] in own:
            offs[p[-1]] = int(p[0], 16)
    return data, relocs, offs

def free_space(args):
    free = json.load(open(os.path.join(ROOT, 'data', 'free_valid.json')))
    cov = open(os.path.join(ROOT, 'data', 'coverage.bin'), 'rb').read() if os.path.exists(os.path.join(ROOT, 'data', 'coverage.bin')) else None
    holes = []
    for f in free:
        s, e = f['start'], f['end']
        if cov is not None:
            hit = [a for a in range(s, e, 2) if cov[(a - 0x06000000) >> 1]]
            if hit:
                print('  hole %08X-%08X executed at %08X: dropped' % (s, e, hit[0])); continue
        s = (s + 3) & ~3
        if e - s >= 8: holes.append([s, e])
    return holes

def pack(chunks, holes):
    order = sorted(chunks, key=lambda c: -c['size'])
    holes = sorted(holes, key=lambda h: h[1] - h[0])
    place = {}
    def rec(i, hs):
        if i == len(order): return True
        c = order[i]; sz = (c['size'] + 3) & ~3
        tried = set()
        for j, (s, e) in enumerate(sorted(hs, key=lambda h: h[1] - h[0])):
            if e - s >= sz and (e - s) not in tried:
                tried.add(e - s)
                hs2 = [h for h in hs if h != [s, e]] + ([[s + sz, e]] if e - s - sz >= 8 else [])
                place[c['name']] = s
                if rec(i + 1, hs2): return True
        return False
    if not rec(0, holes): sys.exit('packing failed')
    return place

# ---------------------------------------------------------------- hooks
def lit_users(img, lit):
    """addresses of mov.l @(disp,PC) instructions that load the literal at lit"""
    out = []
    for pc in range(max(BASE, lit - 1024), lit, 2):
        op = struct.unpack('>H', img[pc - BASE:pc - BASE + 2])[0]
        if op >> 12 == 0xD and ((pc & ~3) + 4 + (op & 0xFF) * 4) == lit: out.append(pc)
    return out

HOOKS = [
    # (name, literal address, original value, new symbol, expected loader pc)
    ('PadRead', 0x06020468, 0x06020998, 'pad_read', 0x0602042A),
    ('ClownInput', 0x06010FB8, 0x0600E208, 'paddle_tick', 0x06010E76),
    ('SpriteEmit', 0x0601FEBC, 0x0604F88C, 'pulse_emit', 0x0601FE86),
]

# inline draw-site patches: (name, addr, original hex, new words; '@sym' = 32-bit symbol)
SITES = [
    ('GlideAim', 0x06004C30, '52b6d14150b442081e096023011e50e9', ['50b4', '1e09', 'd101', '410b', '0009', '0009', '@glide_tab']),
    ('GlideClownA', 0x06004D8E, '51b650b45cb54108410871f84128301c', ['50b4', '5cb5', 'd101', '410b', '0009', '@glide_add_m8', '0009']),
    ('GlideClownB', 0x06004F40, '51b6d33e50b4412841084108' + '5cb5301c', ['d33e', '50b4', '5cb5', 'd101', '410b', '0009', '@glide_add0']),
    ('GlideClownC', 0x0600535A, '51b65cb54108410871f84128301c', ['5cb5', 'd101', '410b', '0009', '0009', '@glide_add_m8']),
]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default=os.path.join(ROOT, 'src', 'md3sat_paddle.s'))
    ap.add_argument('--in', dest='inp', default=os.path.join(ROOT, 'work', '0.BIN'))
    ap.add_argument('--out', default=os.path.join(ROOT, 'build', '0.BIN'))
    ap.add_argument('--equ', action='append', default=[])
    args = ap.parse_args()
    header, chunks = split_chunks(args.src)
    for e in args.equ:
        k, v = e.split('='); header = '\t.equ\t%s, %s\n' % (k, v) + header
    allsyms = {l: 0x06000000 for c in chunks for l in c['labels']}
    with tempfile.TemporaryDirectory() as tmp:
        for c in chunks:
            data, rel, offs = assemble(header, c, allsyms, tmp)
            c['size'] = len(data)
        holes = free_space(args)
        print('free: %d holes, %d bytes; code: %d bytes in %d chunks' % (len(holes), sum(e - s for s, e in holes), sum(c['size'] for c in chunks), len(chunks)))
        place = pack(chunks, holes)
        syms = {}
        for c in chunks:
            _, _, offs = assemble(header, c, allsyms, tmp)
            for l, o in offs.items(): syms[l] = place[c['name']] + o
        img = bytearray(open(args.inp, 'rb').read())
        log = dict(chunks=[], hooks=[], symbols={k: '%08X' % v for k, v in sorted(syms.items(), key=lambda x: x[1])})
        for c in chunks:
            data, rel, offs = assemble(header, c, syms, tmp)
            if rel: sys.exit('relocations left in %s:\n%s' % (c['name'], '\n'.join(rel)))
            assert len(data) == c['size']
            a = place[c['name']]
            img[a - BASE:a - BASE + len(data)] = data
            log['chunks'].append(dict(name=c['name'], addr='%08X' % a, size=len(data)))
            print('  %-10s %08X %4d' % (c['name'], a, len(data)))
        for name, lit, orig, sym, loader in HOOKS:
            cur = struct.unpack('>I', img[lit - BASE:lit - BASE + 4])[0]
            if cur != orig: sys.exit('hook %s: literal %08X holds %08X, expected %08X' % (name, lit, cur, orig))
            users = lit_users(img, lit)
            if users != [loader]: sys.exit('hook %s: literal used by %s' % (name, [hex(u) for u in users]))
            img[lit - BASE:lit - BASE + 4] = struct.pack('>I', syms[sym])
            log['hooks'].append(dict(name=name, literal='%08X' % lit, was='%08X' % orig, now='%08X' % syms[sym]))
        for name, addr, orig, words in SITES:
            o = addr - BASE; ob = bytes.fromhex(orig)
            if bytes(img[o:o + len(ob)]) != ob: sys.exit('site %s: original bytes differ' % name)
            nb = b''.join(struct.pack('>I', syms[w[1:]]) if w.startswith('@') else bytes.fromhex(w) for w in words)
            assert len(nb) == len(ob), name
            for i, w in enumerate(words):
                pass
            img[o:o + len(nb)] = nb
            log['hooks'].append(dict(name=name, addr='%08X' % addr, was=orig, now=nb.hex()))
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        open(args.out, 'wb').write(img)
        json.dump(log, open(os.path.join(os.path.dirname(args.out), 'build_log.json'), 'w'), indent=1)
        with open(os.path.join(os.path.dirname(args.out), 'symbols.txt'), 'w') as f:
            for k, v in sorted(syms.items(), key=lambda x: x[1]): f.write('%08X %s\n' % (v, k))
    print('wrote', args.out)

if __name__ == '__main__':
    main()
