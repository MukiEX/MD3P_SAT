#!/usr/bin/env python3
"""CHD v5 CD-ROM writer/reader (test fixtures + verification for the browser patcher).

Writer mimics chdman: 8-frame hunks (19584 bytes), codecs cdlz/cdzl/cdfl (smallest wins),
identical hunks become SELF references, Huffman+RLE compressed map, CHT2 metadata,
raw and overall SHA-1. Audio is stored big-endian like chdman.
"""
import sys, os, struct, zlib, lzma, hashlib, ctypes as C, heapq
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdsec import _ecc_block

FRAME = 2448; SECTOR = 2352; SUB = 96; HUNKFRAMES = 8; HUNKBYTES = FRAME * HUNKFRAMES
CT0, CT1, CT2, CT3, NONE, SELF, PARENT, RLE_S, RLE_L, SELF0, SELF1, PSELF, P0, P1 = range(14)
SYNC = bytes([0] + [0xFF] * 10 + [0])

CRC16T = []
for i in range(256):
    c = i << 8
    for _ in range(8): c = ((c << 1) ^ 0x1021) & 0xFFFF if c & 0x8000 else (c << 1) & 0xFFFF
    CRC16T.append(c)
def crc16(b):
    c = 0xFFFF
    for x in b: c = ((c << 8) & 0xFFFF) ^ CRC16T[(c >> 8) ^ x]
    return c

# ------------------------------------------------------------ bit io
class BitW:
    def __init__(s): s.out = bytearray(); s.acc = 0; s.n = 0
    def write(s, v, bits):
        for i in range(bits - 1, -1, -1):
            s.acc = (s.acc << 1) | ((v >> i) & 1); s.n += 1
            if s.n == 8: s.out.append(s.acc); s.acc = 0; s.n = 0
    def flush(s):
        if s.n: s.out.append(s.acc << (8 - s.n)); s.acc = 0; s.n = 0
        return bytes(s.out)
class BitR:
    def __init__(s, b): s.b = b; s.pos = 0
    def read(s, bits):
        v = 0
        for _ in range(bits):
            byte = s.b[s.pos >> 3] if (s.pos >> 3) < len(s.b) else 0
            v = (v << 1) | ((byte >> (7 - (s.pos & 7))) & 1); s.pos += 1
        return v

