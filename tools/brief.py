#!/usr/bin/env python3
"""brief.py: ONE page of facts about one retail SH-4 function, so the first 30 exploration calls (sed/grep over asm, reading other ports) are not needed. Stdlib only.

  python3 -I tools/dc/brief.py 0x8c043680          # writes work/brief/fn_8c043680.md and prints the summary (everything except the long listing)

Sections: INPUTS (scalar / pointer + field offsets / stack arguments / float / loop-COUNT candidate), RETURNS, CALLEES (argument registers at each call),
CONSTANTS (pool ints and float literals), STRUCT OFFSETS, LOOPS, HAZARDS (what went wrong on similar functions), NEXT COMMANDS, then the full annotated listing.
All of it is derived from instructions and the literal pool (dcfacts.py / sh4_annotate.py); classifications are HYPOTHESES until autodiff proves the port.
"""
import os, re, sys

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
import dcfacts


def project_root():
    d = os.getcwd()
    for _ in range(5):
        if os.path.isdir(os.path.join(d, 'tools')) and (os.path.exists(os.path.join(d, 'AGENTS.md')) or os.path.isdir(os.path.join(d, 'work'))):
            return d
        d = os.path.dirname(d)
    return os.getcwd()


def asm_dir(root):
    for d in ('research/ghidra/asm', 'work/research/asm'):
        if os.path.isdir(os.path.join(root, d)):
            return os.path.join(root, d)
    return None


def decomp_dir(root):
    for d in ('research/ghidra/decompiled', 'work/research/decompiled'):
        if os.path.isdir(os.path.join(root, d)):
            return os.path.join(root, d)
    return None


def ops_of(root, addr, cache={}):
    """opcode-name sequence of a function (None when its asm window is not available)"""
    if addr in cache:
        return cache[addr]
    seq = None
    try:
        import sh4_annotate as sa
        ins = sa.parse(sa.load_func(asm_dir(root), addr))
        seq = [i['op'].split('/')[0] for i in ins] or None
    except Exception:
        seq = None
    cache[addr] = seq
    return seq


def similar_ports(root, addr, n=3):
    """Already ported (verified) functions whose opcode sequence is closest to this one: retrieval of style/idiom references
    (what the matching-decomp projects found works better than an easiest-first queue). -> [(ratio, addr, path)]"""
    import difflib, glob
    mine = ops_of(root, addr)
    if not mine or not asm_dir(root):
        return []
    cands = {}
    for p in glob.glob(os.path.join(root, 'core', 'nd_[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f].c')):
        cands[0x8c000000 | int(os.path.basename(p)[3:9], 16)] = p
    for p in glob.glob(os.path.join(root, 'port', 'fn_8c[0-9a-f]*.c')) + glob.glob(os.path.join(root, 'match', 'fn_8c[0-9a-f]*.c')):
        cands[int(os.path.basename(p)[3:11], 16)] = p
    out = []
    for a, p in cands.items():
        if a == addr:
            continue
        s = ops_of(root, a)
        if not s or abs(len(s) - len(mine)) > max(40, len(mine)):
            continue
        r = difflib.SequenceMatcher(None, mine, s, autojunk=False).ratio()
        out.append((r, a, os.path.relpath(p, root)))
    out.sort(reverse=True)
    return [x for x in out if x[0] >= 0.45][:n]


def decompile_hint(root, addr, maxl=70):
    d = decomp_dir(root)
    if not d:
        return None
    try:
        t = open(os.path.join(d, '%08x.c' % (addr & 0xffff0000))).read()
    except OSError:
        return None
    m = re.search(r'/\* ===== \S+ @ %08x ===== \*/' % addr, t)
    if not m:
        return None
    end = t.find('/* ===== ', m.end())
    body = t[m.end():end if end > 0 else len(t)].strip('\n').split('\n')
    return '\n'.join(body[:maxl]) + ('\n... (%d more lines)' % (len(body) - maxl) if len(body) > maxl else '')


def caller_sites(root, addr, n=4):
    d = decomp_dir(root)
    if not d:
        return []
    import glob
    pat = re.compile(r'\bFUN_%08x\s*\(|\b\w+_%08x\s*\(' % (addr, addr))
    out = []
    for p in sorted(glob.glob(os.path.join(d, '8c*.c'))):
        try:
            lines = open(p).read().split('\n')
        except OSError:
            continue
        for i, l in enumerate(lines):
            if pat.search(l) and not re.match(r'\s*(void|int|uint|float|char|short|undefined|bool)\b.*\)\s*$', l) and '=====' not in l:
                out.append(l.strip()[:200])
                if len(out) >= n:
                    return out
    return out


