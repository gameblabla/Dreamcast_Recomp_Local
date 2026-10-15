#!/usr/bin/env python3
"""Self-test of the guard rails (offline). Run: python3 -I tests/test_tools.py [--emulator]   (--emulator also runs the slow Ghidra-based checks)
Needs a project with work/research + game/ for the asm-based checks (skipped otherwise)."""
import json, os, subprocess, sys, tempfile, shutil
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import adcheck
FX = os.path.join(ROOT, 'tests', 'fixtures')
fails, ran = [], 0


def check(name, cond, info=''):
    global ran
    ran += 1
    print(('ok    ' if cond else 'FAIL  ') + name + ('' if cond else '  ' + info))
    if not cond:
        fails.append(name)


def run(*a, env=None):
    r = subprocess.run([sys.executable, '-I'] + list(a), capture_output=True, text=True, cwd=ROOT, env=dict(os.environ, **(env or {})))
    return r.returncode, r.stdout + r.stderr


# ---- pure python checks (no project data needed)
spec = {'func': '8c073f72', 'port': {'wrapper': 'x.c', 'sources': ['x.c']}, 'regions': [{'addr': '8c000000', 'len': 100}, {'addr': '8c000010', 'len': 100}],
        'callees': [{'addr': '2349141190'}], 'bogus': 1, 'args': {'r9': [1]}}
e = adcheck.validate_spec(spec, '/nonexistent')
check('validate: unknown key', any('bogus' in x for x in e))
check('validate: overlapping regions', any('overlap' in x for x in e))
check('validate: decimal callee address', any('not hex' in x for x in e))
check('validate: bad arg register', any('r9' in x for x in e))
check('validate: missing port file', any('not found' in x for x in e))
fp0 = adcheck.fingerprint({'regions': [{'addr': '8c000000', 'len': 4096, 'fill': 'edge'}], 'args': {'r4': [1, 2, 3, 4, 5]}, 'callees': [{'addr': '8c070498', 'ints': 4, 'floats': 3}]}, 80, 24, 1)
fp1 = adcheck.fingerprint({'regions': [{'addr': '8c000000', 'len': 4096, 'fill': 'zero'}], 'args': {'r4': [1, 2]}, 'callees': [{'addr': '8c070498', 'ints': 1, 'floats': 3}], 'equivalent_mutants': ['a']}, 60, 12, 1)
w = adcheck.weaker(fp0, fp1)
check('ratchet: weaker spec detected', len(w) >= 5, str(w))
check('ratchet: identical spec is not weaker', adcheck.weaker(fp0, fp0) == [])
check('hint: constant', 'zero-filled' in adcheck.mutation_hint('8 -> 9'))
check('hint: comparison', 'EQUAL' in adcheck.mutation_hint('<= -> <'))
ev = adcheck.f_events(' ret=0 F8c0ffff0=2,1,fffffffe,ffffffff,0,0,0,0, F8c0ffff0=3,1,fffffffe,5,0,0,0,0,')
spec2 = {'callees': [{'addr': '8c0ffff0', 'ints': 1, 'floats': 0}]}
pr = adcheck.unchecked_args(spec2, [ev])
check('unchecked args: varying r7 flagged (callee asm unknown -> strict)', any('r7' in x for x in pr), str(pr))
check('unchecked args: ignore with reason accepted', not adcheck.unchecked_args(dict(spec2, ignore_args={'8c0ffff0': ['r5', 'r6', 'r7', 'fr4', 'fr5', 'fr6', 'fr7']}), [ev]))
check('fault explain: time-limit mentions stub', any('stubbed' in x for x in adcheck.explain_fault('FAULT time-limit (120000 ms)', {'regions': [{'addr': '8c000000', 'len': 16}]})))

# ---- asm-based checks
have = os.path.exists(os.path.join(ROOT, 'work', 'research', 'asm')) and os.path.exists(os.path.join(ROOT, 'game', '1ST_READ.BIN'))
if not have:
    print('skip  asm-based checks (no work/research + game/1ST_READ.BIN in this project)')
