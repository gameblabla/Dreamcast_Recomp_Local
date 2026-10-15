#!/usr/bin/env python3
"""sdk_index.py: build a LOCAL function-signature table from your own Dreamcast SDK copy, so library code in any game of that era is named
(relocation-tolerant Ghidra function-ID hashes, much better than the CRC table that only knows R8/R10/R11). Stdlib only + wine/wibo + Ghidra.

  python3 -I tools/sdk_index.py build SDK_DIR [--out DIR]    # lbr+lnk (Hitachi tools from the SDK) -> ELF -> Ghidra ExportSigs -> DIR/katana-sdk.sigs
  python3 -I tools/sdk_index.py status [--out DIR]

Nothing from the SDK is committed or bundled: libraries are copied to a scratch dir only for linking and deleted afterwards; the result is a table of
hashes + symbol names that stays under work/ (git-ignored). DIR defaults to $DR_SDK_INDEX or work/sdk_index. The wine prefix needs ~2 GB: it lives in
DIR/wineprefix (set DR_WINEPREFIX to put it elsewhere, e.g. tmpfs). `./dcre export` applies the table automatically when it exists.
Needs: wine or wibo, Ghidra headless (./dcre doctor). Takes a few minutes (Nadesico's 1.42J: 10 libraries).
"""
import glob, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
MAPNAMES = os.path.join(ROOT, 'skills', 'dc-decomp-kickoff', 'scripts', 'map_names.py')
GSCRIPTS = os.path.join(ROOT, 'skills', 'dc-decomp-kickoff', 'scripts', 'ghidra')


def default_out():
    return os.environ.get('DR_SDK_INDEX') or os.path.join(ROOT, 'work', 'sdk_index')


def find_ci(root, name):
    for dp, dn, fn in os.walk(root):
        for f in fn:
            if f.lower() == name.lower():
                return os.path.join(dp, f)
    return None


def headless():
    for c in (os.environ.get('GHIDRA_HEADLESS'), shutil.which('analyzeHeadless'), '/usr/libexec/ghidra/support/analyzeHeadless',
              os.path.join(os.environ.get('GHIDRA_INSTALL_DIR', '/nonexistent'), 'support', 'analyzeHeadless'), '/opt/ghidra/support/analyzeHeadless'):
        if c and os.path.exists(c):
            return c
    sys.exit('Ghidra headless not found: set GHIDRA_HEADLESS')


