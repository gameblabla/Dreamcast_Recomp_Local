#!/usr/bin/env python3
"""dcre: one entry point for the whole Dreamcast recomp workflow. Run `./dcre help`.

  ./dcre doctor            check every tool this project needs and say what is missing
  ./dcre extract           disc image -> game/ (1ST_READ.BIN, IP.BIN, all files)         [reads DISC from project.env]
  ./dcre sdk               identify the SDK/compiler the game was built with; tells you what SDK copy to ask for
  ./dcre import            create the Ghidra project (SuperH4 LE, base address) from game/1ST_READ.BIN
  ./dcre export            find missed code, name SDK functions, dump functions/call graph/asm/decompiled C to work/research/
 ./dcre libtriage [cmd]    SDK-LESS FALLBACK: separate library code from game code by structure (only runs when no matching SDK is available; --force overrides)
  ./dcre status            triage summary: what is done / left
  ./dcre next [N] [MAXB]   cheapest READY functions to decompile next
  ./dcre slice ADDR        annotated asm + classified callees of one function
  ./dcre annotate ADDR     annotated asm only (literal values, call args, loops)
  ./dcre autodiff SPEC     retail-vs-C differential in the Ghidra SH-4 emulator (adds --mutate for the full proof)
  ./dcre bytematch ...     compare compiled C with the retail bytes (see tools/bytematch.py)
  ./dcre permute ...       tiny source permuter for byte-matching (tools/permute.py)
  ./dcre emu GAME [...]    run flycast headless (tools/flycast_run.sh)
  ./dcre agent ADDR        run a local opencode headless agent on one function (uses the decomp-function skill)
"""
import os, shutil, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
T = os.path.join(ROOT, 'tools')
PY = [sys.executable, '-I']


def load_env():
    env = dict(os.environ)
    p = os.path.join(ROOT, 'project.env')
    if os.path.exists(p):
        for line in open(p):
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            v = v.split(' #')[0].strip().strip('"').strip("'")
            env.setdefault(k.strip(), os.path.expandvars(v))
    env.setdefault('DR_PROJECT_NAME', 'drproject')
    env.setdefault('DR_BASE', '0x8c010000')
    env['DR_BIN'] = env.get('DR_BIN', os.path.join(ROOT, 'game', '1ST_READ.BIN'))
    env['DR_SDK_DIRS'] = env.get('SDK_DIRS', env.get('DR_SDK_DIRS', ''))
    env['AD_GHIDRA_PROJECT'] = env.get('AD_GHIDRA_PROJECT', os.path.join(ROOT, 'work', 'ghidra_project'))
    env['AD_SCRIPTS'] = env.get('AD_SCRIPTS', os.path.join(ROOT, 'ghidra', 'scripts'))
    return env


def rel(p):
    return p if os.path.isabs(p) else os.path.join(ROOT, p)


def headless(env):
    for c in (env.get('GHIDRA_HEADLESS'), shutil.which('analyzeHeadless'), '/usr/libexec/ghidra/support/analyzeHeadless',
              os.path.join(env.get('GHIDRA_INSTALL_DIR', '/nonexistent'), 'support', 'analyzeHeadless'), '/opt/ghidra/support/analyzeHeadless'):
        if c and os.path.exists(c):
            return c
    return None


def run(cmd, env, **kw):
    return subprocess.call(cmd, env=env, cwd=ROOT, **kw)


