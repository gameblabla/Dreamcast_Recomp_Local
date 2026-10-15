#!/usr/bin/env python3
"""shc.py: run the ORIGINAL Hitachi SH C compiler (from a Katana SDK you own) under wine/wibo, or fall back to sh-elf-gcc. Game-independent. Stdlib only.

  python3 -I tools/shc.py find                                  # where is shc.exe? (DR_SHC_DIR, then SDK_DIRS)
  python3 -I tools/shc.py compile SRC.c [--func F] [-o OUT.bin] [--addr 0x8c010000] [--flags 'EXTRA SHC FLAGS'] [--opt 0|1|2] [--gcc]
        -> OUT.bin = linked bytes of the P section, starting at --func if given (literal pool included), plus a symbol list on stdout
  python3 -I tools/shc.py asm SRC.c [--flags ...]               # SHC's own assembly listing (SRC.src printed), handy to compare with retail asm
  python3 -I tools/shc.py cc SRC.c OBJ.o                        # drop-in for bytematch's --cc: writes an ELF-like .o only for the gcc fallback

Compiler selection (printed on every run, and in the verdict of bytematch):
  SHC   the SDK's shc.exe (SHC 5.1 Release04 in Katana 1.42J). Needed for real byte-matching. Found via DR_SHC_DIR or SDK_DIRS (project.env).
  GCC   sh-elf-gcc -O2 -m4-single-only -ml: NO SDK available. Structure-only candidate: it cannot reproduce SHC's register allocation, so a
        bytematch against it is at best a hint (the verdict says "gcc fallback"). Behaviour must be proven with autodiff instead.
Default SHC flags (reproduced Katana game code): -cpu=sh4 -endian=little -fpu=single -division=cpu -round=nearest -pic=0 -macsave=0
-optimize=1 -size -string=const. Override with --flags (appended, so later options win) or env DR_SHC_FLAGS (replaces the defaults).
DR_NO_SHC=1 pretends no SDK compiler exists.
Environment quirks of shc.exe (found the hard way): SHC_LIB/SHC_TMP/SHC_INC must ALL be set, as Windows paths (Z:\\...), no trailing backslash;
wine needs a prefix (DR_WINEPREFIX, default $TMPDIR/dcre_wineprefix_UID: ~300 MB, keep it off a nearly full disk) and DISPLAY must be empty. The SDK is only READ, never copied or modified.
"""
import argparse, glob, os, re, shutil, struct, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
DEFAULT_FLAGS = '-cpu=sh4 -endian=little -fpu=single -division=cpu -round=nearest -pic=0 -macsave=0 -optimize=1 -size -string=const'
GCC = 'sh-elf-gcc -O2 -m4-single-only -ml -fno-pic -ffreestanding'


def sdk_dirs():
    out = [d if os.path.isabs(d) else os.path.normpath(os.path.join(ROOT, d)) for d in os.environ.get('DR_SDK_DIRS', '').split(':') if d]
    p = os.path.join(ROOT, 'project.env')
    if not out and os.path.exists(p):
        m = re.search(r'^SDK_DIRS="?([^"\n]*)"?', open(p).read(), re.M)
        if m:
            out = [d if os.path.isabs(d) else os.path.normpath(os.path.join(ROOT, d)) for d in m.group(1).split(':') if d]
    return out


