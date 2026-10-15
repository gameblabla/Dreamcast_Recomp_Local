#!/usr/bin/env python3
"""libtriage.py: separate linked SDK/middleware library code from game code WITHOUT having the SDK. Game-independent. Stdlib only.

  python3 -I tools/libtriage.py run [--holdout N]     # classify every function -> work/research/lib_triage.tsv + summary
  python3 -I tools/libtriage.py summary               # counts per class (reads lib_triage.tsv)
  python3 -I tools/libtriage.py why ADDR              # evidence chain for one function
  python3 -I tools/libtriage.py validate [--frac 0.3] # hold-out test: hide part of the exact matches, see what is recovered, and
                                                      # how many known GAME functions (ported/curated) are wrongly called library

ONLY FOR THE NO-SDK CASE. `./dcre libtriage` / `./dcre export` skip it when `./dcre sdk` finds the exact SDK release in SDK_DIRS
(names, headers and byte-matching come from the SDK then); `--force` overrides.

Why: the CRC table in third_party/dc-re-ghidra only knows R8/R10/R11 builds, so a game linked with Katana R1.42J (or any older/odd build)
exact-matches only ~3% of its library code (Nadesico: 153 of ~1700 library functions). Library code is the bulk of what a
local agent would otherwise waste hours on. This tool spreads those few exact matches over the rest of the library using
structure that survives a different library version, so no SDK copy is needed:

  class         meaning (evidence)                                                                   confidence
  sdk-exact     whole-function CRC matches a known library function (name known)                      certain
  lib-callee    DIRECTLY CALLED by a library function. Link-time code cannot call game code           high
                (game code is only reached from libraries through pointers), so a callee of a
                library function is library. Propagated to a fixpoint.
  lib-run       sits between two library functions of the SAME module in address order, in a stretch  medium
                with no known game function. Libraries are linked as contiguous objects.
  lib-hint      none of the above, but its size equals exactly one function of the library module     low (a NAME GUESS only)
                that owns the surrounding code (see column hint); never used as evidence itself
  game-known    ported / curated by you (src/ port/ core/, docs/PORTED.tsv, names.tsv): never relabelled
  game-likely   no library evidence AND located below every library function: linkers place the game's own objects
                first, so this is almost certainly game code (still verify with `why`/slice)                  medium
  unknown       no evidence either way: treat as game code (the safe default: it costs a little time, never correctness)

Safety rules: lib-* is only ever propagated from sdk-exact seeds or from other lib-* functions; game-known blocks propagation;
a run is only filled between anchors of one module and at most DR_LIBRUN_MAX bytes wide (default 0x6000).
triage.py treats sdk-exact/lib-callee/lib-run as class 'sdk' (skipped by `next`), and shows lib-hint/unknown as todo.
"""
import collections, csv, os, random, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
G = os.environ.get('DR_RESEARCH', os.path.join(ROOT, 'work', 'research'))
SYMDB = os.path.join(ROOT, 'third_party', 'dc-re-ghidra', 'sdk-symbols.txt')
RUN_MAX = int(os.environ.get('DR_LIBRUN_MAX', '0x6000'), 16) if os.environ.get('DR_LIBRUN_MAX') else 0x6000
OUT = os.path.join(G, 'lib_triage.tsv')
SURE = ('sdk-exact', 'lib-callee', 'lib-run')


def tsv(name):
    p = os.path.join(G, name)
    if not os.path.exists(p):
        return []
    with open(p, newline='') as f:
        return list(csv.DictReader(f, delimiter='\t'))


def module_of(sdk_name):
    """'r8.libninja.a._kmiInit' -> 'libninja' (the library file; the release prefix is dropped)."""
    p = sdk_name.split('.')
    return p[1] if len(p) > 2 else '?'


def game_known(funcs):
    """Addresses the user already ported or named: negative anchors. Same rules as triage.py."""
    sys.path.insert(0, HERE)
    import triage
    done = triage.done_set()
    neg = {a for a in funcs if a in done or a[-6:] in done}
    p = os.path.join(ROOT, 'names.tsv')
    if os.path.exists(p):
        for line in open(p):
            if line.startswith('#') or not line.strip():
                continue
            a = line.split('\t')[0].strip().lower().replace('0x', '')
            if a in funcs:
                neg.add(a)
    return neg