SPECIAL = [(r'\bdiv0[us]\b|\bdiv1\b', 'division is built from div0u/div0s + div1 steps (or calls the div_s32 helper): model it as truncating signed division, divide by 0 gives 0 in this game\'s helper'),
           (r'\bfsca\b|\bfsrra\b|\bfipr\b|\bftrv\b|\bfmac\b|\bfsqrt\b', 'special FPU ops (fsca/fsrra/fipr/ftrv/fmac/fsqrt): results are approximations/rounded differently from libm; see skills sh4-fpu-to-c and skmp-sh4-fpu (bit-exact models)'),
           (r'\bmac\.[wl]\b|\bdmuls\.l\b|\bdmulu\.l\b|\bmul\.l\b', '32x32 multiply / MAC: MACL/MACH are separate registers (sts MACL,rN)'),
           (r'\btrapa\b|\bldc\b|\bstc\b|\bsleep\b|\bpref\b|\bocb\w+\b|\bsynco\b|\bmovca\.l\b', 'privileged / cache / system instructions: hardware-facing code (not game rules): host-callback or park it'),
           (r'\bjmp\s+@r\d+|\bjsr\s+@r\d+|\bbraf\b|\bbsrf\b', 'indirect jump/call (jump table or function pointer): the table must be a spec region; run discover.py indirect to resolve targets')]