else:
    rc, out = run('tools/sh4_annotate.py', '0x8c073f72')
    check('annotate: tail call detected', 'TAIL FUN_8c070498' in out and 'TAIL CALL' in out, out[-300:])
    check('annotate: multiply does not define a register', 'r4=(inherited)' in out)
    rc, out = run('tools/dcfacts.py', '0x8c073f72')
    d = json.loads(out)
    check('facts: params/data/scaled load', d['params'] == ['r4', 'r5', 'r6'] and len(d['data']) == 2 and d['scaled_loads'][0]['field_off'] == 76, out[:200])
    tmp = tempfile.mkdtemp()
    rc, out = run('tools/specgen.py', '0x8c073f72', '--out', tmp)
    sp = json.load(open(os.path.join(tmp, 'spec_8c073f72.json')))
    check('specgen: tail callee ints=4, auto args, edge regions, index patches', sp['callees'][0]['ints'] == 1 and sp['callees'][0]['floats'] == 3 and sp['args']['r4'] == 'auto' and all(r['fill'] == 'edge' for r in sp['regions']) and sp['regions'][0]['patch'], out)
    rc, out = run('tools/specgen.py', '0x8c073f72', '--out', tmp)
    check('specgen: refuses to overwrite a spec', rc != 0 and 'refusing' in out)
    bad = os.path.join(FX, '073f72_local_model_attempt')
    port = open(os.path.join(bad, 'nd_073f72.c')).read().replace('1584', '132').replace('0x4c', '0x44')
    open(os.path.join(tmp, 'p.c'), 'w').write(port)
    rc, out = run('tools/portlint.py', '0x8c073f72', os.path.join(tmp, 'p.c'))
    check('portlint: wrong stride and offset flagged', '0x630' in out and '0x4c' in out, out)
    rc, out = run('tools/portlint.py', '0x8c073f72', os.path.join(bad, 'nd_073f72.c'), '--spec', os.path.join(bad, 'spec.json'))
    check('portlint: model port wrapper/spec agree', 'error(s)' in out)
    shutil.rmtree(tmp)

# ---- 2026-10-15 second-trial fixes (offline)
import importlib
rc, out = run('tools/readmem.py', '0x4ca24', '4')
check('readmem: a truncated address is refused with the real offset explained', rc != 0 and '0x3ca24' in out and 'FULL address' in out, out)
if os.path.exists(os.path.join(ROOT, 'game', '1ST_READ.BIN')):
    rc, out = run('tools/readmem.py', '0x8c04ca18', '16')
    check('readmem: virtual address -> file offset 0x3ca18, f32 view', rc == 0 and 'file offset 0x3ca18' in out and 'f32=-8192' in out, out)
    rc, out = run('tools/sh4_annotate.py', '0x8c04c938')
    check('annotate: mova + fmov.s @r0 resolves the float literal', rc == 0 and 'fr3 = -8192f' in out and '[literal at 8c04ca18]' in out, out[:300])
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import dcfacts, portlint
    tmp = tempfile.mkdtemp()
    bad_c = os.path.join(tmp, 'fn_8c04c938.c')
    open(bad_c, 'w').write('#include "autodiff.h"\nvoid fn_8c04c938(ad_regs *c){ float t = ad_rd32(ad_rd32(0x8c04ca18)); fprintf(stderr, "x"); }\n')
    errs, warns = portlint.lint(0x8c04c938, [bad_c])
    check('portlint: debug print / literal-pool run-time read / nested ad_rd are ERRORs', sum(('debug output' in e) + ('INSIDE the retail function' in e) + ('nested ad_rd' in e) for e in errs) == 3, str(errs))
    good_c = os.path.join(tmp, 'fn_8c04c938.c')
    open(good_c, 'w').write('#include "autodiff.h"\nvoid fn_8c04c938(ad_regs *c){ uint32_t t = 0xc6000000u; (void)t; }\n')
    errs, warns = portlint.lint(0x8c04c938, [good_c])
    check('portlint: embedding the literal is accepted', not [e for e in errs if 'INSIDE' in e or 'debug' in e], str(errs))
    shutil.rmtree(tmp)