def classify(funcs, calls, seeds, neg, db_len=None):
    """seeds: {addr: module}. Returns {addr: (class, module, evidence)}."""
    lab = {a: ('sdk-exact', m, 'CRC match') for a, m in seeds.items() if a in funcs and a not in neg}
    # 1. callee closure
    frontier = list(lab)
    while frontier:
        f = frontier.pop()
        m = lab[f][1]
        for c in calls.get(f, ()):
            if c in funcs and c not in lab and c not in neg:
                lab[c] = ('lib-callee', m, 'called by %s' % f)
                frontier.append(c)
    # 2. runs between same-module anchors
    order = sorted(funcs, key=lambda a: int(a, 16))
    prev = None            # (index, module) of last library function seen
    run = []
    for i, a in enumerate(order):
        if a in lab:
            if prev is not None and run and lab[prev][1] == lab[a][1]:
                lo, hi = int(prev, 16), int(a, 16) + int(funcs[a]['bytes'])
                if hi - lo <= RUN_MAX and not any(x in neg for x in run):
                    for x in run:
                        lab[x] = ('lib-run', lab[a][1], 'between %s and %s' % (prev, a))
            prev, run = a, []
        elif a in neg:
            prev, run = None, []
        elif prev is not None:
            run.append(a)
    # 3. runs can expose new callees: close again (callee of a run function is library)
    frontier = [a for a, v in lab.items() if v[0] == 'lib-run']
    while frontier:
        f = frontier.pop()
        for c in calls.get(f, ()):
            if c in funcs and c not in lab and c not in neg:
                lab[c] = ('lib-callee', lab[f][1], 'called by %s' % f)
                frontier.append(c)
    return lab


def load():
    funcs = {r['address'].lower(): r for r in tsv('functions.tsv')}
    if not funcs:
        sys.exit('missing %s/functions.tsv: run `./dcre export` first' % G)
    calls = collections.defaultdict(set)
    for r in tsv('callgraph.tsv'):
        calls[r['caller'].lower()].add(r['callee'].lower())
    seeds = {r['address'].lower(): module_of(r['sdk_name']) for r in tsv('sdk_matches.tsv')}
    return funcs, calls, seeds


def hints(funcs, lab):
    """For functions with no label: unique same-size candidate in the module that owns the surrounding library code."""
    if not os.path.exists(SYMDB):
        return {}
    bylen = collections.defaultdict(lambda: collections.defaultdict(set))   # module -> len -> names
    for line in open(SYMDB):
        s = line.rstrip('\n').split('@')
        if len(s) >= 5:
            bylen[s[3].replace('.a', '')][int(s[1])].add(s[4])
    order = sorted(funcs, key=lambda a: int(a, 16))
    out, last = {}, None
    nxt = {}
    n = None
    for a in reversed(order):
        nxt[a] = n
        if a in lab:
            n = lab[a][1]
    for a in order:
        if a in lab:
            last = lab[a][1]
        elif last and nxt[a] == last:
            c = bylen.get(last, {}).get(int(funcs[a]['bytes']), set())
            if len(c) == 1:
                out[a] = (last, next(iter(c)))
    return out


def cmd_run(args):
    funcs, calls, seeds = load()
    neg = game_known(funcs)
    lab = classify(funcs, calls, seeds, neg)
    hint = hints(funcs, lab)
    lowest = min((int(a, 16) for a in lab), default=None)
    os.makedirs(G, exist_ok=True)
    with open(OUT, 'w') as f:
        f.write('address\tclass\tmodule\tbytes\thint\tevidence\n')
        for a in sorted(funcs, key=lambda x: int(x, 16)):
            if a in lab:
                c, m, e = lab[a]
                f.write('%s\t%s\t%s\t%s\t\t%s\n' % (a, c, m, funcs[a]['bytes'], e))
            elif a in neg:
                f.write('%s\tgame-known\t\t%s\t\tported or curated\n' % (a, funcs[a]['bytes']))
            elif a in hint:
                f.write('%s\tlib-hint\t%s\t%s\t%s\tsame size as exactly one %s function (name guess only)\n' % (a, hint[a][0], funcs[a]['bytes'], hint[a][1], hint[a][0]))
            elif lowest is not None and int(a, 16) < lowest:
                f.write('%s\tgame-likely\t\t%s\t\tbelow the first library function (%08x): game objects are linked first\n' % (a, funcs[a]['bytes'], lowest))
            else:
                f.write('%s\tunknown\t\t%s\t\t\n' % (a, funcs[a]['bytes']))
    print('wrote %s' % OUT)
    cmd_summary()


