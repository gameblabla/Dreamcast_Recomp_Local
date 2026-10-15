#!/usr/bin/env python3
"""adcheck.py: guard rails around tools/autodiff.py (spec validation, spec lint from the retail asm, unchecked-argument detection,
proof ledger + weakening ratchet, mutation/fault/mismatch explanations). Game-independent, stdlib only.

Why it exists (trial of a 27B local model on a float + tail-call function, 235 tool calls, 19/24 mutants alive): the model wrote a spec that
compared only 1 of the 4 integer registers a tail call hands to its callee, with 8 hand-picked argument values and zero-filled tables, then
reported success from partial evidence and later weakened its own spec. Everything below turns such a mistake into a printed, specific
failure BEFORE a human has to notice:

  validate_spec  schema errors (unknown key, bad hex, missing file, overlapping regions) with the exact fix
  lint           facts from the asm (dcfacts) vs the spec: parameters without values, callees not stubbed, tail call without ints=4,
                 check_ret vs return kind, data pointers outside every region, argument pools with < 4 distinct values, no float inputs for
                 float parameters
  unchecked_args every register the retail code passes to a stubbed callee that the spec does not compare AND that varies between cases is
                 a failure, unless the callee provably does not read it (callee asm signature) or the spec ignores it with a written reason
  ledger         work/proofs/<func>.json: spec fingerprint + port hashes + result of every run; a later run whose spec is WEAKER than the
                 strongest previous one (fewer cases/mutants/arg values/regions/callee registers, more declared-equivalent mutants) cannot be PROVEN
"""
import hashlib, json, os, re, sys, time

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)

SPEC_KEYS = {'captured', 'captured_max', 'write_trace', 'ptr_args', 'stack_args', 'arg_limits', 'func', 'cases', 'seed', 'check_ret', 'port', 'args', 'regions', 'callees', 'real', 'equivalent_mutants', 'asm_dir',
             'allow_uncovered', 'image', 'ignore_args', 'ignore_args_reason', 'notes', 'name', 'auto_range'}
FLOOR_CASES = 40
FLOOR_MUTANTS = 24


# ---------------------------------------------------------------- spec validation
def validate_spec(spec, root):
    errs = []
    for k in spec:
        if k not in SPEC_KEYS:
            errs.append('unknown spec key %r (typo?). Known keys: %s' % (k, ', '.join(sorted(SPEC_KEYS))))
    missing = [k for k in ('func', 'port', 'regions') if k not in spec]
    for k in missing:
        errs.append('missing required key %r' % k)
    if missing:
        return errs
    if not re.fullmatch(r'(0x)?[0-9a-fA-F]{6,8}', str(spec['func'])):
        errs.append('"func" must be a hex address like "8c073f72", got %r' % spec['func'])
    port = spec['port']
    if not isinstance(port, dict) or 'wrapper' not in port or 'sources' not in port:
        errs.append('"port" needs {"wrapper": path, "sources": [paths], "include": [dirs]}')
    else:
        for p in [port['wrapper']] + list(port['sources']):
            if not os.path.exists(os.path.join(root, p)):
                errs.append('port file not found: %s (paths are relative to the project root %s)' % (p, root))
    regs = spec['regions']
    spans = []
    for i, r in enumerate(regs):
        if not re.fullmatch(r'(0x)?[0-9a-fA-F]{6,8}', str(r.get('addr', ''))):
            errs.append('region %d: "addr" must be hex, got %r' % (i, r.get('addr')))
            continue
        if not isinstance(r.get('len'), int) or r['len'] <= 0:
            errs.append('region %d (%s): "len" must be a positive integer' % (i, r['addr']))
            continue
        a = int(str(r['addr']), 16)
        if r.get('fill', 'edge') not in ('edge', 'rand', 'zero', 'image', 'rawrand'):
            errs.append('region %d: unknown fill %r' % (i, r.get('fill')))
        for p in r.get('patch', []):
            if p.get('off', 0) + p.get('len', 1) > r['len']:
                errs.append('region %d (%s): patch at off %d len %d lies outside the region (len %d)' % (i, r['addr'], p.get('off', 0), p.get('len', 1), r['len']))
        for w in r.get('word_choice', []):
            if w.get('off', 0) + 4 > r['len']:
                errs.append('region %d (%s): word_choice at off %d lies outside the region (len %d)' % (i, r['addr'], w.get('off', 0), r['len']))
        spans.append((a, a + r['len'], i))
    spans.sort()
    for (a0, b0, i0), (a1, b1, i1) in zip(spans, spans[1:]):
        if a1 < b0:
            errs.append('regions %d and %d overlap (%08x-%08x vs %08x-%08x): the port and the emulator would see different bytes' % (i0, i1, a0, b0, a1, b1))
    for k, v in spec.get('args', {}).items():
        if not re.fullmatch(r'r[4-7]|fr([4-9]|1[01])', k):
            errs.append('arg %r: only r4..r7 and fr4..fr11 are inputs' % k)
        if isinstance(v, list) and not v:
            errs.append('arg %r: empty value list' % k)
    for c in spec.get('callees', []):
        if not re.fullmatch(r'(0x)?[0-9a-fA-F]{6,8}', str(c.get('addr', ''))):
            errs.append('callee address %r is not hex (stub addresses are HEX strings; a decimal address silently never matches)' % c.get('addr'))
        for key in ('ints', 'floats'):
            if key in c and (not isinstance(c[key], int) or not 0 <= c[key] <= 8):
                errs.append('callee %s: %r must be an integer 0..8' % (c.get('addr'), key))
    if spec.get('ignore_args') and not spec.get('ignore_args_reason'):
        errs.append('"ignore_args" needs "ignore_args_reason": say why the callee does not read those registers')
    return errs


