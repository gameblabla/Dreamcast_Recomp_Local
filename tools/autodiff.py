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
Environment: AD_SANITIZE=1 (build the port with UBSan+ASan: signed overflow, bad shifts, out-of-bounds reads become failures), AD_CFLAGS, AD_GHIDRA_HEADLESS, AD_GHIDRA_PROJECT, AD_PROGRAM (project/program names), AD_SCRIPTS (DrEmu.java dir), AD_TMP.
"""
import argparse, json, os, random, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
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
                           '-postScript', 'DrEmu.java', cf, rf], capture_output=True, text=True, env=env)


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
        elif t.startswith('X='):
            regs['X'] = t[2:]
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


def run_mutants(spec, srcs, emu, run_port, tmp, rnd, limit, cases, *_):
    killed = survived = equiv = 0
    surv = []
    for si, path in enumerate(srcs):
        src, muts = make_mutants(path, rnd, max(1, limit // max(1, len(srcs))))
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
                    if (spec.get('check_ret', True) and er != pr) or eev != pev or any(diff_region(ereg[q], preg.get(q, '')) for q in ereg if q not in ('X', 'T')):
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
    ap.add_argument('--mutate', type=int, nargs='?', const=24, default=0, help='also run N automatic mutants of the port sources (default 24)')
    a = ap.parse_args()
    spec = json.load(open(a.spec))
    ncase = a.cases or spec.get('cases', 60)
    rnd = random.Random(a.seed if a.seed is not None else spec.get('seed', 1))
    tmp = os.environ.get('AD_TMP') or os.path.join(os.getcwd(), 'work', 'autodiff')   # inside the project: agents can read case files there without leaving the workspace
    os.makedirs(tmp, exist_ok=True)
    img = spec.get('image', {})
    binp = img.get('bin', BIN_DEFAULT)
    image = open(binp, 'rb').read() if os.path.exists(binp) else b''
    base = int(img.get('base', os.environ.get('DR_BASE', '0x8c010000')), 16)
    func = spec['func']
    regions = spec['regions']
    callees = spec.get('callees', [])

    warn = []
    if ncase < 20:
        warn.append('only %d cases: use >= 40 (weak coverage)' % ncase)
    if all(r.get('fill', 'edge') == 'zero' and not r.get('patch') and not r.get('word_choice') for r in regions):
        warn.append('every region is fill=zero with no patch/word_choice: inputs never vary, use "edge" or "rand"')
    if not spec.get('args') and not any(r.get('fill', 'edge') != 'zero' for r in regions):
        warn.append('no register args and no varied memory: the test cannot distinguish conditional from unconditional code')
    for w in warn:
        print('WARNING (spec too weak): ' + w)
    # ---- build the case set
    emu_lines, c_lines, cases = [], [], []
    for _ in range(ncase):
        regs = {k: pick(rnd, v) for k, v in spec.get('args', {}).items()}
        mem = [(hx(r['addr']), fill_region(rnd, r, image, base)) for r in regions]
        toks = ['call ' + func, 'cover', 'trace'] + ['%s=%x' % (k, v) for k, v in regs.items()]
        toks += ['wbytes:%x=%s' % (ad, m.hex()) for ad, m in mem]
        for c in callees:
            toks.append('callog=%s:%d:%d' % (c['addr'], c.get('ints', 0), c.get('floats', 0)))
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
        cmd = ['cc', '-std=gnu99', '-O1', '-g', '-Wall'] + cflags + inc + [HERE + '/autodiff/autodiff_main.c', os.path.join(ROOT, port['wrapper'])] + sources + ['-o', exe]
        b = subprocess.run(cmd, capture_output=True, text=True)
        if b.returncode:
            return None, 'port build failed:\n' + b.stderr[-3000:]
        try:
            cr = subprocess.run([exe], input='\n'.join(header + c_lines) + '\n', capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            return None, 'timeout'
        if cr.returncode:
            return None, 'port driver crashed (exit %d):\n%s' % (cr.returncode, cr.stderr[-2000:])
        return cr.stdout.split('\n'), ''

    srcs = [os.path.join(ROOT, x) for x in port.get('sources', [])]
    cout, err = run_port(srcs, 'port')
    if cout is None:
        sys.exit(err)

    # ---- run the retail function
    emu = run_emulator(emu_lines, 'ad_' + func, tmp)

    bad = fault = 0
    shown = 0
    covered = set()
    for i, (e, o) in enumerate(zip(emu, cout)):
        if e.startswith('FAULT'):
            fault += 1
            if fault <= 2:
                print('case %d FAULT: %s\n  (a read/write outside the declared regions, an unstubbed callee, or an infinite loop)' % (i, e[:300]))
            continue
        er, eev, ereg = parse_result(e)
        pr, pev, preg = parse_result(o)
        why = []
        if spec.get('check_ret', True) and er != pr:
            why.append('return value: retail r0=%s port=%s' % (er, pr))
        if eev != pev:
            j = next((k for k in range(max(len(eev), len(pev))) if (eev[k] if k < len(eev) else None) != (pev[k] if k < len(pev) else None)), 0)
            why.append('call log differs at call #%d (callee-addr=args): retail=%s port=%s' % (j, eev[j] if j < len(eev) else '<none>', pev[j] if j < len(pev) else '<none>'))
        for k in ereg:
            if k == 'T':
                continue
            if k == 'X':
                covered.update(int(x, 16) for x in ereg[k].split(',') if x)
                continue
            d = diff_region(ereg[k], preg.get(k, ''))
            if d:
                why.append('%s: first differing byte at offset 0x%x (+%d): retail=%s port=%s' % (k, d[0], d[0], d[1], d[2]))
        if why:
            bad += 1
            if shown < 2:
                shown += 1
                print('case %d MISMATCH args=%s' % (i, {k: '%x' % v for k, v in cases[i].items()}))
                for w in why:
                    print('   ' + w)
                print('   retail made %d logged callee call(s), port made %d%s' % (len(eev), len(pev), ' (port calls it %s than retail)' % ('MORE' if len(pev) > len(eev) else 'FEWER') if len(eev) != len(pev) else ''))
                if ereg.get('T'):
                    print('   retail control-flow jumps (instruction addresses where execution was not sequential): ' + compress_trace(ereg['T'])[:700])
                    print('   -> compare with the annotated listing: this is the path the retail code took for these inputs; make your port take the same path and the same call order')
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
    if warn and not uncovered: reasons.append('weak spec')
    if mrc is None: reasons.append('mutation check not run (add --mutate)')
    elif mrc: reasons.append('mutants survived (strengthen the inputs until all are killed)')
    print('RESULT: PROVEN' if not reasons else 'RESULT: NOT PROVEN -- ' + '; '.join(reasons))
    sys.exit(0 if not reasons else 1)


if __name__ == '__main__':
    main()
