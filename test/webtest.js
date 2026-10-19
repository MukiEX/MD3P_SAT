// node test/webtest.js : exercises web/patchcore.js on the BIN and the CHD fixture
const fs = require('fs'), PC = require('../web/patchcore.js'), PATCH = require('../web/patchdata.js');
PATCH.sectors.forEach((s) => { if (typeof s.data === 'string') s.data = Uint8Array.from(Buffer.from(s.data, 'base64')); });
function reader(path) {
  const fd = fs.openSync(path, 'r'), size = fs.fstatSync(fd).size;
  return { size, read: (off, len) => { const b = Buffer.alloc(len); fs.readSync(fd, b, 0, len, off); return new Uint8Array(b.buffer, b.byteOffset, len); } };
}
function assemble(parts, rd, out) {
  const fd = fs.openSync(out, 'w'); let crc = 0, size = 0;
  for (const p of parts) {
    let d = p.data;
    if (!d) { const [a, b] = p.src; for (let o = a; o < b; o += 1 << 22) { const x = rd.read(o, Math.min(1 << 22, b - o)); crc = PC.crc32(x, crc); size += x.length; fs.writeSync(fd, x); } continue; }
    crc = PC.crc32(d, crc); size += d.length; fs.writeSync(fd, d);
  }
  fs.closeSync(fd); return { crc, size };
}
const t0 = Date.now();
const mode = process.argv[2];
if (mode === 'bin') {
  const r = reader(process.argv[3]);
  const res = PC.patchBin(r.read, r.size, PATCH, process.argv[5] ? JSON.parse(process.argv[5]) : null);
  console.log(assemble(res.parts, r, process.argv[4]), Date.now() - t0, 'ms');
} else if (mode === 'chd') {
  const r = reader(process.argv[3]);
  const c = PC.chdOpen(r.read, r.size);
  console.log('hunks', c.hunks, 'comps', c.comps, 'meta', c.meta.length, 'firstoffs', c.firstoffs);
  const res = PC.patchChd(c, PATCH, process.argv[5] ? JSON.parse(process.argv[5]) : null, null);
  console.log('modified', res.modifiedHunks, 'raw', res.rawsha1, 'sha1', res.sha1);
  console.log(assemble(res.parts, r, process.argv[4]), Date.now() - t0, 'ms');
} else if (mode === 'decode') {   // decode every hunk and compare with a raw dump
  const r = reader(process.argv[3]); const c = PC.chdOpen(r.read, r.size); const raw = fs.readFileSync(process.argv[4]);
  let bad = 0; for (let i = 0; i < c.hunks; i++) { const d = PC.chdReadHunk(c, i); const ref = raw.subarray(i * c.hunkbytes, (i + 1) * c.hunkbytes); for (let k = 0; k < ref.length; k++) if (d[k] !== ref[k]) { bad++; console.log('hunk', i, 'type', c.entry(i).type, 'differs at', k); break; } }
  console.log('decode mismatches', bad, Date.now() - t0, 'ms');
}