# ---------------------------------------------------------------- lint against the retail asm facts
def lint(spec, f):
    """-> (errors, warnings) as lists of strings. `f` = dcfacts.facts(); None when no asm is available."""
    warns = []
    if f is None:
        return [], ['no asm window for this function: spec lint skipped (run ./dcre export). The spec cannot be checked against the retail code.']
    args = spec.get('args', {})
    code_addrs = [int(x, 16) for x in re.findall(r'^[> ]([0-9a-f]{8}):', f.get('text', ''), flags=re.M)]
    if code_addrs:
        c_lo, c_hi = min(code_addrs), max(code_addrs) + 0x48
        for r in spec.get('regions', []):
            try:
                ra = int(str(r['addr']), 16)
            except (KeyError, ValueError):
                continue
            if ra < c_hi and ra + int(r.get('len', 0)) > c_lo:
                return [('region %s (+%d) overlaps the retail function itself (%08x..%08x: code and literal pool). The emulator would OVERWRITE the constants the code reads, '
                         'so retail and port diverge for reasons that have nothing to do with the port. Delete that region; literal-pool values are read from the image '
                         '(embed them in the port as numbers, see `sh4_annotate.py`)' % (r['addr'], r.get('len', 0), c_lo, c_hi))], warns
    for p in f['params']:
        if p not in args:
            warns.append('retail reads parameter %s before writing it, but the spec gives it no values: it is 0 in every case. Add "%s": "auto" (boundary values harvested from the asm) or a list.' % (p, p))
    for k, v in args.items():
        if isinstance(v, list) and k not in spec.get('ptr_args', {}):
            if len(set(v)) < 4:
                warns.append('arg %s has only %d distinct value(s) %s: use "auto" or include boundaries (0, 1, -1, compared constants +-1)' % (k, len(set(v)), sorted(set(v))[:4]))
        elif v not in ('rand', 'auto') and not isinstance(v, dict):
            warns.append('arg %s is the constant %r in every case: use "auto" or a list' % (k, v))
        if k.startswith('fr') is False and k not in f['params'] and k in ('r4', 'r5', 'r6', 'r7') and not any(c['tail'] for c in f['calls']):
            warns.append('spec varies %s but the retail code never reads it before writing it: the wrapper should not need it (check the signature with ./dcre annotate)' % k)
    if any(p.startswith('fr') for p in f['params']) and not any(k.startswith('fr') for k in args):
        warns.append('retail reads float parameter(s) %s but the spec has no fr args' % ','.join(p for p in f['params'] if p.startswith('fr')))
    stubbed = {str(c['addr']).lower().replace('0x', '') for c in spec.get('callees', [])} | {str(x).lower().replace('0x', '') for x in spec.get('real', [])}
    spec_c = {str(c['addr']).lower().replace('0x', ''): c for c in spec.get('callees', [])}
    for c in f['calls']:
        if c['target'] is None:
            warns.append('call at %08x has an unresolved (indirect) target: look at the register source in the asm; an unstubbed indirect call faults or runs real code' % c['addr'])
            continue
        t = '%08x' % c['target']
        if t not in stubbed:
            warns.append('retail calls %s (%s)%s but the spec neither stubs it ("callees") nor runs it for real ("real"): it will run as retail code (slow, can hang)' % (t, c['name'], ' as a TAIL CALL' if c['tail'] else ''))
        elif c['tail'] and t in spec_c:
            reads = callee_reads(t, None)
            need = 4 if reads is None else max([int(r[1:]) - 3 for r in reads if re.fullmatch(r'r[4-7]', r)] or [0])
            needf = 3 if reads is None else max([int(r[2:]) - 3 for r in reads if re.fullmatch(r'fr[4-9]|fr1[01]', r)] or [0])
            if spec_c[t].get('ints', 0) < need or spec_c[t].get('floats', 0) < needf:
                warns.append('TAIL CALL to %s: the callee %s r4..r%d / fr4..fr%d (inherited registers pass through unchanged, some set on only one path); the spec compares ints=%d floats=%d. Raise them and pass the c->r[] values through in the wrapper/port.'
                             % (t, 'reads' if reads is not None else 'is unknown (assume it reads)', 3 + need, 3 + needf, spec_c[t].get('ints', 0), spec_c[t].get('floats', 0)))
        elif t in spec_c and not c['tail']:
            want = max([int(k[1:]) - 3 for k in c['args'] if re.fullmatch(r'r[4-7]', k) and not c['args'][k].startswith(('(inherited)', '(set on SOME'))] or [0])
            if spec_c[t].get('ints', 0) < want:
                warns.append('call to %s: the caller sets r4..r%d but the spec compares ints=%d' % (t, 3 + want, spec_c[t].get('ints', 0)))
    cr = spec.get('check_ret', True)
    if f['returns'] == 'value' and not cr:
        warns.append('retail writes r0 before rts but "check_ret" is false: the return value is not compared')
    if f['returns'] == 'void' and cr and not any(c['tail'] for c in f['calls']):
        warns.append('retail does not seem to return a value (no r0 write near rts) but "check_ret" is true: expect false mismatches; set false if confirmed in the asm')
    spans = [(int(str(r['addr']), 16), int(str(r['addr']), 16) + r['len']) for r in spec['regions']]
    for d in f['data']:
        if not any(a <= d < b for a, b in spans):
            warns.append('retail loads the data address %08x (literal pool) but no region contains it: either declare a region there or the function never dereferences it' % d)
    if all(r.get('fill', 'edge') == 'zero' for r in spec['regions']) and not any(r.get('patch') or r.get('word_choice') for r in spec['regions']):
        pass          # reported by autodiff itself
    return [], warns


