#!/usr/bin/env python3
"""specgen.py: generate a STRONG autodiff spec + wrapper skeleton for one retail function from its asm, so the spec is never hand-weakened. Stdlib only.

  python3 -I tools/specgen.py 0x8c073f72 [--out port/tests] [--port port/fn_8c073f72.c] [--include port]

Writes <out>/spec_<addr>.json and <out>/wrapper_<addr>.c (a skeleton with TODOs; it will not compile until you finish it - on purpose).
What the generator decides from the asm (tools/dcfacts.py), instead of the model guessing:
  args      every parameter read before written -> "auto" (boundary values: compared immediates and small constants +-1, 0, -1, random words);
            float parameters -> a list of IEEE bit patterns (0, 1, -1, 2, large, tiny, random)
  regions   every data address loaded from the literal pool -> a region (>= 4 KiB; >= 8 strides when a stride/size constant like 0x630 is loaded;
            large enough for the highest struct offset seen), filled with varied "edge" bytes (never all zero), merged when they would overlap
  callees   every call, TAIL calls with "ints": 4 (the callee gets the caller's r4-r7), floats from the registers set before the call
  check_ret from the return-value heuristic
The result is a starting point that already passes the spec lint; weaken nothing, only ADD (word_choice/patch for the exact values a branch needs).
"""
import argparse, json, os, re, sys

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
import dcfacts

MAXEL = 8          # elements per strided table in generated regions
FLOATS = [0x00000000, 0x3f800000, 0xbf800000, 0x40000000, 0x47000000, 0xc7000000, 0x3f000000, 0x7f7fffff, 0x00800000, 0x42c80000, 0xc2c80000, 0x3dcccccd]


def regions_for(f):
    strides = [c['value'] for c in f['consts'] if c['kind'] == 'literal-pool' and 0x100 <= c['value'] <= 0x4000]
    maxoff = max([o for offs in f['offsets'].values() for o in offs] + [c['value'] for c in f['consts'] if c['kind'] == 'imm' and c['value'] < 0x400] + [0])
    stride = max(strides) if strides else 0
    ln = max(4096, (stride * MAXEL if stride else 0) + maxoff + 16)
    ln = (ln + 15) & ~15
    out = []
    for d in sorted(f['data']):
        if out and d < out[-1]['_end']:
            out[-1]['_end'] = max(out[-1]['_end'], d + ln)
            continue
        out.append(dict(_start=d, _end=d + ln))
    regs = []
    for o in out:
        regs.append({'addr': '%08x' % o['_start'], 'len': o['_end'] - o['_start'], 'fill': 'edge'})
    return regs, stride


