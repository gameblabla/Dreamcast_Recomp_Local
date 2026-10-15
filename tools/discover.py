#!/usr/bin/env python3
"""discover.py: how complete is the static picture of the binary? Game-independent, stdlib only, reads work/research/ (./dcre export).

  python3 -I tools/discover.py indirect    # every jsr/jmp/braf/bsrf through a register, classified; writes work/research/indirect.tsv
  python3 -I tools/discover.py gaps        # bytes of the image that no function, literal-pool slot or padding explains (code Ghidra never found)
  python3 -I tools/discover.py all

Why (lessons from the public SH-4 static recompilers dream-recomp / dcrecomp): static discovery typically reaches only 79-90% of a binary; what it misses is
reached through computed jumps (switch tables, function-pointer tables, callbacks). Unexplained runs of >= 16 bytes in the code range, and indirect
call sites with no resolved target, are exactly the places to look for missed functions. This tool lists them so they can be seeded (names.tsv /
DrFindCode) instead of being discovered by a crash.
  indirect kinds:  literal  = target loaded from the literal pool (resolved, ordinary call)
                   fnptr    = target read from memory (callback/vtable/function-pointer table): the callees are data-defined
                   switch   = braf/jmp through a computed offset (jump table): case bodies are only reachable through the table
                   unknown  = register set by something else (look at the asm)
"""
import os, re, sys

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
RES = os.environ.get('DR_RESEARCH', os.path.join(ROOT, 'work', 'research'))
BIN = os.environ.get('DR_BIN', os.path.join(ROOT, 'game', '1ST_READ.BIN'))
BASE = int(os.environ.get('DR_BASE', '0x8c010000'), 16)


def functions():
    out = []
    for i, ln in enumerate(open(os.path.join(RES, 'functions.tsv'))):
        t = ln.rstrip('\n').split('\t')
        if i and len(t) >= 3:
            out.append((int(t[0], 16), t[1], int(t[2])))
    return sorted(out)


def asm_lines():
    d = os.path.join(RES, 'asm')
    for f in sorted(os.listdir(d)):
        if f.endswith('.asm'):
            for ln in open(os.path.join(d, f), errors='replace'):
                m = re.match(r'([0-9a-f]{8}):\t([^\t;]*)(?:\t;\s*(.*))?$', ln.rstrip('\n'))
                if m:
                    yield int(m.group(1), 16), m.group(2).strip(), (m.group(3) or '').strip()


def cmd_indirect():
    fn = functions()
    starts = [a for a, _, _ in fn]
    import bisect
    def owner(a):
        i = bisect.bisect_right(starts, a) - 1
        return fn[i][1] if i >= 0 else '?'
    hist = []
    rows = []
    for a, ins, cmt in asm_lines():
        m = re.match(r'(jsr|jmp)\s+@(r\d+)$', ins) or re.match(r'(braf|bsrf)\s+(r\d+)$', ins)
        if m:
            op, reg = m.groups()
            if op in ('braf', 'bsrf'):
                kind = 'switch'
            elif re.search(r'<\w+>', cmt) and not cmt.startswith(('ff', 'a0', '1')):
                kind = 'literal'
            else:
                kind = 'unknown'
                for pa, pi, pc in reversed(hist[-8:]):
                    mm = re.match(r'mov\.l\s+(\S+),%s$' % reg, pi)
                    if mm:
                        src = mm.group(1)
                        if src.startswith('0x'):
                            kind = 'literal'
                        elif src.startswith('@'):
                            kind = 'fnptr'
                        break
                    if re.match(r'(mov|add|extu\.\w|shll\d*)\s.*,%s$' % reg, pi) or re.match(r'(shll\d*|shlr\d*)\s+%s$' % reg, pi):
                        continue
            if op == 'jmp' and kind == 'unknown':
                kind = 'switch'
            rows.append((a, kind, owner(a), op, reg, cmt[:60]))
        hist.append((a, ins, cmt))
        if len(hist) > 64:
            hist.pop(0)
    p = os.path.join(RES, 'indirect.tsv')
    with open(p, 'w') as f:
        f.write('address\tkind\tfunction\top\treg\tcomment\n')
        for r in rows:
            f.write('%08x\t%s\t%s\t%s\t%s\t%s\n' % r)
    cnt = {}
    for r in rows:
        cnt[r[1]] = cnt.get(r[1], 0) + 1
    print('indirect jumps/calls: %d (%s)  -> %s' % (len(rows), ', '.join('%s %d' % kv for kv in sorted(cnt.items())), os.path.relpath(p, ROOT)))
    print('  fnptr/switch/unknown are not statically resolved: their targets come from data (tables, structs). Seed any function found that way in names.tsv.')


