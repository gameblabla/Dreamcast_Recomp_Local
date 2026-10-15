#!/usr/bin/env python3
"""attempts.py: every autodiff run snapshots the port; the best one (fewest mismatches/faults, then fewest uncovered instructions) is kept. Stdlib only.

  python3 -I tools/dc/attempts.py list 0x8c043680          # score history (newest last), best marked *
  python3 -I tools/dc/attempts.py best 0x8c043680          # path of the best snapshot
  python3 -I tools/dc/attempts.py restore 0x8c043680 [N|best]   # copy a snapshot back over port/fn_<addr>.c (the current file is snapshotted first)
Why: matching-decomp projects keep EVERY attempt in its own file so a good match cannot be degraded by later edits; a model that is "improving"
its port can silently regress from 3 mismatches to 30. Restore the best, form ONE new hypothesis, change ONE thing.
"""
import glob, json, os, re, shutil, sys, time


def root():
    d = os.getcwd()
    for _ in range(5):
        if os.path.isdir(os.path.join(d, 'port')) or os.path.isdir(os.path.join(d, 'work')):
            return d
        d = os.path.dirname(d)
    return os.getcwd()


def adir(addr, proj=None):
    return os.path.join(proj or root(), 'work', 'attempts', '%08x' % (int(str(addr), 16) & 0xffffffff))


def load(addr, proj=None):
    try:
        return json.load(open(os.path.join(adir(addr, proj), 'index.json')))
    except (OSError, ValueError):
        return {'runs': [], 'best': None}


def snapshot(proj, func, src_paths, bad, fault, uncovered, survivors, result):
    """called by autodiff after every run"""
    d = adir(func, proj)
    os.makedirs(d, exist_ok=True)
    idx = load(func, proj)
    main = next((p for p in src_paths if re.search(r'fn_|nd_', os.path.basename(p)) and os.path.exists(p)), None) or next((p for p in src_paths if os.path.exists(p)), None)
    if not main:
        return None
    n = len(idx['runs']) + 1
    score = [int(bad) + int(fault), int(uncovered), int(survivors)]
    fn = '%03d_m%d_u%d_s%d%s' % (n, score[0], score[1], score[2], os.path.splitext(main)[1])
    shutil.copy(main, os.path.join(d, fn))
    idx['runs'].append(dict(n=n, file=fn, score=score, result=result[:200], time=time.strftime('%H:%M:%S')))
    if idx['best'] is None or score < idx['runs'][idx['best'] - 1]['score']:
        idx['best'] = n
    json.dump(idx, open(os.path.join(d, 'index.json'), 'w'), indent=1)
    return idx


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ('list', 'best', 'restore'):
        sys.exit(__doc__)
    cmd, addr = sys.argv[1], sys.argv[2]
    idx = load(addr)
    if not idx['runs']:
        sys.exit('no attempts recorded for %s yet (autodiff records one per run)' % addr)
    if cmd == 'list':
        for r in idx['runs']:
            print('%s #%d  mismatches+faults=%d uncovered=%d survivors=%d  %s  %s' % ('*' if r['n'] == idx['best'] else ' ', r['n'], r['score'][0], r['score'][1], r['score'][2], r['time'], r['file']))
        return
    d = adir(addr)
    if cmd == 'best':
        print(os.path.join(d, idx['runs'][idx['best'] - 1]['file']))
        return
    which = sys.argv[3] if len(sys.argv) > 3 else 'best'
    n = idx['best'] if which == 'best' else int(which)
    src = os.path.join(d, idx['runs'][n - 1]['file'])
    h = '%08x' % (int(addr, 16) & 0xffffffff)
    cand = [p for p in glob.glob(os.path.join(root(), 'port', 'fn_%s.c' % h)) + glob.glob(os.path.join(root(), 'core', 'nd_%s.c' % h[2:]))]
    if not cand:
        sys.exit('cannot find port/fn_%s.c to restore into' % h)
    cur = cand[0]
    shutil.copy(cur, os.path.join(d, 'before_restore_%s%s' % (time.strftime('%H%M%S'), os.path.splitext(cur)[1])))
    shutil.copy(src, cur)
    print('restored attempt #%d (%s) over %s; the previous file is kept as before_restore_* in %s' % (n, idx['runs'][n - 1]['file'], os.path.relpath(cur), os.path.relpath(d)))


if __name__ == '__main__':
    main()
