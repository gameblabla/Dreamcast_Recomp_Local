#!/usr/bin/env python3
"""sdk_headers_strip.py SDK_DIR OUT_DIR: write a STRIPPED copy of the SDK's C headers (struct/enum/typedef/prototype/#define skeleton only).

Removed: all comments (incl. Shift-JIS text and copyright/banner blocks), string literals, blank lines, #include of non-SDK files kept as-is,
#pragma/#ifdef guards kept. Kept: declarations that tell you struct layouts, enum values, constants and function signatures, which is what a
decompilation needs. No library code is involved. Stdlib only.
"""
import os, re, sys

def strip(t):
    t = t.replace('\r', '').replace('\x0c', '')
    t = re.sub(r'/\*.*?\*/', '', t, flags=re.S)
    t = re.sub(r'//[^\n]*', '', t)
    t = re.sub(r'"(?:\\.|[^"\\\n])*"', '""', t)
    out = []
    for l in t.split('\n'):
        l = re.sub(r'[ \t]+$', '', l)
        if l.strip():
            out.append(l)
    return '\n'.join(out) + '\n'

if len(sys.argv) != 3:
    sys.exit(__doc__)
src, dst = sys.argv[1], sys.argv[2]
n = size = 0
for dp, dn, fn in os.walk(src):
    if '/shc/' in dp.lower() or '/doc' in dp.lower():
        continue
    for f in fn:
        if f.lower().endswith('.h') and 'include' in dp.lower():
            rel = os.path.relpath(os.path.join(dp, f), src)
            o = os.path.join(dst, rel)
            os.makedirs(os.path.dirname(o), exist_ok=True)
            s = strip(open(os.path.join(dp, f), encoding='latin-1').read())
            open(o, 'w', encoding='latin-1').write(s)
            n += 1; size += len(s)
print('%d headers, %d bytes -> %s' % (n, size, dst))