def find_shc():
    """-> (bin_dir, include_dirs) of the Hitachi tools, or None. Looks at DR_SHC_DIR first, then walks SDK_DIRS for shc.exe."""
    if os.environ.get('DR_NO_SHC') == '1':      # force the no-SDK path (tests, or to compare against the fallback)
        return None
    cands = []
    if os.environ.get('DR_SHC_DIR'):
        cands.append(os.environ['DR_SHC_DIR'])
    for d in sdk_dirs():
        for dp, dn, fn in os.walk(d):
            if any(f.lower() == 'shc.exe' for f in fn) and any(f.lower() == 'shcgen.exe' for f in fn):
                cands.append(dp)
            if len(cands) > 4 or dp.count(os.sep) - d.count(os.sep) > 6:
                dn[:] = []
    for c in cands:
        if os.path.isdir(c) and any(f.lower() == 'shc.exe' for f in os.listdir(c)):
            top = os.path.dirname(c)
            inc = [p for p in glob.glob(os.path.join(top, '*')) if os.path.basename(p).lower() == 'include']
            inc += [p for p in glob.glob(os.path.join(os.path.dirname(top), '*', '[Ii]nclude')) if os.path.isdir(p)]
            return c, inc
    return None


def runner():
    return shutil.which('wibo') or shutil.which('wine')


def win(p):
    return 'Z:' + os.path.abspath(p).replace('/', '\\')


def wine_env(bindir, tmp):
    e = dict(os.environ, WINEDEBUG='-all', DISPLAY='', WAYLAND_DISPLAY='', SHC_LIB=win(bindir), SHC_TMP=win(tmp), SHC_INC=win(bindir),
             WINEPREFIX=os.environ.get('DR_WINEPREFIX') or os.path.join(os.environ.get('TMPDIR', '/tmp'), 'dcre_wineprefix_%d' % os.getuid()))
    os.makedirs(e['WINEPREFIX'], exist_ok=True)      # wine refuses to create a prefix in a directory we do not own (e.g. directly in /tmp): create it first
    return e


def exe(bindir, name):
    for f in os.listdir(bindir):
        if f.lower() == name.lower():
            return os.path.join(bindir, f)
    sys.exit('%s not found in %s' % (name, bindir))


def run_tool(bindir, tmp, name, args, cwd):
    r = subprocess.run([runner(), exe(bindir, name)] + args, cwd=cwd, env=wine_env(bindir, tmp), capture_output=True, text=True, errors='replace')
    out = '\n'.join(l for l in (r.stdout + r.stderr).replace('\r', '').splitlines() if not re.search(r'MESA|pci id|fixme:', l))
    return r.returncode, out


def shc_flags(a):
    base = os.environ.get('DR_SHC_FLAGS') or DEFAULT_FLAGS
    if getattr(a, 'opt', None) is not None:
        base = re.sub(r'-optimize=\d', '-optimize=%d' % a.opt, base)
    return base.split() + (a.flags or '').split()


def inc_args(incs, tmp):
    """shc.exe splits -include= on spaces (SDK folders have them): expose each include dir through a space-free symlink in tmp."""
    links = []
    for i, p in enumerate(incs):
        l = os.path.join(tmp, 'inc%d' % i)
        os.symlink(os.path.abspath(p), l)
        links.append(win(l))
    return ['-include=' + ','.join(links)] if links else []


def read_syms(src, extra):
    """Absolute symbols the C may reference as externs. Sources: `//@sym NAME 0xADDR` lines in the C file, and --syms FILE (two tokens per line,
    NAME ADDR or ADDR NAME, ADDR hex; '#' comments). -> {name: addr}"""
    out = {}
    def add(n, v):
        out[n] = int(v, 16)
    for ln in open(src, errors='replace'):
        m = re.match(r'\s*//@sym\s+(\w+)\s+(?:0x)?([0-9a-fA-F]+)\s*$', ln)
        if m:
            add(m.group(1), m.group(2))
    if extra:
        for ln in open(extra, errors='replace'):
            t = ln.split('#')[0].split()
            if len(t) < 2:
                continue
            for n, v in ((t[0], t[1]), (t[1], t[0])):
                if re.fullmatch(r'(0x)?[0-9a-fA-F]{6,8}', v) and re.fullmatch(r'\w+', n):
                    add(n, v.replace('0x', '')); break
    return out