def cmd_gaps():
    img = open(BIN, 'rb').read()
    fn = functions()
    end_img = BASE + len(img)
    fn = [f for f in fn if BASE <= f[0] < end_img]            # drop P2 mirrors / out-of-image entries (e.g. 0xAC...)
    code_end = max(a + n for a, _, n in fn) + 0x100          # data (.data/.rodata, assets) after the last function is out of scope
    img_n = min(len(img), code_end - BASE)
    covered = bytearray(len(img))          # 1 = explained
    for a, _, n in fn:
        for i in range(max(0, a - BASE), min(len(img), a - BASE + n)):
            covered[i] = 1
    pool = 0
    for a, ins, cmt in asm_lines():       # pc-relative literal slots (mov.w/mov.l 0xADDR,rN and mova): both the slot and a pool word it belongs to
        m = re.match(r'mov\.([wl])\s+(0x[0-9a-f]{8}),r\d+$', ins)
        if m:
            t, n = int(m.group(2), 16) - BASE, 2 if m.group(1) == 'w' else 4
            for i in range(max(0, t), min(len(img), t + n)):
                if not covered[i]:
                    covered[i] = 2; pool += 1
    zero = 0
    for i, b in enumerate(img):
        if not covered[i] and b == 0:
            covered[i] = 3; zero += 1
    runs, i = [], 0
    while i < img_n:
        if covered[i]:
            i += 1; continue
        j = i
        while j < img_n and not covered[j]:
            j += 1
        runs.append((BASE + i, j - i)); i = j
    big = [r for r in runs if r[1] >= 16]
    tot = sum(r[1] for r in runs)
    print('code range %08x-%08x (%d bytes): functions %d, literal-pool slots %d, zero padding %d, UNEXPLAINED %d bytes in %d runs (%d runs >= 16 bytes)'
          % (BASE, code_end, img_n, covered[:img_n].count(1), covered[:img_n].count(2), covered[:img_n].count(3), tot, len(runs), len(big)))
    p = os.path.join(RES, 'gaps.tsv')
    with open(p, 'w') as f:
        f.write('address\tbytes\tlooks_like\n')
        for a, n in big:
            raw = img[a - BASE:a - BASE + n]
            w = [int.from_bytes(raw[k:k + 4], 'little') for k in range(0, n - 3, 4)]
            ptrs = sum(1 for x in w if BASE <= x < end_img or 0x8c000000 <= x < 0x8d000000)
            ascii_ = sum(1 for b in raw if 32 <= b < 127) / n
            hw = [int.from_bytes(raw[k:k + 2], 'little') for k in range(0, min(n, 8) - 1, 2)]
            prologue = a % 2 == 0 and any(x == 0x4F22 or (0x2F86 <= x <= 0x2FE6 and x & 0xF == 6) or (x & 0xFF00) == 0x7F00 for x in hw[:3])   # sts.l pr,@-r15 / mov.l rN,@-r15 / add #-n,r15
            kind = 'text' if ascii_ > 0.8 else ('pointers/data' if w and ptrs * 2 >= len(w) else 'code?' if prologue else 'data')
            f.write('%08x\t%d\t%s\n' % (a, n, kind))
    print('  runs >= 16 bytes -> %s   (looks_like=code? are the ones to check: disassemble there and add the entry to names.tsv)' % os.path.relpath(p, ROOT))
    for a, n in sorted(big, key=lambda r: -r[1])[:8]:
        print('   %08x  %6d bytes' % (a, n))


def main():
    a = sys.argv[1:] or ['all']
    if not os.path.exists(os.path.join(RES, 'functions.tsv')):
        sys.exit('no %s: run ./dcre export first' % RES)
    if a[0] in ('indirect', 'all'):
        cmd_indirect()
    if a[0] in ('gaps', 'all'):
        cmd_gaps()
    if a[0] not in ('indirect', 'gaps', 'all'):
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