def cmd_doctor(env):
    ok = True
    def chk(name, found, hint, required=True):
        nonlocal ok
        print('  [%s] %-22s %s' % ('ok' if found else ('MISSING' if required else 'optional'), name, found if isinstance(found, str) else ('' if found else hint)))
        if required and not found:
            ok = False
    print('tools')
    chk('python3', sys.version.split()[0], '')
    chk('cc (gcc/clang)', shutil.which('cc') or shutil.which('gcc'), 'install a C compiler (build-essential / base-devel)')
    chk('java (17+)', shutil.which('java'), 'install a JDK 17 or newer (Ghidra needs it)')
    chk('Ghidra headless', headless(env), 'install Ghidra 11/12 and set GHIDRA_HEADLESS=/path/to/support/analyzeHeadless')
    chk('xvfb-run', shutil.which('xvfb-run'), 'install xvfb (only for running flycast headless)', False)
    chk('sh-elf-gcc / objdump', shutil.which('sh-elf-gcc') and shutil.which('sh-elf-objdump'), 'build or install an sh-elf binutils+gcc (KallistiOS toolchain works): needed for bytematch/permute', False)
    chk('opencode', shutil.which('opencode'), 'install opencode (https://opencode.ai) to run local-model agents', False)
    chk('wine/wibo', shutil.which('wine') or shutil.which('wibo'), 'needed only to run the ORIGINAL Hitachi SHC compiler from the SDK', False)
    print('project files')
    chk('project.env', os.path.exists(rel('project.env')) and 'present', 'copy project.env.example to project.env and edit')
    disc = env.get('DISC', '')
    chk('DISC', disc if disc and os.path.exists(rel(disc)) else '', 'set DISC in project.env (.gdi/.cue/.iso or folder)')
    chk('game/1ST_READ.BIN', os.path.exists(env['DR_BIN']) and env['DR_BIN'], 'run ./dcre extract', False)
    chk('Ghidra project', os.path.isdir(env['AD_GHIDRA_PROJECT']) and env['AD_GHIDRA_PROJECT'], 'run ./dcre import', False)
    chk('work/research', os.path.exists(rel('work/research/functions.tsv')) and 'present', 'run ./dcre export', False)
    print('third party')
    chk('dc-re-ghidra', os.path.exists(rel('third_party/dc-re-ghidra/sdk-symbols.txt')) and 'present', 'git submodule update --init third_party/dc-re-ghidra')
    chk('flycast (submodule)', os.path.exists(rel('third_party/flycast/CMakeLists.txt')) and 'present', 'git submodule update --init third_party/flycast (only needed to rebuild)', False)
    chk('flycast-bin', os.path.exists(rel('third_party/flycast-bin/flycast')) and 'present', 'copy precompiled headless flycast to third_party/flycast-bin/ or build it (docs/FLYCAST.md)', False)
    print('SDK folders (SDK_DIRS)')
    dirs = [d for d in env['DR_SDK_DIRS'].split(':') if d]
    if not dirs:
        print('  [none] set SDK_DIRS in project.env. You can proceed without an SDK, but it is much slower (see docs/SDKS.md); `./dcre sdk` says which one to get.')
    for d in dirs:
        print('  [%s] %s' % ('ok' if os.path.exists(rel(d)) else 'MISSING', d))
    print('\nREADY' if ok else '\nNOT READY: fix the MISSING required items above')
    return 0 if ok else 1


def ghidra_args(env, mode):
    hl = headless(env)
    if not hl:
        sys.exit('Ghidra not found: set GHIDRA_HEADLESS (see ./dcre doctor)')
    proj = env['AD_GHIDRA_PROJECT']; name = env['DR_PROJECT_NAME']
    os.makedirs(proj, exist_ok=True)
    return hl, proj, name, os.path.join(ROOT, 'ghidra', 'scripts'), os.path.join(ROOT, 'work', 'research')


def cmd_import(env):
    hl, proj, name, scripts, out = ghidra_args(env, 'import')
    if not os.path.exists(env['DR_BIN']):
        sys.exit('missing %s: run ./dcre extract first' % env['DR_BIN'])
    for f in os.listdir(proj):
        if f.startswith(name + '.'):
            p = os.path.join(proj, f)
            shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    os.makedirs(os.path.join(ROOT, 'work', 'logs'), exist_ok=True)
    log = open(os.path.join(ROOT, 'work', 'logs', 'import.log'), 'w')
    print('importing %s (SuperH4:LE, base %s) ... (logs: work/logs/import.log)' % (env['DR_BIN'], env['DR_BASE']))
    r = subprocess.call([hl, proj, name, '-import', env['DR_BIN'], '-loader', 'BinaryLoader', '-loader-baseAddr', env['DR_BASE'],
                         '-processor', 'SuperH4:LE:32:default', '-scriptPath', scripts, '-preScript', 'DrSetup.java'], stdout=log, stderr=subprocess.STDOUT)
    if r:
        sys.exit('import failed, see work/logs/import.log')
    return cmd_export(env)


def cmd_export(env):
    hl, proj, name, scripts, out = ghidra_args(env, 'export')
    os.makedirs(out, exist_ok=True)
    sym = rel('third_party/dc-re-ghidra/sdk-symbols.txt')
    names = rel('names.tsv')
    if not os.path.exists(names):
        open(names, 'w').write('# address<TAB>name<TAB>kind(func|data|label)<TAB>comment   (curated names; applied on every export)\n')
    prog = os.path.basename(env['DR_BIN'])
    log = open(os.path.join(ROOT, 'work', 'logs', 'export.log'), 'w') if os.path.isdir(os.path.join(ROOT, 'work', 'logs')) else open(os.devnull, 'w')
    print('finding code, naming SDK functions, dumping asm + decompiled C (several minutes) ... (logs: work/logs/export.log)')
    args = [hl, proj, name, '-process', prog, '-scriptPath', scripts, '-preScript', 'DrFindCode.java']
    if os.path.exists(sym):
        args += ['-postScript', 'DrSdkRename.java', sym, os.path.join(out, 'sdk_matches.tsv')]
    fx = rel('ghidra/stdcall_noclobber_fpscr.xml')
    if os.path.exists(fx) and os.environ.get('DR_NO_FPSCR_FIX') != '1':   # readable SH-4 float decompilation (docs/GHIDRA_SH4_FPU.md)
        args += ['-postScript', 'DrFpscrConv.java', fx]
    args += ['-postScript', 'DrNames.java', names, '-postScript', 'DrConst.java', '-postScript', 'DrDump.java', out]
    r = subprocess.call(args, stdout=log, stderr=subprocess.STDOUT)
    if r or not os.path.exists(os.path.join(out, 'functions.tsv')):
        sys.exit('export failed, see work/logs/export.log')
    print('done: work/research/{functions,callgraph,hw_access,strings}.tsv, asm/, decompiled/')
    if os.environ.get('DR_NO_LIBTRIAGE') != '1':      # no-SDK fallback only; skipped automatically when the exact SDK is present
        cmd_libtriage(env, ['run'])
    return 0