def shc_compile(src, func, addr, a):
    """-> (bytes, symbols{name:addr}, log). Raises SystemExit with the compiler diagnostics on failure."""
    found = find_shc()
    if not found or not runner():
        sys.exit('no SHC available (%s). Give SDK_DIRS a Katana SDK, set DR_SHC_DIR, or use --gcc (structure-only fallback).'
                 % ('wine/wibo missing' if found else 'no shc.exe in DR_SHC_DIR / SDK_DIRS'))
    bindir, incs = found
    with tempfile.TemporaryDirectory(prefix='shc_') as tmp:
        shutil.copy(src, os.path.join(tmp, 'in.c'))
        rc, log = run_tool(bindir, tmp, 'shc.exe', shc_flags(a) + inc_args(incs, tmp) + ['-code=machinecode', 'in.c'], tmp)
        if rc or not any(f.lower() == 'in.obj' for f in os.listdir(tmp)):
            sys.exit('SHC failed:\n' + log[-2000:])
        inputs = 'in'
        syms_abs = read_syms(src, getattr(a, 'syms', None))
        if syms_abs:     # absolute symbols via a generated asmsh file (.EQU), so `extern` data/functions at fixed retail addresses link
            asm = '\n'.join('          .EXPORT _%s\n_%s .EQU H\'%08X' % (n, n, v) for n, v in sorted(syms_abs.items())) + '\n          .END\n'
            open(os.path.join(tmp, 'syms.src'), 'w').write(asm)
            rc, alog = run_tool(bindir, tmp, 'asmsh.exe', ['syms.src', '-cpu=sh4', '-endian=little'], tmp)
            if not any(f.lower() == 'syms.obj' for f in os.listdir(tmp)):
                sys.exit('asmsh failed on the generated symbol file:\n' + alog[-1500:])
            inputs = 'in,syms'
        addr &= ~3        # lnk rejects a start address that is not 4-aligned; a 2-mod-4 retail function only changes pool alignment (NORMALIZED covers it)
        sub = 'input %s\nstart P(%X)\nelf\nprint in.map\noutput in.elf\nexit\n' % (inputs, addr)
        open(os.path.join(tmp, 'l.sub'), 'w').write(sub)
        rc, llog = run_tool(bindir, tmp, 'LNK.EXE', ['-subcommand=l.sub'], tmp)
        if 'COMPLETED' not in llog or not os.path.exists(os.path.join(tmp, 'in.elf')):
            sys.exit('SHC link failed (undefined externals? stub them in the source):\n' + llog[-2000:])
        syms = {}
        for m in re.finditer(r'^(\S+)\s+H\'([0-9A-F]{8})\s+ENT', open(os.path.join(tmp, 'in.map'), errors='replace').read(), re.M):
            syms[m.group(1).lstrip('_')] = int(m.group(2), 16)
        raw = elf_load(open(os.path.join(tmp, 'in.elf'), 'rb').read())
        return raw, syms, log


def elf_load(b):
    """Concatenate the file bytes of every PT_LOAD segment (the linker writes one segment per section; P comes first)."""
    ph_off, = struct.unpack_from('<I', b, 28); ph_sz, ph_n = struct.unpack_from('<HH', b, 42)
    out = b''
    for i in range(ph_n):
        t, off, va, pa, fsz, msz, fl, al = struct.unpack_from('<8I', b, ph_off + i * ph_sz)
        if t == 1:
            out += b[off:off + fsz]
    return out


def gcc_compile(src, func):
    cc = GCC.split()
    with tempfile.TemporaryDirectory(prefix='shcgcc_') as tmp:
        o, bn = os.path.join(tmp, 'c.o'), os.path.join(tmp, 'c.bin')
        r = subprocess.run(cc + ['-c', src, '-o', o], capture_output=True, text=True)
        if r.returncode:
            sys.exit('gcc failed:\n' + r.stderr[-2000:])
        subprocess.run(['sh-elf-objcopy', '-O', 'binary', '-j', '.text', o, bn], check=True)
        nm = subprocess.run(['sh-elf-nm', o], capture_output=True, text=True).stdout
        syms = {m.group(2).lstrip('_'): int(m.group(1), 16) for m in re.finditer(r'^([0-9a-f]+)\s+[Tt]\s+(\S+)$', nm, re.M)}
        return open(bn, 'rb').read(), syms


