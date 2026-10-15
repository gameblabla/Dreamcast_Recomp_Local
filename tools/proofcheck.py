#!/usr/bin/env python3
"""proofcheck.py: are the "CONFIRMED / PROVEN / VERIFIED" claims in port files and reports backed by a proof? Stdlib only.

  python3 -I tools/proofcheck.py [FILES or DIRS ...]        default: port/ and reports under work/reports/
  python3 -I tools/proofcheck.py --func 8c073f72           show the ledger of one function

autodiff appends every run to work/proofs/<func>.json (spec fingerprint, sha of each port source, result). A claim for function F is BACKED only if
the newest ledger entry for F ended `RESULT: PROVEN` AND the port sources it recorded still have the same hash (editing the port after the proof
voids it). Also reported: a ledger whose newest PROVEN entry was later followed by a run with a weaker spec (see tools/adcheck.py).
Exit 1 when any claim is unbacked. (Trial finding: a local model wrote "CONFIRMED by retail differential" when no differential had run.)
"""
import hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
CLAIM = re.compile(r'\b(CONFIRMED|PROVEN|VERIFIED)\b')
ADDR = re.compile(r'(?:8c|nd_|fn_8c|fn_)([0-9a-f]{6})', re.I)


def sha(p):
    try:
        return hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16]
    except OSError:
        return None


def ledger(func):
    p = os.path.join(ROOT, 'work', 'proofs', '%s.json' % func.lower().replace('0x', '').lower())
    try:
        return json.load(open(p))
    except (OSError, ValueError):
        return None


def backed(func):
    """-> (ok, why)"""
    led = None
    for cand in (func, '8c' + func[-6:]):
        led = ledger(cand) or led
    if not led or not led.get('runs'):
        return False, 'no proof ledger (autodiff was never run to completion for this function)'
    last = led['runs'][-1]
    if last.get('override'):
        return False, 'the newest run used AD_ALLOW_WEAKER (a human-only override): not accepted as a proof'
    if not last.get('proven'):
        return False, 'newest run is NOT PROVEN (%s)' % last['result'][:120]
    for rel, h in last['port'].items():
        if sha(os.path.join(ROOT, rel)) != h:
            return False, 'port file %s changed after the proof (hash mismatch): re-run autodiff' % rel
    return True, 'PROVEN %s, spec sha %s, %d cases' % (last['time'], last['spec_sha'], last['fp']['cases'])


def scan(paths):
    bad = 0
    files = []
    for p in paths:
        if os.path.isdir(p):
            for dp, dn, fn in os.walk(p):
                files += [os.path.join(dp, x) for x in fn if x.endswith(('.c', '.h', '.md', '.txt'))]
        elif os.path.exists(p):
            files.append(p)
    for fp in sorted(files):
        try:
            lines = open(fp, errors='replace').read().split('\n')
        except OSError:
            continue
        name_addr = ADDR.search(os.path.basename(fp))
        for n, ln in enumerate(lines, 1):
            if not CLAIM.search(ln):
                continue
            if re.search(r'\b(HYPOTHESIS|NOT|never|unless|if|until|do not|don\'t|rule|means|only when|must)\b', ln, re.I):
                continue                        # rules and negations are not claims
            m = ADDR.search(ln) or name_addr
            if not m:
                continue
            func = m.group(1).lower()
            ok, why = backed(func)
            if not ok:
                bad += 1
                print('UNBACKED  %s:%d  claims %s for %s -> %s' % (os.path.relpath(fp, ROOT), n, CLAIM.search(ln).group(1), func, why))
    return bad


def main():
    a = sys.argv[1:]
    if a[:1] == ['--func']:
        led = ledger(a[1])
        if not led:
            sys.exit('no ledger for %s' % a[1])
        for r in led['runs'][-8:]:
            print('%s  %-3s  cases=%s mutants=%s  %s' % (r['time'], 'OK' if r['proven'] else '--', r['fp']['cases'], r['fp']['mutants'], r['result'][:110]))
        ok, why = backed(a[1])
        print('claims backed:', ok, '-', why)
        sys.exit(0 if ok else 1)
    paths = a or [os.path.join(ROOT, 'port'), os.path.join(ROOT, 'work', 'reports')]
    bad = scan(paths)
    print('proofcheck: %d unbacked claim(s)' % bad)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
