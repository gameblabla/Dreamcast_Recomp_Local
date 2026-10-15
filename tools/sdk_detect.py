#!/usr/bin/env python3
"""sdk_detect.py: which Dreamcast SDK / compiler built this game, and do we have it? Game-independent. Stdlib only.

  python3 -I tools/sdk_detect.py BIN [SDK_DIR ...]

1. Reads the library banners ("<module> Ver x.y Build: date") from BIN and ranks the public SDK releases by how many of the
   game's library builds they contain (skills/dc-decomp-kickoff/scripts/sdk_scan.py + references/sdk-banners.tsv).
2. Looks for compiler fingerprints (GCC / SHC / Hitachi strings) in BIN.
3. Inventories each SDK_DIR you pass (or DR_SDK_DIRS=dir:dir): is the best-matching release there, do the compiler binaries
   (shc.exe / sh-elf gcc) and the .lib libraries exist?
Exit codes: 0 = the matching SDK is available; 3 = SDK missing or only a near match: the output ends with the exact thing to ASK THE USER FOR.
You can proceed without the SDK (names via signatures from other releases, no byte-matching) but it is much slower and the
result is weaker: say so when asking.
"""
import os, re, subprocess, sys

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
SCAN = os.path.join(ROOT, 'skills/dc-decomp-kickoff/scripts/sdk_scan.py')
TABLE = os.path.join(ROOT, 'skills/dc-decomp-kickoff/references/sdk-banners.tsv')


def compilers(data):
    found = []
    for pat, label in ((rb'GCC: \(GNU\) ([0-9][0-9.]+)', 'GCC'), (rb'(Hitachi[^\x00]{0,60})', 'Hitachi'), (rb'(SHC[^\x00]{0,40}(?:Ver|Rel)[^\x00]{0,20})', 'SHC'),
                       (rb'(Hitachi SH[^\x00]{0,60})', 'Hitachi SH'), (rb'(KATANA[^\x00]{0,40})', 'KATANA'), (rb'(gcc2_compiled\.)', 'gcc2 marker'),
                       (rb'(CodeWarrior[^\x00]{0,40})', 'CodeWarrior')):
        for m in sorted(set(re.findall(pat, data)))[:4]:
            found.append('%s: %s' % (label, m.decode('latin-1') if isinstance(m, bytes) else m))
    return found


def inventory(d):
    r = {'dir': d, 'exists': os.path.isdir(d), 'shc': [], 'gcc': [], 'lib': 0, 'headers': 0, 'iso': []}
    if not r['exists']:
        return r
    for dp, dn, fn in os.walk(d):
        for f in fn:
            fl = f.lower()
            if fl in ('shc.exe', 'shcpp.exe', 'asmsh.exe', 'lnk.exe', 'lbr.exe'):
                r['shc'].append(os.path.join(dp, f))
            elif fl.startswith(('sh-elf-gcc', 'sh4-gcc', 'gcc.exe', 'cc1.exe')):
                r['gcc'].append(os.path.join(dp, f))
            elif fl.endswith('.lib'):
                r['lib'] += 1
            elif fl.endswith('.h'):
                r['headers'] += 1
            elif fl.endswith(('.iso', '.zip')):
                r['iso'].append(f)
        if len(r['shc']) > 8 or r['lib'] > 2000:
            break
    return r


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    binp = sys.argv[1]
    dirs = sys.argv[2:] or [d for d in os.environ.get('DR_SDK_DIRS', '').split(':') if d]
    data = open(binp, 'rb').read()
    print('== game library banners vs public SDK releases')
    r = subprocess.run([sys.executable, '-I', SCAN, TABLE, binp], capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip())
    full = re.search(r'Full match: (.*)', r.stdout)
    best = full.group(1).strip() if full else None
    if not best:
        m = re.search(r'^\s*(\d+)/(\d+)\s+(.+?)\s+\(libraries', r.stdout, re.M)
        near = m.group(3) if m else None
    print('\n== compiler fingerprints in the binary')
    for c in compilers(data) or ['none found (stripped; use the instruction idioms: see docs/BYTE_MATCHING.md)']:
        print('  ' + c)
    print('\n== your SDK folders')
    have = False
    if not dirs:
        print('  none configured (set SDK_DIRS in project.env, or pass folders)')
    for d in dirs:
        inv = inventory(d)
        print('  %s: %s  shc-tools=%d gcc-tools=%d .lib=%d headers=%d images=%s' % (d, 'ok' if inv['exists'] else 'MISSING', len(inv['shc']), len(inv['gcc']), inv['lib'], inv['headers'], ','.join(inv['iso'][:3]) or '-'))
        if inv['exists'] and (inv['lib'] or inv['headers'] or inv['shc']):
            have = True
        # does the folder (or its images) contain the best-matching release? use sdk_scan on it
        if inv['exists'] and best:
            rr = subprocess.run([sys.executable, '-I', SCAN, d, binp], capture_output=True, text=True)
            fm = re.search(r'Full match: (.*)', rr.stdout)
            top = re.search(r'^\s*(\d+)/(\d+)\s+(.+?)\s+\(', rr.stdout, re.M)
            print('     scan of this folder: ' + (('FULL MATCH (%s)' % (best or fm.group(1))) if fm else ('best %s/%s %s' % top.group(1, 2, 3) if top else 'no banner match')))
            if fm:
                print('\nRESULT: the exact SDK (%s) is available in %s. Byte-matching with the original compiler is possible.' % (best or fm.group(1), d)); sys.exit(0)
    print()
    shipped = sorted(os.path.basename(x) for x in __import__('glob').glob(os.path.join(ROOT, 'data', 'sigs', '*.sigs')))
    if best and any(t[len('katana-'):-5] in best for t in shipped):
        print('NOTE: this repo ships library signatures for %s (data/sigs/, hashes+names only): library functions are named WITHOUT an SDK.' % best)
        print('      The SDK is only needed for the original compiler (byte-matching) and exact headers; include/sdk_stripped_* has the declarations.')
    if best:
        print('RESULT: SDK NEEDED. The game was built with: %s.' % best)
        print('ASK THE USER: "Please give me a copy of the Dreamcast SDK %s (Katana/Shinobi libraries + SHC compiler) as a folder or .iso/.zip and set SDK_DIRS in project.env to it."' % best)
    else:
        print('RESULT: the SDK release could not be identified from banners (stripped libraries or an unlisted release).')
        print('ASK THE USER: which Katana SDK release the game used (1.00J / 1.42J / R8 / R9 / R10.1 / R11b ...) and for a copy of it; the closest public one by date is the best fallback.')
    print('No SDK? `./dcre libtriage` (run automatically by `./dcre export`) still separates linked library code from game code by structure.')
    print('Without it you can still proceed (the SH-4 reasoning, emulator differential and port workflow do not need the SDK), but naming library functions,')
    print('headers/struct layouts and byte-matching with the original compiler will be much slower or impossible. Say this when asking.')
    sys.exit(3)


if __name__ == '__main__':
    main()
