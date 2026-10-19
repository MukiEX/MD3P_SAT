/* Magical Drop III Saturn Paddle Edition - patch core (runs in a Web Worker or Node).
 * CRC32, SHA-1, raw inflate, raw LZMA, FLAC frames, CD-ROM Mode 1 EDC/ECC, CHD v5 (CD)
 * reader and writer, stored ZIP.  No dependencies.
 */
'use strict';
var PC = (function () {

// ---------------------------------------------------------------- CRC32 / CRC16
const CRC32T = new Int32Array(256);
for (let i = 0; i < 256; i++) { let c = i; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; CRC32T[i] = c; }
function crc32(buf, crc) {
  let c = (crc === undefined ? 0 : crc) ^ -1;
  for (let i = 0; i < buf.length; i++) c = CRC32T[(c ^ buf[i]) & 0xFF] ^ (c >>> 8);
  return (c ^ -1) >>> 0;
}
const CRC16T = new Uint16Array(256);
for (let i = 0; i < 256; i++) { let c = i << 8; for (let k = 0; k < 8; k++) c = c & 0x8000 ? ((c << 1) ^ 0x1021) & 0xFFFF : (c << 1) & 0xFFFF; CRC16T[i] = c; }
function crc16(buf) { let c = 0xFFFF; for (let i = 0; i < buf.length; i++) c = ((c << 8) & 0xFFFF) ^ CRC16T[(c >> 8) ^ buf[i]]; return c; }

// ---------------------------------------------------------------- SHA-1 (incremental)
function SHA1() { this.h = new Int32Array([0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0 | 0]); this.buf = new Uint8Array(64); this.n = 0; this.len = 0; this.w = new Int32Array(80); }
SHA1.prototype.block = function (b, o) {
  const w = this.w, h = this.h;
  for (let i = 0; i < 16; i++) w[i] = (b[o + 4 * i] << 24) | (b[o + 4 * i + 1] << 16) | (b[o + 4 * i + 2] << 8) | b[o + 4 * i + 3];
  for (let i = 16; i < 80; i++) { const x = w[i - 3] ^ w[i - 8] ^ w[i - 14] ^ w[i - 16]; w[i] = (x << 1) | (x >>> 31); }
  let a = h[0], bb = h[1], c = h[2], d = h[3], e = h[4];
  for (let i = 0; i < 80; i++) {
    let f, k;
    if (i < 20) { f = (bb & c) | (~bb & d); k = 0x5A827999; }
    else if (i < 40) { f = bb ^ c ^ d; k = 0x6ED9EBA1; }
    else if (i < 60) { f = (bb & c) | (bb & d) | (c & d); k = 0x8F1BBCDC | 0; }
    else { f = bb ^ c ^ d; k = 0xCA62C1D6 | 0; }
    const t = (((a << 5) | (a >>> 27)) + f + e + k + w[i]) | 0;
    e = d; d = c; c = (bb << 30) | (bb >>> 2); bb = a; a = t;
  }
  h[0] = (h[0] + a) | 0; h[1] = (h[1] + bb) | 0; h[2] = (h[2] + c) | 0; h[3] = (h[3] + d) | 0; h[4] = (h[4] + e) | 0;
};
SHA1.prototype.update = function (d) {
  let i = 0; this.len += d.length;
  if (this.n) { while (this.n < 64 && i < d.length) this.buf[this.n++] = d[i++]; if (this.n === 64) { this.block(this.buf, 0); this.n = 0; } }
  for (; i + 64 <= d.length; i += 64) this.block(d, i);
  while (i < d.length) this.buf[this.n++] = d[i++];
  return this;
};
SHA1.prototype.digest = function () {
  const bits = this.len * 8, pad = new Uint8Array(((this.n < 56) ? 56 : 120) - this.n + 8);
  pad[0] = 0x80; const hi = Math.floor(bits / 4294967296), lo = bits >>> 0;
  const L = pad.length; pad[L - 8] = hi >>> 24; pad[L - 7] = hi >>> 16; pad[L - 6] = hi >>> 8; pad[L - 5] = hi;
  pad[L - 4] = lo >>> 24; pad[L - 3] = lo >>> 16; pad[L - 2] = lo >>> 8; pad[L - 1] = lo;
  this.update(pad);
  const out = new Uint8Array(20);
  for (let i = 0; i < 5; i++) { out[4 * i] = this.h[i] >>> 24; out[4 * i + 1] = this.h[i] >>> 16; out[4 * i + 2] = this.h[i] >>> 8; out[4 * i + 3] = this.h[i]; }
  return out;
};
function sha1(d) { return new SHA1().update(d).digest(); }
const hex = (b) => Array.from(b, (x) => x.toString(16).padStart(2, '0')).join('');

// ---------------------------------------------------------------- raw inflate
const LBASE = [3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 17, 19, 23, 27, 31, 35, 43, 51, 59, 67, 83, 99, 115, 131, 163, 195, 227, 258];
const LEXT = [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 0];
const DBASE = [1, 2, 3, 4, 5, 7, 9, 13, 17, 25, 33, 49, 65, 97, 129, 193, 257, 385, 513, 769, 1025, 1537, 2049, 3073, 4097, 6145, 8193, 12289, 16385, 24577];
const DEXT = [0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13];
function huffTable(lens, n) {           // returns {count, sym} canonical decoding tables
  const count = new Uint16Array(16), offs = new Uint16Array(16), sym = new Uint16Array(n);
  for (let i = 0; i < n; i++) count[lens[i]]++;
  count[0] = 0;
  for (let i = 1; i < 16; i++) offs[i] = offs[i - 1] + count[i - 1];
  for (let i = 0; i < n; i++) if (lens[i]) sym[offs[lens[i]]++] = i;
  return { count, sym };
}
function inflateRaw(src, so, slen, dst, dlen) {
  let pos = so, end = so + slen, bitbuf = 0, bitcnt = 0, out = 0;
  function bits(n) {
    while (bitcnt < n) { if (pos >= end) throw new Error('inflate: input overrun'); bitbuf |= src[pos++] << bitcnt; bitcnt += 8; }
    const v = bitbuf & ((1 << n) - 1); bitbuf >>>= n; bitcnt -= n; return v;
  }
  function decode(t) {
    let code = 0, first = 0, index = 0;
    for (let len = 1; len < 16; len++) {
      code |= bits(1); const c = t.count[len];
      if (code - c < first) return t.sym[index + (code - first)];
      index += c; first += c; first <<= 1; code <<= 1;
    }
    throw new Error('inflate: bad code');
  }
  let fixedL = null, fixedD = null, last = 0;
  do {
    last = bits(1); const type = bits(2);
    if (type === 0) {
      bitbuf = 0; bitcnt = 0;
      const len = src[pos] | (src[pos + 1] << 8); pos += 4;
      for (let i = 0; i < len; i++) dst[out++] = src[pos++];
      continue;
    }
    let lt, dt;
    if (type === 1) {
      if (!fixedL) { const l = new Uint8Array(288); l.fill(8, 0, 144); l.fill(9, 144, 256); l.fill(7, 256, 280); l.fill(8, 280, 288); fixedL = huffTable(l, 288); const d = new Uint8Array(30).fill(5); fixedD = huffTable(d, 30); }
      lt = fixedL; dt = fixedD;
    } else if (type === 2) {
      const hlit = bits(5) + 257, hdist = bits(5) + 1, hclen = bits(4) + 4;
      const ord = [16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15];
      const cl = new Uint8Array(19); for (let i = 0; i < hclen; i++) cl[ord[i]] = bits(3);
      const ct = huffTable(cl, 19), lens = new Uint8Array(hlit + hdist);
      for (let i = 0; i < hlit + hdist;) {
        const s = decode(ct);
        if (s < 16) lens[i++] = s;
        else { let rep, v = 0; if (s === 16) { v = lens[i - 1]; rep = 3 + bits(2); } else if (s === 17) rep = 3 + bits(3); else rep = 11 + bits(7); while (rep--) lens[i++] = v; }
      }
      lt = huffTable(lens.subarray(0, hlit), hlit); dt = huffTable(lens.subarray(hlit), hdist);
    } else throw new Error('inflate: bad block type');
    for (;;) {
      let s = decode(lt);
      if (s < 256) dst[out++] = s;
      else if (s === 256) break;
      else {
        s -= 257; const len = LBASE[s] + bits(LEXT[s]); const ds = decode(dt); const dist = DBASE[ds] + bits(DEXT[ds]);
        for (let i = 0; i < len; i++, out++) dst[out] = dst[out - dist];
      }
    }
  } while (!last && out < dlen);
  if (out !== dlen) throw new Error('inflate: size mismatch ' + out + ' != ' + dlen);
}

// ---------------------------------------------------------------- raw LZMA (lc3 lp0 pb2 by default)
function lzmaDecode(src, so, slen, dst, dlen, lc, lp, pb) {
  lc = lc === undefined ? 3 : lc; lp = lp || 0; pb = pb === undefined ? 2 : pb;
  let ip = so + 1, range = 0xFFFFFFFF, code = 0; const end = so + slen;
  for (let i = 0; i < 4; i++) code = ((code << 8) | src[ip++]) >>> 0;
  const nb = () => ip < end ? src[ip++] : 0;
  const PROB_INIT = 1024;
  const probs = (n) => new Uint16Array(n).fill(PROB_INIT);
  function bit(p, i) {
    const bound = (range >>> 11) * p[i];
    let b;
    if (code < bound) { range = bound; p[i] += (2048 - p[i]) >> 5; b = 0; }
    else { range = (range - bound) >>> 0; code = (code - bound) >>> 0; p[i] -= p[i] >> 5; b = 1; }
    if (range < 0x1000000) { range = (range << 8) >>> 0; code = ((code << 8) | nb()) >>> 0; }
    return b;
  }
  function direct(n) {
    let r = 0;
    while (n--) {
      range >>>= 1; let b = 0;
      if (code >= range) { code = (code - range) >>> 0; b = 1; }
      r = (r << 1) | b;
      if (range < 0x1000000) { range = (range << 8) >>> 0; code = ((code << 8) | nb()) >>> 0; }
    }
    return r >>> 0;
  }
  function tree(p, base, nbits) { let m = 1; for (let i = 0; i < nbits; i++) m = (m << 1) | bit(p, base + m); return m - (1 << nbits); }
  function rtree(p, base, nbits) { let m = 1, s = 0; for (let i = 0; i < nbits; i++) { const b = bit(p, base + m); m = (m << 1) | b; s |= b << i; } return s; }
  const literal = probs(0x300 << (lc + lp));
  const isMatch = probs(12 << 4), isRep = probs(12), isRepG0 = probs(12), isRepG1 = probs(12), isRepG2 = probs(12), isRep0Long = probs(12 << 4);
  const posSlot = probs(4 << 6), posDec = probs(115), align = probs(16);
  function lenDecoder() { return { choice: probs(2), low: probs(16 << 3), mid: probs(16 << 3), high: probs(256) }; }
  const lenD = lenDecoder(), repLenD = lenDecoder();
  function decLen(L, ps) {
    if (!bit(L.choice, 0)) return tree(L.low, ps << 3, 3);
    if (!bit(L.choice, 1)) return 8 + tree(L.mid, ps << 3, 3);
    return 16 + tree(L.high, 0, 8);
  }
  let state = 0, rep0 = 0, rep1 = 0, rep2 = 0, rep3 = 0, out = 0;
  const pbMask = (1 << pb) - 1, lpMask = (1 << lp) - 1;
  while (out < dlen) {
    const ps = out & pbMask;
    if (!bit(isMatch, (state << 4) + ps)) {
      const prev = out > 0 ? dst[out - 1] : 0;
      const base = 0x300 * (((out & lpMask) << lc) + (prev >> (8 - lc)));
      let sym = 1;
      if (state >= 7) {
        let mb = dst[out - rep0 - 1];
        do {
          const m = (mb >> 7) & 1; mb <<= 1;
          const b = bit(literal, base + ((1 + m) << 8) + sym); sym = (sym << 1) | b;
          if (m !== b) break;
        } while (sym < 0x100);
      }
      while (sym < 0x100) sym = (sym << 1) | bit(literal, base + sym);
      dst[out++] = sym & 0xFF;
      state = state < 4 ? 0 : state < 10 ? state - 3 : state - 6;
      continue;
    }
    let len;
    if (bit(isRep, state)) {
      if (!bit(isRepG0, state)) {
        if (!bit(isRep0Long, (state << 4) + ps)) { state = state < 7 ? 9 : 11; dst[out] = dst[out - rep0 - 1]; out++; continue; }
      } else {
        let d;
        if (!bit(isRepG1, state)) d = rep1;
        else { if (!bit(isRepG2, state)) d = rep2; else { d = rep3; rep3 = rep2; } rep2 = rep1; }
        rep1 = rep0; rep0 = d;
      }
      len = decLen(repLenD, ps); state = state < 7 ? 8 : 11;
    } else {
      rep3 = rep2; rep2 = rep1; rep1 = rep0;
      len = decLen(lenD, ps); state = state < 7 ? 7 : 10;
      const lstate = len < 4 ? len : 3;
      const slot = tree(posSlot, lstate << 6, 6);
      if (slot < 4) rep0 = slot;
      else {
        const nd = (slot >> 1) - 1; let dist = ((2 | (slot & 1)) << nd) >>> 0;
        if (slot < 14) dist += rtree(posDec, dist - slot, nd);
        else { dist += direct(nd - 4) << 4; dist += rtree(align, 0, 4); }
        rep0 = dist >>> 0;
      }
      if (rep0 === 0xFFFFFFFF) break;   // end marker
    }
    len += 2;
    if (rep0 >= out) throw new Error('lzma: bad distance');
    for (let i = 0; i < len && out < dlen; i++, out++) dst[out] = dst[out - rep0 - 1];
  }
  if (out !== dlen) throw new Error('lzma: size mismatch');
}

// ---------------------------------------------------------------- FLAC frames (CHD cdfl)
function flacDecode(src, so, slen, dst, nsamples) {
  // decodes stereo 16-bit frames into dst as big-endian interleaved; returns bytes consumed
  let pos = so, bitpos = 0; const end = so + slen;
  function rd(n) {             // n <= 32
    let v = 0;
    while (n > 0) {
      if (pos >= end) throw new Error('flac: overrun');
      const avail = 8 - bitpos, take = n < avail ? n : avail;
      const b = (src[pos] >> (avail - take)) & ((1 << take) - 1);
      v = v * (1 << take) + b; n -= take; bitpos += take;
      if (bitpos === 8) { bitpos = 0; pos++; }
    }
    return v;
  }
  function rds(n) { const v = rd(n); return v >= Math.pow(2, n - 1) ? v - Math.pow(2, n) : v; }
  function unary() { let q = 0; while (rd(1) === 0) q++; return q; }
  function align() { if (bitpos) { bitpos = 0; pos++; } }
  let done = 0; const ch = [new Int32Array(65536), new Int32Array(65536)];
  while (done < nsamples) {
    align();
    const sync = rd(14); if (sync !== 0x3FFE) throw new Error('flac: lost sync');
    rd(1); rd(1);
    const bsc = rd(4), src_ = rd(4), chan = rd(4), ssc = rd(3); rd(1);
    // utf-8 coded number
    let x = rd(8); if (x & 0x80) { let n = 0; while (x & (0x80 >> n)) n++; for (let i = 1; i < n; i++) rd(8); }
    let bs;
    if (bsc === 1) bs = 192; else if (bsc >= 2 && bsc <= 5) bs = 576 << (bsc - 2); else if (bsc === 6) bs = rd(8) + 1; else if (bsc === 7) bs = rd(16) + 1; else if (bsc >= 8) bs = 256 << (bsc - 8); else throw new Error('flac: bad blocksize');
    if (src_ === 12) rd(8); else if (src_ === 13 || src_ === 14) rd(16);
    rd(8); // crc8
    const bpsBase = ssc === 4 || ssc === 0 ? 16 : ssc === 5 ? 20 : ssc === 6 ? 24 : ssc === 1 ? 8 : ssc === 2 ? 12 : 16;
    const nch = chan < 8 ? chan + 1 : 2;
    for (let c = 0; c < nch; c++) {
      let bps = bpsBase;
      if ((chan === 8 && c === 1) || (chan === 9 && c === 0) || (chan === 10 && c === 1)) bps++;
      rd(1); const type = rd(6); let wasted = 0;
      if (rd(1)) { wasted = unary() + 1; bps -= wasted; }
      const s = ch[c];
      if (type === 0) { const v = rds(bps); for (let i = 0; i < bs; i++) s[i] = v; }
      else if (type === 1) { for (let i = 0; i < bs; i++) s[i] = rds(bps); }
      else if (type >= 8 && type <= 12) {
        const order = type - 8;
        for (let i = 0; i < order; i++) s[i] = rds(bps);
        residual(s, order, bs);
        for (let i = order; i < bs; i++) {
          let p = 0;
          if (order === 1) p = s[i - 1]; else if (order === 2) p = 2 * s[i - 1] - s[i - 2];
          else if (order === 3) p = 3 * s[i - 1] - 3 * s[i - 2] + s[i - 3];
          else if (order === 4) p = 4 * s[i - 1] - 6 * s[i - 2] + 4 * s[i - 3] - s[i - 4];
          s[i] += p;
        }
      } else if (type >= 32) {
        const order = type - 31;
        for (let i = 0; i < order; i++) s[i] = rds(bps);
        const prec = rd(4) + 1; const shift = rds(5); const coef = new Array(order);
        for (let i = 0; i < order; i++) coef[i] = rds(prec);
        residual(s, order, bs);
        const div = Math.pow(2, shift);
        for (let i = order; i < bs; i++) {
          let sum = 0; for (let j = 0; j < order; j++) sum += coef[j] * s[i - j - 1];
          s[i] += Math.floor(sum / div);
        }
      } else throw new Error('flac: reserved subframe');
      if (wasted) for (let i = 0; i < bs; i++) s[i] *= (1 << wasted);
    }
    align(); rd(16);  // crc16
    const L = ch[0], R = ch[1];
    for (let i = 0; i < bs && done < nsamples; i++, done++) {
      let l = L[i], r = R[i];
      if (chan === 8) r = l - r;                     // left/side
      else if (chan === 9) l = l + r;                // side/right (L holds side)
      else if (chan === 10) { let mid = l * 2 | (r & 1); l = (mid + r) >> 1; r = (mid - r) >> 1; }
      const o = done * 4; dst[o] = (l >> 8) & 0xFF; dst[o + 1] = l & 0xFF; dst[o + 2] = (r >> 8) & 0xFF; dst[o + 3] = r & 0xFF;
    }
  }
  align();
  return pos - so;
  function residual(s, order, bs) {
    const method = rd(2), porder = rd(4), pbits = method === 0 ? 4 : 5, esc = method === 0 ? 15 : 31;
    const parts = 1 << porder; let i = order;
    for (let p = 0; p < parts; p++) {
      const n = (p === 0 ? (bs >> porder) - order : bs >> porder);
      const k = rd(pbits);
      if (k === esc) { const nb = rd(5); for (let j = 0; j < n; j++) s[i++] = nb ? rds(nb) : 0; }
      else for (let j = 0; j < n; j++) { const q = unary(); const v = k ? q * (1 << k) + rd(k) : q; s[i++] = (v & 1) ? -((v + 1) / 2) : v / 2; }
    }
  }
}

// ---------------------------------------------------------------- CD Mode 1 EDC / ECC
const EDCT = new Int32Array(256);
for (let i = 0; i < 256; i++) { let e = i; for (let k = 0; k < 8; k++) e = (e >>> 1) ^ (e & 1 ? 0xD8018001 : 0); EDCT[i] = e; }
const ECCF = new Uint8Array(256), ECCB = new Uint8Array(256);
for (let i = 0; i < 256; i++) { const j = ((i << 1) ^ (i & 0x80 ? 0x11D : 0)) & 0xFF; ECCF[i] = j; ECCB[i ^ j] = i; }
function eccBlock(sec, majc, minc, majm, mini, dest) {
  const size = majc * minc;
  for (let major = 0; major < majc; major++) {
    let index = (major >> 1) * majm + (major & 1), a = 0, b = 0;
    for (let minor = 0; minor < minc; minor++) {
      const t = sec[12 + index]; index += mini; if (index >= size) index -= size;
      a ^= t; b ^= t; a = ECCF[a];
    }
    a = ECCB[ECCF[a] ^ b]; sec[dest + major] = a; sec[dest + major + majc] = a ^ b;
  }
}
function eccGenerate(sec) { eccBlock(sec, 86, 24, 2, 86, 0x81C); eccBlock(sec, 52, 43, 86, 88, 0x8C8); }
function fixMode1(sec) {
  let e = 0; for (let i = 0; i < 0x810; i++) e = EDCT[(e ^ sec[i]) & 0xFF] ^ (e >>> 8);
  sec[0x810] = e & 0xFF; sec[0x811] = (e >>> 8) & 0xFF; sec[0x812] = (e >>> 16) & 0xFF; sec[0x813] = (e >>> 24) & 0xFF;
  sec.fill(0, 0x814, 0x81C); eccGenerate(sec);
}
const SYNC = [0, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 0];

// ---------------------------------------------------------------- bit streams (MSB first)
function BitR(b, o) { this.b = b; this.p = o * 8; }
BitR.prototype.read = function (n) { let v = 0; for (let i = 0; i < n; i++) { const byte = this.b[this.p >> 3]; v = v * 2 + ((byte >> (7 - (this.p & 7))) & 1); this.p++; } return v; };
function BitW() { this.out = []; this.acc = 0; this.n = 0; }
BitW.prototype.write = function (v, n) { for (let i = n - 1; i >= 0; i--) { this.acc = (this.acc << 1) | (Math.floor(v / Math.pow(2, i)) & 1); if (++this.n === 8) { this.out.push(this.acc); this.acc = 0; this.n = 0; } } };
BitW.prototype.bytes = function () { if (this.n) this.out.push(this.acc << (8 - this.n)); this.n = 0; return Uint8Array.from(this.out); };

// ---------------------------------------------------------------- CHD v5
const FRAME = 2448, SECTOR = 2352;
const T = { NONE: 4, SELF: 5, PARENT: 6, RLE_S: 7, RLE_L: 8, SELF0: 9, SELF1: 10, PSELF: 11, P0: 12, P1: 13 };
const be32 = (b, o) => ((b[o] << 24) | (b[o + 1] << 16) | (b[o + 2] << 8) | b[o + 3]) >>> 0;
const be48 = (b, o) => be32(b, o) * 65536 + ((b[o + 4] << 8) | b[o + 5]);
const be64 = (b, o) => be32(b, o) * 4294967296 + be32(b, o + 4);
function put(b, o, v, n) { for (let i = n - 1; i >= 0; i--) { b[o + i] = v % 256; v = Math.floor(v / 256); } }

function chdOpen(read, size) {
  const h = read(0, 124);
  if (String.fromCharCode.apply(null, h.subarray(0, 8)) !== 'MComprHD') throw new Error('not a CHD file');
  if (be32(h, 12) !== 5) throw new Error('only CHD version 5 is supported (convert with chdman copy)');
  const comps = [0, 1, 2, 3].map((i) => String.fromCharCode.apply(null, h.subarray(16 + 4 * i, 20 + 4 * i)));
  const c = { read, size, header: h, comps, logical: be64(h, 32), mapoff: be64(h, 40), metaoff: be64(h, 48), hunkbytes: be32(h, 56), unitbytes: be32(h, 60),
    rawsha1: h.slice(64, 84), sha1: h.slice(84, 104), parent: h.slice(104, 124) };
  if (c.parent.some((x) => x)) throw new Error('CHDs with a parent are not supported');
  c.hunks = Math.ceil(c.logical / c.hunkbytes);
  // ---- map
  const mh = read(c.mapoff, 16);
  const mapbytes = be32(mh, 0), firstoffs = be48(mh, 4), mapcrc = (mh[10] << 8) | mh[11];
  const lengthbits = mh[12], selfbits = mh[13], parentbits = mh[14];
  const mb = read(c.mapoff + 16, mapbytes + 8);
  const br = new BitR(mb, 0);
  const L = []; while (L.length < 16) { let v = br.read(4); if (v !== 1) L.push(v); else { v = br.read(4); if (v === 1) L.push(1); else { let r = br.read(4) + 3; while (r--) L.push(v); } } }
  // canonical codes -> lookup (8 bits)
  const histo = new Array(33).fill(0); L.forEach((l) => { if (l) histo[l]++; });
  let cur = 0; for (let ln = 32; ln > 0; ln--) { const nx = (cur + histo[ln]) >> 1; histo[ln] = cur; cur = nx; }
  const lut = new Int16Array(256).fill(-1), lutlen = new Uint8Array(256);
  L.forEach((l, s) => { if (!l) return; const code = histo[l]++; const sh = 8 - l; for (let k = 0; k < (1 << sh); k++) { lut[(code << sh) | k] = s; lutlen[(code << sh) | k] = l; } });
  const dec = () => { const save = br.p; const v = br.read(8); const s = lut[v]; if (s < 0) throw new Error('bad map code'); br.p = save + lutlen[v]; return s; };
  const raw = new Uint8Array(c.hunks * 12);
  let last = 0, rep = 0;
  for (let i = 0; i < c.hunks; i++) {
    if (rep > 0) { raw[i * 12] = last; rep--; continue; }
    const v = dec();
    if (v === T.RLE_S) { raw[i * 12] = last; rep = 2 + dec(); }
    else if (v === T.RLE_L) { raw[i * 12] = last; rep = 2 + 16 + (dec() << 4); rep += dec(); }
    else raw[i * 12] = last = v;
  }
  let curoff = firstoffs, lastSelf = 0, lastParent = 0;
  for (let i = 0; i < c.hunks; i++) {
    let t = raw[i * 12], length = 0, offset = 0, crc = 0;
    switch (t) {
      case 0: case 1: case 2: case 3: length = br.read(lengthbits); offset = curoff; curoff += length; crc = br.read(16); break;
      case T.NONE: length = c.hunkbytes; offset = curoff; curoff += length; crc = br.read(16); break;
      case T.SELF: lastSelf = offset = br.read(selfbits); break;
      case T.PARENT: offset = br.read(parentbits); lastParent = offset; break;
      case T.SELF1: lastSelf++; /* fall through */
      case T.SELF0: t = T.SELF; offset = lastSelf; break;
      case T.PSELF: t = T.PARENT; offset = lastParent = (i * c.hunkbytes) / c.unitbytes; break;
      case T.P1: lastParent += c.hunkbytes / c.unitbytes; /* fall through */
      case T.P0: t = T.PARENT; offset = lastParent; break;
      default: throw new Error('bad map entry type ' + t);
    }
    raw[i * 12] = t; put(raw, i * 12 + 1, length, 3); put(raw, i * 12 + 4, offset, 6); put(raw, i * 12 + 10, crc, 2);
  }
  if (crc16(raw) !== mapcrc) throw new Error('CHD map CRC mismatch');
  c.map = raw; c.firstoffs = firstoffs;
  c.entry = (i) => ({ type: raw[i * 12], length: (raw[i * 12 + 1] << 16) | (raw[i * 12 + 2] << 8) | raw[i * 12 + 3], offset: be48(raw, i * 12 + 4), crc: (raw[i * 12 + 10] << 8) | raw[i * 12 + 11] });
  // ---- metadata chain
  c.meta = []; let mo = c.metaoff;
  while (mo) { const m = read(mo, 16); const len = ((m[5] << 16) | (m[6] << 8) | m[7]); c.meta.push({ off: mo, tag: m.slice(0, 4), flags: m[4], data: read(mo + 16, len) }); mo = be64(m, 8); if (c.meta.length > 1000) throw new Error('metadata loop'); }
  return c;
}
function cdDecompress(comp, src, dst, hunkbytes) {
  const frames = hunkbytes / FRAME, sectors = new Uint8Array(frames * SECTOR), subs = new Uint8Array(frames * 96);
  let o;
  if (comp === 'cdlz' || comp === 'cdzl') {
    const cb = hunkbytes < 65536 ? 2 : 3, eb = (frames + 7) >> 3, hb = eb + cb;
    let base = (src[eb] << 8) | src[eb + 1]; if (cb > 2) base = (base << 8) | src[eb + 2];
    if (comp === 'cdlz') lzmaDecode(src, hb, base, sectors, sectors.length); else inflateRaw(src, hb, base, sectors, sectors.length);
    inflateRaw(src, hb + base, src.length - hb - base, subs, subs.length);
    for (let f = 0; f < frames; f++) {
      dst.set(sectors.subarray(f * SECTOR, (f + 1) * SECTOR), f * FRAME);
      dst.set(subs.subarray(f * 96, (f + 1) * 96), f * FRAME + SECTOR);
      if (src[f >> 3] & (1 << (f & 7))) { const s = dst.subarray(f * FRAME, f * FRAME + SECTOR); s.set(SYNC, 0); eccGenerate(s); }
    }
  } else if (comp === 'cdfl') {
    const used = flacDecode(src, 0, src.length, sectors, frames * SECTOR / 4);
    inflateRaw(src, used, src.length - used, subs, subs.length);
    for (let f = 0; f < frames; f++) { dst.set(sectors.subarray(f * SECTOR, (f + 1) * SECTOR), f * FRAME); dst.set(subs.subarray(f * 96, (f + 1) * 96), f * FRAME + SECTOR); }
  } else throw new Error('unsupported codec ' + comp);
}
function chdReadHunk(c, i, depth) {
  const e = c.entry(i), out = new Uint8Array(c.hunkbytes);
  if (e.type === T.SELF) { if ((depth || 0) > 8) throw new Error('self loop'); return chdReadHunk(c, e.offset, (depth || 0) + 1); }
  if (e.type === T.PARENT) throw new Error('parent reference');
  const src = c.read(e.offset, e.length);
  if (e.type === T.NONE) out.set(src); else cdDecompress(c.comps[e.type], src, out, c.hunkbytes);
  if (crc16(out) !== e.crc) throw new Error('hunk ' + i + ' CRC mismatch');
  return out;
}

// ---------------------------------------------------------------- the patch
// P = { trackCrc, trackSectors, sectors: [{lba, orig_crc, data(Uint8Array 2352)}], tune: {lba, off} }
function applyOptions(P, opts) {
  // returns map lba -> new sector bytes, with the tuning block edited and EDC/ECC rebuilt
  const out = new Map();
  for (const s of P.sectors) out.set(s.lba, Uint8Array.from(s.data));
  if (opts) {
    const t = P.tune, sec = out.get(t.lba);
    if (opts.speed !== undefined) sec[16 + t.off + 5] = opts.speed;
    if (opts.flags !== undefined) sec[16 + t.off + 13] = opts.flags;
    fixMode1(sec);
  }
  return out;
}

function patchBin(read, size, P, opts, progress) {
  const tlen = P.trackSectors * SECTOR;
  if (size < tlen) throw new Error('This file is ' + Math.round(size / 1024) + ' KB, smaller than Track 01 (' + Math.round(tlen / 1048576) + ' MB). Choose the Track 01 .bin or the whole-disc .chd.');
  let crc = 0;
  for (let o = 0; o < tlen; o += 1 << 20) { crc = crc32(read(o, Math.min(1 << 20, tlen - o)), crc); progress && progress(o / tlen); }
  if (crc !== P.trackCrc) {
    if (P.patchedCrc && crc === P.patchedCrc) throw new Error('This Track 01 is already patched (CRC32 ' + crc.toString(16).toUpperCase() + '). Start from the original dump.');
    throw new Error('Track 01 CRC32 is ' + crc.toString(16).toUpperCase().padStart(8, '0') + ', expected ' + P.trackCrc.toString(16).toUpperCase() + ' (Redump dump of T-1313G required)');
  }
  const news = applyOptions(P, opts);
  const parts = []; let at = 0;
  const lbas = Array.from(news.keys()).sort((a, b) => a - b);
  for (const l of lbas) { parts.push({ src: [at, l * SECTOR] }); parts.push({ data: news.get(l) }); at = (l + 1) * SECTOR; }
  parts.push({ src: [at, size] });
  return { parts, merged: size > tlen };
}

function patchChd(c, P, opts, progress) {
  const news = applyOptions(P, opts);
  const spH = c.hunkbytes / FRAME;
  const modified = new Map();             // hunk -> new data
  for (const [lba] of news) { const h = Math.floor(lba / spH); if (!modified.has(h)) modified.set(h, null); }
  // pass: decode everything (raw SHA-1, track CRC, original-sector check)
  const sha = new SHA1(); let left = c.logical, tcrc = 0, tsec = 0;
  for (let i = 0; i < c.hunks; i++) {
    let d = chdReadHunk(c, i);
    for (let f = 0; f < spH && tsec < P.trackSectors; f++, tsec++) tcrc = crc32(d.subarray(f * FRAME, f * FRAME + SECTOR), tcrc);
    if (tsec === P.trackSectors && tcrc !== P.trackCrc) throw new Error('Track 01 CRC32 is ' + tcrc.toString(16).toUpperCase().padStart(8, '0') + ', expected ' + P.trackCrc.toString(16).toUpperCase());
    if (modified.has(i)) {
      d = Uint8Array.from(d);
      for (const [lba, sec] of news) if (Math.floor(lba / spH) === i) d.set(sec, (lba % spH) * FRAME);
      modified.set(i, d);
    }
    const n = Math.min(left, c.hunkbytes); sha.update(n === c.hunkbytes ? d : d.subarray(0, n)); left -= n;
    if (progress && (i & 63) === 0) progress(i / c.hunks);
  }
  const rawsha1 = sha.digest();
  // ---- layout: header | original bytes up to the first hunk | hunks in order | map
  const parts = [{ data: null }, { src: [124, c.firstoffs] }];
  const raw = new Uint8Array(c.hunks * 12);
  let off = c.firstoffs, maxlen = 0, maxself = 0;
  for (let i = 0; i < c.hunks; i++) {
    let e = c.entry(i);
    if (modified.has(i)) {
      const d = modified.get(i);
      raw[i * 12] = T.NONE; put(raw, i * 12 + 1, c.hunkbytes, 3); put(raw, i * 12 + 4, off, 6); put(raw, i * 12 + 10, crc16(d), 2);
      parts.push({ data: d }); off += c.hunkbytes; continue;
    }
    if (e.type === T.SELF) {
      let ref = e.offset, d = 0; while (c.entry(ref).type === T.SELF && d++ < 8) ref = c.entry(ref).offset;
      if (!modified.has(ref)) { raw[i * 12] = T.SELF; put(raw, i * 12 + 4, ref, 6); maxself = Math.max(maxself, ref); continue; }
      e = c.entry(ref);     // the referenced hunk changed: keep our own copy of its original blob
    }
    raw[i * 12] = e.type; put(raw, i * 12 + 1, e.length, 3); put(raw, i * 12 + 4, off, 6); put(raw, i * 12 + 10, e.crc, 2);
    if (e.type < 4) maxlen = Math.max(maxlen, e.length);
    parts.push({ src: [e.offset, e.offset + e.length] }); off += e.length;
  }
  // ---- compressed map: 16 fixed 4-bit codes, no RLE
  const bitsFor = (v) => { let b = 0; while (Math.pow(2, b) <= v) b++; return b; };
  const lengthbits = bitsFor(maxlen), selfbits = bitsFor(maxself);
  const bw = new BitW(); bw.write(1, 4); bw.write(4, 4); bw.write(13, 4);
  for (let i = 0; i < c.hunks; i++) bw.write(raw[i * 12], 4);
  for (let i = 0; i < c.hunks; i++) {
    const t = raw[i * 12];
    if (t < 4) { bw.write((raw[i * 12 + 1] << 16) | (raw[i * 12 + 2] << 8) | raw[i * 12 + 3], lengthbits); bw.write((raw[i * 12 + 10] << 8) | raw[i * 12 + 11], 16); }
    else if (t === T.NONE) bw.write((raw[i * 12 + 10] << 8) | raw[i * 12 + 11], 16);
    else if (t === T.SELF) bw.write(be48(raw, i * 12 + 4), selfbits);
  }
  const comp = bw.bytes();
  const mapoff = off;
  const map = new Uint8Array(16 + comp.length);
  put(map, 0, comp.length, 4); put(map, 4, c.firstoffs, 6); put(map, 10, crc16(raw), 2);
  map[12] = lengthbits; map[13] = selfbits; map[14] = 0; map[15] = 0; map.set(comp, 16);
  parts.push({ data: map });
  // metadata must live before the first hunk (it is copied with that prefix)
  let metaoff = c.metaoff;
  if (c.meta.some((m) => m.off >= c.firstoffs || m.off < 124)) {
    // rewrite the chain after the map
    let mo = mapoff + map.length; metaoff = mo;
    c.meta.forEach((m, k) => {
      const b = new Uint8Array(16 + m.data.length); b.set(m.tag, 0); b[4] = m.flags; put(b, 5, m.data.length, 3);
      const nxt = k === c.meta.length - 1 ? 0 : mo + b.length; put(b, 8, nxt, 8); b.set(m.data, 16); parts.push({ data: b }); mo += b.length;
    });
  }
  // overall SHA-1 = sha1(rawsha1 + sorted(tag + sha1(data)) for checksummed metadata)
  const mh = c.meta.filter((m) => m.flags & 1).map((m) => { const x = new Uint8Array(24); x.set(m.tag, 0); x.set(sha1(m.data), 4); return x; });
  mh.sort((a, b) => { for (let i = 0; i < 24; i++) if (a[i] !== b[i]) return a[i] - b[i]; return 0; });
  const s2 = new SHA1().update(rawsha1); mh.forEach((x) => s2.update(x)); const overall = s2.digest();
  const hdr = Uint8Array.from(c.header);
  put(hdr, 40, mapoff, 8); put(hdr, 48, metaoff, 8); hdr.set(rawsha1, 64); hdr.set(overall, 84);
  parts[0].data = hdr;
  return { parts, rawsha1: hex(rawsha1), sha1: hex(overall), modifiedHunks: Array.from(modified.keys()) };
}

// ---------------------------------------------------------------- stored ZIP
function zipStored(name, size, crc) {
  const enc = new TextEncoder().encode(name);
  const lh = new Uint8Array(30 + enc.length), dv = new DataView(lh.buffer);
  dv.setUint32(0, 0x04034b50, true); dv.setUint16(4, 20, true); dv.setUint16(6, 0x0800, true); dv.setUint16(8, 0, true);
  dv.setUint32(14, crc, true); dv.setUint32(18, size, true); dv.setUint32(22, size, true); dv.setUint16(26, enc.length, true); lh.set(enc, 30);
  const cd = new Uint8Array(46 + enc.length), dc = new DataView(cd.buffer);
  dc.setUint32(0, 0x02014b50, true); dc.setUint16(4, 20, true); dc.setUint16(6, 20, true); dc.setUint16(8, 0x0800, true);
  dc.setUint32(16, crc, true); dc.setUint32(20, size, true); dc.setUint32(24, size, true); dc.setUint16(28, enc.length, true); dc.setUint32(42, 0, true); cd.set(enc, 46);
  const eocd = new Uint8Array(22), de = new DataView(eocd.buffer);
  de.setUint32(0, 0x06054b50, true); de.setUint16(8, 1, true); de.setUint16(10, 1, true); de.setUint32(12, cd.length, true); de.setUint32(16, lh.length + size, true);
  return { head: lh, tail: [cd, eocd] };
}

return { crc32, crc16, sha1, SHA1, hex, inflateRaw, lzmaDecode, flacDecode, fixMode1, eccGenerate, chdOpen, chdReadHunk, patchBin, patchChd, applyOptions, zipStored, FRAME, SECTOR };
})();
if (typeof module !== 'undefined') module.exports = PC;
