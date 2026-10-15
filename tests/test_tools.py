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


# ---- automation round 3: parameter classes, specgen skeleton/wrapper, hints, brief
check('value_hint: sign vs zero extension', 'extension' in (adcheck.value_hint(0xffffff80, 0x80) or ''))
check('value_hint: port never produced', 'never produced' in (adcheck.value_hint(5, 0) or ''))
check('value_hint: off by one', 'off by one' in (adcheck.value_hint(10, 11) or ''))
check('value_hint: shift', 'shift' in (adcheck.value_hint(0x1100, 0x4400) or ''))
if os.path.exists(os.path.join(ROOT, 'game', '1ST_READ.BIN')):
    try:
        import dcfacts as _df
        t1 = _df.annotate_text(0x8c04c938)
        pc1 = _df.param_classes(t1)
        check('param_classes: output pointers r4/r5 are WRITTEN pointers, no stack args', set(pc1['ptr']) == {'r4', 'r5'} and all(v['writes'] for v in pc1['ptr'].values()) and not pc1['stack_args'], str(pc1))
        pc2 = _df.param_classes(_df.annotate_text(0x8c043680))
        check('param_classes: stack argument 0 is an INDEX (scaled, added to a table base), not a pointer; r7 a loop count', pc2['stack_args'] == [0] and not pc2['stack_ptr'] and 'S0' in pc2['index'] and 'r7' in pc2['count'], str(pc2))
        tdir = tempfile.mkdtemp()
        rc, out = run('tools/specgen.py', '0x8c043680', '--out', os.path.join(tdir, 'tests'), '--port', os.path.join(tdir, 'fn_8c043680.c'))
        sp_ = json.load(open(os.path.join(tdir, 'tests', 'spec_8c043680.json'))) if rc == 0 else {}
        check('specgen: stack region with a small-index patch, arg_limits for the loop count, no bogus pointer', rc == 0 and sp_.get('stack_args') == 1 and 'stack0' not in sp_.get('ptr_args', {}) and sp_.get('arg_limits', {}).get('r7') == [-2, 40] and any(r['addr'] == '8cffff00' and r.get('patch') for r in sp_['regions']), out[-300:])
        wr = open(os.path.join(tdir, 'tests', 'wrapper_8c043680.c')).read()
        sk = open(os.path.join(tdir, 'fn_8c043680.c')).read()
        check('specgen: complete wrapper (no #error) and a port skeleton with typed helpers', '#error' not in wr and 'fn_8c043680(c)' in wr and '#error "port not written"' in sk and 'call_8c07d700(uint32_t a0, uint32_t a1, uint32_t a2, uint32_t a3)' in sk and 'ad_rd32(c->r[15] + 0)' in sk, sk[:300])
        rc, out = run('tools/specgen.py', '0x8c04c938', '--out', os.path.join(tdir, 'tests'), '--port', os.path.join(tdir, 'fn_8c04c938.c'))
        sk2 = open(os.path.join(tdir, 'fn_8c04c938.c')).read()
        check('specgen: float literals become KF_ macros (0xc6000000) in the skeleton', 'KF_8C04CA18_FR3 0xc6000000u' in sk2, sk2[:200])
        shutil.rmtree(tdir)
        rc, out = run('tools/brief.py', '0x8c043680')
        check('brief: similar ported functions, caller call sites and decompile hint sections', rc == 0 and 'SIMILAR PORTED FUNCTIONS' in out and 'HOW CALLERS PASS THE ARGUMENTS' in out and 'GHIDRA DECOMPILE' in out, out[-300:])
        import attempts as _at
        td_ = tempfile.mkdtemp(); os.makedirs(os.path.join(td_, 'port')); pf_ = os.path.join(td_, 'port', 'fn_8c000000.c')
        for k_, (b_, f_) in enumerate([(5, 0), (3, 0), (9, 0)]):
            open(pf_, 'w').write('/* v%d */' % k_)
            _at.snapshot(td_, '8c000000', [pf_], b_, f_, 0, 0, 'RESULT: NOT PROVEN')
        ix_ = json.load(open(os.path.join(td_, 'work', 'attempts', '8c000000', 'index.json')))
        check('attempts: snapshots every run and remembers the best (fewest mismatches)', ix_['best'] == 2 and len(ix_['runs']) == 3)
        shutil.rmtree(td_)
        check('brief: inputs, stack index, loop count, hazards, callees grouped', rc == 0 and 'INDEX' in out and 'COUNT' in out and 'HAZARDS' in out and 'call site(s)' in out, out[:400])
    except Exception as ex:
        check('automation round 3 (needs the project asm)', False, repr(ex))


# ---- rank.py / agentrun helpers
try:
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import agentrun as _ar
    _td = tempfile.mkdtemp(); os.makedirs(os.path.join(_td, 'work', 'proofs'))
    json.dump({'runs': [{'result': 'RESULT: NOT PROVEN -- 30 mismatches (x)'}, {'result': 'RESULT: NOT PROVEN -- 2 emulator faults; x'}, {'result': 'RESULT: PROVEN'}]}, open(os.path.join(_td, 'work', 'proofs', '8c000000.json'), 'w'))
    check('agentrun: scores() reads mismatches/faults from the ledger', _ar.scores(_td, '8c000000') == [30, 2, 0])
    shutil.rmtree(_td)
except Exception as ex:
    check('agentrun helpers import', False, repr(ex))
if os.path.exists(os.path.join(ROOT, 'game', '1ST_READ.BIN')):
    rc, out = run('tools/rank.py', '0x8c043680', '0x8c04c938')
    rows = [l.split('\t') for l in out.strip().split('\n')[1:]]
    check('rank: both ranked, the float+pointer function 8c04c938 is the harder one', rc == 0 and len(rows) == 2 and float(rows[0][0]) < float(rows[1][0]) and rows[1][1] == '8c04c938', out)


