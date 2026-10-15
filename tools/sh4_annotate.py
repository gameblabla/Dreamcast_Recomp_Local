#!/usr/bin/env python3
"""sh4_annotate.py: make an SH-4 function listing readable for a lift to C. Game-independent.

  python3 -I tools/dc/sh4_annotate.py 0x8c06fac4                    # project asm windows + 1ST_READ.BIN
  python3 -I tools/dc/sh4_annotate.py --asm FILE.asm --func 8c06fac4 --bin IMAGE.BIN --base 0x8c010000

What it adds to the raw listing (all things a model gets wrong when it guesses):
  1. LITERALS : `mov.w/mov.l <poolAddr>,rN` lines get the VALUE read from the binary (mov.w is sign-extended).
                A mov.w pool value is usually a loop stride / size / offset: never guess it.
  2. CALLS    : one row per jsr/bsr: target, r4-r7 and fr4-fr11 values at the call (delay slot included),
                registers never set in the function are shown as `(inherited)`: those are the CALLER'S args passed through.
  3. SIGNATURE: which of r4-r7 / fr4-fr7 are read before written (= the function's own parameters) and whether
                r0 / fr0 is set before `rts` (= return value).
  4. LOOPS    : backward branches (do/while shape), with the compare just before them.
Listing format (Ghidra export): `8c06fac4:<TAB>mnemonic operands<TAB>; comment`, delay-slot lines start with `_`.
"""
import argparse, os, re, struct, sys

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
LINE = re.compile(r'^([0-9a-f]{8}):\s+(_?)(\S+)\s*([^;]*?)\s*(?:;\s*(.*))?$')


def load_func(asm_dir, addr):
    path = os.path.join(asm_dir, '%08x.asm' % (addr & 0xffff0000))
    out, on = [], False
    for ln in open(path).read().split('\n'):
        if ln.startswith('; ===== '):
            if on:
                break
            on = ('@ %08x' % addr) in ln
            continue
        if on and ln.strip():
            out.append(ln)
    return out


def parse(lines):
    ins = []
    for ln in lines:
        m = LINE.match(ln)
        if m:
            ins.append(dict(addr=int(m.group(1), 16), delay=bool(m.group(2)), op=m.group(3), args=m.group(4).strip(), cmt=m.group(5) or ''))
    return ins


