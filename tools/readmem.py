#!/usr/bin/env python3
"""readmem.py: read retail memory at a VIRTUAL ADDRESS (the only safe way to look at constants, tables and literal pools). Stdlib only.

  python3 -I tools/dc/readmem.py 0x8c04ca18            # 16 bytes as hex + u16/s16/u32/s32/f32 views
  python3 -I tools/dc/readmem.py 0x8c04ca18 32 --as f32
  python3 -I tools/dc/readmem.py --file-offset 0x8c04ca18   # -> the file offset (address - load base)

WHY THIS EXISTS: a local model once opened 1ST_READ.BIN with the LOW BITS of an address as the file offset (0x4ca24 instead of
0x8c04ca24 - 0x8c010000 = 0x3ca24), read garbage, concluded "the binary on disk is corrupt / differs from Ghidra" and burned 70 tool calls.
The file is correct, the offset was wrong. Never open the .BIN by hand (python -c open(...)): use this tool, or `sh4_annotate.py`, which
already prints every literal-pool value (`=> r5 = 1584`, `fr3 = 25.0f`).
"""
import argparse, os, struct, sys

HERE = os.path.dirname(os.path.realpath(__file__))


def find_image():
    if os.environ.get('DR_BIN') and os.path.exists(os.environ['DR_BIN']):
        return os.environ['DR_BIN']
    for up in ('..', '../..', '../../..'):
        root = os.path.abspath(os.path.join(HERE, up))
        for rel in ('game/1ST_READ.BIN', 'game/Track_3/1ST_READ.BIN'):
            p = os.path.join(root, rel)
            if os.path.exists(p):
                return p
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('addr'); ap.add_argument('len', nargs='?', type=lambda x: int(x, 0), default=16)
    ap.add_argument('--as', dest='fmt', choices=['hex', 'u8', 'u16', 's16', 'u32', 's32', 'f32'], default='hex')
    ap.add_argument('--file-offset', action='store_true', help='only print the file offset for the address')
    ap.add_argument('--bin'); ap.add_argument('--base', default=os.environ.get('DR_BASE', '0x8c010000'))
    a = ap.parse_args()
    base = int(a.base, 16)
    addr = int(a.addr, 0)
    if addr < base:
        sys.exit('readmem: %#x is below the load base %#x. It must be a RAM address like 0x8c04ca18. If you took it from a file offset, the address is offset + %#x.\n'
                 '  If you truncated an address (0x8c04ca24 -> 0x4ca24) use the FULL address; the file offset of 0x8c04ca24 is %#x.' % (addr, base, base, 0x8c04ca24 - base))
    off = addr - base
    if a.file_offset:
        print('%#x' % off)
        return
    binp = a.bin or find_image()
    if not binp:
        sys.exit('readmem: 1ST_READ.BIN not found (set DR_BIN=/path/1ST_READ.BIN)')
    data = open(binp, 'rb').read()
    if off + a.len > len(data):
        sys.exit('readmem: %#x..%#x is outside the image (%d bytes at base %#x). RAM outside the executable (heap, globals set at run time) cannot be read from the file:\n'
                 '  declare it as a region in the spec instead.' % (addr, addr + a.len, len(data), base))
    chunk = data[off:off + a.len]
    print('# %s  file offset %#x  (address %#x - base %#x)' % (os.path.basename(binp), off, addr, base))
    step = {'hex': 4, 'u8': 1, 'u16': 2, 's16': 2, 'u32': 4, 's32': 4, 'f32': 4}[a.fmt]
    for i in range(0, len(chunk), 16 if a.fmt == 'hex' else step):
        row = chunk[i:i + (16 if a.fmt == 'hex' else step)]
        line = '%08x: %s' % (addr + i, row.hex())
        if a.fmt == 'hex':
            for j in range(0, len(row) - 3, 4):
                w = int.from_bytes(row[j:j + 4], 'little')
                f = struct.unpack('<f', struct.pack('<I', w))[0]
                line += '\n    +%x  u32=%d (0x%08x)  s32=%d  f32=%s  u16=[%d,%d]' % (j, w, w, w - (1 << 32) if w >> 31 else w, ('%g' % f), w & 0xffff, w >> 16)
        elif len(row) == step:
            v = int.from_bytes(row, 'little', signed=a.fmt.startswith('s'))
            line += '   %s=%s' % (a.fmt, ('%g' % struct.unpack('<f', row)[0]) if a.fmt == 'f32' else v)
        print(line)


if __name__ == '__main__':
    main()
