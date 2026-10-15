#!/usr/bin/env python3
"""autodiff.py: automatic retail-vs-port differential for ONE SH-4 function. Game-independent (Ghidra SH-4 emulator).

  python3 -I tools/dc/autodiff.py SPEC.json [--cases N] [--seed S] [--keep]

You write two small files, no per-function Python harness:
  SPEC.json   which function, which memory it touches, which callees it calls
  wrapper.c   implements ad_wrapper() from tools/dc/autodiff/autodiff.h: calls YOUR port with the case's arguments
Output: one summary line `autodiff <func>: N cases, M mismatches, F faults` (exit 0 only if M == F == 0), then the
first differing case with the exact diff (return value / call log / region + first differing byte offset).

SPEC.json keys (addresses are hex strings, no 0x needed):
  "func":    "8c06fac4"
  "port":    {"wrapper": "path/wrapper.c", "sources": ["core/nd_x.c", ...], "include": ["core"]}
  "args":    {"r4": "rand" | [list of values] | {"range": [lo, hi]}, "fr4": [...float bit patterns...]}   (default: 0)
  "regions": [{"addr": "8c23e914", "len": 110880, "fill": "edge" (default, same as "rand": word-aware boundary values) | "zero" | "image" | "rawrand",
               "patch": [{"off": 79, "len": 1, "choice": [0, 1, 255]}]}]
             every byte the function reads or writes must lie in a region; ALL regions are compared after the call.
             "edge" = bytes drawn from {0,1,0x7f,0x80,0xff,random}: finds >/>= and sign bugs; "image" = copy from the binary.
             "word_choice": [{"off":0,"choice":[0,1,-1]}] sets little-endian 32-bit words (use for counters, pointers, ids).
  "callees": [{"addr": "8c103248", "ints": 2, "floats": 0, "ret": [0, 1]}]   stubbed + logged (args compared IN ORDER)
  "real":    ["8c08ba28"]   callees that run as REAL retail code (memset/memcpy/strlen: port inlines them, no call logged)
  "check_ret": true | false (void function: false)
  "equivalent_mutants": ["nd_x.c:11  0x1b120 -> 110879"]   surviving mutants you proved equivalent (explain in the port header)
  "asm_dir": optional dir of asm windows for the coverage check; "allow_uncovered": [addr...] unreachable instructions
  "image":   {"bin": "game/1ST_READ.BIN", "base": "0x8c010000"}   (only needed for fill=image)
Environment: AD_SANITIZE=1 (build the port with UBSan+ASan: signed overflow, bad shifts, misaligned access [UBSan 'alignment' check; the SH-4 raises an address error where x86 silently works], out-of-bounds reads become failures), AD_CFLAGS, AD_GHIDRA_HEADLESS, AD_GHIDRA_PROJECT, AD_PROGRAM (project/program names), AD_SCRIPTS (DrEmu.java dir), AD_TMP.
"""
import argparse, json, os, random, re, shutil, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import adcheck

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
BIN_DEFAULT = os.environ.get('DR_BIN', os.path.join(ROOT, 'game/1ST_READ.BIN'))
HEADLESS = os.environ.get('AD_GHIDRA_HEADLESS', '/usr/libexec/ghidra/support/analyzeHeadless')
PROJECT = os.environ.get('AD_GHIDRA_PROJECT', os.path.join(ROOT, 'work/ghidra_project'))
PNAME = os.environ.get('AD_GHIDRA_PNAME', os.environ.get('DR_PROJECT_NAME', 'drproject'))
PROGRAM = os.environ.get('AD_PROGRAM', os.environ.get('DR_PROGRAM', '1ST_READ.BIN'))
SCRIPTS = os.environ.get('AD_SCRIPTS', os.path.join(ROOT, 'ghidra/scripts'))


def hx(s):
    return int(str(s), 16)


def pick(rnd, spec, width=32):
    if spec is None:
        return 0
    if spec == 'rand':
        return rnd.randrange(1 << width)
    if isinstance(spec, list):
        return rnd.choice(spec) & ((1 << width) - 1)
    if isinstance(spec, dict) and 'range' in spec:
        return rnd.randint(*spec['range']) & ((1 << width) - 1)
    return int(spec) & ((1 << width) - 1)


def fill_region(rnd, r, image, base):
    n = r['len']
    mode = r.get('fill', 'edge')
    if mode == 'zero':
        b = bytearray(n)
    elif mode == 'rawrand':
        b = bytearray(rnd.getrandbits(8) for _ in range(n))
    elif mode == 'image':
        o = hx(r['addr']) - base
        b = bytearray(image[o:o + n]) if o >= 0 else bytearray(n)
    else:   # 'edge' (default; 'rand' is treated the same): per-region granularity 1/2/4, so s16/u32 compares (==0, ==0xfe, <0, max) fire
        gran = rnd.choice([1, 2, 2, 4, 4])
        vals = [0, 0, 0, 1, 2, 3, 0x7f, 0x80, 0xfe, 0xff, 0x7fff, 0x8000, 0xffff, 0x7fffffff, 0x80000000, 0xffffffff]
        zero_p = rnd.choice([0.2, 0.5, 0.8])
        b = bytearray(n)
        for k in range(0, n - gran + 1, gran):
            v = 0 if rnd.random() < zero_p else (rnd.choice(vals) if rnd.random() < 0.6 else rnd.getrandbits(8 * gran))
            b[k:k + gran] = (v & ((1 << (8 * gran)) - 1)).to_bytes(gran, 'little')
    for p in r.get('patch', []):
        for k in range(p['off'], p['off'] + p['len'], 1):
            b[k] = rnd.choice(p['choice']) & 0xff
    for p in r.get('word_choice', []):
        v = rnd.choice(p['choice']) & 0xffffffff
        b[p['off']:p['off'] + 4] = v.to_bytes(4, 'little')
    return bytes(b)


