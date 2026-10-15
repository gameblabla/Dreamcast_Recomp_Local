#!/usr/bin/env python3
"""rank.py: which ready function should the agent port NEXT? Difficulty estimate + similarity to already ported functions. Stdlib only.

  python3 -I tools/dc/rank.py [N=60] [--maxb 600]        # ranks the first N ready slices from triage.py next
  python3 -I tools/dc/rank.py 0x8c043680 0x8c04c938 ...  # ranks the given addresses

Why: easiest-first runs out of steam; matching-decomp projects found that functions SIMILAR to ones already done are cheap (the model copies the idiom),
and Mizuchi's Decomp Atlas ranks by a difficulty model over instruction/branch/label counts. Score = difficulty x (1 - 0.5 x best similarity).
difficulty = instructions + 4*branches + 10*calls + 6*float ops + 25*(stack args) + 30*(loop with a COUNT parameter) + 60*(indirect jump/call).
Lower is better. Everything is an estimate: the first real trials (our own ledger) decide.
"""
import os, re, subprocess, sys

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
import brief, dcfacts


def candidates(n, maxb):
    r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'triage.py'), 'next', str(n), str(maxb)], capture_output=True, text=True, cwd=brief.project_root())
    return [int(l.split()[0], 16) for l in r.stdout.split('\n') if re.match(r'^[0-9a-f]{8}\s', l)]


def features(addr):
    text = dcfacts.annotate_text(addr)
    f = dcfacts.facts(addr, text)
    pc = dcfacts.param_classes(text)
    ins = re.findall(r'^[> ]([0-9a-f]{8}): ([ _])(\S+)', text, flags=re.M)
    ops = [i[2] for i in ins]
    br = sum(1 for o in ops if re.match(r'(bt|bf|bra|bsr|jmp|jsr|braf|bsrf)', o))
    fl = sum(1 for o in ops if re.match(r'f[a-z]+', o) and o not in ('fmov', 'fmov.s'))
    ind = len(re.findall(r'\b(jmp\s+@r\d+|braf\s+r\d+)', text)) + sum(1 for c in f['calls'] if not c['target'])     # jump tables / unresolved calls (a normal `jsr @rN` with a known pool target is just a call)
    loops = len(f['loops']) // 3 if f['loops'] else 0
    diff = len(ops) + 4 * br + 10 * len(f['calls']) + 6 * fl + 25 * len(pc['stack_args']) + (30 if (pc['count'] and f['loops']) else 0) + 60 * ind
    return dict(addr=addr, instr=len(ops), branches=br, calls=len(f['calls']), floats=fl, stack=len(pc['stack_args']), ptr=len(pc['ptr']) + len(pc['stack_ptr']), count=bool(pc['count']), indirect=ind, difficulty=diff)


def main():
    args = sys.argv[1:]
    maxb = 600
    if '--maxb' in args:
        i = args.index('--maxb'); maxb = int(args[i + 1]); del args[i:i + 2]
    root = brief.project_root()
    addrs = [int(a, 16) for a in args if re.match(r'(0x)?[0-9a-fA-F]{8}$', a)] or candidates(int(args[0]) if args and args[0].isdigit() else 60, maxb)
    rows = []
    for a in addrs:
        try:
            ft = features(a)
            sim = brief.similar_ports(root, a, n=1)
            ft['sim'] = sim[0][0] if sim else 0.0
            ft['sim_to'] = '%08x' % sim[0][1] if sim else '-'
            ft['score'] = ft['difficulty'] * (1 - 0.5 * ft['sim'])
            rows.append(ft)
        except Exception as ex:
            print('# skipped %08x: %s' % (a, str(ex)[:80]), file=sys.stderr)
    rows.sort(key=lambda r: r['score'])
    print('score\taddr\tinstr\tbr\tcalls\tfloat\tstack\tptr\tcount\tind\tsimilar%\tsimilar_to')
    for r in rows:
        print('%.0f\t%08x\t%d\t%d\t%d\t%d\t%d\t%d\t%s\t%d\t%.0f\t%s' % (r['score'], r['addr'], r['instr'], r['branches'], r['calls'], r['floats'], r['stack'], r['ptr'], 'Y' if r['count'] else '-', r['indirect'], r['sim'] * 100, r['sim_to']))


if __name__ == '__main__':
    main()