def reg_reads_writes(i):
    """(reads, writes) of general/float registers for the common instruction shapes (enough for args/ret recovery)."""
    op, a = i['op'], [x.strip() for x in re.split(r',(?![^(]*\))', i['args'])] if i['args'] else []
    R = re.compile(r'\b(r\d+|fr\d+|dr\d+)\b')
    regs = lambda s: R.findall(s)
    stores = op.startswith(('mov.b', 'mov.w', 'mov.l', 'fmov')) and len(a) == 2 and '@' in a[1] and not a[1].startswith('@-r15') or op == 'mov.l' and len(a) == 2 and a[1].startswith('@-')
    if op.startswith(('mov', 'fmov')) and len(a) == 2:
        if stores:
            return regs(a[0]) + regs(a[1]), []
        if a[1].startswith('r') or a[1].startswith('fr') or a[1].startswith('dr'):
            rd = regs(a[0]) if '@' in a[0] or a[0].startswith(('r', 'fr', 'dr')) else []
            return rd, regs(a[1])
    if op in ('jsr', 'jmp', 'braf', 'bsrf'):
        return regs(i['args']), []
    if op.startswith(('mul', 'dmul', 'mac')) and len(a) == 2:      # multiply/MAC read both operands and write only MACH/MACL (never a general register)
        return regs(a[0]) + regs(a[1]), []
    if op in ('rts', 'nop') or op.startswith(('bra', 'bt', 'bf', 'bsr', 'sts', 'lds')):
        return [], []
    if op in ('fldi0', 'fldi1', 'float', 'ftrc') and a:
        return ([] if op.startswith('fldi') else regs(a[0])), regs(a[-1]) if op.startswith('fldi') else regs(a[-1])
    if a:   # ALU 2-operand: dst is read too except for mov-like / extu / exts / neg / not / swap
        dst = regs(a[-1])
        src = regs(a[0]) if len(a) > 1 else []
        pure = op.startswith(('extu', 'exts', 'neg', 'not', 'swap', 'mova', 'movt', 'mov'))
        if op.startswith(('cmp', 'tst')):
            return src + dst, []
        return src + ([] if pure else dst), dst
    return [], []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('addr', nargs='?')
    ap.add_argument('--asm'); ap.add_argument('--func'); ap.add_argument('--bin')
    ap.add_argument('--base', default=os.environ.get('DR_BASE', '0x8c010000'))
    ap.add_argument('--asm-dir', default=os.path.join(ROOT, 'work/research/asm'))
    a = ap.parse_args()
    base = int(a.base, 16)
    binp = a.bin or os.environ.get('DR_BIN', os.path.join(ROOT, 'game/1ST_READ.BIN'))
    image = open(binp, 'rb').read() if os.path.exists(binp) else b''
    if a.asm:
        lines = open(a.asm).read().split('\n')
        if a.func:
            lines = [l for l in lines if l.strip()]
    else:
        lines = load_func(a.asm_dir, int(a.addr, 16))
    ins = parse(lines)
    if not ins:
        sys.exit('no instructions parsed')

    def lit(addr, size):
        o = addr - base
        if o < 0 or o + size > len(image):
            return None
        return int.from_bytes(image[o:o + size], 'little', signed=(size == 2))

    targets = set()
    for i in ins:
        if i['op'] in ('bra', 'bt', 'bf', 'bt/s', 'bf/s') and re.match(r'0x[0-9a-f]+', i['args']):
            targets.add(int(i['args'].split()[0], 16))
    print('# ANNOTATED LISTING (literal values from the binary; `=>` marks what the tool resolved)')
    r0lit = None        # address loaded by the latest `mova <pool>,r0`; the following `fmov.s @r0,frN` / `mov.l @r0,rN` loads the VALUE stored there
    for i in ins:
        note = ''
        m = re.match(r'(mov\.[wl])\s+(0x[0-9a-f]{8}),(r\d+)', i['op'] + ' ' + i['args'])
        if m:
            v = lit(int(m.group(2), 16), 2 if m.group(1) == 'mov.w' else 4)
            if v is not None:
                note = '   => %s = %s (0x%x)' % (m.group(3), v, v & 0xffffffff)
        if i['addr'] in targets:
            r0lit = None
        cnote = ''
        if i['op'] == 'mova':
            mm = re.match(r'(0x[0-9a-f]+),r0$', i['args'])
            r0lit = int(mm.group(1), 16) if mm else None
        elif r0lit is not None:
            mm = re.match(r'@r0(\+)?,(f?r\d+)$', i['args'])
            if mm and i['op'] in ('fmov.s', 'mov.l', 'mov.w', 'mov.b'):
                size = {'fmov.s': 4, 'mov.l': 4, 'mov.w': 2, 'mov.b': 1}[i['op']]
                o = r0lit - base
                if 0 <= o and o + size <= len(image):
                    raw = int.from_bytes(image[o:o + size], 'little')
                    if i['op'] == 'fmov.s':
                        fv = struct.unpack('<f', struct.pack('<I', raw))[0]
                        cnote = '   ; => %s = %s (0x%08x) [literal at %08x]' % (mm.group(2), ('%gf' % fv), raw, r0lit)
                    else:
                        sv = raw - (1 << (8 * size)) if raw >> (8 * size - 1) else raw
                        cnote = '   ; => %s = %d (0x%x) [literal at %08x]' % (mm.group(2), sv, raw, r0lit)
            if 'r0' in reg_reads_writes(i)[1]:
                r0lit = None
        mark = '>' if i['addr'] in targets else ' '
        print('%s%08x: %s%-8s %-28s%s' % (mark, i['addr'], '_' if i['delay'] else ' ', i['op'], i['args'], note + (cnote or ('   ; ' + i['cmt'] if i['cmt'] and not note else ''))))

    f_lo, f_hi = min(x['addr'] for x in ins), max(x['addr'] for x in ins)
    # constant propagation, reset at branch targets
    state = {}
    maybe = {}         # register -> last instruction text that wrote it on SOME path (state is cleared at branch targets)
    def val(r):
        return state.get(r, '(inherited)')
    calls = []
    first_read, written = {}, set()
    loops = []
    clear_pending = False
    hist = []   # (addr, reg, value-string) of constant loads, for loop-bound lookup
    for idx, i in enumerate(ins):
        if clear_pending and not i['delay']:
            clear_pending = False
            for r in list(state):
                if r in ('r0', 'r1', 'r2', 'r3', 'r4', 'r5', 'r6', 'r7') or r.startswith('fr'):
                    del state[r]
        if i['addr'] in targets:
            state = {k: v for k, v in state.items() if False}
        rd, wr = reg_reads_writes(i)
        for r in rd:
            if r not in written and r not in first_read and re.fullmatch(r'r[4-7]|fr[4-9]|fr1[01]', r):
                first_read[r] = i['addr']
        op, ar = i['op'], i['args']
        m = re.match(r'(mov\.[wl])\s+(0x[0-9a-f]{8}),(r\d+)$', op + ' ' + ar)
        if m:
            v = lit(int(m.group(2), 16), 2 if m.group(1) == 'mov.w' else 4)
            state[m.group(3)] = '0x%x' % (v & 0xffffffff) if v is not None else '?'
            hist.append((i['addr'], m.group(3), state[m.group(3)]))
        elif op == 'mov' and re.match(r'#(-?0x[0-9a-f]+|-?\d+),(r\d+)$', ar):
            v, r = ar.split(',')
            state[r] = '0x%x' % (int(v[1:], 0) & 0xffffffff)
            hist.append((i['addr'], r, state[r]))
        elif op == 'mov' and re.match(r'(r\d+),(r\d+)$', ar):
            s, d = ar.split(',')
            state[d] = val(s) if s in state else s
        elif op == 'fldi1':
            state[ar.strip()] = '0x3f800000 (1.0f)'
        elif op == 'fldi0':
            state[ar.strip()] = '0x0 (0.0f)'
        elif op == 'add' and re.match(r'#(-?0x[0-9a-f]+|-?\d+),(r\d+)$', ar):
            v, r = ar.split(',')
            if r in state and re.fullmatch(r'0x[0-9a-f]+', state[r]):
                state[r] = '0x%x' % ((int(state[r], 16) + int(v[1:], 0)) & 0xffffffff)
            else:
                state[r] = '(%s %+d)' % (state.get(r, r), int(v[1:], 0))
        elif op == 'add' and re.match(r'(r\d+),(r\d+)$', ar):
            s, d = ar.split(',')
            state[d] = '(%s + %s)' % (state.get(d, d), state.get(s, s))
        elif wr:
            for r in wr:
                state[r] = '<%s %s @%08x>' % (op, ar, i['addr'])
        for r in wr:
            written.add(r)
            maybe[r] = '%s %s @%08x' % (op, ar, i['addr'])
        tgt0 = re.search(r'([0-9a-f]{8})<([^>]*)>', i['cmt'])
        is_tail = op == 'jmp' and tgt0 is not None and not (f_lo <= int(tgt0.group(1), 16) <= f_hi)   # jmp @rN to another function = tail call
        if op in ('jsr', 'bsr') or is_tail:
            # arguments include the delay slot instruction (executes before the callee starts)
            snap = dict(state)
            if idx + 1 < len(ins) and ins[idx + 1]['delay']:
                ds = ins[idx + 1]
                dop, dar = ds['op'], ds['args']
                m = re.match(r'#(-?0x[0-9a-f]+|-?\d+),(r\d+)$', dar) if dop == 'mov' else None
                if m:
                    snap[m.group(2)] = '0x%x (delay slot)' % (int(m.group(1), 0) & 0xffffffff)
                elif dop == 'mov' and re.match(r'(r\d+),(r\d+)$', dar):
                    s, d = dar.split(','); snap[d] = snap.get(s, s) + ' (delay slot)'
                else:
                    _, w2 = reg_reads_writes(ds)
                    for r in w2:
                        snap[r] = '<%s %s (delay slot)>' % (dop, dar)
            tgt = tgt0
            for k in range(4, 8):          # registers not known on this path but written on another path are NOT plain "inherited"
                if 'r%d' % k not in snap and 'r%d' % k in maybe:
                    snap['r%d' % k] = '(set on SOME path only: %s)' % maybe['r%d' % k]
            calls.append((i['addr'], tgt.group(1) if tgt else '?', ('TAIL ' if is_tail else '') + (tgt.group(2) if tgt else '?'), snap))
            clear_pending = True           # caller-saved registers die at a call (after its delay slot runs)
        if op in ('bt', 'bf', 'bt/s', 'bf/s', 'bra') and re.match(r'0x[0-9a-f]+', ar):
            t = int(ar.split()[0], 16)
            if t <= i['addr']:
                prev = ''.join('%08x %s %s; ' % (x['addr'], x['op'], x['args']) for x in ins[max(0, idx - 2):idx] if x['op'].startswith(('cmp', 'tst', 'dt')))
                loops.append((i['addr'], t, op, prev))

    print('\n# CALLS (args at the call incl. delay slot; `(inherited)` = never set here, passes the caller\'s own value)')
    for addr, t, name, st in calls:
        ints = ' '.join('r%d=%s' % (k, st.get('r%d' % k, '(inherited)')) for k in range(4, 8))
        fl = ' '.join('fr%d=%s' % (k, st['fr%d' % k]) for k in range(4, 12) if 'fr%d' % k in st)
        print('call @%08x -> %s %s: %s %s' % (addr, t, name, ints, fl))
    # suggested autodiff "callees" block (ints = r4.. count up to the last register the caller sets; floats likewise)
    sug = {}
    for addr, t, name, st in calls:
        ni = max([k - 3 for k in range(4, 8) if 'r%d' % k in st and not str(st['r%d' % k]).startswith('(set on SOME')] or [0])
        if name.startswith('TAIL '):           # a tail call hands the caller's whole register file to the callee: compare all of r4-r7
            ni = 4
        nf = max([k - 3 for k in range(4, 12) if 'fr%d' % k in st] or [0])
        o = sug.setdefault(t, [name, 0, 0])
        o[1], o[2] = max(o[1], ni), max(o[2], nf)
    if sug:
        print('\n# SUGGESTED autodiff "callees" (counts = argument registers set before the call; ADD any inherited r4-r7 you know are')
        print('# passed through; memset/memcpy/strlen-like callees: delete them from the list and do the work inline in the port)')
        for t, (name, ni, nf) in sug.items():
            print('  {"addr": "%s", "ints": %d, "floats": %d},   // %s' % (t[-8:], ni, nf, name))
        if any(n.startswith('TAIL ') for _, _, n, _ in calls):
            print('# TAIL CALL: `jmp @rN` to another function. The callee receives r4-r7/fr4-fr7 exactly as they are at the jmp (including values set on only one path')
            print('# and values inherited from the caller). The port must pass the same values, and the spec must compare them (ints: 4). The call is the LAST thing')
            print('# the function does: no code after it, and the callee\'s return value is this function\'s return value.')
    print('\n# SIGNATURE (params = read before written)')
    print('reads-before-write:', ', '.join('%s@%08x' % kv for kv in sorted(first_read.items())) or 'none (no register args)')
    last = max((k for k, i in enumerate(ins) if i['op'] == 'rts'), default=None)
    ret = ''
    if last is not None:
        win = ins[max(0, last - 6):last + 2]
        if any(x['op'] == 'mov' and x['args'].endswith(',r0') or x['op'].startswith(('mov', 'extu', 'exts', 'add')) and x['args'].endswith(',r0') for x in win):
            ret = 'r0 written near rts (returns a value)'
        elif any('fr0' in x['args'] for x in win):
            ret = 'fr0 involved near rts (float return?)'
        else:
            ret = 'no write to r0/fr0 near rts (void or r0 passthrough)'
    print('return:', ret)
    print('\n# LOOPS (backward branches). counter = register stepped by `add #imm` inside the loop; compare operands show their constant values')
    for addr, t, op, prev in loops:
        print('%s @%08x -> %08x   %s' % (op, addr, t, prev))
        body = [x for x in ins if t <= x['addr'] <= addr]
        steps = ['%s %s @%08x' % (x['op'], x['args'], x['addr']) for x in body if x['op'] == 'add' and x['args'].startswith('#')]
        cmps = [x for x in body if x['op'].startswith(('cmp', 'dt'))]
        if steps:
            print('    steps: ' + '; '.join(steps))
        for c in cmps:
            vals = []
            for r in re.findall(r'\br\d+\b', c['args']):
                h = [v for (a_, rr, v) in hist if rr == r and a_ <= c['addr']]
                if h:
                    vals.append('%s=%s' % (r, h[-1]))
            print('    compare @%08x %s %s   %s' % (c['addr'], c['op'], c['args'], ' '.join(vals)))
        if op in ('bf', 'bf/s'):
            print('    exit rule: `%s` jumps back while the T bit is CLEAR, so the loop CONTINUES while NOT(compare) and ends when the compare is TRUE' % op)
        elif op in ('bt', 'bt/s'):
            print('    exit rule: `%s` jumps back while the T bit is SET: loop continues while the compare is TRUE' % op)
    if not loops:
        print('none')


if __name__ == '__main__':
    main()