def captured_cases(spec, regions, rnd, image, base):
    """Real game inputs recorded by tools/dcprobe.py (`capture`): [(regs, mem)] in the same shape as the synthetic cases. Pointer parameters are RELOCATED to the
    synthetic region of the spec (the bytes the real pointer pointed to are copied there), stack arguments are replayed into the stack region, scalars as they were."""
    path = spec['captured'] if os.path.isabs(spec['captured']) else os.path.join(ROOT, spec['captured'])
    try:
        data = json.load(open(path))
    except (OSError, ValueError) as ex:
        sys.exit('"captured": cannot read %s (%s). Create it with: python3 -I tools/dc/dcprobe.py capture 0x%s --state N --spec <this spec>' % (path, ex, spec['func']))
    ptr = spec.get('ptr_args', {})
    out = []
    for hit in data.get('hits', [])[:spec.get('captured_max', 20)]:
        rg = hit['regs']
        regs = {}
        for k in spec.get('args', {}):
            if k in ptr:
                regs[k] = hx(ptr[k]['base'])
            else:
                regs[k] = rg.get(k, 0) & 0xffffffff
        mem = []
        for r in regions:
            a = hx(r['addr'])
            b = None
            if hit.get('mem', {}).get('%08x' % a):
                b = bytes.fromhex(hit['mem']['%08x' % a])
            for pk, pv in ptr.items():
                if hx(pv['base']) == a and hit.get('ptrmem', {}).get(pk):
                    b = bytes.fromhex(hit['ptrmem'][pk])
            if a == 0x8cffff00:
                words = list(hit.get('stack', []))
                for pk, pv in ptr.items():
                    if pk.startswith('stack') and pk[5:].isdigit() and int(pk[5:]) < len(words):
                        words[int(pk[5:])] = hx(pv['base'])
                b = b''.join((w & 0xffffffff).to_bytes(4, 'little') for w in words)
            filler = fill_region(rnd, r, image, base)
            b = ((b or b'') + filler[len(b or b''):])[:r['len']]
            mem.append((a, b))
        out.append((regs, mem))
    return out


def private_project(tmp):
    """Private read-only copy of the Ghidra project (no lock clashes with other jobs / parallel autodiff runs)."""
    import shutil
    dst = os.path.join(tmp, 'ghidra_proj')
    if not os.path.exists(os.path.join(dst, PNAME + '.gpr')):
        os.makedirs(dst, exist_ok=True)
        shutil.copytree(os.path.join(PROJECT, PNAME + '.rep'), os.path.join(dst, PNAME + '.rep'), dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('*.lock*', '*.lock~'))
        shutil.copy(os.path.join(PROJECT, PNAME + '.gpr'), dst)
    return dst


def _run_headless(cf, rf, env, project=None):
    return subprocess.run([HEADLESS, project or PROJECT, PNAME, '-process', PROGRAM, '-noanalysis', '-readOnly', '-scriptPath', SCRIPTS,
                           '-postScript', 'DrEmu.java', cf, rf], capture_output=True, text=True, env=env, timeout=int(os.environ.get('AD_EMU_TIMEOUT', '3600')))


def run_emulator(lines, tag, tmp):
    cf, rf = os.path.join(tmp, tag + '_cases.txt'), os.path.join(tmp, tag + '_results.txt')
    open(cf, 'w').write('\n'.join(lines) + '\n')
    if os.path.exists(rf):
        os.remove(rf)
    env = dict(os.environ)
    tb = os.path.join(tmp, 'fsca_table.bin')
    if 'ND_FSCA_TABLE' not in env and os.path.exists(tb):
        env['ND_FSCA_TABLE'] = tb
    import time
    for attempt in range(40):      # another Ghidra headless job may hold the project lock: wait and retry
        r = _run_headless(cf, rf, env, private_project(os.path.dirname(cf)))
        if 'Unable to lock project' not in (r.stdout + r.stderr):
            break
        time.sleep(15)
    if not os.path.exists(rf) or os.path.getsize(rf) == 0:
        sys.exit('emulator run failed (is ghidra/project imported? AD_* env?):\n' + (r.stdout + r.stderr)[-3000:])
    return open(rf).read().split('\n')[:len(lines)]


def parse_result(line):
    """-> (ret, [events], {region addr: hex})"""
    toks = line.split()
    ret = None
    ev, regs = [], {}
    for t in toks:
        if t.startswith('ret='):
            ret = t[4:]
        elif t.startswith('rbytes:'):
            k, v = t.split('=', 1)
            regs[k] = v
        elif re.match(r'^[CAD][0-9a-f]+=', t):
            ev.append(t)
        elif re.match(r'^F[0-9a-f]+=', t):
            regs['F'] = regs.get('F', '') + ' ' + t          # full argument registers of stubbed calls: analysed separately, never diffed
        elif t.startswith('ABI='):
            regs['ABI'] = t[4:]
        elif t.startswith('X='):
            regs['X'] = t[2:]
        elif t.startswith('WL='):
            regs['WL'] = t[3:]
        elif t.startswith('T='):
            regs['T'] = t[2:]
    return ret, ev, regs


