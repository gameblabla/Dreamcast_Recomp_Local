#!/usr/bin/env python3
"""dcfacts.py: machine-readable facts about ONE retail SH-4 function, derived from the annotated asm (tools/sh4_annotate.py). Stdlib only.

  python3 -I tools/dcfacts.py 0x8c073f72            # JSON on stdout
  from dcfacts import facts; f = facts(0x8c073f72)

Single source of truth for specgen / portlint / autodiff: nothing here is guessed from the decompiler, everything comes from instructions and the
literal pool. Keys:
  params   ['r4','r5','r6','fr4'...]   registers read before written (the function's own parameters)
  returns  'value' | 'void' | 'float'  (heuristic, from r0/fr0 near rts; tail calls return the callee's value)
  consts   [{'value': int, 'kind': 'literal-pool'|'imm', 'addr': int, 'reg': 'r13'}]   every constant the code loads
  data     [int]   literal-pool values that look like data addresses (inside RAM, not call targets): candidate regions
  calls    [{'addr','target','name','tail','args': {reg: text}}]
  loops    [text]  raw LOOPS section lines
  offsets  sorted {width: [offsets]}   `mov.b/w/l @(disp,rN)` displacements (struct field offsets) seen in the code
  cmps     [int]   immediates / small constants compared (boundary-value candidates)
"""
import os, re, subprocess, sys

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
RAM_LO, RAM_HI = 0x8c000000, 0x8d000000


def annotate_text(addr, extra=None):
    cmd = [sys.executable, '-I', os.path.join(HERE, 'sh4_annotate.py'), '0x%x' % addr] + (extra or [])
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
    if r.returncode:
        raise RuntimeError('sh4_annotate failed for %08x: %s' % (addr, (r.stderr or r.stdout)[-400:]))
    return r.stdout


def facts(addr, text=None):
    t = text if text is not None else annotate_text(addr)
    f = dict(func=addr, params=[], returns='void', consts=[], data=[], calls=[], loops=[], offsets={}, cmps=[], text=t)
    sec = ''
    call_targets = set()
    for ln in t.split('\n'):
        if ln.startswith('# CALLS'):
            sec = 'calls'; continue
        if ln.startswith('# SIGNATURE'):
            sec = 'sig'; continue
        if ln.startswith('# LOOPS'):
            sec = 'loops'; continue
        if ln.startswith('# SUGGESTED'):
            sec = 'sug'; continue
        if sec == '':
            m = re.match(r'[> ]([0-9a-f]{8}): ([ _])(\S+)\s+(.*?)(?:\s+=> (r\d+) = (-?\d+) \(0x([0-9a-f]+)\))?(?:\s+;.*)?$', ln)
            if not m:
                continue
            ad, delay, op, args, reg, dec, hx = m.groups()
            args = args.strip()
            ad = int(ad, 16)
            if reg:
                v = int(hx, 16)
                f['consts'].append(dict(value=v, kind='literal-pool', addr=ad, reg=reg))
            im = re.match(r'#(-?(?:0x)?[0-9a-f]+),(r\d+)$', args)
            if op in ('mov', 'add') and im:
                try:
                    f['consts'].append(dict(value=int(im.group(1), 0) & 0xffffffff, kind='imm', addr=ad, reg=im.group(2)))
                except ValueError:
                    pass
            if op.startswith('cmp') or op.startswith('tst'):
                mm = re.match(r'#(-?(?:0x)?[0-9a-f]+),', args)
                if mm:
                    try:
                        f['cmps'].append(int(mm.group(1), 0))
                    except ValueError:
                        pass
            md = re.match(r'(mov\.[bwl]|fmov\.s|fmov)\s+', op + ' ')
            for mo in re.finditer(r'@\((-?0x[0-9a-f]+|-?\d+),r\d+\)', args):
                w = {'mov.b': 1, 'mov.w': 2, 'mov.l': 4, 'fmov.s': 4, 'fmov': 4}.get(op, 0)
                if w:
                    f['offsets'].setdefault(w, set()).add(int(mo.group(1), 0))
        elif sec == 'calls':
            m = re.match(r'call @([0-9a-f]{8}) -> (\S+) (.*?): (.*)$', ln)
            if m:
                a_, tgt, name, rest = m.groups()
                tail = name.startswith('TAIL ')
                nm = name[5:] if tail else name
                args = {}
                for am in re.finditer(r'(f?r\d+)=(\(set on SOME path only: [^)]*\)|\(inherited\)|<[^>]*>|\S+(?: \(delay slot\))?)', rest):
                    args[am.group(1)] = am.group(2)
                f['calls'].append(dict(addr=int(a_, 16), target=int(tgt, 16) if re.fullmatch(r'[0-9a-f]{8}', tgt) else None, name=nm, tail=tail, args=args))
        elif sec == 'sig':
            if ln.startswith('reads-before-write:'):
                f['params'] = re.findall(r'\b(f?r\d+)@', ln)
            elif ln.startswith('return:'):
                f['returns'] = 'value' if 'r0 written' in ln else ('void' if 'no write' in ln else ('float' if 'fr0' in ln else 'void'))
        elif sec == 'loops':
            if ln.strip():
                f['loops'].append(ln)
    call_targets = {c['target'] for c in f['calls'] if c['target']}
    seen = set()
    for c in f['consts']:
        v = c['value']
        if c['kind'] == 'literal-pool' and RAM_LO <= v < RAM_HI and v not in call_targets and v not in seen:
            seen.add(v); f['data'].append(v)
    f['offsets'] = {w: sorted(o) for w, o in f['offsets'].items()}
    f['scaled_loads'] = scaled_loads(t)
    return f


