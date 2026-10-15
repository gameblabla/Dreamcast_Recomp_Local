#!/usr/bin/env python3
"""portlint.py: cheap static checks of a C port (+ wrapper) against the retail asm facts, BEFORE spending an emulator run. Stdlib only.

  python3 -I tools/portlint.py 0x8c073f72 port/fn_8c073f72.c [--wrapper W.c] [--spec SPEC.json]

Findings are WARN (probably wrong) or ERROR (cannot be right). Exit 1 on any ERROR. These are the mistakes seen from a local 27B model:
  - a stride / offset / size constant loaded by the asm (e.g. 0x630) that never appears in the port: the port invented its own (0x84 was used instead)
  - a field read width (mov.w = 16 bit) with no int16_t/uint16_t anywhere in the port: u8 was used where the asm reads an s16
  - a stubbed callee reported with fewer argument registers than the spec compares, or reported with a literal where the asm passes an inherited value
  - unfinished markers (#error, TODO, FIXME, 'not implemented') and CONFIRMED/PROVEN claims inside the port file
"""
import argparse, json, os, re, sys

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
import dcfacts


def strip_c(src):
    src = re.sub(r'/\*.*?\*/', ' ', src, flags=re.S)
    return re.sub(r'//[^\n]*', ' ', src)


def numbers(src):
    out = set()
    for m in re.finditer(r'(?<![\w.])(0[xX][0-9a-fA-F]+|\d+)[uUlL]*(?![\w.])', src):
        try:
            out.add(int(m.group(1), 0))
        except ValueError:
            pass
    return out


def lint(addr, port_paths, wrapper=None, spec=None):
    f = dcfacts.facts(addr)
    errs, warns = [], []
    port_paths = list(port_paths) + [p[:-2] + '.h' for p in port_paths if p.endswith('.c') and os.path.exists(p[:-2] + '.h')]     # constants often live in the header
    raw = ''.join(open(p).read() for p in port_paths)
    code = strip_c(raw)
    nums = numbers(code) | numbers(strip_c(open(wrapper).read()) if wrapper and os.path.exists(wrapper) else '')
    for m in re.finditer(r'\b(?:f?printf|puts|fputs|perror|putchar)\s*\(', code):
        errs.append('debug output (%s) in the port: ports are pure functions of their inputs; print nothing (use the mismatch report of autodiff, or the `trace`)' % m.group(0).strip('( '))
        break
    lo_hi = [int(x, 16) for x in re.findall(r'^[> ]([0-9a-f]{8}):', f['text'], flags=re.M)]
    if lo_hi:
        lo, hi = min(lo_hi), max(lo_hi) + 0x48        # + the literal pool that trails the code
        for m in re.finditer(r'ad_(?:rd|mem|wr)\w*\(\s*(?:\(\w+\s*\*?\))?\s*(0[xX][0-9a-fA-F]+)', code):
            v = int(m.group(1), 16)
            if lo <= v <= hi:
                errs.append('the port reads %#x which is INSIDE the retail function (code / literal pool %#x..%#x). Literal-pool constants are embedded in the port as plain numbers: '
                            'see the `=>` / `[literal at ...]` values in `sh4_annotate.py`, or `readmem.py %#x`. Never declare code as a spec region (the emulator would overwrite the constants).' % (v, lo, hi, v))
                break
    if re.search(r'ad_rd\w*\(\s*ad_rd', code):
        errs.append('nested ad_rd(ad_rd(...)): that dereferences a VALUE as an address. `mova` / `mov.l <pool>,rN` loads a constant or an address ONCE; a second load happens only if the asm has a second `mov.l @rN`')
    for m in re.finditer(r'#\s*error|\bTODO\b|\bFIXME\b|not implemented|XXX', raw):
        errs.append('unfinished marker %r in the port' % m.group(0))
        break
    if re.search(r'\b(CONFIRMED|PROVEN|VERIFIED)\b', raw) and not os.path.exists(os.path.join(os.path.dirname(HERE), 'work', 'proofs', '%08x.json' % addr)):
        warns.append('the port claims CONFIRMED/PROVEN/VERIFIED but no proof ledger exists for this function (work/proofs/%08x.json): claims need a RESULT: PROVEN run' % addr)
    seen = set()
    for c in f['consts']:
        v = c['value']
        sv = v - (1 << 32) if v & 0x80000000 else v
        if c['kind'] == 'literal-pool' and (0x18 <= v <= 0x4000):
            if v not in nums and v not in seen:
                warns.append('constant 0x%x (%d) loaded from the literal pool at %08x (a stride/size/bound) does not appear in the port: if your code uses another number, it is wrong' % (v, v, c['addr']))
        elif c['kind'] == 'imm' and 0x10 <= v < 0x100 and v not in nums and v not in seen:
            warns.append('immediate 0x%x used at %08x (field offset / mask / bound) does not appear in the port' % (v, c['addr']))
        seen.add(v)
    for w, offs in f['offsets'].items():
        for o in offs:
            if o not in nums and o >= 0x10:
                warns.append('retail accesses offset +0x%x (%d-byte access) but the port never uses that offset' % (o, w))
    for t in re.findall(r'mov\.w\s+@', f['text']):      # data loads only (a mov.w from the literal pool is just a constant)
        if not re.search(r'int16_t|uint16_t|short', code):
            warns.append('retail has 16-bit loads (mov.w, sign-extended) but the port has no int16_t/uint16_t/short: a wrong width gives silently wrong values')
        break
    if wrapper and spec:
        w = strip_c(open(wrapper).read())
        for c in spec.get('callees', []):
            m = re.findall(r'ad_call\(\s*(?:0x)?%s\s*,[^,]+,\s*(\d+)\s*,[^,]+,\s*(\d+)' % re.escape(str(c['addr']).lower().replace('0x', '')), w, flags=re.I)
            if not m:
                warns.append('wrapper never calls ad_call for callee %s that the spec stubs' % c['addr'])
            else:
                for ni, nf in m:
                    if int(ni) != c.get('ints', 0) or int(nf) != c.get('floats', 0):
                        errs.append('wrapper reports callee %s with %s ints/%s floats but the spec compares %d/%d' % (c['addr'], ni, nf, c.get('ints', 0), c.get('floats', 0)))
    return errs, warns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('addr'); ap.add_argument('port', nargs='+'); ap.add_argument('--wrapper'); ap.add_argument('--spec')
    a = ap.parse_args()
    spec = json.load(open(a.spec)) if a.spec else None
    errs, warns = lint(int(a.addr, 16), a.port, a.wrapper or (spec['port']['wrapper'] if spec else None), spec)
    for e in errs:
        print('ERROR ' + e)
    for w in warns:
        print('WARN  ' + w)
    print('portlint %s: %d error(s), %d warning(s)' % (a.addr, len(errs), len(warns)))
    sys.exit(1 if errs else 0)


if __name__ == '__main__':
    main()