def compress_trace(t):
    """collapse repeated cycles of 1-4 addresses: 'a b a b a b' -> '(a b)x3'"""
    xs = [x for x in t.rstrip(',').split(',') if x]
    out, i = [], 0
    while i < len(xs):
        done = False
        for per in (1, 2, 3, 4):
            reps = 1
            while xs[i + reps * per:i + (reps + 1) * per] == xs[i:i + per] and i + (reps + 1) * per <= len(xs):
                reps += 1
            if reps >= 3:
                out.append('(%s)x%d' % (' '.join(xs[i:i + per]), reps)); i += reps * per; done = True
                break
        if not done:
            out.append(xs[i]); i += 1
    return ' '.join(out)


STACK_LO, STACK_HI = 0x8cfe0000, 0x8cffff00      # retail pushes/pops below the entry sp: not observable behaviour, never part of the write trace


def wl_list(s):
    out = []
    for t in (s or '').split(','):
        parts = t.split(':')
        if len(parts) == 3:
            try:
                a = int(parts[0], 16)
            except ValueError:
                continue
            if STACK_LO <= a < STACK_HI:
                continue
            out.append((a, parts[1], parts[2]))
    return out


def wl_diff(e, p):
    """first difference between the retail and the port store sequences, or None. Order, count, width and value all matter (Mizuchi's behavioural check does the same)."""
    el, pl = wl_list(e), wl_list(p)
    for k in range(max(len(el), len(pl))):
        a = el[k] if k < len(el) else None
        b = pl[k] if k < len(pl) else None
        if a != b:
            f = lambda x: '%08x:%s=%s' % (x[0], x[1], x[2]) if x else '<none>'
            hint = ''
            if a and b and a[0] == b[0] and a[1] != b[1]:
                hint = ' (same address, different WIDTH: mov.b/mov.w/mov.l)'
            elif a and b and a[0] == b[0]:
                hint = ' (same address and width, different VALUE)'
            elif a and b:
                hint = ' (different ADDRESS or ORDER: check the index/offset arithmetic and the order of the stores)'
            elif a and not b:
                hint = ' (the port made FEWER stores: a store is missing, or the port wrote through ad_mem() instead of ad_wr8/16/32, which are the logged accessors)'
            else:
                hint = ' (the port made MORE stores than retail)'
            return 'write #%d differs: retail %s | port %s%s; retail made %d store(s), port %d' % (k, f(a), f(b), hint, len(el), len(pl))
    return None


def diff_region(a, b):
    n = min(len(a), len(b)) // 2
    for i in range(n):
        if a[2 * i:2 * i + 2] != b[2 * i:2 * i + 2]:
            return i, a[2 * i:2 * i + 2], b[2 * i:2 * i + 2]
    return None


MUT_OPS = [(r'<=', '<'), (r'>=', '>'), (r'(?<![<>=!])<(?![<=])', '<='), (r'(?<![<>=!-])>(?![>=])', '>='), (r'==', '!='), (r'!=', '=='),
           (r'&&', '||'), (r'\|\|', '&&'), (r'\+=', '-='), (r'(?<=[\w\)\] ]) \+ (?=[\w\(])', ' - '), (r'<<', '>>'), (r'&(?=\s*0x)', '|')]
LIT = re.compile(r'(?<![\w.])(0x[0-9a-fA-F]+|[0-9]+)(u|U)?(?![\w.])')


def strip_comments_mask(src):
    """-> list of (start,end) code spans (outside comments / strings / preprocessor lines)."""
    spans, i, n, start = [], 0, len(src), 0
    while i < n:
        if src.startswith('/*', i):
            spans.append((start, i)); j = src.find('*/', i + 2); i = (j + 2) if j >= 0 else n; start = i
        elif src.startswith('//', i):
            spans.append((start, i)); j = src.find('\n', i); i = j if j >= 0 else n; start = i
        elif src[i] == '"':
            j = i + 1
            while j < n and src[j] != '"':
                j += 2 if src[j] == '\\' else 1
            i = j + 1
        else:
            i += 1
    spans.append((start, n))
    return [(a_, b_) for a_, b_ in spans if a_ < b_]


def make_mutants(path, rnd, limit):
    src = open(path).read()
    muts = []
    for a_, b_ in strip_comments_mask(src):
        seg = src[a_:b_]
        for m in re.finditer(r'(?m)^[ \t]*#.*$', seg):      # skip preprocessor lines
            pass
        for pat, rep in MUT_OPS:
            for m in re.finditer(pat, seg):
                ls = seg.rfind('\n', 0, m.start()) + 1
                if seg[ls:].lstrip().startswith('#'):
                    continue
                muts.append((a_ + m.start(), a_ + m.end(), rep, '%s -> %s' % (m.group(0).strip(), rep.strip())))
        for m in LIT.finditer(seg):
            ls = seg.rfind('\n', 0, m.start()) + 1
            if seg[ls:].lstrip().startswith('#'):
                continue
            v = int(m.group(1), 0)
            for nv in (v + 1, v - 1):
                if nv >= 0:
                    muts.append((a_ + m.start(), a_ + m.end(), (hex(nv) if m.group(1).startswith('0x') else str(nv)) + (m.group(2) or ''), '%s -> %d' % (m.group(1), nv)))
    rnd.shuffle(muts)
    return src, muts[:limit]


def mutation_targets(spec, srcs):
    """Which port sources are mutated: spec port.mutate, else the files named after the function (nd_073f72.c), else all.
    Shared library sources (soft-float, rng...) listed in port.sources are NOT mutated here: one function's inputs can never exercise every line of a
    library, so those mutants would be unkillable noise (this made a correct port look unprovable); the library has its own unit tests + mutation check."""
    names = spec['port'].get('mutate')
    if names:
        sel = [x for x in srcs if any(x.endswith(n) for n in names)]
    else:
        key = str(spec['func']).lower().replace('0x', '')[-6:]
        sel = [x for x in srcs if key in os.path.basename(x).lower()]
    return sel or srcs


