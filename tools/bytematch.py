#!/usr/bin/env python3
"""bytematch.py: compare a compiled C function with the retail bytes. Game-independent. Needs an SH objdump (sh-elf-objdump).

  python3 -I tools/bytematch.py --addr 8c06fac4 --len 96 --src fn.c --func fn_8c06fac4 [--cc 'CMD {src} {obj}'] [--bin 1ST_READ.BIN --base 0x8c010000]
  python3 -I tools/bytematch.py --addr ... --len ... --cand-bin candidate.bin            (candidate bytes already extracted, e.g. from an SHC object)

Default compiler (no --cc / DR_CC / --cand-bin): tools/shc.py = the ORIGINAL Hitachi SHC from your SDK (SDK_DIRS / DR_SHC_DIR, run under wine),
linked at --addr so branch/literal layout lines up; WITHOUT an SDK it falls back to sh-elf-gcc and the verdict line is tagged `compiler=GCC`
(structure-only hint, never a proof of matching). --gcc forces the fallback, --shc-flags=OPTS adds SHC options (use the = form),
--syms FILE (or `//@sym NAME 0xADDR` lines in the C) defines absolute extern symbols at their retail addresses.
Custom compiler: --cc or env DR_CC, with {src} and {obj}, e.g. `sh-elf-gcc -O2 -m4-single-only -ml -c {src} -o {obj}` (ELF .text). The comparison is on instruction streams:
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


def disasm(raw, tmp, pad=0):
    """objdump computes pc-relative targets from the file start, so a function at 2 mod 4 gets wrong literal slots: pad it back to its real alignment."""
    p = os.path.join(tmp, 'x.bin')
    open(p, 'wb').write(b'\0' * pad + raw)
    out = subprocess.run([OBJDUMP, '-b', 'binary', '-m', 'sh4', '-EL', '-D', p], capture_output=True, text=True).stdout
    lines = []
    for ln in out.splitlines():
        m = re.match(r'\s*([0-9a-f]+):\s+((?:[0-9a-f]{2} ){2})\s*(.*)$', ln)
        if m:
            if int(m.group(1), 16) >= pad:
                lines.append((int(m.group(1), 16) - pad, m.group(2).strip(), m.group(3).strip()))
    return lines


def norm(ins, raw=None, pad=0):
    """Mask layout-only differences. Literal-pool loads keep their VALUE (read from raw at the pool slot), so a wrong global/call address is a DIFF."""
    m = re.match(r'^(mov\.[wl])\s+(?:0x)?([0-9a-f]+),(r\d+)$', re.sub(r'!.*$', '', ins).strip())
    if m and raw is not None:
        n = 4 if m.group(1) == 'mov.l' else 2
        o = int(m.group(2), 16)
        if 0 <= o and o + n <= len(raw):
            return '%s @(pc)=0x%x,%s' % (m.group(1), int.from_bytes(raw[o:o + n], 'little'), m.group(3))
    t = re.sub(r'!.*$', '', ins).strip()
    t = re.sub(r'@\(0x[0-9a-f]+,pc\)|@\([0-9a-f]+,pc\)', '@(pc)', t)
    t = re.sub(r'^(b[tf][/.]s|b[tf]|bra|bsr)\s+\S+', r'\1 TARGET', t)
    t = re.sub(r'^(mov\.[wl])\s+(?:0x)?[0-9a-f]+,(r\d+)$', r'\1 @(pc),\2', t)      # objdump prints pc-relative literal loads as a bare address
    t = re.sub(r'^mova\s+\S+', 'mova @(pc)', t)
    return re.sub(r'\s+', ' ', t)


KIND = ['custom']
PAD = [0]


def cand_bytes(a, tmp):
    if a.cand_bin:
        return open(a.cand_bin, 'rb').read()
    if not (a.cc or os.environ.get('DR_CC')):
        sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
        import shc
        ns = argparse.Namespace(flags=a.shc_flags or '', opt=None, syms=a.syms)
        raw, KIND[0], syms = shc.compile_to_bytes(os.path.abspath(a.src), a.func, int(a.addr, 16), ns, a.gcc)
        PAD[0] = (syms.get((a.func or '').lstrip('_'), 0)) & 3
        return raw
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


def tag_kind():
    return {'GCC': 'GCC(fallback: NOT the original compiler, a match here proves nothing)'}.get(KIND[0], KIND[0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--addr', required=True); ap.add_argument('--len', type=int, required=True)
    ap.add_argument('--bin', default=os.environ.get('DR_BIN', os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'game', '1ST_READ.BIN')))
    ap.add_argument('--base', default=os.environ.get('DR_BASE', '0x8c010000'))
    ap.add_argument('--src'); ap.add_argument('--func'); ap.add_argument('--cc'); ap.add_argument('--cand-bin'); ap.add_argument('--gcc', action='store_true'); ap.add_argument('--shc-flags'); ap.add_argument('--syms')
    a = ap.parse_args()
    if not (a.src or a.cand_bin):
        sys.exit(__doc__)
    addr = int(a.addr, 16)
    retail_ext = open(a.bin, 'rb').read()[addr - int(a.base, 16):][:a.len + 0x400]
    retail = retail_ext[:a.len]
    with tempfile.TemporaryDirectory() as tmp:
        cand = cand_bytes(a, tmp)[:a.len + 0x400]
        rpad = addr & 3
        R, C = disasm(retail, tmp, rpad), disasm(cand[:a.len], tmp, PAD[0]) if cand else []
        if cand[:a.len] == retail:
            print('BYTEMATCH %08x EXACT score=0 compiler=%s' % (addr, tag_kind())); return
        rn, cn = [norm(x[2], b'\0' * rpad + retail_ext, rpad) for x in R], [norm(x[2], b'\0' * PAD[0] + cand, PAD[0]) for x in C]
        sm = difflib.SequenceMatcher(None, rn, cn, autojunk=False)
        diffs = sum(max(i2 - i1, j2 - j1) for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != 'equal')
        if diffs == 0 and len(rn) == len(cn):
            print('BYTEMATCH %08x NORMALIZED score=0 compiler=%s  (same instructions; only pool layout / displacements differ)' % (addr, tag_kind())); return
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag != 'equal':
                print('first difference at retail +0x%x (instruction %d):' % (R[i1][0] if i1 < len(R) else len(retail), i1))
                for k in range(max(0, i1 - 2), min(len(R), i2 + 2)):
                    print('  retail  +%04x  %s' % (R[k][0], R[k][2]))
                print('  ---')
                for k in range(max(0, j1 - 2), min(len(C), j2 + 2)):
                    print('  cand    +%04x  %s' % (C[k][0], C[k][2]))
                break
        print('BYTEMATCH %08x DIFF %d score=%d compiler=%s  (retail %d instr, candidate %d instr)' % (addr, diffs, diffs, tag_kind(), len(rn), len(cn)))


if __name__ == '__main__':
    main()
