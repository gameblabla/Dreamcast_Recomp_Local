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


def param_classes(text):
    """Classify the function's inputs from the annotated listing (flow-insensitive copy tracking, single forward pass):
      ptr         {'r4': {'off': [0, 4, 0x24], 'writes': True, 'null_check': False}}  parameter later used as the BASE of a memory access (mov @rN / @(d,rN) / @rN+ ...)
      stack_args  [0, 1]      stack arguments (5th, 6th ... argument): loads from [entry-sp + 4*i] (Ghidra `Stack[0x..]` comments with a non-negative offset)
      stack_ptr   {1: {...}}  stack arguments that are dereferenced later (same record as ptr)
      count       ['r7']      parameters copied into a register that is compared inside a loop (advisory: loop COUNT candidates; may over-report)
    A register that mixes several parameters (add rS,rD of two origins) is ambiguous and is NOT reported as a pointer."""
    ins = []
    for ln in text.split('\n'):
        m = re.match(r'[> ]([0-9a-f]{8}): ([ _])(\S+)\s+(.*?)(?:\s+=> (r\d+) = (-?\d+) \(0x([0-9a-f]+)\))?(?:\s+;\s*(.*))?$', ln)
        if m:
            ins.append((int(m.group(1), 16), m.group(3), m.group(4).strip(), m.group(8) or '', m.group(5), int(m.group(7), 16) if m.group(7) else None))
    out = dict(ptr={}, stack_args=[], stack_ptr={}, count=[], index=[])
    if not ins:
        return out
    org = {r: {r} for r in ('r4', 'r5', 'r6', 'r7')}
    slot = {}
    stack_seen = set()
    regre = re.compile(r'\br(\d+)\b')

    def note_ptr(p, d, write, nullchk=False):
        key = p if p.startswith('r') else int(p[1:])
        dest = out['ptr'] if p.startswith('r') else out['stack_ptr']
        e = dest.setdefault(key, dict(off=[], writes=False, null_check=False))
        if d is not None and d not in e['off']:
            e['off'].append(d)
        e['writes'] = e['writes'] or write
        e['null_check'] = e['null_check'] or nullchk

    cmp_sites = []
    constaddr = set()                       # registers currently holding a RAM address loaded from the literal pool (a table / global base)
    index_of = set()                        # parameters proven to be INDEXES / scaled values (shifted, multiplied, or added to a table base)
    for ad, op, a, cm, creg, cval in ins:
        parts = [x.strip() for x in re.split(r',(?![^(]*\))', a)] if a else []
        if creg:
            if cval is not None and 0x8c000000 <= cval < 0x8d000000:
                constaddr.add(creg)
            else:
                constaddr.discard(creg)
        if op.startswith('cmp/') or op == 'dt':
            cmp_sites.append((ad, set().union(*[org.get(r, set()) for r in re.findall(r'\br\d+\b', a)])))
        reads_mem = None
        for k, pt in enumerate(parts):
            mm = re.fullmatch(r'@\(?(?:(?:0x)?([0-9a-f]+),)?(r\d+)\)?[+]?|@-(r\d+)|@\(r0,(r\d+)\)', pt)
            if not mm:
                continue
            base = mm.group(2) or mm.group(3) or mm.group(4)
            if pt.startswith('@(r0,'):
                continue                      # @(r0,rN): rN may be the index or the base: no evidence either way
            else:
                disp = int(mm.group(1), 16) if mm.group(1) else 0
            if base == 'r15' or base is None:
                continue
            o = org.get(base, set())
            if len(o) == 1:
                is_store = (k == len(parts) - 1) and op.startswith(('mov', 'fmov')) and len(parts) == 2 and not parts[0].startswith('@')
                note_ptr(next(iter(o)), disp, is_store or (k == 1 and op.startswith(('mov', 'fmov'))))
        # stack argument load: [entry sp + d], Ghidra comment Stack[0x..]
        ms = re.search(r'Stack\[(0x[0-9a-f]+)\]', cm)
        if ms and op.startswith('mov') and len(parts) == 2 and re.fullmatch(r'r\d+', parts[1]) and parts[0].startswith('@'):
            idx = int(ms.group(1), 16) // 4
            if idx not in stack_seen:
                stack_seen.add(idx); out['stack_args'].append(idx)
            org[parts[1]] = {'S%d' % idx}
            continue
        # origin updates
        if op in ('mov', 'extu.b', 'extu.w', 'exts.b', 'exts.w', 'neg', 'not', 'swap.w', 'swap.b') and len(parts) == 2 and re.fullmatch(r'r\d+', parts[0]) and re.fullmatch(r'r\d+', parts[1]):
            org[parts[1]] = set(org.get(parts[0], set()))
        elif op == 'add' and len(parts) == 2 and re.fullmatch(r'r\d+', parts[0]) and re.fullmatch(r'r\d+', parts[1]):
            if (parts[0] in constaddr and org.get(parts[1])) or (parts[1] in constaddr and org.get(parts[0])):
                idxr = parts[1] if parts[0] in constaddr else parts[0]      # param + table base: the PARAM is an index
                index_of |= {p for p in org.get(idxr, set())}
                org[parts[1]] = set()
            else:
                org[parts[1]] = org.get(parts[1], set()) | org.get(parts[0], set())
        elif op.startswith(('shl', 'shr', 'shal', 'shar', 'mul', 'rotl', 'rotr')) and parts and re.fullmatch(r'r\d+', parts[-1]):
            index_of |= org.get(parts[-1], set())                  # scaled by a shift / multiply: an index or a size, not a pointer
            org[parts[-1]] = set()
        elif op in ('add', 'sub') and parts and re.fullmatch(r'r\d+', parts[-1]):
            pass                                                   # add #imm / sub keeps the origin
        elif op == 'mov.l' and len(parts) == 2:
            m1 = re.fullmatch(r'@\((?:0x)?([0-9a-f]+),r15\)|@r15', parts[1])
            m0 = re.fullmatch(r'@\((?:0x)?([0-9a-f]+),r15\)|@r15', parts[0])
            if m1 and re.fullmatch(r'r\d+', parts[0]):
                slot[m1.group(1) or '0'] = set(org.get(parts[0], set()))
            elif m0 and re.fullmatch(r'r\d+', parts[1]):
                org[parts[1]] = set(slot.get(m0.group(1) or '0', set()))
            elif re.fullmatch(r'r\d+', parts[1]):
                org[parts[1]] = set()
        else:
            from_sa = None
            try:
                import sh4_annotate as _sa
                from_sa = _sa.reg_reads_writes(dict(op=op, args=a))[1]
            except Exception:
                from_sa = [parts[-1]] if parts and re.fullmatch(r'r\d+', parts[-1]) and not op.startswith(('cmp', 'tst')) else []
            for w in from_sa:
                if w in org:
                    org[w] = set()
        # null checks on pointer-ish registers
        if op in ('tst',) and len(parts) == 2 and parts[0] == parts[1]:
            for p in org.get(parts[0], set()):
                (out['ptr'].get(p) or out['stack_ptr'].get(int(p[1:]) if p.startswith('S') else -1) or {}).update({'null_check': True}) if (out['ptr'].get(p) or out['stack_ptr'].get(int(p[1:]) if p.startswith('S') else -1)) else None
    # a parameter that was later shown to be an index/scaled value is not a pointer (drop entries recorded before the scaling was seen)
    for p in list(out['ptr']):
        if p in index_of:
            del out['ptr'][p]
    for p in list(out['stack_ptr']):
        if 'S%d' % p in index_of:
            del out['stack_ptr'][p]
    out['index'] = sorted(index_of)
    # loop-count candidates (advisory)
    for k, (ad, op, a, cm, _c, _v) in enumerate(ins):
        if op in ('bt', 'bf', 'bt/s', 'bf/s', 'bra') and re.match(r'0x[0-9a-f]+', a):
            t = int(a.split()[0], 16)
            if t < ad:
                for ad2, origins in cmp_sites:
                    if t <= ad2 <= ad:
                        for p in origins:
                            if p in ('r4', 'r5', 'r6', 'r7') and p not in out['count']:
                                out['count'].append(p)
    out['count'].sort()
    out['stack_args'].sort()
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