def run_mutants(spec, srcs, emu, run_port, tmp, rnd, limit, cases, *_):
    killed = survived = equiv = 0
    surv = []
    targets = mutation_targets(spec, srcs)
    print('mutating: ' + ', '.join(os.path.basename(x) for x in targets) + ('' if len(targets) == len(srcs) else '   (other sources are libraries: covered by their own unit tests; list files in port.mutate to change this)'))
    for si, path in enumerate(srcs):
        if path not in targets:
            continue
        src, muts = make_mutants(path, rnd, max(1, limit // max(1, len(targets))))
        for k, (a_, b_, rep, desc) in enumerate(muts):
            mp = os.path.join(tmp, 'mut_%d_%d_%s' % (si, k, os.path.basename(path)))
            open(mp, 'w').write(src[:a_] + rep + src[b_:])
            new = [mp if x == path else x for x in srcs]
            cout, err = run_port(new, 'mut')
            line = src.count('\n', 0, a_) + 1
            dead = cout is None
            if not dead:
                for e, o in zip(emu, cout):
                    if e.startswith('FAULT'):
                        continue
                    er, eev, ereg = parse_result(e); pr, pev, preg = parse_result(o)
                    if (spec.get('check_ret', True) and er != pr) or eev != pev or any(diff_region(ereg[q], preg.get(q, '')) for q in ereg if q not in ('X', 'T', 'F', 'ABI', 'WL')) or (spec.get('write_trace') and 'WL' in ereg and wl_diff(ereg.get('WL'), preg.get('WL'))):
                        dead = True; break
            tagd = '%s:%d  %s' % (os.path.basename(path), line, desc)
            if dead:
                killed += 1
            elif any(tagd.startswith(x) or x == tagd for x in spec.get('equivalent_mutants', [])):
                equiv += 1
            else:
                survived += 1; surv.append(tagd)
    print('mutants: %d killed, %d SURVIVED, %d declared equivalent' % (killed, survived, equiv))
    for sline in surv:
        print('  SURVIVED ' + sline)
        print('      hint: ' + adcheck.mutation_hint(sline.split('  ', 1)[1] if '  ' in sline else sline))
    if surv:
        print('  -> a surviving mutant means the inputs cannot tell that line apart from the original: strengthen the spec (boundary values')
        print('     for that comparison / constant, loops that iterate >1 time, both branch outcomes) until it is killed. ONLY if it is provably')
        print('     equivalent (e.g. bound 110880 vs 110879 when the loop stride makes both identical), copy its exact "file:line  a -> b" text into the')
        print('     spec key "equivalent_mutants": [...] and say why in the port header.')
    return 1 if survived else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('spec'); ap.add_argument('--cases', type=int); ap.add_argument('--seed', type=int)
    ap.add_argument('--keep', action='store_true')
    ap.add_argument('--final', action='store_true', help='the judge run to quote in a report: >= 300 cases, seed 7, >= 60 mutants, sanitizers on. A claim is only backed by a PROVEN --final run.')
    ap.add_argument('--mutate', type=int, nargs='?', const=24, default=0, help='also run N automatic mutants of the port sources (default 24)')
    a = ap.parse_args()
    spec = json.load(open(a.spec))
    if a.final:
        a.cases = max(a.cases or 0, 300)
        a.seed = 7 if a.seed is None else a.seed
        a.mutate = max(a.mutate or 0, 60)
        os.environ.setdefault('AD_SANITIZE', '1')
    ncase = a.cases or spec.get('cases', 60)
    rnd = random.Random(a.seed if a.seed is not None else spec.get('seed', 1))
    tmp = os.environ.get('AD_TMP') or os.path.join(os.getcwd(), 'work', 'autodiff')   # inside the project: agents can read case files there without leaving the workspace
    os.makedirs(tmp, exist_ok=True)
    img = spec.get('image', {})
    binp = img.get('bin', BIN_DEFAULT)
    image = open(binp, 'rb').read() if os.path.exists(binp) else b''
    base = int(img.get('base', os.environ.get('DR_BASE', '0x8c010000')), 16)
    errs = adcheck.validate_spec(spec, ROOT)
    if errs:
        sys.exit('SPEC ERROR(S) in %s:\n  - ' % a.spec + '\n  - '.join(errs))
    func = spec['func']
    regions = spec['regions']
    callees = spec.get('callees', [])
    try:
        sys.path.insert(0, HERE)
        import dcfacts
        os.environ.setdefault('DR_ASM_DIR', spec.get('asm_dir', ''))
        facts = dcfacts.facts(hx(func))
    except Exception as ex:
        facts = None
        print('note: retail facts unavailable (%s); spec lint is limited' % str(ex).split('\n')[0][:120])
    if facts and any(v == 'auto' for v in spec.get('args', {}).values()):     # "auto": boundary values harvested from the asm + random words
        pool = adcheck.auto_pool(facts, random.Random(1234), rng=spec.get('auto_range'))
        lim = spec.get('arg_limits', {})       # {"r7": [lo, hi]}: signed range for a count/length/index argument that drives a loop (unbounded values make the port AND the retail code run for ever)
        spec['args'] = {k: ((adcheck.auto_pool(facts, random.Random(1234), rng=lim[k]) if k in lim else pool) if v == 'auto' else v) for k, v in spec['args'].items()}
    elif any(v == 'auto' for v in spec.get('args', {}).values()):
        sys.exit('"auto" args need the retail asm facts (./dcre export first)')
    lint_errs, lint_warns = adcheck.lint(spec, facts)
    if lint_errs:
        sys.exit('SPEC LINT ERROR(S) in %s (fix the spec, then rerun):\n  - ' % a.spec + '\n  - '.join(lint_errs))

    warn = list(lint_warns)
    if ncase < 20:
        warn.append('only %d cases: use >= 40 (weak coverage)' % ncase)
    if all(r.get('fill', 'edge') == 'zero' and not r.get('patch') and not r.get('word_choice') for r in regions):
        warn.append('every region is fill=zero with no patch/word_choice: inputs never vary, use "edge" or "rand"')
    if not spec.get('args') and not any(r.get('fill', 'edge') != 'zero' for r in regions):
        warn.append('no register args and no varied memory: the test cannot distinguish conditional from unconditional code')
    if ncase < adcheck.FLOOR_CASES:
        warn.append('below the case floor (%d < %d); the floor is not negotiable, fix the port or strengthen inputs instead' % (ncase, adcheck.FLOOR_CASES))
    if a.mutate and a.mutate < adcheck.FLOOR_MUTANTS:
        warn.append('below the mutant floor (%d < %d)' % (a.mutate, adcheck.FLOOR_MUTANTS))
    fp = adcheck.fingerprint(spec, ncase, a.mutate, a.seed if a.seed is not None else spec.get('seed', 1))
    led = adcheck.ledger_load(ROOT, func)
    best = adcheck.ledger_best(led)
    if best:
        wk = adcheck.weaker(best['fp'], fp)
        if wk and os.environ.get('AD_ALLOW_WEAKER'):
            print('NOTE: AD_ALLOW_WEAKER is set: weakening allowed (%s). The ledger records the override and `claims` will not accept this run as a proof.' % '; '.join(wk))
        if wk and not os.environ.get('AD_ALLOW_WEAKER'):
            warn.append('SPEC WEAKENED compared with the strongest earlier run (%s): %s. A mismatch is a port bug; weakening the spec to hide it is not allowed.' % (best['time'], '; '.join(wk)))
    for w in warn:
        print('WARNING (spec too weak): ' + w)
    # ---- build the case set
    emu_lines, c_lines, cases = [], [], []

    def synth_cases():
        for _ in range(ncase):
            yield ({k: pick(rnd, v) for k, v in spec.get('args', {}).items()}, [(hx(r['addr']), fill_region(rnd, r, image, base)) for r in regions])
    cap = captured_cases(spec, regions, rnd, image, base) if spec.get('captured') else []
    if cap:
        print('[autodiff] + %d REAL game case(s) replayed from %s (case numbers >= %d)' % (len(cap), spec['captured'], ncase), flush=True)
    for regs, mem in __import__('itertools').chain(synth_cases(), cap):
        toks = ['call ' + func, 'cover', 'trace'] + (['wlog'] if True else []) + ['%s=%x' % (k, v) for k, v in regs.items()]
        toks += ['wbytes:%x=%s' % (ad, m.hex()) for ad, m in mem]
        for c in callees:
            toks.append('callog=%s:%d:%d' % (c['addr'], c.get('ints', 0), c.get('floats', 0)))
            toks.append('fullog=' + c['addr'])
            if c.get('ret'):
                toks.append('skipseq=%s:%s' % (c['addr'], ','.join('%x' % (v & 0xffffffff) for v in c['ret'])))
            else:
                toks.append('skip=' + c['addr'])
        toks += ['rbytes:%x:%d' % (hx(r['addr']), r['len']) for r in regions]
        emu_lines.append(' '.join(toks))
        c_lines.append(' '.join(['%s=%x' % kv for kv in regs.items()] + ['m%x=%s' % (ad, m.hex()) for ad, m in mem]))
        cases.append(regs)

    # ---- build + run the port driver
    port = spec['port']
    inc = ['-I', HERE + '/autodiff'] + sum((['-I', os.path.join(ROOT, p)] for p in port.get('include', [])), [])
    header = ['region %x %d' % (hx(r['addr']), r['len']) for r in regions]
    header += ['callee %s %s' % (c['addr'], ','.join('%x' % (v & 0xffffffff) for v in c.get('ret', []))) for c in callees]

    def run_port(sources, tag):
        exe = os.path.join(tmp, 'autodiff_%s_%s' % (func, tag))
        cflags = __import__('shlex').split(os.environ.get('AD_CFLAGS', ''))
        if os.environ.get('AD_SANITIZE'):   # run the port under UBSan+ASan: undefined behaviour in the PORT is a bug even if the bytes of the result match
            cflags += ['-fsanitize=undefined,address', '-fno-sanitize-recover=all']
        cmd = [os.environ.get('AD_CC', 'cc'), '-std=gnu99', '-O1', '-g', '-Wall'] + cflags + inc + [HERE + '/autodiff/autodiff_main.c', os.path.join(ROOT, port['wrapper'])] + sources + ['-o', exe]
        b = subprocess.run(cmd, capture_output=True, text=True)
        if b.returncode and os.environ.get('AD_SANITIZE') and ('lasan' in b.stderr or 'lubsan' in b.stderr) and shutil.which('clang') and cmd[0] != 'clang':
            cmd[0] = 'clang'           # this gcc package has no sanitizer runtimes; clang usually does
            b = subprocess.run(cmd, capture_output=True, text=True)
        if b.returncode and os.environ.get('AD_SANITIZE') and ('lasan' in b.stderr or 'lubsan' in b.stderr):
            print('NOTE: no sanitizer runtime (gcc/clang): the port runs WITHOUT UBSan/ASan this time')
            cmd = [x for x in cmd if not x.startswith('-fsanitize') and x != '-fno-sanitize-recover=all']
            b = subprocess.run(cmd, capture_output=True, text=True)
        if b.returncode:
            return None, 'port build failed:\n' + b.stderr[-3000:]
        try:
            cr = subprocess.run([exe], input='\n'.join(header + c_lines) + '\n', capture_output=True, text=True, timeout=int(os.environ.get('AD_PORT_TOTAL_S', '600')))
        except subprocess.TimeoutExpired:
            return None, ('port run exceeded %s s in total (the PORT binary, not the emulator): some case loops for ever. Set a per-case limit with '
                          'AD_PORT_CASE_S=5 to learn which case/args, then bound that argument with "arg_limits" in the spec.' % os.environ.get('AD_PORT_TOTAL_S', '600'))
        if cr.returncode in (97, 98):
            line = [l for l in cr.stderr.split('\n') if l.startswith('AD_')][-1:] or [cr.stderr[-300:]]
            regs_only = ' '.join(re.findall(r'\b(?:fr?\d+|r\d+)=[0-9a-f]+', line[0])) if 'args:' in line[0] else ''
            head = line[0].split('args:')[0].strip() + (' regs: ' + regs_only if regs_only else '')
            suspects = sorted({m.group(1) for m in re.finditer(r'\b(r\d+)=([0-9a-f]+)\b', line[0]) if int(m.group(2), 16) > 0x10000})
            culprits = []
            mcase = re.search(r'case=(\d+)', line[0])
            if mcase and 0 < int(mcase.group(1)) <= len(c_lines):      # bisect: lower ONE big argument at a time on the aborting case; the one that makes it terminate is the count
                base_toks = c_lines[int(mcase.group(1)) - 1].split()
                for sname in suspects:
                    toks = [('%s=3' % sname) if t.startswith(sname + '=') else t for t in base_toks]
                    try:
                        r2 = subprocess.run([exe], input='\n'.join(header + [' '.join(toks)]) + '\n', capture_output=True, text=True, timeout=60, env=dict(os.environ, AD_PORT_CASE_S='3'))
                        if r2.returncode not in (97, 98):
                            culprits.append(sname)
                    except subprocess.TimeoutExpired:
                        pass
            inside = []
            for cu in culprits:
                mv = re.search(r'\b%s=([0-9a-f]+)\b' % cu, line[0])
                lr = spec.get('arg_limits', {}).get(cu)
                if mv and lr:
                    sv = int(mv.group(1), 16)
                    sv = sv - (1 << 32) if sv & 0x80000000 else sv
                    if lr[0] <= sv <= lr[1]:
                        inside.append((cu, sv, lr))
            if inside:
                cu, sv, lr = inside[0]
                return None, ('PORT RUN ABORTED: ' + head[:400] + '\n'
                              '  BISECTED: %s = %d makes the PORT loop (lowering it to 3 terminates), but %d is INSIDE the spec range arg_limits %s = %s, so the retail code is expected to terminate for it.\n'
                              '  -> This is a PORT BUG, not a spec problem. Do NOT narrow arg_limits (the ratchet will flag it). Typical causes: a signed count compared as unsigned (retail `cmp/ge`, `cmp/gt` are SIGNED:\n'
                              '     declare the count int32_t, never uint32_t, so a negative value runs zero iterations), a loop that never decrements/increments, or a bound taken from the wrong register.' % (cu, sv, sv, cu, lr))
            if culprits:
                bis = '  BISECTED: lowering only %s to 3 makes this case terminate, so %s is the loop COUNT.\n' % (' and '.join(culprits), ' and '.join(culprits))
                lim = ', '.join('"%s": [-2, 24]' % x for x in culprits)
            else:
                bis = ''
                lim = ', '.join('"%s": [-2, 24]' % x for x in (suspects or ['r7']))
            return None, ('PORT RUN ABORTED: ' + head[:400] + '\n' + bis +
                          '  -> NOT an emulator problem. The PORT ran >%ss on this case or called a callee >50000 times. The retail code has the same loop: an argument that is a\n'
                          '     COUNT / LENGTH / INDEX (digit_count, n, size ...) received a huge generated value%s.\n'
                          '     Fix the SPEC input range, not the port: ADD  "arg_limits": {%s}  to the spec (signed inclusive range applied to "auto" values; use the real domain of\n'
                          '     that argument; coordinates/pointers/ids stay unlimited), or replace "auto" by a list. Do NOT lower cases/seed. Then rerun.' %
                          (os.environ.get('AD_PORT_CASE_S', '10'), (' (large args in this case: %s)' % ', '.join(suspects)) if suspects else '', lim))
        if cr.returncode:
            hint = ''
            if 'outside every declared region' in cr.stderr:
                hint = '\n  -> the PORT (or wrapper) touched memory the spec does not declare. ' + ' '.join(adcheck.explain_fault(cr.stderr, spec))
            elif 'not declared in the spec' in cr.stderr:
                hint = '\n  -> the port calls a callee the spec does not list: add it to "callees" (hex address) after checking it in ./dcre annotate'
            elif 'runtime error' in cr.stderr:
                hint = '\n  -> undefined behaviour in the port (UBSan): fix the port; do not weaken the spec'
            return None, 'port driver crashed (exit %d):\n%s%s' % (cr.returncode, cr.stderr[-2000:], hint)
        return cr.stdout.split('\n'), ''

    srcs = [os.path.join(ROOT, x) for x in port.get('sources', [])]
    print('[autodiff] phase 1/3: build + run the port on %d cases%s' % (ncase, ' (FINAL judge run)' if a.final else ''), flush=True)
    cout, err = run_port(srcs, 'port')
    if cout is None:
        sys.exit(err)

    # ---- run the retail function
    print('[autodiff] phase 2/3: retail function in the SH-4 emulator (%d cases; expect ~%d s, first start of Ghidra ~30 s; a case that runs >%s ms is reported as FAULT)' %
          (ncase, max(30, ncase // 4), os.environ.get('ND_CASE_MS', '120000')), flush=True)
    emu = run_emulator(emu_lines, 'ad_' + func, tmp)
    print('[autodiff] phase 3/3: compare%s' % (' + mutants' if a.mutate else ''), flush=True)

    bad = fault = 0
    wl_notes = [0]
    shown = 0
    covered = set()
    abi_seen = set()
    for i, (e, o) in enumerate(zip(emu, cout)):
        if e.startswith('FAULT'):
            fault += 1
            if fault <= 2:
                print('case %d FAULT: %s\n  (a read/write outside the declared regions, an unstubbed callee, or an infinite loop; for a loop/time-limit fault bound the count argument with "arg_limits")' % (i, e[:300]))
                for x in adcheck.explain_fault(e, spec):
                    print('  -> ' + x)
            continue
        er, eev, ereg = parse_result(e)
        pr, pev, preg = parse_result(o)
        why = []
        if spec.get('check_ret', True) and er != pr:
            why.append('return value: retail r0=%s port=%s' % (er, pr))
        if eev != pev:
            j = next((k for k in range(max(len(eev), len(pev))) if (eev[k] if k < len(eev) else None) != (pev[k] if k < len(pev) else None)), 0)
            why.append('call log differs at call #%d (callee-addr=args): retail=%s port=%s' % (j, eev[j] if j < len(eev) else '<none>', pev[j] if j < len(pev) else '<none>'))
            why.append('   decoded: retail %s | port %s' % (adcheck.decode_event(eev[j], spec, facts) if j < len(eev) else '<none>', adcheck.decode_event(pev[j], spec, facts) if j < len(pev) else '<none>'))
        for k in ereg:
            if k == 'T':
                continue
            if k == 'ABI':
                abi_seen.update(ereg[k].split(','))
                continue
            if k == 'F':
                continue
            if k == 'WL':
                continue
            if k == 'X':
                covered.update(int(x, 16) for x in ereg[k].split(',') if x)
                continue
            d = diff_region(ereg[k], preg.get(k, ''))
            if d:
                why.append('%s: first differing byte at offset 0x%x (+%d): retail=%s port=%s' % (k, d[0], d[0], d[1], d[2]))
        if 'WL' in ereg:
            wd = wl_diff(ereg.get('WL'), preg.get('WL'))
            if wd and spec.get('write_trace'):
                why.append(wd)
            elif wd:
                wl_notes[0] += 1
        if why:
            try:
                hints = []
                if spec.get('check_ret', True) and er != pr and er and pr and re.fullmatch(r'[0-9a-f]+', str(er)) and re.fullmatch(r'[0-9a-f]+', str(pr)):
                    hints.append(adcheck.value_hint(int(str(er), 16), int(str(pr), 16)))
                for w_ in why:
                    mm_ = re.search(r'retail=([0-9a-f]{2}) port=([0-9a-f]{2})', w_)
                    if mm_:
                        hints.append(adcheck.value_hint(int(mm_.group(1), 16), int(mm_.group(2), 16), 8))
                hints = [h for h in hints if h]
                if hints:
                    why.append('HINT: ' + hints[0])
            except Exception:
                pass
            bad += 1
            if shown < 2:
                shown += 1
                print('case %d%s MISMATCH args=%s' % (i, ' (REAL game input)' if i >= ncase else '', {k: '%x' % v for k, v in cases[i].items()}))
                for w in why:
                    print('   ' + w)
                print('   retail made %d logged callee call(s), port made %d%s' % (len(eev), len(pev), ' (port calls it %s than retail)' % ('MORE' if len(pev) > len(eev) else 'FEWER') if len(eev) != len(pev) else ''))
                if ereg.get('T'):
                    print('   retail taken-branch TARGETS (addresses where execution jumped to; this is NOT the list of executed instructions): ' + compress_trace(ereg['T'])[:500])
                    try:
                        import sh4_annotate as _sa2
                        _ins = _sa2.parse(_sa2.load_func(next(d_ for d_ in (spec.get('asm_dir'), os.path.join(ROOT, 'research/ghidra/asm'), os.path.join(ROOT, 'work/research/asm')) if d_ and os.path.isdir(d_)), hx(func)))
                        _lst = {x['addr']: x for x in _ins}
                        _tg = {int(t, 16) for t in re.findall(r'[0-9a-f]{8}', ereg['T'])}
                        _ex = sorted(int(t, 16) for t in re.findall(r'[0-9a-f]{8}', ereg.get('X', '')))
                        if _ex:
                            _rg, _s, _p = [], _ex[0], _ex[0]
                            for _a in _ex[1:]:
                                if _a - _p > 4:
                                    _rg.append((_s, _p)); _s = _a
                                _p = _a
                            _rg.append((_s, _p))
                            print('   retail EXECUTED %d of %d instructions, in ranges: %s' % (len(_ex), len([x for x in _ins if not x['delay']]), ' '.join('%08x-%08x' % r_ for r_ in _rg[:12])))
                            _dec = []
                            for _a in _ex:
                                _i = _lst.get(_a)
                                if _i and _i['op'] in ('bt', 'bf', 'bt/s', 'bf/s'):
                                    _t = int(_i['args'].split()[0], 16) if re.match(r'0x[0-9a-f]+', _i['args']) else None
                                    _dec.append('%08x %s %s %s' % (_a, _i['op'], _i['args'].split()[0] if _i['args'] else '', 'TAKEN' if _t in _tg else 'not taken'))
                            if _dec:
                                print('   retail decisions: ' + ' | '.join(_dec[:14]))
                    except Exception:
                        pass
                    print('   -> compare with the annotated listing: this is the path the retail code took for these inputs; make your port take the same path and the same call order')
    unchecked = adcheck.unchecked_args(spec, [adcheck.f_events(e) for e in emu if not e.startswith('FAULT')])
    for u in unchecked:
        print('UNCHECKED CALLEE ARGUMENT: ' + u)
    if abi_seen:
        print('ABI NOTE: the retail function returns with %s changed (callee-saved r8-r14 / sp r15). That is NOT the standard SH-4 C convention:' % ','.join(sorted(abi_seen)))
        print('   it is hand-written asm or relies on its caller (register-passing helper, longjmp-like code). The port signature must model it;')
        print('   a plain C function cannot reproduce it. (Informational: does not change the verdict. Source: the idea of ABI_CHECK in sp00nznet/dcrecomp.)')
    # ---- instruction coverage of the RETAIL function (a port can only be proven on code the cases actually ran)
    uncovered = []
    try:
        sys.path.insert(0, HERE)
        import sh4_annotate as _sa
        asm_dir = spec.get('asm_dir', os.path.join(ROOT, 'work/research/asm'))
        fins = [i['addr'] for i in _sa.parse(_sa.load_func(asm_dir, hx(func))) if not i['delay']]   # delay slots run inside their branch's emulator step
        allow = {hx(x) for x in spec.get('allow_uncovered', [])}
        uncovered = [x for x in fins if x not in covered and x not in allow]
        print('coverage: %d/%d retail instructions executed' % (len(fins) - len([x for x in fins if x not in covered]), len(fins)))
        if uncovered:
            print('WEAK SPEC: retail instructions NEVER executed by any case: ' + ' '.join('%08x' % x for x in uncovered[:40]))
            print('   -> the port code for those paths is UNTESTED. Look at the branch before the first address, then make the inputs')
            print('      reach it (fill "rand"/"edge" instead of "image"/"zero", word_choice/patch/args for the compared value). If a path is')
            print('      truly unreachable (error trap) list it in "allow_uncovered".')
    except Exception as ex:   # no asm window available (non-project binary): coverage check skipped
        print('coverage check skipped: %s' % ex)
    if uncovered:
        warn.append('uncovered retail instructions')
    if wl_notes[0]:
        print('NOTE: the store SEQUENCE differs from retail in %d case(s) although the final memory matches. Set "write_trace": true in the spec to make that a mismatch (new specs from specgen have it), and write memory with ad_wr8/16/32.' % wl_notes[0])
    print('autodiff %s: %d cases, %d mismatches, %d faults%s' % (func, len(emu), bad, fault, '  [WEAK SPEC: %d warning(s)]' % len(warn) if warn else ''))
    if not a.keep and not os.environ.get('AD_TMP'):
        pass
    rc = 1 if bad or fault or uncovered else 0
    mrc = None
    if a.mutate:
        mrc = run_mutants(spec, srcs, emu, run_port, tmp, rnd, a.mutate, cases, bad, fault)
        rc = max(rc, mrc)
    reasons = []
    if bad: reasons.append('%d mismatches (a mismatch is ALWAYS a port bug: fix the port, never weaken the spec)' % bad)
    if fault: reasons.append('%d emulator faults' % fault)
    if uncovered: reasons.append('retail instructions never executed')
    if unchecked: reasons.append('callee argument registers that vary are not compared')
    if warn and not uncovered: reasons.append('weak spec')
    if mrc is None: reasons.append('mutation check not run (add --mutate)')
    elif mrc: reasons.append('mutants survived (strengthen the inputs until all are killed)')
    result = 'RESULT: PROVEN' if not reasons else 'RESULT: NOT PROVEN -- ' + '; '.join(reasons)
    print(result)
    if not reasons and not a.final:
        print('NOT YET QUOTABLE: this run is provisional. Run `python3 -I tools/dc/autodiff.py %s --final` (new seed, 300 cases, 60 mutants, sanitizers) and quote THAT result line.' % a.spec)
    try:
        adcheck.ledger_save(ROOT, led, a.spec, spec, fp, srcs, result, not reasons, os.path.join(ROOT, port['wrapper']), final=a.final)
    except Exception as ex:
        print('note: proof ledger not written: %s' % ex)
    try:
        import attempts
        nsurv = 1 if mrc else 0
        snap = attempts.snapshot(ROOT, func, srcs, bad, fault, len(uncovered), nsurv, result)
        if snap:
            r_ = snap['runs'][-1]
            print('[attempts] snapshot #%d score=%s %s; best is #%d  (python3 -I tools/dc/attempts.py list|restore %s)' % (r_['n'], r_['score'], '' if snap['best'] == r_['n'] else '(WORSE than best: consider `attempts.py restore %s best` and one new hypothesis)' % func, snap['best'], func))
    except Exception as ex:
        print('note: attempt snapshot skipped: %s' % ex)
    sys.exit(0 if not reasons else 1)


if __name__ == '__main__':
    main()