def sdk_available(env):
    """True when `dcre sdk` finds the exact matching SDK release in SDK_DIRS (sdk_detect exit 0)."""
    if not os.path.exists(env['DR_BIN']):
        return False
    dirs = [rel(d) for d in env['DR_SDK_DIRS'].split(':') if d]
    if not dirs:
        return False
    r = subprocess.run(PY + [os.path.join(T, 'sdk_detect.py'), env['DR_BIN']] + dirs, env=env, cwd=ROOT, capture_output=True)
    return r.returncode == 0


def cmd_libtriage(env, rest):
    force = '--force' in rest
    rest = [x for x in rest if x != '--force']
    sub = rest or ['run']
    if sub[0] == 'run' and not force and sdk_available(env):
        print('exact SDK found in SDK_DIRS: libtriage is only the no-SDK fallback, so it is skipped (use the SDK names/headers). --force to run anyway.')
        p = rel('work/research/lib_triage.tsv')
        if os.path.exists(p):
            os.remove(p)
        return 0
    return run(PY + [os.path.join(T, 'libtriage.py')] + sub, env)


def main():
    a = sys.argv[1:]
    if not a or a[0] in ('help', '-h', '--help'):
        print(__doc__); return 0
    env = load_env()
    c, rest = a[0], a[1:]
    if c == 'doctor':
        return cmd_doctor(env)
    if c == 'extract':
        disc = env.get('DISC')
        if not disc:
            sys.exit('set DISC in project.env (copy project.env.example)')
        return run(PY + [os.path.join(T, 'disc_extract.py'), rel(disc), rel('game')] + rest, env)
    if c == 'sdk':
        return run(PY + [os.path.join(T, 'sdk_detect.py'), env['DR_BIN']] + [rel(d) for d in env['DR_SDK_DIRS'].split(':') if d], env)
    if c == 'import':
        return cmd_import(env)
    if c == 'export':
        return cmd_export(env)
    if c == 'libtriage':
        return cmd_libtriage(env, rest)
    if c == 'status':
        return run(PY + [os.path.join(T, 'triage.py'), 'summary'], env)
    if c == 'next':
        return run(PY + [os.path.join(T, 'triage.py'), 'next'] + rest, env)
    if c == 'slice':
        return run(PY + [os.path.join(T, 'triage.py'), 'slice'] + rest, env)
    if c == 'annotate':
        return run(PY + [os.path.join(T, 'sh4_annotate.py')] + rest, env)
    if c == 'autodiff':
        return run(PY + [os.path.join(T, 'autodiff.py')] + rest, env)
    if c == 'bytematch':
        return run(PY + [os.path.join(T, 'bytematch.py')] + rest, env)
    if c == 'permute':
        return run(PY + [os.path.join(T, 'permute.py')] + rest, env)
    if c == 'emu':
        return run([os.path.join(T, 'flycast_run.sh')] + rest, env)
    if c == 'agent':
        addr = rest[0]
        prompt = ('Task: decompile/port the function at address %s of this Dreamcast (SH-4) game to integer-only C in port/fn_%s.c and port/fn_%s.h. '
                  'Load the skill `decomp-function` first and follow it literally; the proof is the final `RESULT:` line of autodiff with --mutate. '
                  'Write your spec and wrapper under port/tests/. Do not commit. Finish with a short report that quotes the final RESULT line and lists anything autodiff cannot show.'
                  % (addr, addr.replace('0x', '')[-8:], addr.replace('0x', '')[-8:]))
        os.makedirs(os.path.join(ROOT, 'port', 'tests'), exist_ok=True)
        return run(['opencode', 'run', '--format', 'json', '--dir', ROOT, prompt], env, stdin=subprocess.DEVNULL)
    sys.exit('unknown command %r; run ./dcre help' % c)


if __name__ == '__main__':
    sys.exit(main())