def auto_pool(f, rnd, n_random=8, rng=None):
    """Boundary values harvested from the asm: 0, +-1, 2, every compared immediate +-1, small literal constants +-1, plus random words."""
    base = {0, 1, 2, 0xffffffff}
    heavy = []
    for c in f['cmps']:
        base.update({(c - 1) & 0xffffffff, c & 0xffffffff, (c + 1) & 0xffffffff})
        heavy += [c & 0xffffffff] * 8 + [(c - 1) & 0xffffffff, (c + 1) & 0xffffffff] * 2      # a compared constant must be hit often: guarded code needs it
    for c in f['consts']:
        v = c['value']
        if v < 0x10000 or v >= 0xffff0000:
            base.update({(v - 1) & 0xffffffff, v, (v + 1) & 0xffffffff})
    if rng:      # spec "auto_range": [lo, hi] (signed): indexes into a bounded table; random extras stay inside, boundaries outside are dropped
        lo, hi = rng
        sg = lambda v: v - (1 << 32) if v & 0x80000000 else v
        pool = sorted(v for v in base if lo <= sg(v) <= hi) + [v for v in heavy if lo <= sg(v) <= hi]
        pool += [rnd.randint(lo, hi) & 0xffffffff for _ in range(n_random)]
        return pool
    pool = sorted(base) + heavy
    pool += [rnd.randrange(1 << 32) for _ in range(n_random)]
    return pool


