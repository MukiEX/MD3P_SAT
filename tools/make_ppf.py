#!/usr/bin/env python3
"""PPF 3.0 patch (no validation block, no undo) between two equal-size images."""
import sys
def make_ppf(orig, new, desc):
    assert len(orig) == len(new)
    out = bytearray(b'PPF30' + bytes([2]) + desc.encode('ascii')[:50].ljust(50, b' ') + bytes([0, 0, 0, 0]))
    i = 0
    while i < len(orig):
        if orig[i] != new[i]:
            j = i
            while j < len(orig) and j - i < 255 and (orig[j] != new[j] or (j + 1 < len(orig) and orig[j+1] != new[j+1] and j - i < 254)):
                j += 1
            out += i.to_bytes(8, 'little') + bytes([j - i]) + new[i:j]
            i = j
        else: i += 1
    return bytes(out)
def apply_ppf(orig, ppf):
    img = bytearray(orig); assert ppf[:5] == b'PPF30'; p = 60
    while p < len(ppf):
        off = int.from_bytes(ppf[p:p+8], 'little'); n = ppf[p+8]; img[off:off+n] = ppf[p+9:p+9+n]; p += 9 + n
    return bytes(img)
if __name__ == '__main__':
    o = open(sys.argv[1], 'rb').read(); n = open(sys.argv[2], 'rb').read()
    ppf = make_ppf(o, n, sys.argv[4] if len(sys.argv) > 4 else 'MD3 Saturn Paddle Edition')
    assert apply_ppf(o, ppf) == n
    open(sys.argv[3], 'wb').write(ppf); print(len(ppf), 'bytes')
