#!/usr/bin/env python3
"""dcprobe.py: capture REAL runtime inputs of a retail function from a Flycast save state, through Flycast's own GDB server. Stdlib only.

  python3 -I tools/dc/dcprobe.py capture 0x8c04c938 --state 1 [--hits 12] [--seconds 120] [--spec port/tests/spec_8c04c938.json]
  python3 -I tools/dc/dcprobe.py peek 0x8c0e204c 64 --state 1          # read live memory of a state
  python3 -I tools/dc/dcprobe.py hot --state 1 --seconds 20 0x8c07d874 0x8c0481e0 ...   # which of these functions run, and how often
  python3 -I tools/dc/dcprobe.py profile --state 2 --seconds 30       # PC sampling: which functions this scene really executes (pick a --state for capture)

What `capture` records at every entry of the function (breakpoint on its first instruction, so r15 is the ENTRY sp and r4-r7/fr4-fr7 are the arguments):
  r0-r15, pr, fr0-fr15, fpscr, the first 16 stack words (stack arguments), and the bytes of every region the spec declares (live game data).
Output: work/probe/fn_<addr>.json. `autodiff.py` replays it when the spec has  "captured": "work/probe/fn_<addr>.json"  (real gameplay inputs on top of
the generated boundary cases: the best check that the port also works on data the game really produces; it also shows whether our pointer/index/stack
classification of the parameters was right).
Requirements: third_party/flycast-bin/flycast (built with ENABLE_GDB_SERVER, see docs/FLYCAST_NOTES.md), xvfb-run, the disc .cue (project.env GAME or --game),
a Flycast .state (--state N copies <game>_N.state from save_states/ or --state-file PATH). The emulator runs headless under xvfb with an ISOLATED config in work/flycast_cfg.
"""
import argparse, glob, json, os, re, shutil, signal, socket, struct, subprocess, sys, time

HERE = os.path.dirname(os.path.realpath(__file__))
REGS = ['r%d' % i for i in range(16)] + ['pc', 'pr', 'gbr', 'vbr', 'mach', 'macl', 'sr', 'fpul', 'fpscr'] + ['fr%d' % i for i in range(16)] + ['ssr', 'spc'] + ['r%d_b' % i for i in range(8)] + ['rb%d' % i for i in range(8)]


def project_root():
    d = os.getcwd()
    for _ in range(5):
        if os.path.isdir(os.path.join(d, 'tools')) and (os.path.exists(os.path.join(d, 'AGENTS.md')) or os.path.isdir(os.path.join(d, 'work'))):
            return d
        d = os.path.dirname(d)
    return os.getcwd()