def scaled_loads(text):
    """16-bit loads whose result is multiplied by a constant (muls.w/mulu.w/mul.l): a table field used as an INDEX into another table.
    -> [{'load': addr, 'field_off': int|None, 'scale': int}]. The field must be constrained in a spec (random bytes would index far outside any region)."""
    ins = []
    for ln in text.split('\n'):
        m = re.match(r'[> ]([0-9a-f]{8}): ([ _])(\S+)\s+(.*?)(?:\s+=>.*)?(?:\s+;.*)?$', ln)
        if m:
            ins.append((int(m.group(1), 16), m.group(3), m.group(4).strip()))
    imm = {}
    out = []
    for k, (ad, op, ar) in enumerate(ins):
        mm = re.match(r'#(-?(?:0x)?[0-9a-f]+),(r\d+)$', ar)
        if op == 'mov' and mm:
            try:
                imm[mm.group(2)] = (int(mm.group(1), 0), k)
            except ValueError:
                pass
        if op == 'mov.w' and re.search(r',(r\d+)$', ar):
            dst = re.search(r',(r\d+)$', ar).group(1)
            for ad2, op2, ar2 in ins[k + 1:k + 7]:
                m2 = re.match(r'(r\d+),(r\d+)$', ar2)
                if op2 in ('muls.w', 'mulu.w', 'mul.l') and m2 and dst in m2.groups():
                    other = m2.group(1) if m2.group(2) == dst else m2.group(2)
                    if other in imm:
                        fo = [v for r_, (v, kk) in imm.items() if r_ in ('r0', 'r1') and 0 < kk < k and k - kk < 10 and v != imm[other][0]]
                        out.append(dict(load=ad, field_off=fo[-1] if fo else None, scale=imm[other][0]))
                    break
    return out


if __name__ == '__main__':
    import json
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    d = facts(int(sys.argv[1], 16))
    d.pop('text')
    d['data'] = ['%08x' % x for x in d['data']]
    for c in d['consts']:
        c['value'] = '0x%x' % c['value']
    for c in d['calls']:
        c['addr'] = '%08x' % c['addr']
        c['target'] = '%08x' % c['target'] if c['target'] else None
    print(json.dumps(d, indent=1))