# ---------------------------------------------------------------- unchecked callee arguments
def f_events(e):
    """retail result line -> {callee: [[r4,r5,r6,r7,fr4,fr5,fr6,fr7] ...]}"""
    out = {}
    for m in re.finditer(r'\bF([0-9a-f]+)=([0-9a-f,]*)', e):
        vals = [int(x, 16) for x in m.group(2).split(',') if x]
        out.setdefault(m.group(1).lstrip('0') or '0', []).append(vals)
    return out


def callee_reads(addr, asm_dir):
    """registers (r4-r7, fr4-fr7) the callee reads before writing, or None when its asm is unavailable (then assume it reads everything)."""
    try:
        import dcfacts
        f = dcfacts.facts(int(addr, 16))
        return set(f['params'])
    except Exception:
        return None


def unchecked_args(spec, all_events):
    """all_events: list (per case) of f_events dicts. -> list of failure strings."""
    probs = []
    ignore = {str(k).lower().replace('0x', ''): set(v) for k, v in spec.get('ignore_args', {}).items()}
    for c in spec.get('callees', []):
        a = str(c['addr']).lower().replace('0x', '')
        key = a.lstrip('0')
        ni, nf = c.get('ints', 0), c.get('floats', 0)
        rows = [r for ev in all_events for r in ev.get(key, [])]
        if not rows:
            continue
        reads, loaded = None, False
        for idx, name in enumerate(['r4', 'r5', 'r6', 'r7', 'fr4', 'fr5', 'fr6', 'fr7']):
            compared = (idx < 4 and idx < ni) or (idx >= 4 and idx - 4 < nf)
            if compared or name in ignore.get(a, set()):
                continue
            vals = {r[idx] for r in rows if idx < len(r)}
            if len(vals) <= 1:
                continue                     # constant across all cases: nothing to learn from comparing it
            if not loaded:
                reads, loaded = callee_reads(a, None), True      # None = callee asm unavailable: assume it reads everything (strict)
            if reads is None or name in reads:
                probs.append('callee %s receives a %s that VARIES between cases (%d distinct values, e.g. %s) but the spec does not compare it (ints=%d floats=%d). '
                             'Raise "ints"/"floats" so the port must pass the same value, or, if the callee provably ignores it, list it in "ignore_args": {"%s": ["%s"]} with "ignore_args_reason".'
                             % (a, name, len(vals), ','.join('%x' % v for v in sorted(vals)[:3]), ni, nf, a, name))
    return probs


# ---------------------------------------------------------------- explanations
HINTS = [
    (r'^<= -> <$|^>= -> >$|^< -> <=$|^> -> >=$', 'off-by-one on a comparison: add a case where the two compared values are EQUAL (and one each side of equal)'),
    (r'^== -> !=$|^!= -> ==$', 'equality test: add cases where the operands are equal and where they differ by 1'),
    (r'^&& -> \|\|$|^\|\| -> &&$', 'boolean combination: add a case where exactly ONE of the conditions is true (each in turn)'),
    (r'^\+ -> -$|^\+= -> -=$', 'addition: add a case where the added term is nonzero and a case where the base is nonzero'),
    (r'^<< -> >>$', 'shift: use values with the top and bottom bits set so left and right shifts differ'),
    (r'^& -> \|$', 'mask: use values with bits outside the mask set'),
    (r'^(0x[0-9a-fA-F]+|\d+) -> \d+$', 'constant changed by 1: some input must land exactly on this constant (offset, stride, size, bound): make a region large enough for several elements of this stride, fill them with distinct values, and give the index argument the values 0..3 and the last valid index'),
]


def mutation_hint(desc):
    for pat, h in HINTS:
        if re.search(pat, desc.strip()):
            return h + ('. If this line reads bytes/words from a table (shifts, offsets, strides), the table must NOT be zero-filled: use fill "edge" (varied bytes) so a wrong shift/offset changes the result' if re.match(r'^(\d+|0x[0-9a-fA-F]+) -> \d+$', desc.strip()) else '')
    return 'no input distinguishes this line from the original: find the branch/expression on this line in the asm and make the inputs reach both outcomes'


