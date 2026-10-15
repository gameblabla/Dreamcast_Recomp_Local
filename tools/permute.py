#!/usr/bin/env python3
"""permute.py: tiny source permuter for byte-matching one function. EXPERIMENTAL helper; read docs/BYTE_MATCHING.md first.

  python3 -I tools/permute.py --addr 8c06fac4 --len 96 --src fn.c --func fn_8c06fac4 [--iters 300] [--seed 1] [--cc ...]

Random-walks semantically neutral source rewrites (operand order, ++i/i++, x*2/x<<1, declaration order, > vs reversed <, !x vs x==0,
for<->while, signedness casts on constants, ...) and keeps the candidate with the lowest tools/bytematch.py score. Writes fn.best.c.
IMPORTANT: a permuter only finds SOME source that compiles to the same bytes. It does not tell you what the code means, and it can
land on a source that is NOT equivalent under a modern compiler. Re-verify every result with tools/autodiff.py (behaviour) and keep
the readable intent in comments. See docs/UB_AND_OLD_COMPILERS.md.
"""
import argparse, os, random, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
RULES = [
    (r'\b(\w+) \+ (\w+)\b', r'\2 + \1'),
    (r'\b(\w+) \* (\w+)\b', r'\2 * \1'),
    (r'\b(\w+) & (\w+)\b', r'\2 & \1'),
    (r'\b(\w+)\+\+;', r'++\1;'), (r'\+\+(\w+);', r'\1++;'),
    (r'\b(\w+) \* 2\b', r'\1 << 1'), (r'\b(\w+) << 1\b', r'\1 * 2'),
    (r'\b(\w+) < (\w+)\b', r'\2 > \1'), (r'\b(\w+) > (\w+)\b', r'\2 < \1'),
    (r'\b(\w+) <= (\w+)\b', r'\2 >= \1'), (r'\b(\w+) >= (\w+)\b', r'\2 <= \1'),
    (r'!(\w+)\b', r'\1 == 0'), (r'\b(\w+) == 0\b', r'!\1'),
    (r'\b(\w+) != 0\b', r'\1'),
    (r'\b(\w+) \+= (\w+);', r'\1 = \1 + \2;'), (r'\b(\w+) = \1 \+ (\w+);', r'\1 += \2;'),
    (r'\b(\w+) -= 1;', r'\1--;'), (r'\b(\w+) \+= 1;', r'\1++;'),
]


def mutate(src, rnd):
    body_start = src.find('{')
    head, body = src[:body_start], src[body_start:]
    lines = body.split('\n')
    for _ in range(30):
        kind = rnd.random()
        if kind < 0.15:   # swap two adjacent simple declaration lines
            idx = [i for i in range(len(lines) - 1) if re.match(r'\s*(unsigned |signed |int |short |char |long |float )[\w *]+;', lines[i]) and re.match(r'\s*(unsigned |signed |int |short |char |long |float )[\w *]+;', lines[i + 1])]
            if idx:
                i = rnd.choice(idx); lines[i], lines[i + 1] = lines[i + 1], lines[i]; return head + '\n'.join(lines)
        pat, rep = rnd.choice(RULES)
        sites = [(i, m) for i, ln in enumerate(lines) for m in re.finditer(pat, ln)]
        if sites:
            i, m = rnd.choice(sites)
            lines[i] = lines[i][:m.start()] + m.expand(rep) + lines[i][m.end():]
            return head + '\n'.join(lines)
    return src


def score(path, a):
    cmd = [sys.executable, '-I', os.path.join(HERE, 'bytematch.py'), '--addr', a.addr, '--len', str(a.len), '--src', path, '--func', a.func]
    if a.cc: cmd += ['--cc', a.cc]
    if a.bin: cmd += ['--bin', a.bin]
    r = subprocess.run(cmd, capture_output=True, text=True)
    m = re.search(r'score=(\d+)', r.stdout)
    return int(m.group(1)) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--addr', required=True); ap.add_argument('--len', type=int, required=True)
    ap.add_argument('--src', required=True); ap.add_argument('--func', required=True)
    ap.add_argument('--iters', type=int, default=300); ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--cc'); ap.add_argument('--bin')
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    best_src = open(a.src).read()
    best = score(a.src, a)
    if best is None:
        sys.exit('baseline does not compile / score')
    print('baseline score', best)
    tmp = a.src + '.perm.c'
    for it in range(a.iters):
        if best == 0:
            break
        cand = mutate(best_src, rnd)
        for _ in range(rnd.choice([0, 0, 1, 2])):
            cand = mutate(cand, rnd)
        if cand == best_src:
            continue
        open(tmp, 'w').write(cand)
        s = score(tmp, a)
        if s is not None and s <= best:
            if s < best:
                print('iter %d: score %d -> %d' % (it, best, s))
            best, best_src = s, cand
    os.remove(tmp) if os.path.exists(tmp) else None
    out = os.path.splitext(a.src)[0] + '.best.c'
    open(out, 'w').write(best_src)
    print('best score %d written to %s%s' % (best, out, '  (MATCH: now run tools/autodiff.py to prove behaviour)' if best == 0 else ''))


if __name__ == '__main__':
    main()
