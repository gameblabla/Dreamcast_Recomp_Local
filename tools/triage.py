#!/usr/bin/env python3
"""triage.py: what is left to decompile and what to do next. Game-independent; reads work/research/*.tsv (from `dcre export`).

  python3 -I tools/triage.py summary             # counts and bytes per class
  python3 -I tools/triage.py next [N] [MAXB]     # N cheapest READY functions (all callees already done/library), default 8, <= 400 bytes
  python3 -I tools/triage.py slice ADDR          # classified callees + annotated asm for one function (start here)

Classes (first match wins):
  sdk   name or sdk_matches.tsv says SDK / middleware, or tools/libtriage.py proved it is linked library code without needing the SDK
        (work/research/lib_triage.tsv: sdk-exact, lib-callee, lib-run; lib-hint and unknown stay todo) (do not decompile: build against the real SDK or replace it)
  lib   address >= DR_LIB_START (env, hex): linked library region of the image (default: none)
  hw    touches PVR/AICA/G2/SH-4 registers >= 3 times (platform code)
  done  ported: a source file named *<addr>* exists under src/ or port/ (env DR_PORT_DIRS=dir,dir) or the address is listed in docs/PORTED.tsv
  todo  everything else
'ready' = todo function whose every callee is done/sdk/lib/hw (bottom-up order, so a callee is never decompiled after its caller).
"""
import collections, csv, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
G = os.path.join(os.environ.get('DR_RESEARCH', os.path.join(ROOT, 'work', 'research')))
LIB_START = int(os.environ.get('DR_LIB_START', '0'), 16) if os.environ.get('DR_LIB_START') else None
PORT_DIRS = os.environ.get('DR_PORT_DIRS', 'src,port,core').split(',')
HW_SYM = re.compile(r'^(PVR|TA_|SPG|FB_|AICA|SPU|G2|SB_|ASIC|GDROM|MAPLE|SQ|STARTRENDER|PT_)', re.I)
SDK_NAME = re.compile(r'^(r\d+\.|lib|_?sg|_?sd|_?pdr|_?mw|_?gd|_?bios|_?syCfg|_?sy|_?njd|_?kos)', re.I)


def tsv(name):
    p = os.path.join(G, name)
    if not os.path.exists(p):
        sys.exit('missing %s: run `./dcre export` first' % p)
    with open(p, newline='') as f:
        return list(csv.DictReader(f, delimiter='\t'))


def done_set():
    s = set()
    for d in PORT_DIRS:
        base = os.path.join(ROOT, d)
        if os.path.isdir(base):
            for fn in os.listdir(base):
                s.update(m.lower() for m in re.findall(r'(?<![0-9a-f])([0-9a-f]{8}|[0-9a-f]{6})(?![0-9a-f])', fn, re.I))
    p = os.path.join(ROOT, 'docs', 'PORTED.tsv')
    if os.path.exists(p):
        s.update(m.lower() for m in re.findall(r'^([0-9a-fA-F]{8})', open(p).read(), re.M))
    return s


def classify():
    funcs = {r['address'].lower(): r for r in tsv('functions.tsv')}
    sdk = {r['address'].lower() for r in tsv('sdk_matches.tsv')} if os.path.exists(os.path.join(G, 'sdk_matches.tsv')) else set()
    callees = collections.defaultdict(set)
    for r in tsv('callgraph.tsv'):
        callees[r['caller'].lower()].add(r['callee'].lower())
    hw = collections.defaultdict(int)
    if os.path.exists(os.path.join(G, 'hw_access.tsv')):
        for r in tsv('hw_access.tsv'):
            a = r['function'].split('@')[-1].lower()
            t = r['target'].lower().zfill(8)
            if t.startswith(('a05f', 'a070', 'a080', 'a100', 'a102')) or HW_SYM.match(r.get('target_symbol', '') or ''):
                hw[a] += 1
    done = done_set()
    lt = os.path.join(G, 'lib_triage.tsv')
    if os.path.exists(lt):
        sdk |= {r['address'].lower() for r in tsv('lib_triage.tsv') if r['class'] in ('sdk-exact', 'lib-callee', 'lib-run')}
    cls = {}
    for a, f in funcs.items():
        short = a[-6:]
        if a in sdk or SDK_NAME.match(f['name']):
            cls[a] = 'sdk'
        elif LIB_START is not None and int(a, 16) >= LIB_START:
            cls[a] = 'lib'
        elif hw.get(a, 0) >= 3:
            cls[a] = 'hw'
        elif a in done or short in done:
            cls[a] = 'done'
        else:
            cls[a] = 'todo'
    return funcs, callees, cls


def cmd_summary():
    funcs, callees, cls = classify()
    cnt, byt = collections.Counter(), collections.Counter()
    for a, c in cls.items():
        cnt[c] += 1
        byt[c] += int(funcs[a]['bytes'])
    tot = sum(byt.values())
    print('functions=%d bytes=%d' % (len(funcs), tot))
    for c in ('done', 'todo', 'hw', 'sdk', 'lib'):
        print('  %-5s n=%5d bytes=%8d (%4.1f%%)' % (c, cnt[c], byt[c], 100 * byt[c] / max(tot, 1)))
    if not os.path.exists(os.path.join(G, 'lib_triage.tsv')):
        print('  (library code not yet separated: run `./dcre libtriage` — works without the SDK)')


def cmd_next(n=8, maxb=400):
    funcs, callees, cls = classify()
    out = []
    for a, c in cls.items():
        b = int(funcs[a]['bytes'])
        if c != 'todo' or b > maxb or b < 8:
            continue
        if any(cls.get(x) == 'todo' and x != a for x in callees.get(a, ())):
            continue
        out.append((-int(funcs[a]['callers']), b, a))
    out.sort()
    for _, b, a in out[:n]:
        print('%s\t%dB\tcallers=%s\t%s' % (a, b, funcs[a]['callers'], funcs[a]['name']))
    print('ready_total=%d' % len(out))


def cmd_slice(addr):
    funcs, callees, cls = classify()
    a = '%08x' % int(addr, 16)
    print('# %s class=%s bytes=%s callers=%s name=%s' % (a, cls.get(a), funcs[a]['bytes'], funcs[a]['callers'], funcs[a]['name']))
    for x in sorted(callees.get(a, ())):
        print('# callee %s %s %s' % (x, cls.get(x), funcs.get(x, {}).get('name', '?')))
    print(subprocess.run([sys.executable, '-I', os.path.join(HERE, 'sh4_annotate.py'), '0x' + a], capture_output=True, text=True).stdout)


if __name__ == '__main__':
    c = sys.argv[1] if len(sys.argv) > 1 else 'summary'
    if c == 'summary':
        cmd_summary()
    elif c == 'next':
        cmd_next(int(sys.argv[2]) if len(sys.argv) > 2 else 8, int(sys.argv[3]) if len(sys.argv) > 3 else 400)
    elif c == 'slice':
        cmd_slice(sys.argv[2])
    else:
        sys.exit(__doc__)