def dcfacts_callee(addr):
    """registers the callee reads before writing (its own parameters) or None when its asm is not available."""
    try:
        return set(dcfacts.facts(addr)['params'])
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('addr'); ap.add_argument('--out', default='port/tests'); ap.add_argument('--port'); ap.add_argument('--include', default='port')
    ap.add_argument('--cases', type=int, default=150)
    a = ap.parse_args()
    addr = int(a.addr, 16)
    f = dcfacts.facts(addr)
    h = '%08x' % addr
    port = a.port or 'port/fn_%s.c' % h
    regs, stride = regions_for(f)
    args = {}
    for p in f['params']:
        args[p] = 'auto' if p.startswith('r') else FLOATS
    if any(c['tail'] for c in f['calls']):       # a tail callee receives the caller's r4-r7: they must vary too, whether or not this function reads them
        for r in ('r4', 'r5', 'r6', 'r7'):
            args.setdefault(r, 'auto')
    callees, seen = [], {}
    for c in f['calls']:
        if c['target'] is None:
            continue
        t = '%08x' % c['target']
        reads = dcfacts_callee(c['target'])
        ni = (4 if reads is None else max([int(r[1:]) - 3 for r in reads if re.fullmatch(r'r[4-7]', r)] or [0])) if c['tail'] else max([int(k[1:]) - 3 for k in c['args'] if re.fullmatch(r'r[4-7]', k) and not c['args'][k].startswith(('(inherited)', '(set on SOME'))] or [0])
        nf = max([int(k[2:]) - 3 for k in c['args'] if re.fullmatch(r'fr(4|5|6|7|8|9|10|11)', k)] or [0])
        if c['tail'] and reads is not None:
            nf = max([int(r[2:]) - 3 for r in reads if re.fullmatch(r'fr[4-9]|fr1[01]', r)] or [0])
        cur = seen.get(t)
        if cur:
            cur['ints'], cur['floats'] = max(cur['ints'], ni), max(cur['floats'], nf)
        else:
            e = {'addr': t, 'ints': ni, 'floats': nf}
            seen[t] = e; callees.append(e)
    if stride:
        # indexes into a table of `stride`-byte elements must stay inside the region (retail would read arbitrary RAM, the wrapper aborts)
        for k, v in args.items():
            pass
    for sl in f.get('scaled_loads', []):
        if sl['field_off'] is None:
            continue
        for r in regs:        # bound the INDEX field (read as s16, scaled by sl['scale']) inside every element of every strided region
            room = max(l['len'] for l in regs if l is not r) if len(regs) > 1 else r['len']
            top = max(1, min(7, room // sl['scale'] - 2))
            if stride:
                r.setdefault('patch', [])
                for kk in range(r['len'] // stride):
                    r['patch'].append({'off': kk * stride + sl['field_off'], 'len': 1, 'choice': list(range(0, top + 1))})     # s16 index: low byte small,
                    r['patch'].append({'off': kk * stride + sl['field_off'] + 1, 'len': 1, 'choice': [0]})                    # high byte 0 (patch bytes are independent)
    spec = {'func': h, 'cases': a.cases, 'seed': 1, 'check_ret': f['returns'] == 'value',
            'port': {'wrapper': '%s/wrapper_%s.c' % (a.out, h), 'sources': [port], 'include': [a.include]},
            'args': args, 'regions': regs, 'callees': callees,
            'notes': 'generated by tools/specgen.py: only ADD to it (never remove args/regions/callee registers; autodiff keeps a ledger and rejects a weaker spec)'}
    if stride:
        spec['auto_range'] = [-2, MAXEL - 1]
    os.makedirs(a.out, exist_ok=True)
    sp = os.path.join(a.out, 'spec_%s.json' % h)
    if os.path.exists(sp):
        sys.exit('%s exists: refusing to overwrite (it may be strengthened already). Delete it by hand to regenerate.' % sp)
    json.dump(spec, open(sp, 'w'), indent=1)
    w = ['/* wrapper skeleton for retail %s, generated by tools/specgen.py. Finish it, then run:  AD_SANITIZE=1 ./dcre autodiff %s --mutate' % (h, sp),
         ' * Rules: pass the retail arguments exactly as the asm shows (see ./dcre annotate 0x%s); report EVERY stubbed call with ad_call(), in order,' % h,
         ' * with all the argument registers listed below; tail calls: report the tail callee LAST and return nothing after it. */',
         '#include "autodiff.h"', '/* #include "%s" */' % os.path.basename(port).replace('.c', '.h'), '']
    for c in callees:
        call = [x for x in f['calls'] if c['addr'] == '%08x' % (x['target'] or 0)][0]
        w.append('/* callee %s%s: compare ints=%d floats=%d. Registers at the call:' % (c['addr'], ' (TAIL CALL)' if call['tail'] else '', c['ints'], c['floats']))
        for k, v in call['args'].items():
            w.append(' *    %-4s = %s' % (k, v))
        w.append(' */')
        w.append('static void report_%s(const uint32_t *ints /* %d */, const uint32_t *floats /* %d */)\n{\n    /* ad_call(0x%s, ints, %d, floats, %d); */\n}\n' % (c['addr'], c['ints'], c['floats'], c['addr'], c['ints'], c['floats']))
    w.append('void ad_wrapper(ad_regs *c)\n{\n    /* TODO: map c->r[4..7] / c->fr[4..] (retail registers) and ad_mem(0x...) (retail memory) onto your port; set c->ret if check_ret */\n    #error "wrapper not finished"\n}')
    wp = os.path.join(a.out, 'wrapper_%s.c' % h)
    if not os.path.exists(wp):
        open(wp, 'w').write('\n'.join(w) + '\n')
    print('wrote %s and %s' % (sp, wp))
    print('params=%s returns=%s regions=%s callees=%s' % (f['params'], f['returns'], [(r['addr'], r['len']) for r in regs], [(c['addr'], c['ints'], c['floats']) for c in callees]))
    if stride:
        print('stride/size constant 0x%x detected: regions hold >= 8 elements; give the index argument small values via "auto" or a list like [0,1,2,3,7]' % stride)


if __name__ == '__main__':
    main()