# ---- step 1/3 of the Mizuchi/Flycast plan: write trace + dcprobe protocol
import autodiff as _ad
check('wl_diff: identical sequences (stack stores ignored)', _ad.wl_diff('8cf00000:1:05,8cfffe00:4:deadbeef,', '8cf00000:1:05,') is None)
d_ = _ad.wl_diff('8cf00000:1:05,8cf00004:4:01000000,', '8cf00000:1:05,')
check('wl_diff: missing store reported with the store index and the accessor hint', d_ and 'write #1' in d_ and 'FEWER' in d_ and 'ad_wr' in d_, str(d_))
check('wl_diff: width difference', 'WIDTH' in (_ad.wl_diff('8cf00000:1:05,', '8cf00000:2:0500,') or ''))
check('wl_diff: order difference', 'ADDRESS or ORDER' in (_ad.wl_diff('8cf00000:1:05,8cf00001:1:06,', '8cf00001:1:06,8cf00000:1:05,') or ''))
import socket as _so, dcprobe as _dp
a_, b_ = _so.socketpair()
g_ = _dp.RSP.__new__(_dp.RSP); g_.s = a_; g_.buf = b''
def _srv(*pkts):
    for pk in pkts:
        b_.sendall(('$%s#%02x' % (pk, sum(pk.encode()) & 0xff)).encode())
_srv('S05', 'OK')              # a stale stop notification followed by the real reply: cmd() must skip the stop and NOT mistake "OK" for console output
check('rsp: cmd() skips a stray stop reply and returns OK (not swallowed as console output)', g_.cmd('Z0,8c000000,2', timeout=2) == 'OK')
_srv('S05')
check('rsp: wait_stop returns the stop reply', g_.wait_stop(2) == 'S05')
import struct as _st
_srv(_st.pack('<59I', *range(59)).hex())
r_ = g_.regs()
check('rsp: register packet decoded in SH-4 order (r0..r15, pc at 16, pr 17, fr0 at 25)', r_['r4'] == 4 and r_['pc'] == 16 and r_['pr'] == 17 and r_['fr0'] == 25 and r_['fr15'] == 40, str(r_)[:80])
a_.close(); b_.close()
# captured real-game cases are relocated onto the spec's synthetic regions
import random as _rnd
_spec = {'func': '8c000000', 'captured': 'cap.json', 'args': {'r4': 'auto', 'r5': 'auto', 'r7': 'auto'},
         'ptr_args': {'r5': {'base': '8cf00000', 'size': 8}, 'stack0': {'base': '8cf02000', 'size': 8}}, 'stack_args': 1}
_regions = [{'addr': '8c0e0000', 'len': 8, 'fill': 'zero'}, {'addr': '8cf00000', 'len': 8, 'fill': 'zero'}, {'addr': '8cf02000', 'len': 8, 'fill': 'zero'}, {'addr': '8cffff00', 'len': 64, 'fill': 'zero'}]
_td = tempfile.mkdtemp()
json.dump({'hits': [{'regs': {'r4': 7, 'r5': 0x8c123450, 'r7': 3}, 'stack': [0x8c999990] + [0] * 15, 'mem': {'8c0e0000': '0102030405060708'},
                     'ptrmem': {'r5': 'aabbccddeeff0011', 'stack0': '1122334455667788'}}]}, open(os.path.join(_td, 'cap.json'), 'w'))
_spec['captured'] = os.path.join(_td, 'cap.json')
_cc = _ad.captured_cases(_spec, _regions, _rnd.Random(1), b'', 0x8c010000)
_regs, _mem = _cc[0]
_m = dict(_mem)
check('captured: scalars as recorded, the pointer arg relocated to its synthetic region', _regs['r4'] == 7 and _regs['r7'] == 3 and _regs['r5'] == 0x8cf00000, str(_regs))
check('captured: fixed-address region restored, pointer bytes copied behind the synthetic base, stack word = relocated pointer',
      _m[0x8c0e0000].hex() == '0102030405060708' and _m[0x8cf00000].hex() == 'aabbccddeeff0011' and _m[0x8cf02000].hex() == '1122334455667788' and _m[0x8cffff00][:4] == (0x8cf02000).to_bytes(4, 'little'), str({hex(k): v.hex()[:16] for k, v in _m.items()}))
shutil.rmtree(_td)
# lessons of the 8c043680 run: stack-frame faults, narrowing arg_limits
check('fault hint: an access below the entry sp says "do not imitate the retail stack frame"', any('BELOW the entry sp' in x for x in adcheck.explain_fault('ad_mem: address 8cfffec8 is outside every declared region', {'regions': [{'addr': '8cffff00', 'len': 64}]})))
_f0 = adcheck.fingerprint({'regions': [{'addr': '8c000000', 'len': 4096}], 'args': {'r7': 'auto'}, 'arg_limits': {'r7': [-2, 40]}}, 150, 0, 1)
_f1 = adcheck.fingerprint({'regions': [{'addr': '8c000000', 'len': 4096}], 'args': {'r7': 'auto'}, 'arg_limits': {'r7': [0, 40]}}, 150, 0, 1)
check('ratchet: narrowing arg_limits (to hide a signedness bug) is a weaker spec', any('narrowed' in x for x in adcheck.weaker(_f0, _f1)) and not adcheck.weaker(_f1, _f0), str(adcheck.weaker(_f0, _f1)))
if os.path.exists(os.path.join(ROOT, 'game', '1ST_READ.BIN')):       # the slow emulator-only checks below need the project data
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