errs, _ = adcheck.lint({'regions': [{'addr': '8c000040', 'len': 16}], 'args': {}}, {'text': '>8c000000:  nop\n 8c000010:  rts\n', 'params': []})
check('lint: a region over the function\'s own code/pool is an ERROR', any('overlaps the retail function itself' in e for e in errs), str(errs))
# C driver: per-case alarm (exit 97) and callee-hit cap (exit 98) with the case args in the message
td = tempfile.mkdtemp()
for name, body, code in (('loop98', 'for (int i = 0; i < 60000; i++) ad_call(0x8c000000, (const uint32_t[]){1}, 1, NULL, 0);', 98), ('spin97', 'volatile int x = 1; while (x) {}', 97)):
    open(os.path.join(td, 'w.c'), 'w').write('#include "autodiff.h"\nvoid ad_wrapper(ad_regs *c){ %s }\n' % body)
    exe = os.path.join(td, name)
    b = subprocess.run(['cc', '-std=gnu99', '-O1', '-I', os.path.join(ROOT, 'tools', 'autodiff'), os.path.join(ROOT, 'tools', 'autodiff', 'autodiff_main.c'), os.path.join(td, 'w.c'), '-o', exe], capture_output=True, text=True)
    if b.returncode:
        check('driver builds (%s)' % name, False, b.stderr[-300:]); continue
    r = subprocess.run([exe], input='region 8c000000 16\ncallee 8c000000 0\nr7=70d3da1f r4=1\n', capture_output=True, text=True, timeout=30, env=dict(os.environ, AD_PORT_CASE_S='1'))
    check('driver: %s exits %d naming the case args' % (name, code), r.returncode == code and 'r7=70d3da1f' in r.stderr and 'case=1' in r.stderr, '%s %s' % (r.returncode, r.stderr[-200:]))
shutil.rmtree(td)
# notes.py
nd = tempfile.mkdtemp(); os.makedirs(os.path.join(nd, 'work'))
r1 = subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'tools', 'notes.py'), 'add', '0x8c043680', 'div_s32: dividend r1, divisor r0'], capture_output=True, text=True, cwd=nd)
r2 = subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'tools', 'notes.py'), 'add', '0x8c043680', 'div_s32: dividend r1, divisor r0'], capture_output=True, text=True, cwd=nd)
r3 = subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'tools', 'notes.py'), 'show', '0x8c043680'], capture_output=True, text=True, cwd=nd)
check('notes: add, de-duplicate, show', 'noted' in r1.stdout and 'already' in r2.stdout and r3.stdout.count('div_s32') == 1, r1.stdout + r2.stdout + r3.stdout)
shutil.rmtree(nd)
# dcguard plugin core (node)
if shutil.which('node'):
    r = subprocess.run(['node', os.path.join(ROOT, 'tests', 'test_dcguard.mjs')], capture_output=True, text=True, cwd=ROOT)
    check('dcguard core: blocks/re-injection rules', r.returncode == 0, (r.stdout + r.stderr)[-600:])
    print(r.stdout.strip())

    if '--emulator' in sys.argv:
        os.makedirs(os.path.join(ROOT, 'work'), exist_ok=True)
        shutil.rmtree(os.path.join(ROOT, 'work', 'proofs'), ignore_errors=True)
        rc, out = run('tools/autodiff.py', os.path.join(bad, 'spec.json'), '--mutate', env={'AD_SANITIZE': '1'})
        check('autodiff: the 27B-model spec for 8c073f72 is NOT PROVEN, tail-call and mutants reported', rc != 0 and 'SURVIVED' in out and 'NOT PROVEN' in out and 'nd_f32.c' not in out.split('mutating:')[1].split('\n')[0].split('(')[0], out[-600:])
        shutil.rmtree(os.path.join(ROOT, 'work', 'proofs'), ignore_errors=True)
        ref = os.path.join(FX, '073f72_reference', 'spec.json')
        rc, out = run('tools/autodiff.py', ref, '--mutate', env={'AD_SANITIZE': '1'})
        check('autodiff: generated spec proves the reference port (provisional)', rc == 0 and 'RESULT: PROVEN' in out and 'NOT YET QUOTABLE' in out, out[-600:])
        rc, out = run('tools/proofcheck.py', '--func', '8c073f72')
        check('proofcheck: a provisional (non --final) PROVEN does not back a claim', rc != 0 and 'provisional' in out, out)
        sp = json.load(open(ref))
        sp['cases'] = 50
        sp['callees'][0]['floats'] = 1
        wk = os.path.join(FX, '073f72_reference', 'weak_spec.json')
        json.dump(sp, open(wk, 'w'))
        rc, out = run('tools/autodiff.py', wk, '--mutate', env={'AD_SANITIZE': '1'})
        os.remove(wk)
        check('ratchet: weaker spec cannot be PROVEN', rc != 0 and 'SPEC WEAKENED' in out, out[-500:])
        shutil.rmtree(os.path.join(ROOT, 'work', 'proofs'), ignore_errors=True)
print('\n%d checks, %d failed' % (ran, len(fails)))
sys.exit(1 if fails else 0)