def build(sdk, out):
    runner = shutil.which('wibo') or shutil.which('wine')
    if not runner:
        sys.exit('need wine or wibo to run the SDK\'s Hitachi tools (lbr.exe/lnk.exe)')
    lbr, lnk = find_ci(sdk, 'lbr.exe'), find_ci(sdk, 'lnk.exe')
    if not (lbr and lnk):
        sys.exit('no lbr.exe/lnk.exe under %s (the SDK\'s shc/bin folder is needed)' % sdk)
    env = dict(os.environ, WINEDEBUG='-all', DISPLAY='', WINEPREFIX=os.environ.get('DR_WINEPREFIX') or os.path.join(out, 'wineprefix'))
    libd, linkd = [os.path.join(out, d) for d in ('libs', 'link')]
    for d in ('elf', 'names', 'sigs', 'libs', 'link'):
        shutil.rmtree(os.path.join(out, d), ignore_errors=True); os.makedirs(os.path.join(out, d))
    n = 0
    seen = set()
    for dp, dn, fn in os.walk(sdk):
        for f in sorted(fn):
            if not f.lower().endswith('.lib'):
                continue
            p = os.path.join(dp, f)
            with open(p, 'rb') as fh:
                if fh.read(1) != b'\xe0':        # Hitachi SYSROF libraries only (ELF/CodeWarrior libs are skipped)
                    continue
            key = (f.lower(), os.path.getsize(p))
            if key in seen:
                continue
            seen.add(key)
            b = re.sub(r'[^a-z0-9]', '_', f.lower()[:-4])
            shutil.copy(p, os.path.join(libd, b + '.lib'))
            n += 1
    print('%d Hitachi libraries' % n)

    def tool(args, stdin=None):
        return subprocess.run([runner] + args, input=stdin, cwd=linkd, env=env, capture_output=True, text=True, errors='replace')

    ok = 0
    for lib in sorted(glob.glob(os.path.join(libd, '*.lib'))):
        b = os.path.basename(lib)[:-4]
        r = tool([lbr], 'library ..\\libs\\%s.lib\nlist\nexit\n' % b)
        mods = [m.group(1) for m in re.finditer(r'^(\S+)\s+Entry date:', r.stdout.replace('\r', ''), re.M)]
        if not mods:
            print('  %s: no modules listed, skipped' % b); continue
        sub = ['elf', 'print %s.map' % b, 'output %s.elf' % b] + ['input ..\\libs\\%s.lib(%s)' % (b, m) for m in mods] + ['exit']
        open(os.path.join(linkd, b + '.sub'), 'w').write('\n'.join(sub) + '\n')
        r = tool([lnk, '-subcommand=%s.sub' % b])
        open(os.path.join(linkd, b + '.log'), 'w').write(r.stdout)
        if os.path.exists(os.path.join(linkd, b + '.elf')) and 'COMPLETED' in r.stdout:
            shutil.copy(os.path.join(linkd, b + '.elf'), os.path.join(out, 'elf'))
            names = subprocess.run([sys.executable, '-I', MAPNAMES, os.path.join(linkd, b + '.map')], capture_output=True, text=True).stdout
            open(os.path.join(out, 'names', b + '.names'), 'w').write(names)
            print('  %-14s %3d modules, %5d symbols' % (b, len(mods), len(names.split('\n')) - 1))
            ok += 1
        else:
            print('  %s: link failed (see %s.log)' % (b, os.path.join(linkd, b)))
    if not ok:
        sys.exit('no library linked')
    shutil.rmtree(libd, ignore_errors=True)         # nothing of the SDK libraries stays on disk
    shutil.rmtree(os.path.join(out, 'link'), ignore_errors=True)
    # Hash every ELF with Ghidra (one headless run)
    proj = os.path.join(out, 'ghproj'); shutil.rmtree(proj, ignore_errors=True); os.makedirs(proj)
    print('hashing with Ghidra ...')
    r = subprocess.run([headless(), proj, 'sdkproj', '-import', os.path.join(out, 'elf'), '-overwrite', '-processor', 'SuperH4:LE:32:default',
                        '-scriptPath', GSCRIPTS, '-postScript', 'ExportSigs.java', os.path.join(out, 'names'), os.path.join(out, 'sigs')],
                       capture_output=True, text=True)
    open(os.path.join(out, 'ghidra.log'), 'w').write(r.stdout + r.stderr)
    sigs = sorted(glob.glob(os.path.join(out, 'sigs', '*.sigs')))
    with open(os.path.join(out, 'katana-sdk.sigs'), 'w') as o:
        for s in sigs:
            o.write(open(s).read())
    with open(os.path.join(out, 'katana-sdk.libs'), 'w') as o:        # symbol -> library file, for module-level triage
        for nf in sorted(glob.glob(os.path.join(out, 'names', '*.names'))):
            lib = os.path.basename(nf)[:-6]
            for line in open(nf):
                if line.strip():
                    o.write('%s\t%s\n' % (line.split(None, 1)[1].strip(), lib))
    shutil.rmtree(proj, ignore_errors=True); shutil.rmtree(os.path.join(out, 'elf'), ignore_errors=True)
    cnt = sum(1 for _ in open(os.path.join(out, 'katana-sdk.sigs')))
    if not cnt:
        sys.exit('empty signature table: see %s/ghidra.log' % out)
    print('%d signatures -> %s/katana-sdk.sigs  (local, git-ignored; delete %s/wineprefix to free ~2 GB)' % (cnt, out, out))


def status(out):
    p = os.path.join(out, 'katana-sdk.sigs')
    print('%s: %s' % (p, ('%d signatures' % sum(1 for _ in open(p))) if os.path.exists(p) else 'not built (python3 -I tools/sdk_index.py build SDK_DIR)'))


def main():
    a = sys.argv[1:]
    out = default_out()
    if '--out' in a:
        i = a.index('--out'); out = os.path.abspath(a[i + 1]); del a[i:i + 2]
    if not a:
        sys.exit(__doc__)
    if a[0] == 'build' and len(a) > 1:
        os.makedirs(out, exist_ok=True)
        build(os.path.abspath(a[1]), out)
    elif a[0] == 'status':
        status(out)
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