def compile_to_bytes(src, func=None, addr=0x8C010000, a=None, force_gcc=False):
    """Public helper for bytematch/permute. -> (bytes_from_func, kind, symbols) where kind is 'SHC' or 'GCC'."""
    a = a or argparse.Namespace(flags='', opt=None)
    if not force_gcc and find_shc() and runner():
        raw, syms, _ = shc_compile(src, func, addr, a)
        base = addr & ~3
        kind = 'SHC'
    else:
        if not force_gcc:
            sys.stderr.write('shc.py: no SDK compiler found; using sh-elf-gcc (structure-only, NOT the original compiler)\n')
        raw, syms = gcc_compile(src, func)
        base, kind = 0, 'GCC'
    off = 0
    if func:
        func = func.lstrip('_')
        if func not in syms:
            sys.exit('function %r not found in the compiled object (have: %s)' % (func, ', '.join(sorted(syms)) or 'none'))
        off = syms[func] - base
    return raw[off:], kind, {k: v - base for k, v in syms.items()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['find', 'compile', 'asm', 'cc'])
    ap.add_argument('files', nargs='*')
    ap.add_argument('--func'); ap.add_argument('-o'); ap.add_argument('--addr', default='0x8c010000')
    ap.add_argument('--flags', default=''); ap.add_argument('--syms'); ap.add_argument('--opt', type=int); ap.add_argument('--gcc', action='store_true')
    a = ap.parse_args()
    if a.cmd == 'find':
        f = find_shc()
        print('SHC: %s' % (('%s  (includes: %s)' % (f[0], ', '.join(f[1]) or '-')) if f else 'NOT FOUND'))
        print('runner: %s' % (runner() or 'none (install wine or wibo)'))
        print('gcc fallback: %s' % (shutil.which('sh-elf-gcc') or 'none'))
        return 0 if f and runner() else 3
    if not a.files:
        sys.exit(__doc__)
    src = os.path.abspath(a.files[0])
    if a.cmd == 'asm':
        found = find_shc()
        if not found or not runner():
            sys.exit('asm listing needs the SDK compiler (SDK_DIRS / DR_SHC_DIR) and wine')
        with tempfile.TemporaryDirectory(prefix='shc_') as tmp:
            shutil.copy(src, os.path.join(tmp, 'in.c'))
            rc, log = run_tool(found[0], tmp, 'shc.exe', shc_flags(a) + inc_args(found[1], tmp) + ['-code=asmcode', 'in.c'], tmp)
            p = os.path.join(tmp, 'in.src')
            if not os.path.exists(p):
                sys.exit('SHC failed:\n' + log[-2000:])
            print(open(p, errors='replace').read())
        return 0
    if a.cmd == 'cc':          # --cc hook for bytematch when only a gcc object is wanted
        if len(a.files) < 2:
            sys.exit('usage: shc.py cc SRC OBJ')
        r = subprocess.run(GCC.split() + ['-c', src, '-o', a.files[1]])
        return r.returncode
    raw, kind, syms = compile_to_bytes(src, a.func, int(a.addr, 16), a, a.gcc)
    out = a.o or os.path.splitext(src)[0] + '.shc.bin'
    open(out, 'wb').write(raw)
    print('compiler=%s bytes=%d -> %s' % (kind, len(raw), out))
    for k, v in sorted(syms.items(), key=lambda x: x[1]):
        print('  %-28s +0x%x' % (k, v))
    return 0


if __name__ == '__main__':
    sys.exit(main())