def cmd_summary(_=None):
    rows = tsv('lib_triage.tsv')
    if not rows:
        sys.exit('run `libtriage.py run` first')
    cnt, byt, mods = collections.Counter(), collections.Counter(), collections.Counter()
    for r in rows:
        cnt[r['class']] += 1
        byt[r['class']] += int(r['bytes'])
        if r['class'] in SURE:
            mods[r['module']] += int(r['bytes'])
    tot = sum(byt.values())
    for c in ('sdk-exact', 'lib-callee', 'lib-run', 'lib-hint', 'game-known', 'game-likely', 'unknown'):
        print('  %-11s n=%5d bytes=%8d (%4.1f%%)' % (c, cnt[c], byt[c], 100 * byt[c] / max(tot, 1)))
    lib = sum(byt[c] for c in SURE)
    print('  => library code identified without the SDK: %d bytes (%.1f%% of all function bytes)' % (lib, 100 * lib / max(tot, 1)))
    print('  by module (bytes): ' + ', '.join('%s=%d' % kv for kv in mods.most_common(10)))


def cmd_why(a):
    a = '%08x' % int(a, 16)
    for r in tsv('lib_triage.tsv'):
        if r['address'] == a:
            print('%s class=%s module=%s hint=%s : %s' % (a, r['class'], r['module'], r['hint'], r['evidence']))
            e = r['evidence']
            seen = 0
            while seen < 12:                       # follow 'called by X' / 'between X and Y' chains back to an exact match
                m = re.search(r'called by ([0-9a-f]{8})|between ([0-9a-f]{8})', e)
                if not m:
                    break
                p = m.group(1) or m.group(2)
                x = next((q for q in tsv('lib_triage.tsv') if q['address'] == p), None)
                if not x:
                    break
                print('  <- %s %s %s' % (p, x['class'], x['evidence']))
                e, seen = x['evidence'], seen + 1
            return
    sys.exit('no such function')


def cmd_validate(args):
    frac = 0.3
    if '--frac' in args:
        frac = float(args[args.index('--frac') + 1])
    funcs, calls, seeds = load()
    neg = game_known(funcs)
    rnd = random.Random(1)
    keys = sorted(seeds)
    hide = set(rnd.sample(keys, int(len(keys) * frac)))
    kept = {a: m for a, m in seeds.items() if a not in hide}
    lab = classify(funcs, calls, kept, neg)
    rec = [a for a in hide if a in lab and lab[a][1] == seeds[a]]
    wrong_mod = [a for a in hide if a in lab and lab[a][1] != seeds[a]]
    fp = [a for a in neg if a in lab]
    full = classify(funcs, calls, seeds, neg)
    print('seeds=%d hidden=%d (%.0f%%)' % (len(keys), len(hide), 100 * frac))
    print('hidden exact matches rediscovered as library: %d/%d (%.0f%%); with the wrong module: %d' % (len(rec), len(hide), 100 * len(rec) / max(len(hide), 1), len(wrong_mod)))
    print('library functions found with partial seeds: %d (all seeds: %d)' % (len(lab), len(full)))
    print('GAME functions (ported/curated, n=%d) wrongly labelled library: %d %s' % (len(neg), len(fp), fp[:8]))
    by = collections.Counter(v[0] for v in lab.values())
    print('by class: ' + ', '.join('%s=%d' % kv for kv in sorted(by.items())))
    return 1 if fp else 0


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a[0] == 'run':
        cmd_run(a[1:])
    elif a[0] == 'summary':
        cmd_summary()
    elif a[0] == 'why' and len(a) > 1:
        cmd_why(a[1])
    elif a[0] == 'validate':
        sys.exit(cmd_validate(a[1:]))
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
