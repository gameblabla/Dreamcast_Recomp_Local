#!/usr/bin/env python3
"""bytematch.py: compare a compiled C function with the retail bytes. Game-independent. Needs an SH objdump (sh-elf-objdump).

  python3 -I tools/bytematch.py --addr 8c06fac4 --len 96 --src fn.c --func fn_8c06fac4 [--cc 'CMD {src} {obj}'] [--bin 1ST_READ.BIN --base 0x8c010000]
  python3 -I tools/bytematch.py --addr ... --len ... --cand-bin candidate.bin            (candidate bytes already extracted, e.g. from an SHC object)

Compiler command: --cc or env DR_CC, with {src} and {obj}; default `sh-elf-gcc -O2 -m4-single-only -ml -c {src} -o {obj}`.
For the ORIGINAL compiler (Hitachi SHC from the SDK) wrap it in your command (wine/wibo) and extract the function bytes yourself
(--cand-bin); see docs/BYTE_MATCHING.md. The comparison is on instruction streams:
  EXACT       identical bytes
  NORMALIZED  identical once literal-pool displacements, pc-relative loads and branch displacements are masked (the layout of the
              pool and the final link address differ in an isolated object: this is what 'matching' means before linking)
  DIFF n      n instructions differ; the first one is printed with context
Prints a final line `BYTEMATCH <addr> <verdict> score=<n>` (score 0 = exact/normalized; used by tools/permute.py).
"""
import argparse, difflib, os, re, shlex, subprocess, sys, tempfile

OBJDUMP = os.environ.get('DR_OBJDUMP', 'sh-elf-objdump')
OBJCOPY = os.environ.get('DR_OBJCOPY', 'sh-elf-objcopy')
NM = os.environ.get('DR_NM', 'sh-elf-nm')
DEFAULT_CC = 'sh-elf-gcc -O2 -m4-single-only -ml -c {src} -o {obj}'


def disasm(raw, tmp):
    p = os.path.join(tmp, 'x.bin')
    open(p, 'wb').write(raw)
    out = subprocess.run([OBJDUMP, '-b', 'binary', '-m', 'sh4', '-EL', '-D', p], capture_output=True, text=True).stdout
    lines = []
    for ln in out.splitlines():
        m = re.match(r'\s*([0-9a-f]+):\s+((?:[0-9a-f]{2} ){2})\s*(.*)$', ln)
        if m:
            lines.append((int(m.group(1), 16), m.group(2).strip(), m.group(3).strip()))
    return lines


def norm(ins):
    t = re.sub(r'!.*$', '', ins).strip()
    t = re.sub(r'@\(0x[0-9a-f]+,pc\)|@\([0-9a-f]+,pc\)', '@(pc)', t)
    t = re.sub(r'^(b[tf][/.]s|b[tf]|bra|bsr)\s+\S+', r'\1 TARGET', t)
    t = re.sub(r'^mova\s+\S+', 'mova @(pc)', t)
    return re.sub(r'\s+', ' ', t)


def cand_bytes(a, tmp):
    if a.cand_bin:
        return open(a.cand_bin, 'rb').read()
    obj = os.path.join(tmp, 'c.o')
    cc = (a.cc or os.environ.get('DR_CC') or DEFAULT_CC).format(src=a.src, obj=obj)
    r = subprocess.run(cc, shell=True, capture_output=True, text=True)
    if r.returncode:
        sys.exit('compile failed:\n' + (r.stderr or r.stdout)[-2000:])
    raw_p = os.path.join(tmp, 'c.bin')
    subprocess.run([OBJCOPY, '-O', 'binary', '-j', '.text', obj, raw_p], check=True)
    raw = open(raw_p, 'rb').read()
    off = 0
    if a.func:
        nm = subprocess.run([NM, obj], capture_output=True, text=True).stdout
        m = re.search(r'^([0-9a-f]+)\s+[Tt]\s+_?%s$' % re.escape(a.func), nm, re.M)
        if m:
            off = int(m.group(1), 16)
    return raw[off:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--addr', required=True); ap.add_argument('--len', type=int, required=True)
    ap.add_argument('--bin', default=os.environ.get('DR_BIN', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'game', '1ST_READ.BIN')))
    ap.add_argument('--base', default=os.environ.get('DR_BASE', '0x8c010000'))
    ap.add_argument('--src'); ap.add_argument('--func'); ap.add_argument('--cc'); ap.add_argument('--cand-bin')
    a = ap.parse_args()
    if not (a.src or a.cand_bin):
        sys.exit(__doc__)
    addr = int(a.addr, 16)
    retail = open(a.bin, 'rb').read()[addr - int(a.base, 16):][:a.len]
    with tempfile.TemporaryDirectory() as tmp:
        cand = cand_bytes(a, tmp)[:a.len + 8]
        R, C = disasm(retail, tmp), disasm(cand[:a.len], tmp) if cand else []
        if cand[:a.len] == retail:
            print('BYTEMATCH %08x EXACT score=0' % addr); return
        rn, cn = [norm(x[2]) for x in R], [norm(x[2]) for x in C]
        sm = difflib.SequenceMatcher(None, rn, cn, autojunk=False)
        diffs = sum(max(i2 - i1, j2 - j1) for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != 'equal')
        if diffs == 0 and len(rn) == len(cn):
            print('BYTEMATCH %08x NORMALIZED score=0   (same instructions; only pool layout / displacements differ)' % addr); return
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag != 'equal':
                print('first difference at retail +0x%x (instruction %d):' % (R[i1][0] if i1 < len(R) else len(retail), i1))
                for k in range(max(0, i1 - 2), min(len(R), i2 + 2)):
                    print('  retail  +%04x  %s' % (R[k][0], R[k][2]))
                print('  ---')
                for k in range(max(0, j1 - 2), min(len(C), j2 + 2)):
                    print('  cand    +%04x  %s' % (C[k][0], C[k][2]))
                break
        print('BYTEMATCH %08x DIFF %d score=%d  (retail %d instr, candidate %d instr)' % (addr, diffs, diffs, len(rn), len(cn)))


if __name__ == '__main__':
    main()