def explain_fault(msg, spec):
    addrs = [int(x, 16) for x in re.findall(r'\b(8c[0-9a-f]{6}|a[c0-9][0-9a-f]{6})\b', msg)]
    spans = [(int(str(r['addr']), 16), r['len']) for r in spec['regions']]
    out = []
    if 'time-limit' in msg or 'step-limit' in msg:
        out.append('the retail code ran too long: a callee that should be stubbed is executing for real (add it to "callees", hex address), or a loop bound comes from a region you left zero/garbage (declare/fill it), or an indirect call target is wrong.')
    for a in addrs[:3]:
        near = min(spans, key=lambda s: min(abs(a - s[0]), abs(a - (s[0] + s[1]))), default=None)
        inside = [s for s in spans if s[0] <= a < s[0] + s[1]]
        if inside:
            out.append('address %08x is inside region %08x+0x%x' % ((a,) + inside[0]))
        else:
            out.append('address %08x is outside every region%s: declare {"addr": "%08x", "len": 4096}' % (a, ' (nearest %08x+0x%x)' % near if near else '', a & ~0xfff))
    return out


def describe(v, spec, f):
    """human description of a 32-bit value seen in a call log (region offset / literal-pool constant / float)."""
    for r in spec['regions']:
        a = int(str(r['addr']), 16)
        if a <= v < a + r['len']:
            return 'region %08x+0x%x' % (a, v - a)
    if f:
        for c in f['consts']:
            if c['value'] == v:
                return 'literal %s at %08x' % ('0x%x' % v, c['addr'])
    if 0x3f000000 <= v <= 0x7f800000 or 0xbf000000 <= v <= 0xff800000:
        import struct
        return 'float %g' % struct.unpack('<f', struct.pack('<I', v))[0]
    return '%d' % (v - (1 << 32) if v & 0x80000000 else v)


def decode_event(ev, spec, f):
    m = re.match(r'[CAD]([0-9a-f]+)=([0-9a-f,]*)', ev)
    if not m:
        return ev
    vals = [int(x, 16) for x in m.group(2).split(',') if x]
    return '%s(%s)' % (m.group(1), ', '.join('0x%x [%s]' % (v, describe(v, spec, f)) for v in vals))


# ---------------------------------------------------------------- proof ledger
def sha(path):
    try:
        return hashlib.sha256(open(path, 'rb').read()).hexdigest()[:16]
    except OSError:
        return None


def value_hint(retail, port, width=32):
    """SH-4-specific reading of two differing integer values (retail vs port): the usual cause, in one line. None when nothing useful."""
    m = (1 << width) - 1
    r, p = retail & m, port & m
    if r == p:
        return None
    if p == 0 and r != 0:
        return 'the port never produced this value (store/branch missing, or an earlier compare takes the other side)'
    if r == 0 and p != 0:
        return 'the port produced a value where retail left 0 (inverted or off-by-one compare, wrong sign/unsigned compare: cmp/ge,gt are SIGNED, cmp/hs,hi UNSIGNED)'
    for bits in (8, 16):
        lo = (1 << bits) - 1
        if (r & lo) == (p & lo):
            sx = lambda v: (v | ~lo) & m if v & (1 << (bits - 1)) else v & lo
            if r == sx(p & lo) or p == sx(r & lo):
                return 'same low %d bits, different extension: mov.%s sign-extends, extu.%s zero-extends (check the load/cast width and signedness)' % (bits, 'b' if bits == 8 else 'w', 'b' if bits == 8 else 'w')
    if abs(r - p) == 1 or abs(r - p) == (1 << width) - 1:
        return 'off by one: > vs >=, a count/loop bound, or the instruction in a branch DELAY SLOT (it runs before the branch is taken)'
    for sh in range(1, 16):
        if max(r, p) >= 0x100 and bin(r).count('1') == bin(p).count('1') and ((r << sh) & m == p or (p << sh) & m == r or (r >> sh) == p or (p >> sh) == r):
            return 'values differ by a shift of %d: wrong shift count / element size (shll2 = *4, shll8 = *256) or wrong field width' % sh
    if (r ^ p) & 0x80000000 and (r & 0x7fffffff) == (p & 0x7fffffff):
        return 'only the sign bit differs: fneg/fabs, a negated operand, or swapped subtraction operands (SH-4 `sub rS,rD` is rD = rD - rS)'
    return None