# ------------------------------------------------------------ huffman (16 codes, max 8 bits)
def huff_lengths(hist, maxbits=8):
    h = list(hist)
    while True:
        heap = [(f, i, (i,)) for i, f in enumerate(h) if f]
        if len(heap) == 1: L = [0] * len(h); L[heap[0][1]] = 1; return L
        heapq.heapify(heap); L = [0] * len(h); cnt = len(h)
        while len(heap) > 1:
            a = heapq.heappop(heap); b = heapq.heappop(heap)
            for i in a[2] + b[2]: L[i] += 1
            heapq.heappush(heap, (a[0] + b[0], cnt, a[2] + b[2])); cnt += 1
        if max(L) <= maxbits: return L
        h = [(f + 1) // 2 if f else 0 for f in h]   # flatten and retry
def canonical(L):
    histo = [0] * 33
    for l in L:
        if l: histo[l] += 1
    cur = 0
    for ln in range(32, 0, -1):
        nxt = (cur + histo[ln]) >> 1; histo[ln] = cur; cur = nxt
    codes = [0] * len(L)
    for i, l in enumerate(L):
        if l: codes[i] = histo[l]; histo[l] += 1
    return codes
def export_tree_rle(bw, L, numbits=4):
    def wr(val, rep):
        while rep > 0:
            if val == 1: bw.write(1, numbits); bw.write(1, numbits); rep -= 1
            elif rep <= 2: bw.write(val, numbits); rep -= 1
            else:
                cur = min(rep - 3, (1 << numbits) - 1)
                bw.write(1, numbits); bw.write(val, numbits); bw.write(cur, numbits); rep -= cur + 3
    last = None; rep = 0
    for l in L:
        if l == last: rep += 1
        else:
            if rep: wr(last, rep)
            last = l; rep = 1
    wr(last, rep)
def import_tree_rle(br, n=16, numbits=4):
    L = [];
    while len(L) < n:
        v = br.read(numbits)
        if v != 1: L.append(v)
        else:
            v = br.read(numbits)
            if v == 1: L.append(1)
            else:
                rep = br.read(numbits) + 3; L += [v] * rep
    return L[:n]

# ------------------------------------------------------------ ECC (mode 1)
def ecc_compute(sec):
    t = bytearray(sec); _ecc_block(t, 86, 24, 2, 86, 0x81C); _ecc_block(t, 52, 43, 86, 88, 0x8C8)
    return bytes(t[0x81C:0x930])
def ecc_ok(sec): return sec[:12] == SYNC and sec[15] == 1 and ecc_compute(sec) == sec[0x81C:0x930]

# ------------------------------------------------------------ FLAC (libFLAC via ctypes)
FLAC_LIB = os.environ.get('LIBFLAC', 'libFLAC.so')
_flac = None
WRITE_CB = C.CFUNCTYPE(C.c_int, C.c_void_p, C.POINTER(C.c_ubyte), C.c_size_t, C.c_uint, C.c_uint, C.c_void_p)
def flac_encode(samples_be, blocksize):
    """samples_be: bytes of interleaved stereo int16 BE. Returns raw FLAC frames (no header)."""
    global _flac
    if _flac is None: _flac = C.CDLL(FLAC_LIB)
    f = _flac; f.FLAC__stream_encoder_new.restype = C.c_void_p
    enc = f.FLAC__stream_encoder_new()
    for fn, v in (('channels', 2), ('bits_per_sample', 16), ('sample_rate', 44100), ('blocksize', blocksize), ('compression_level', 8)):
        getattr(f, 'FLAC__stream_encoder_set_' + fn).argtypes = [C.c_void_p, C.c_uint]
        getattr(f, 'FLAC__stream_encoder_set_' + fn)(enc, v)
    f.FLAC__stream_encoder_set_streamable_subset.argtypes = [C.c_void_p, C.c_int]
    f.FLAC__stream_encoder_set_streamable_subset(enc, 0)
    out = bytearray()
    def wcb(e, buf, n, samples, frame, cd):
        if samples: out.extend(C.string_at(buf, n))
        return 0
    cb = WRITE_CB(wcb)
    f.FLAC__stream_encoder_init_stream.argtypes = [C.c_void_p, WRITE_CB, C.c_void_p, C.c_void_p, C.c_void_p, C.c_void_p]
    assert f.FLAC__stream_encoder_init_stream(enc, cb, None, None, None, None) == 0
    n = len(samples_be) // 2
    arr = (C.c_int32 * n)(*struct.unpack('>%dh' % n, samples_be))
    f.FLAC__stream_encoder_process_interleaved.argtypes = [C.c_void_p, C.c_void_p, C.c_uint]
    assert f.FLAC__stream_encoder_process_interleaved(enc, arr, n // 2)
    f.FLAC__stream_encoder_finish.argtypes = [C.c_void_p]; f.FLAC__stream_encoder_finish(enc)
    f.FLAC__stream_encoder_delete.argtypes = [C.c_void_p]; f.FLAC__stream_encoder_delete(enc)
    return bytes(out)
def flac_blocksize(nbytes):
    b = nbytes // 4
    while b > 2048: b //= 2
    return b

# ------------------------------------------------------------ codecs
def lzma_raw(data):
    return lzma.compress(data, format=lzma.FORMAT_RAW, filters=[{'id': lzma.FILTER_LZMA1, 'lc': 3, 'lp': 0, 'pb': 2, 'dict_size': 1 << 16, 'preset': 9}])
def deflate_raw(data):
    c = zlib.compressobj(9, zlib.DEFLATED, -15); return c.compress(data) + c.flush()

def compress_cd(hunk, use=('cdlz', 'cdzl', 'cdfl')):
    frames = len(hunk) // FRAME
    sectors = bytearray(); subs = bytearray(); ecc = bytearray((frames + 7) // 8)
    for f in range(frames):
        sec = bytearray(hunk[f * FRAME:f * FRAME + SECTOR])
        if ecc_ok(sec):
            ecc[f // 8] |= 1 << (f % 8)
            sec[:12] = b'\0' * 12; sec[0x81C:0x930] = b'\0' * 276
        sectors += sec; subs += hunk[f * FRAME + SECTOR:(f + 1) * FRAME]
    cands = {}
    cb = 2 if len(hunk) < 65536 else 3
    subz = deflate_raw(bytes(subs))
    for name, fn in (('cdlz', lzma_raw), ('cdzl', deflate_raw)):
        if name not in use: continue
        base = fn(bytes(sectors))
        cands[name] = bytes(ecc) + len(base).to_bytes(cb, 'big') + base + subz
    if 'cdfl' in use:
        raw = b''.join(hunk[f * FRAME:f * FRAME + SECTOR] for f in range(frames))
        cands['cdfl'] = flac_encode(raw, flac_blocksize(frames * SECTOR)) + subz
    best = min(cands, key=lambda k: len(cands[k]))
    return best, cands[best]

# ------------------------------------------------------------ writer
def write_chd(path, tracks, codecs=('cdlz', 'cdzl', 'cdfl'), force=None):
    """tracks: list of dict(type='MODE1_RAW'|'AUDIO', data=bytes (2352/frame, audio little endian))"""
    logical = bytearray(); meta = []
    for i, t in enumerate(tracks):
        frames = len(t['data']) // SECTOR
        for f in range(frames):
            sec = t['data'][f * SECTOR:(f + 1) * SECTOR]
            if t['type'] == 'AUDIO':
                a = bytearray(sec); a[0::2], a[1::2] = sec[1::2], sec[0::2]; sec = bytes(a)
            logical += sec + b'\0' * SUB
        pad = (-frames) % 4
        logical += b'\0' * (FRAME * pad)
        meta.append(('TRACK:%d TYPE:%s SUBTYPE:NONE FRAMES:%d PREGAP:%d PGTYPE:%s PGSUB:RW_RAW POSTGAP:0' %
                     (i + 1, t['type'], frames, t.get('pregap', 0), 'VAUDIO' if t['type'] == 'AUDIO' else 'MODE1')).encode() + b'\0')
    logicalbytes = len(logical)
    logical += b'\0' * ((-len(logical)) % HUNKBYTES)
    nh = len(logical) // HUNKBYTES
    tags = [b'cdlz', b'cdzl', b'cdfl']
    entries = []; blobs = []; seen = {}
    for h in range(nh):
        hd = bytes(logical[h * HUNKBYTES:(h + 1) * HUNKBYTES]); crc = crc16(hd)
        if hd in seen: entries.append((SELF, 0, seen[hd], 0)); continue
        seen[hd] = h
        if force and h in force:
            if force[h] == 'none': entries.append((NONE, HUNKBYTES, 0, crc)); blobs.append(hd); continue
            name, blob = compress_cd(hd, (force[h],))
        else:
            name, blob = compress_cd(hd, codecs)
        if len(blob) >= HUNKBYTES: entries.append((NONE, HUNKBYTES, 0, crc)); blobs.append(hd)
        else: entries.append((tags.index(name.encode()), len(blob), 0, crc)); blobs.append(blob)
    # layout: header, metadata, hunks, map
    hdr_len = 124
    metabin = bytearray(); mpos = hdr_len
    for i, m in enumerate(meta):
        nxt = 0 if i == len(meta) - 1 else mpos + 16 + len(m)
        metabin += b'CHT2' + struct.pack('>I', (0x01 << 24) | len(m)) + struct.pack('>Q', nxt) + m
        mpos += 16 + len(m)
    firstoffs = hdr_len + len(metabin)
    # raw map with real offsets
    raw = bytearray(); cur = firstoffs; bi = 0
    for (t, ln, ref, crc) in entries:
        if t in (CT0, CT1, CT2, CT3, NONE): raw += bytes([t]) + ln.to_bytes(3, 'big') + cur.to_bytes(6, 'big') + crc.to_bytes(2, 'big'); cur += ln
        else: raw += bytes([t]) + b'\0\0\0' + ref.to_bytes(6, 'big') + b'\0\0'
    mapbin = compress_map(raw, nh, firstoffs)
    mapoffset = cur
    rawsha1 = hashlib.sha1(bytes(logical[:logicalbytes])).digest()
    mh = sorted(b'CHT2' + hashlib.sha1(m).digest() for m in meta)
    sha1 = hashlib.sha1(rawsha1 + b''.join(mh)).digest()
    hdr = b'MComprHD' + struct.pack('>II', 124, 5) + b''.join(tags) + b'\0\0\0\0' + struct.pack('>QQQII', logicalbytes, mapoffset, hdr_len, HUNKBYTES, FRAME) + rawsha1 + sha1 + b'\0' * 20
    with open(path, 'wb') as fo:
        fo.write(hdr); fo.write(metabin)
        for b in blobs: fo.write(b)
        fo.write(mapbin)
    return dict(hunks=nh, types=[e[0] for e in entries])

def bits_for(v):
    b = 0
    while (1 << b) <= v: b += 1
    return b

def compress_map(raw, nh, firstoffs):
    # promote SELF refs, gather symbols with RLE
    syms = []; last = 0; count = 0; last_self = 0; maxlen = 0; maxself = 0
    comps = []
    for h in range(nh):
        t = raw[h * 12]
        if t == SELF:
            ref = int.from_bytes(raw[h * 12 + 4:h * 12 + 10], 'big')
            if ref == last_self: t = SELF0
            elif ref == last_self + 1: t = SELF1; last_self = ref
            else: last_self = ref; maxself = max(maxself, ref)
        if t in (CT0, CT1, CT2, CT3): maxlen = max(maxlen, int.from_bytes(raw[h * 12 + 1:h * 12 + 4], 'big'))
        comps.append(t)
    def flush(cnt, lc):
        while cnt:
            if cnt < 3: syms.append(lc); cnt -= 1
            elif cnt <= 3 + 15: syms.extend([RLE_S, cnt - 3]); cnt = 0
            else:
                this = min(cnt, 3 + 16 + 255); v = this - 3 - 16
                syms.extend([RLE_L, v >> 4, v & 15]); cnt -= this
    for t in comps:
        if t == last: count += 1
        else:
            flush(count, last); count = 0
            syms.append(t); last = t
    flush(count, last)
    hist = [0] * 16
    for s in syms: hist[s] += 1
    L = huff_lengths(hist); codes = canonical(L)
    bw = BitW(); export_tree_rle(bw, L)
    for s in syms: bw.write(codes[s], L[s])
    lengthbits = bits_for(maxlen); selfbits = bits_for(maxself); parentbits = 0
    for h in range(nh):
        t = comps[h]
        if t in (CT0, CT1, CT2, CT3):
            bw.write(int.from_bytes(raw[h * 12 + 1:h * 12 + 4], 'big'), lengthbits); bw.write(int.from_bytes(raw[h * 12 + 10:h * 12 + 12], 'big'), 16)
        elif t == NONE: bw.write(int.from_bytes(raw[h * 12 + 10:h * 12 + 12], 'big'), 16)
        elif t == SELF: bw.write(int.from_bytes(raw[h * 12 + 4:h * 12 + 10], 'big'), selfbits)
    comp = bw.flush()
    # crc of the decoded raw map (SELF0/1 decoded back to SELF with offsets)
    return struct.pack('>I', len(comp)) + firstoffs.to_bytes(6, 'big') + struct.pack('>H', crc16(raw)) + bytes([lengthbits, selfbits, parentbits, 0]) + comp

# ------------------------------------------------------------ reader (map only + simple codecs)
def read_header(d):
    assert d[:8] == b'MComprHD'
    ln, ver = struct.unpack('>II', d[8:16]); assert ver == 5
    comps = [d[16 + 4 * i:20 + 4 * i] for i in range(4)]
    logical, mapoff, metaoff, hunkbytes, unitbytes = struct.unpack('>QQQII', d[32:64])
    return dict(comps=comps, logical=logical, mapoff=mapoff, metaoff=metaoff, hunkbytes=hunkbytes, unitbytes=unitbytes,
                rawsha1=d[64:84], sha1=d[84:104])

if __name__ == '__main__':
    # fixture: Track 01 + synthetic audio tracks
    import math, random
    data = open(sys.argv[1], 'rb').read()
    random.seed(7)
    def tone(sec, f1, f2):
        n = sec * 75 * 588
        out = bytearray()
        for i in range(n):
            l = int(9000 * math.sin(i * f1) + random.randint(-300, 300)); r = int(7000 * math.sin(i * f2))
            out += struct.pack('<hh', l, r)
        return bytes(out)
    tracks = [dict(type='MODE1_RAW', data=data)]
    tracks.append(dict(type='AUDIO', data=tone(2, 0.031, 0.047), pregap=150))
    tracks.append(dict(type='AUDIO', data=b'\0' * (SECTOR * 75 * 3), pregap=150))   # silence -> SELF refs
    tracks.append(dict(type='AUDIO', data=tone(1, 0.013, 0.0071), pregap=150))
    # force a few data hunks onto the other codecs to exercise every decoder path
    force = {3: 'cdzl', 4: 'cdfl', 5: 'none'}
    info = write_chd(sys.argv[2], tracks, force=force)
    from collections import Counter
    print(info['hunks'], Counter(info['types']))