def build(addr):
    text = dcfacts.annotate_text(addr)
    f = dcfacts.facts(addr, text)
    pc = dcfacts.param_classes(text)
    h = '%08x' % addr
    L = ['# Brief for 0x%s  (generated by tools/brief.py; HYPOTHESIS until `autodiff.py SPEC --final` is PROVEN)' % h, '']
    nins = len(re.findall(r'^[> ]([0-9a-f]{8}):', text, flags=re.M))
    L.append('size: %d instructions; calls: %d; returns: %s' % (nins, len(f['calls']), {'value': 'a value in r0', 'float': 'a float in fr0', 'void': 'nothing'}.get(f['returns'], f['returns'])))
    L += ['', '## INPUTS']
    for p in f['params']:
        if p.startswith('fr'):
            L.append('- %s: float argument (raw IEEE bits)' % p)
        elif p in pc['ptr']:
            e = pc['ptr'][p]
            L.append('- %s: POINTER to a struct/buffer; field offsets used %s; %s%s' % (p, [hex(o) for o in sorted(e['off'])], 'WRITTEN through' if e['writes'] else 'read only', '; null-checked' if e['null_check'] else ''))
        else:
            L.append('- %s: scalar%s%s' % (p, ' (copied into a register compared in a loop: probably a COUNT; huge values hang)' if p in pc['count'] else '', ' (INDEX: shifted/multiplied/added to a table base; keep it small)' if p in pc.get('index', []) else ''))
    for i in pc['stack_args']:
        e = pc['stack_ptr'].get(i)
        L.append('- stack argument %d (5th+ argument, at entry-sp + %d): %s' % (i, 4 * i, ('POINTER, field offsets %s' % [hex(o) for o in sorted(e['off'])]) if e else ('INDEX (scaled and added to a table base)' if 'S%d' % i in pc.get('index', []) else 'scalar')))
    if not f['params'] and not pc['stack_args']:
        L.append('- none read before written (globals only)')
    L += ['', '## CALLEES (argument registers at the call; "(inherited)" = the caller\'s own value passed through)']
    groups = {}
    for c in f['calls']:
        groups.setdefault(c['target'], []).append(c)
    for tgt_, cs in groups.items():
        c = cs[0]
        tgt = '%08x' % tgt_ if tgt_ else 'INDIRECT (jump table / function pointer: resolve with discover.py)'
        L.append('- %s %s: %d call site(s) at %s%s' % (tgt, c.get('name') or '', len(cs), ', '.join('%08x' % x['addr'] for x in cs), '  [TAIL CALL: callee gets r4-r7/fr4-fr7 as they are; report it last]' if c['tail'] else ''))
        for k, v in c['args'].items():
            L.append('    first call: %-4s = %s' % (k, v))
    if not f['calls']:
        L.append('- none')
    pool = {}
    for c in f['consts']:
        if c['kind'] == 'literal-pool':
            pool.setdefault(c['value'], c)
    flt = re.findall(r'; => (fr\d+) = (\S+) \((0x[0-9a-f]+)\) \[literal at ([0-9a-f]+)\]', text)
    L += ['', '## CONSTANTS (literal pool; use these exact values)']
    targets_ = {c['target'] for c in f['calls'] if c['target']}
    for v, c in sorted(pool.items(), key=lambda kv: kv[1]['addr']):
        if v in targets_:
            continue                                  # a callee address: listed under CALLEES
        kind = '  (RAM address: a global / table / struct, give it a spec region)' if 0x8c000000 <= v < 0x8d000000 else ''
        L.append('- 0x%x (%d) loaded into %s at %08x%s' % (v, v - (1 << 32) if v >> 31 else v, c['reg'], c['addr'], kind))
    for reg, val, bits, at in flt:
        L.append('- float %s = %s (bits %s), literal at %s -> %s' % (reg, val, bits, at, reg))
    if not pool and not flt:
        L.append('- none')
    L += ['', '## STRUCT FIELD OFFSETS (width in bytes -> offsets seen as @(disp,rN))']
    for w, offs in sorted(f['offsets'].items()):
        L.append('- %d-byte: %s' % (w, ', '.join('0x%x' % o for o in sorted(set(offs)))))
    if not f['offsets']:
        L.append('- none')
    L += ['', '## LOOPS']
    L += ['- ' + l.strip() for l in f['loops'][:20]] or ['- none']
    hz = []
    if pc['ptr'] or pc['stack_ptr']:
        hz.append('Pointer inputs: the spec gives them dedicated regions (specgen). Access them with ad_rd8/ad_rd8s/ad_rd16/ad_rd16s/ad_rd32/ad_wr*; widths follow the load (mov.b signed, mov.w signed, extu zero-extends).')
    if pc['stack_args']:
        hz.append('Stack arguments exist: read them with ad_rd32(c->r[15] + 4*i). Do not assume the function has only 4 arguments.')
    if pc['count']:
        hz.append('Loop-count candidate %s: keep it bounded in the spec ("arg_limits"); a huge value makes the retail code and the port run for ever.' % ', '.join(pc['count']))
    for rx, msg in SPECIAL:
        if re.search(rx, text):
            hz.append('SPECIAL OPCODES: ' + msg)
    if any(c['tail'] for c in f['calls']):
        hz.append('TAIL CALL: report the callee with all four int registers (and float registers it reads), LAST, and return nothing after it.')
    if flt or re.search(r'\bf(add|sub|mul|div|cmp/\w+|ldi[01]|float|trc|sqrt|abs|neg)\b', text):
        hz.append('Float code: operands are raw IEEE bit patterns; fcmp/gt rA,rB is T = rB > rA; use the exact literals above (e.g. 0xc6000000), never a decimal approximation.')
    if re.search(r'\bdiv0s|div1\b|8c08b258', text):
        hz.append('Division helper: div_s32 takes the dividend in r1 and the divisor in r0 and returns the truncated quotient in r0 (division by 0 gives 0).')
    hz.append('A delay-slot instruction (marked `_`) executes BEFORE the branch takes effect; compares are signed (cmp/ge, cmp/gt) or unsigned (cmp/hs, cmp/hi): keep the kind.')
    L += ['', '## HAZARDS (from earlier runs)'] + ['- ' + x for x in hz]
    L += ['', '## NEXT COMMANDS',
          '1. python3 -I tools/dc/specgen.py 0x%s      (spec with pointer/stack regions + loop limits, complete wrapper, port skeleton port/fn_%s.c)' % (h, h),
          '2. write the body of port/fn_%s.c (remove the #error line), then: python3 -I tools/dc/portlint.py 0x%s port/fn_%s.c --spec port/tests/spec_%s.json' % (h, h, h, h),
          '3. python3 -I tools/dc/autodiff.py port/tests/spec_%s.json      (fix mismatches using the printed retail path + HINT)' % h,
          '4. python3 -I tools/dc/autodiff.py port/tests/spec_%s.json --mutate   (kill every survivor with inputs)' % h,
          '5. python3 -I tools/dc/autodiff.py port/tests/spec_%s.json --final    (quote its RESULT line)' % h]
    root = project_root()
    sim = []
    try:
        sim = similar_ports(root, addr)
    except Exception as ex:
        sim = []
    L += ['', '## SIMILAR PORTED FUNCTIONS (opcode-sequence similarity; verified ports to copy idioms from, never constants)']
    L += ['- %.0f%%  0x%08x  %s' % (r * 100, a, p) for r, a, p in sim] or ['- none above 45%']
    cs = caller_sites(root, addr)
    L += ['', '## HOW CALLERS PASS THE ARGUMENTS (Ghidra decompile of the call sites: shows what the pointer/scalar arguments really are; types/widths unreliable)']
    L += ['- ' + x for x in cs] or ['- no direct call sites in the decompiled windows (indirect call or entry point)']
    dh = decompile_hint(root, addr)
    L += ['', '## GHIDRA DECOMPILE (structure hint ONLY: parameter meaning, widths, signs and delay slots are often wrong; the asm decides)']
    L += [dh] if dh else ['(not available)']
    summary = '\n'.join(L)
    return summary, summary + '\n\n## FULL ANNOTATED LISTING\n' + text


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    addr = int(sys.argv[1], 16)
    summary, full = build(addr)
    d = os.path.join(project_root(), 'work', 'brief')
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, 'fn_%08x.md' % addr)
    open(p, 'w').write(full)
    print(summary)
    print('\n(full brief incl. the annotated listing: %s)' % os.path.relpath(p))


if __name__ == '__main__':
    main()