def fingerprint(spec, ncase, mutate, seed):
    def nvals(v):
        if isinstance(v, list):
            return len(set(v))
        return 1000 if v in ('rand', 'auto') or isinstance(v, dict) else 1
    return dict(cases=ncase, mutants=mutate, seed=seed,
                args={k: nvals(v) for k, v in spec.get('args', {}).items()},
                regions=len(spec['regions']), region_bytes=sum(r['len'] for r in spec['regions']),
                varied=sum(1 for r in spec['regions'] if r.get('fill', 'edge') != 'zero' or r.get('patch') or r.get('word_choice')),
                callees={str(c['addr']).lower().replace('0x', ''): [c.get('ints', 0), c.get('floats', 0)] for c in spec.get('callees', [])},
                real=len(spec.get('real', [])), equiv=len(spec.get('equivalent_mutants', [])), allow_uncovered=len(spec.get('allow_uncovered', [])),
                ignore_args=sum(len(v) for v in spec.get('ignore_args', {}).values()), check_ret=bool(spec.get('check_ret', True)))


def weaker(prev, cur):
    """list of reasons `cur` is weaker than `prev` (both fingerprints)."""
    w = []
    if cur['cases'] < prev['cases']:
        w.append('cases %d < %d' % (cur['cases'], prev['cases']))
    if prev['mutants'] and cur['mutants'] < prev['mutants']:
        w.append('mutants %d < %d' % (cur['mutants'], prev['mutants']))
    for k, n in prev['args'].items():
        if cur['args'].get(k, 0) < n:
            w.append('arg %s has %d value(s) now, %d before' % (k, cur['args'].get(k, 0), n))
    if cur['regions'] < prev['regions']:
        w.append('regions %d < %d' % (cur['regions'], prev['regions']))
    if cur['varied'] < prev['varied']:
        w.append('varied regions %d < %d' % (cur['varied'], prev['varied']))
    if cur['region_bytes'] < prev['region_bytes'] // 2:
        w.append('total region size halved')
    for a, (i, fl) in prev['callees'].items():
        ci, cf = cur['callees'].get(a, [0, 0])
        if ci < i or cf < fl:
            w.append('callee %s compares ints/floats %d/%d now, %d/%d before' % (a, ci, cf, i, fl))
    for k, msg in (('equiv', 'more declared-equivalent mutants'), ('allow_uncovered', 'more allowed-uncovered instructions'), ('ignore_args', 'more ignored callee arguments')):
        if cur[k] > prev[k]:
            w.append('%s (%d > %d)' % (msg, cur[k], prev[k]))
    if prev['check_ret'] and not cur['check_ret']:
        w.append('check_ret turned off')
    return w


def ledger_path(root, func):
    return os.path.join(root, 'work', 'proofs', '%s.json' % str(func).lower().replace('0x', ''))


def ledger_load(root, func):
    try:
        return json.load(open(ledger_path(root, func)))
    except (OSError, ValueError):
        return {'func': str(func), 'runs': []}


def ledger_best(led):
    """strongest fingerprint among previous runs that ended PROVEN (else among all runs)."""
    runs = [r for r in led['runs'] if r.get('proven')] or led['runs']
    best = None
    for r in runs:
        if best is None or (r['fp']['cases'], r['fp']['mutants']) > (best['fp']['cases'], best['fp']['mutants']):
            best = r
    return best


def ledger_save(root, led, spec_path, spec, fp, srcs, result, proven, wrapper, final=False):
    led['runs'].append(dict(override=bool(os.environ.get('AD_ALLOW_WEAKER')), time=time.strftime('%Y-%m-%dT%H:%M:%S'), spec_sha=sha(spec_path), fp=fp, port={os.path.relpath(s, root): sha(s) for s in srcs},
                            wrapper=sha(wrapper), result=result, proven=proven, final=bool(final)))
    led['runs'] = led['runs'][-30:]
    p = ledger_path(root, led['func'])
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(led, open(p, 'w'), indent=1)