class RSP:
    """minimal GDB remote serial protocol client (enough for Flycast's stub)"""
    def __init__(self, host='127.0.0.1', port=3263, timeout=30):
        self.s = socket.create_connection((host, port), timeout=timeout)
        self.s.settimeout(timeout)
        self.buf = b''

    def close(self):
        try:
            self.s.close()
        except OSError:
            pass

    def _recv(self):
        d = self.s.recv(65536)
        if not d:
            raise ConnectionError('gdb stub closed the connection')
        self.buf += d

    def send(self, pkt):
        cs = sum(pkt.encode()) & 0xff
        self.s.sendall(('$%s#%02x' % (pkt, cs)).encode())

    def recv(self, timeout=None):
        if timeout is not None:
            self.s.settimeout(timeout)
        while True:
            m = re.search(rb'\$([^#]*)#[0-9a-fA-F]{2}', self.buf)
            if m:
                self.buf = self.buf[m.end():]
                self.s.sendall(b'+')
                return m.group(1).decode(errors='replace')
            self.buf = re.sub(rb'^[+-]+', b'', self.buf)
            self._recv()

    def cmd(self, pkt, timeout=None, stop_ok=False):
        self.send(pkt)
        while True:
            r = self.recv(timeout)
            if stop_ok or not (re.fullmatch(r'[ST][0-9a-f]{2}.*', r) or (r != 'OK' and re.fullmatch(r'O[0-9a-f]+', r))) or pkt in ('?', 's', 'vCont;s'):
                return r

    # ---- helpers
    def regs(self):
        raw = self.cmd('g')
        vals = struct.unpack('<%dI' % (len(raw) // 8), bytes.fromhex(raw))
        return {n: v for n, v in zip(REGS, vals)}

    def mem(self, addr, n):
        out = b''
        while n > 0:
            k = min(n, 0x800)
            r = self.cmd('m%x,%x' % (addr, k))
            if r.startswith('E') or len(r) < 2 * k:
                raise IOError('memory read failed at %08x (+%d): %r' % (addr, k, r[:20]))
            out += bytes.fromhex(r[:2 * k])
            addr += k
            n -= k
        return out

    def set_break(self, addr, kind=0):
        # Flycast's stub supports SOFTWARE breakpoints (Z0) and watchpoints (Z2-Z4); Z1 (hardware break) answers with an empty packet
        return self.cmd('Z%d,%x,2' % (kind, addr))

    def clear_break(self, addr, kind=0):
        return self.cmd('z%d,%x,2' % (kind, addr))

    def cont(self):
        self.send('c')

    BRANCH = re.compile(r'^(?:[0-9a-f]{1}[0-9a-f]{3})$')

    def arm(self, addr):
        """insert a software breakpoint; remember the original opcode (Flycast patches `trapa #0x20` into the code, so it must be read first)"""
        if not hasattr(self, 'orig'):
            self.orig = {}
        if addr not in self.orig:
            self.orig[addr] = struct.unpack('<H', self.mem(addr, 2))[0]
        op = self.orig[addr]
        # an entry instruction that is a branch (bra/bsr/jmp/jsr/rts/bt/bf/braf/bsrf/rte) has a delay slot: stepping over it with a temporary breakpoint would be wrong
        top = op >> 12
        low = op & 0xff
        if top in (0xA, 0xB, 0x8) and (top != 0x8 or (op >> 8) in (0x89, 0x8B, 0x8D, 0x8F)) or (top == 0x4 and low in (0x0B, 0x2B)) or op in (0x000B, 0x002B) or (top == 0x0 and low in (0x03, 0x23)):
            raise SystemExit('dcprobe: the first instruction of %08x is a branch (opcode %04x); breakpoint it at its second instruction instead' % (addr, op))
        r = self.set_break(addr, 0)
        if r != 'OK':
            raise SystemExit('dcprobe: the stub refused a breakpoint at %08x (%r)' % (addr, r))

    def resume_from(self, addr, armed=()):
        """continue from a hit at addr: restore the opcode, run ONE instruction by means of a temporary breakpoint at addr+2, re-arm, continue"""
        tmp = addr + 2
        self.clear_break(addr, 0)
        self.set_break(tmp, 0)
        self.cont()
        while True:
            self.stop_or_poll(0.6)
            pc = self.regs()['pc']
            if pc == tmp:
                break
            if pc in armed:                     # another armed function trapped inside this one instruction (an interrupt handler): let it go, we only lose that one hit
                self.clear_break(pc, 0); self.set_break(pc + 2, 0); self.cont(); self.wait_stop(30); self.clear_break(pc + 2, 0); self.set_break(pc, 0); self.cont()
                continue
            raise IOError('unexpected stop at %08x while stepping over %08x' % (pc, addr))
        self.clear_break(tmp, 0)
        self.set_break(addr, 0)
        self.cont()

    def stop_or_poll(self, quick):
        """wait for a stop reply; the STOCK stub drops a stop reply that races with the '+' ack of the 'c' (log: "Message dropped: $S05"), which happens when the trap is
        one instruction away. If nothing arrives quickly, interrupt: the target is already stopped there and answers S02 (the patched flycast-probe never loses it)."""
        try:
            return self.recv(quick)
        except (socket.timeout, TimeoutError):
            self.interrupt()
            return self.recv(15)

    def wait_stop(self, timeout):
        return self.recv(timeout)

    def interrupt(self):
        self.s.sendall(b'\x03')


def launch(args, root):
    game = args.game or os.environ.get('GAME') or next(iter(glob.glob(os.path.join(root, '..', '*.cue')) + glob.glob(os.path.join(root, '..', '..', '*.cue')) + glob.glob(os.path.join(root, 'game', '*.cue'))), None)
    if not game or not os.path.exists(game):
        sys.exit('dcprobe: disc image not found: pass --game PATH.cue (or GAME= in project.env)')
    binp = args.flycast or next((p for p in (os.path.join(root, 'third_party', 'flycast-bin', 'flycast-probe'), os.path.join(root, 'Dreamcast_Recomp_Local', 'third_party', 'flycast-bin', 'flycast-probe'),
                                              os.path.join(root, 'third_party', 'flycast-bin', 'flycast'), os.path.join(root, 'Dreamcast_Recomp_Local', 'third_party', 'flycast-bin', 'flycast')) if os.path.exists(p)), None)   # flycast-probe = our patched build (tools/build_flycast.sh)
    if not binp:
        sys.exit('dcprobe: flycast binary not found (third_party/flycast-bin/flycast); see docs/FLYCAST_NOTES.md to build it with -DENABLE_GDB_SERVER=ON')
    cfg = os.path.join(root, 'work', 'flycast_cfg')
    data = os.path.join(cfg, 'data', 'flycast')
    os.makedirs(os.path.join(cfg, 'config'), exist_ok=True); os.makedirs(data, exist_ok=True)
    name = os.path.splitext(os.path.basename(game))[0]
    cfgs = ['config:UseReios=yes', 'config:Debug.GDBEnabled=yes', 'config:Debug.GDBPort=%d' % args.port, 'config:Debug.GDBWaitForConnection=yes',
            'config:rend.ThreadedRendering=no', 'config:aica.NoSound=yes']
    if args.state_file or args.state is not None:
        src = args.state_file or next((p for d_ in (root, os.path.join(root, '..'), os.path.join(root, '..', '..')) for p in (os.path.join(d_, 'save_states', '%s_%s.state' % (name, args.state)), os.path.join(d_, 'save_states', '%s.state' % name)) if os.path.exists(p)), None)
        if not src or not os.path.exists(src):
            sys.exit('dcprobe: save state not found for slot %s (save_states/%s_%s.state); use --state-file' % (args.state, name, args.state))
        slot = args.state if args.state is not None else 0
        dst = os.path.join(data, '%s_%s.state' % (name, slot))
        if os.path.lexists(dst):
            os.remove(dst)
        os.symlink(os.path.abspath(src), dst)
        cfgs += ['config:Dreamcast.AutoLoadState=yes', 'config:Dreamcast.SavestateSlot=%s' % slot]
    env = dict(os.environ, XDG_CONFIG_HOME=os.path.join(cfg, 'config'), XDG_DATA_HOME=os.path.join(cfg, 'data'))
    cmd = ['xvfb-run', '-a', binp]
    for c in cfgs:
        cmd += ['-config', c]
    cmd.append(game)
    log = open(os.path.join(cfg, 'flycast_probe.log'), 'w')
    p = subprocess.Popen(cmd, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    return p, cfg


def connect(p, port, wait):
    t0 = time.time()
    last = None
    while time.time() - t0 < wait:
        if p.poll() is not None:
            raise SystemExit('dcprobe: flycast exited early (code %s); see work/flycast_cfg/flycast_probe.log' % p.returncode)
        try:
            g = RSP(port=port, timeout=60)
            g.first_stop = g.cmd('?', timeout=30)      # the listener can accept and then reset while the game is still starting: retry the whole handshake
            return g
        except (OSError, ConnectionError) as ex:
            last = ex
            time.sleep(1.0)
    raise SystemExit('dcprobe: GDB port %d never opened (%s). The listener starts only when a game is running; check work/flycast_cfg/flycast_probe.log' % (port, last))


def stop(p):
    try:
        os.killpg(p.pid, signal.SIGTERM); time.sleep(1)
        if p.poll() is None:
            os.killpg(p.pid, signal.SIGKILL)
    except OSError:
        pass


def regions_from_spec(path):
    try:
        spec = json.load(open(path))
    except (OSError, ValueError):
        return [], {}
    out = []
    for r in spec.get('regions', []):
        a = int(str(r['addr']), 16)
        if a >= 0x8cf00000:           # synthetic regions (pointer params, stack): relocated at replay time, never read from the game
            continue
        out.append((a, int(r['len'])))
    return out, spec


def cmd_capture(a):
    root = project_root()
    addr = int(a.addr, 16)
    regions, spec = regions_from_spec(a.spec) if a.spec else ([], {})
    for m in a.mem or []:
        x, n = m.split(':'); regions.append((int(x, 16), int(n, 0)))
    p, cfg = launch(a, root)
    hits = []
    try:
        g = connect(p, a.port, a.boot_wait)
        print('[dcprobe] attached; breakpoint at %08x' % addr, flush=True)
        g.cmd('?')
        g.arm(addr)
        t0 = time.time()
        g.cont()
        while len(hits) < a.hits and time.time() - t0 < a.seconds:
            try:
                st = g.wait_stop(max(1, a.seconds - (time.time() - t0)))
            except socket.timeout:
                break
            regs = g.regs()
            if regs['pc'] != addr:
                g.cont(); continue
            last_pc = addr
            sp = regs['r15']
            hit = dict(regs={k: v for k, v in regs.items() if re.fullmatch(r'r\d+|fr\d+|pr|pc|fpscr|fpul|sr|gbr|mach|macl', k)}, stack=list(struct.unpack('<16I', g.mem(sp, 64))), mem={})
            for ra, rn in regions:
                try:
                    hit['mem']['%08x' % ra] = g.mem(ra, rn).hex()
                except IOError as ex:
                    hit['mem']['%08x' % ra] = None
            hit['ptrmem'] = {}
            for pk, pv in (spec.get('ptr_args') or {}).items():       # the bytes the REAL pointer points to (replayed into the spec's synthetic region)
                real = regs.get(pk) if pk.startswith('r') else (hit['stack'][int(pk[5:])] if pk.startswith('stack') and pk[5:].isdigit() and int(pk[5:]) < 16 else None)
                try:
                    hit['ptrmem'][pk] = g.mem(real, int(pv['size'])).hex() if real else None
                except IOError:
                    hit['ptrmem'][pk] = None
            hits.append(hit)
            print('[dcprobe] hit %d: r4=%08x r5=%08x r6=%08x r7=%08x sp=%08x pr=%08x' % (len(hits), regs['r4'], regs['r5'], regs['r6'], regs['r7'], sp, regs['pr']), flush=True)
            g.resume_from(addr, ())
        try:
            g.interrupt(); g.clear_break(addr, 0)
        except Exception:
            pass
        g.close()
    finally:
        stop(p)
    out = os.path.join(root, 'work', 'probe', 'fn_%08x.json' % addr)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(dict(func='%08x' % addr, state=a.state if a.state is not None else a.state_file, regions=['%08x:%d' % r for r in regions], hits=hits), open(out, 'w'), indent=1)
    print('[dcprobe] %d hit(s) -> %s' % (len(hits), os.path.relpath(out, root)))
    if not hits:
        print('[dcprobe] no hit: the function did not run in %ds from this state. Try another --state, a longer --seconds, or a function the scene calls (use `hot`).' % a.seconds)
        sys.exit(2)


def cmd_peek(a):
    root = project_root()
    p, cfg = launch(a, root)
    try:
        g = connect(p, a.port, a.boot_wait)
        data = g.mem(int(a.addr, 16), int(a.len, 0))
        for i in range(0, len(data), 16):
            print('%08x: %s' % (int(a.addr, 16) + i, data[i:i + 16].hex()))
        g.close()
    finally:
        stop(p)


def cmd_hot(a):
    root = project_root()
    p, cfg = launch(a, root)
    counts = {int(x, 16): 0 for x in a.addrs}
    try:
        g = connect(p, a.port, a.boot_wait)
        g.cmd('?')
        for x in list(counts):
            try:
                g.arm(x)
            except SystemExit as ex:
                print('# skipped %08x: %s' % (x, str(ex).split(': ', 1)[-1][:90])); del counts[x]
        t0 = time.time()
        g.cont()
        while time.time() - t0 < a.seconds:
            try:
                g.wait_stop(max(1, a.seconds - (time.time() - t0)))
            except socket.timeout:
                break
            pc = g.regs()['pc']
            if pc in counts:
                counts[pc] += 1
                g.resume_from(pc, tuple(counts))
            else:
                g.cont()
        g.interrupt()
        g.close()
    finally:
        stop(p)
    for x, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print('%08x  %d hit(s) in %ds' % (x, n, a.seconds))


def function_table(root):
    """[(addr, size, name)] sorted, from the Ghidra export (research/ghidra/functions.tsv or work/research/functions.tsv)"""
    for rel in ('research/ghidra/functions.tsv', 'work/research/functions.tsv'):
        p = os.path.join(root, rel)
        if os.path.exists(p):
            rows = []
            for ln in open(p).read().split('\n')[1:]:
                f = ln.split('\t')
                if len(f) >= 3 and re.fullmatch(r'[0-9a-f]{8}', f[0]):
                    rows.append((int(f[0], 16), int(f[2]), f[1]))
            return sorted(rows)
    return []


def cmd_profile(a):
    """sample the program counter while the state runs: which functions does this scene really execute? (interrupt every --interval s)"""
    import bisect, collections
    root = project_root()
    table = function_table(root)
    starts = [r[0] for r in table]
    p, cfg = launch(a, root)
    cnt = collections.Counter(); callers = collections.Counter()
    n = 0
    t0 = time.time()
    try:
        g = connect(p, a.port, a.boot_wait)
        t0 = time.time()
        while time.time() - t0 < a.seconds:
            g.cont(); time.sleep(a.interval); g.interrupt()
            try:
                g.wait_stop(15)
            except (socket.timeout, TimeoutError):
                break
            r = g.regs(); n += 1
            for tag, pc in (('pc', r['pc']), ('pr', r['pr'])):
                i = bisect.bisect_right(starts, pc) - 1
                if i >= 0 and pc < table[i][0] + max(table[i][1], 2):
                    (cnt if tag == 'pc' else callers)[(table[i][0], table[i][2])] += 1
        g.close()
    finally:
        stop(p)
    print('# %d samples in %.0fs. pc = samples whose PC was inside the function; via-pr = samples whose CALLER (pr) was inside it' % (n, time.time() - t0))
    allk = set(cnt) | set(callers)
    for (ad, nm) in sorted(allk, key=lambda k: -(cnt[k] * 2 + callers[k]))[:a.top]:
        print('%08x  pc=%-3d via-pr=%-3d  %s' % (ad, cnt[(ad, nm)], callers[(ad, nm)], nm))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    def common(q):
        q.add_argument('--state', type=int); q.add_argument('--state-file'); q.add_argument('--game'); q.add_argument('--flycast')
        q.add_argument('--port', type=int, default=3263); q.add_argument('--boot-wait', type=float, default=90, help='seconds to wait for the GDB listener')
    c = sp.add_parser('capture'); c.add_argument('addr'); c.add_argument('--hits', type=int, default=12); c.add_argument('--seconds', type=float, default=120)
    c.add_argument('--spec', help='autodiff spec: its fixed-address regions are captured at every hit'); c.add_argument('--mem', action='append', help='extra ADDR:LEN to capture'); common(c)
    k = sp.add_parser('peek'); k.add_argument('addr'); k.add_argument('len'); common(k)
    h = sp.add_parser('hot'); h.add_argument('addrs', nargs='+'); h.add_argument('--seconds', type=float, default=20); common(h)
    f = sp.add_parser('profile'); f.add_argument('--seconds', type=float, default=30); f.add_argument('--interval', type=float, default=0.12); f.add_argument('--top', type=int, default=25); common(f)
    a = ap.parse_args()
    try:
        {'capture': cmd_capture, 'peek': cmd_peek, 'hot': cmd_hot, 'profile': cmd_profile}[a.cmd](a)
    except (ConnectionError, BrokenPipeError) as ex:
        sys.exit('dcprobe: flycast died or dropped the connection (%s). Some save states crash this build on load; try another --state. Log: work/flycast_cfg/flycast_probe.log' % ex)


if __name__ == '__main__':
    main()
