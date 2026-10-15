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
    if '--emulator' in sys.argv:
        os.makedirs(os.path.join(ROOT, 'work'), exist_ok=True)
        shutil.rmtree(os.path.join(ROOT, 'work', 'proofs'), ignore_errors=True)
        rc, out = run('tools/autodiff.py', os.path.join(bad, 'spec.json'), '--mutate', env={'AD_SANITIZE': '1'})
        check('autodiff: the 27B-model spec for 8c073f72 is NOT PROVEN, tail-call and mutants reported', rc != 0 and 'SURVIVED' in out and 'NOT PROVEN' in out and 'nd_f32.c' not in out.split('mutating:')[1].split('\n')[0].split('(')[0], out[-600:])
        shutil.rmtree(os.path.join(ROOT, 'work', 'proofs'), ignore_errors=True)
        ref = os.path.join(FX, '073f72_reference', 'spec.json')
        rc, out = run('tools/autodiff.py', ref, '--mutate', env={'AD_SANITIZE': '1'})
        check('autodiff: generated spec proves the reference port', rc == 0 and 'RESULT: PROVEN' in out, out[-600:])
        rc, out = run('tools/proofcheck.py', '--func', '8c073f72')
        check('proofcheck: ledger backs the proof', rc == 0 and 'True' in out, out)
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
