"""Tiny SH-2 control-flow decoder used for reachability / free-space analysis."""
import struct

def s8(v): return v - 256 if v & 0x80 else v
def s12(v): return v - 4096 if v & 0x800 else v

class Image:
    def __init__(s, data, base):
        s.d = data; s.base = base; s.end = base + len(data)
    def inside(s, a): return s.base <= a < s.end
    def u16(s, a): o = a - s.base; return struct.unpack('>H', s.d[o:o + 2])[0]
    def u32(s, a): o = a - s.base; return struct.unpack('>I', s.d[o:o + 4])[0]

def decode(op, pc):
    """Return (kind, info) for control-relevant instructions.
    kinds: 'bra','bsr' (target, delayed), 'bcc' (target, delayed?), 'ret' (delayed),
    'jmp','jsr' (reg, delayed), 'braf','bsrf' (reg), 'lit32' (addr), 'lit16' (addr), 'mova' (addr), None"""
    hi = op >> 12
    if hi == 0xA: return ('bra', pc + 4 + s12(op & 0xFFF) * 2, True)
    if hi == 0xB: return ('bsr', pc + 4 + s12(op & 0xFFF) * 2, True)
    if (op & 0xFF00) in (0x8900, 0x8B00): return ('bcc', pc + 4 + s8(op & 0xFF) * 2, False)
    if (op & 0xFF00) in (0x8D00, 0x8F00): return ('bcc', pc + 4 + s8(op & 0xFF) * 2, True)
    if op in (0x000B, 0x002B): return ('ret', None, True)
    if (op & 0xF0FF) == 0x402B: return ('jmp', (op >> 8) & 15, True)
    if (op & 0xF0FF) == 0x400B: return ('jsr', (op >> 8) & 15, True)
    if (op & 0xF0FF) == 0x0023: return ('braf', (op >> 8) & 15, True)
    if (op & 0xF0FF) == 0x0003: return ('bsrf', (op >> 8) & 15, True)
    if hi == 0xD: return ('lit32', ((pc & ~3) + 4 + (op & 0xFF) * 4), (op >> 8) & 15)
    if hi == 0x9: return ('lit16', pc + 4 + (op & 0xFF) * 2, (op >> 8) & 15)
    if (op & 0xFF00) == 0xC700: return ('mova', ((pc & ~3) + 4 + (op & 0xFF) * 4), None)
    if op == 0x001B: return ('sleep', None, False)
    return (None, None, None)

# opcodes that are illegal / never emitted (helps reject data)
def plausible(op):
    hi = op >> 12; lo = op & 0xF
    if op == 0: return False
    if hi == 0:
        if lo in (2,): return ((op >> 4) & 0xF) in (0, 1, 2)
        if lo in (3,): return ((op >> 4) & 0xF) in (0, 2)
        if lo in (4, 5, 6, 7, 0xC, 0xD, 0xE, 0xF): return True
        if lo == 8: return op in (0x0008, 0x0018, 0x0028)
        if lo == 9: return op in (0x0009, 0x0019) or (op & 0xF0FF) == 0x0029
        if lo == 0xA: return ((op >> 4) & 0xF) in (0, 1, 2)
        if lo == 0xB: return op in (0x000B, 0x001B, 0x002B)
        return False
    if hi == 4:
        x = op & 0xFF
        return x in (0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0E, 0x10, 0x11, 0x12, 0x13, 0x15, 0x16, 0x17,
                     0x18, 0x19, 0x1A, 0x1B, 0x1E, 0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x29, 0x2A, 0x2B, 0x2E) or lo in (0xC, 0xD, 0xF)
    if hi == 8: return ((op >> 8) & 0xF) in (0, 1, 4, 5, 8, 9, 0xB, 0xD, 0xF)
    if hi == 3: return lo not in (1, 9)
    if hi == 6: return True
    if hi == 2: return lo != 3
    if hi == 0xC: return True
    if hi == 0xF: return False
    return True

def is_prologue(op):
    return (op & 0xF00F) == 0x2006 and (op & 0x00F0) >> 4 != 15 and (op & 0x0F00) == 0x0F00 or op == 0x4F22 or (op & 0xFF00) == 0x7F00 and (op & 0x80)
