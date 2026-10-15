#!/usr/bin/env python3
"""agentrun.py: run a local opencode (v2) agent on ONE function under a watchdog, and write an honest report. Stdlib only.

  python3 -I tools/dc/agentrun.py 0x8c043680 [--hours 2] [--resumes 4] [--idle-min 12] [--max-step-tokens 6000] [--project DIR] [--runner opencode]

What it fixes (all seen in real runs of a local 27B model):
  * a reply that hits the output limit (`reason: length`, 31K tokens of the same paragraph) used to END the run with exit code 0
    -> the run is killed and the SAME session is resumed (-s ID) with a short nudge that points at the notes file
  * silent stalls (no event for --idle-min minutes) -> same
  * the agent exits without a FINAL proof in the ledger -> resumed up to --resumes times, each time told the newest ledger line
  * repeated identical commands / blocked repeats (the dcguard plugin blocks them) are counted and reported
  * completion is decided by the proof LEDGER (`autodiff --final` -> RESULT: PROVEN, port unchanged since), never by what the agent says
Report: work/agent/<addr>.report.md (+ the raw event log work/agent/<addr>.jsonl).
"""
import argparse, collections, json, os, re, signal, subprocess, sys, time

HERE = os.path.dirname(os.path.realpath(__file__))


def find_project(start):
    d = os.path.abspath(start)
    for _ in range(4):
        if os.path.exists(os.path.join(d, 'AGENTS.md')) and os.path.isdir(os.path.join(d, 'tools')):
            return d
        d = os.path.dirname(d)
    return os.path.abspath(start)


def ledger(project, addr):
    try:
        return json.load(open(os.path.join(project, 'work', 'proofs', '%s.json' % addr)))
    except (OSError, ValueError):
        return {'runs': []}


def proven_final(project, addr):
    """the proof ledger decides (proofcheck.backed: newest run PROVEN, FINAL, no override, port files unchanged since)"""
    sys.path.insert(0, HERE)
    import importlib, proofcheck
    importlib.reload(proofcheck)
    ok, _why = proofcheck.backed(addr)
    return ok


def scores(project, addr):
    out = []
    for r in ledger(project, addr).get('runs', []):
        m = re.search(r'(\d+) mismatches', r.get('result', '')); f = re.search(r'(\d+) emulator faults', r.get('result', ''))
        out.append((int(m.group(1)) if m else 0) + (int(f.group(1)) if f else 0))
    return out


def ledger_line(project, addr):
    runs = ledger(project, addr).get('runs', [])
    if not runs:
        return 'no autodiff run has completed yet (the ledger is empty)'
    l = runs[-1]
    return '%d autodiff runs; newest at %s: %s%s' % (len(runs), l['time'][11:], l['result'][:260], ' [FINAL]' if l.get('final') else ' [provisional]')


def runner_cmd(runner):
    help_ = subprocess.run([runner, 'run', '--help'], capture_output=True, text=True).stdout
    new = '--standalone' in help_
    return new


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('addr'); ap.add_argument('--project', default='.'); ap.add_argument('--runner', default='opencode')
    ap.add_argument('--hours', type=float, default=2.0); ap.add_argument('--resumes', type=int, default=4)
    ap.add_argument('--idle-min', type=float, default=12.0); ap.add_argument('--max-step-tokens', type=int, default=4500)
    ap.add_argument('--blocked-limit', type=int, default=8, help='plugin-blocked calls in one stretch before the session is nudged')
    ap.add_argument('--prompt-extra', default='')
    ap.add_argument('--soft-frac', type=float, default=0.75, help='fraction of --hours after which the agent is told to wrap up (Mizuchi soft timeout)')
    ap.add_argument('--stall-runs', type=int, default=8, help='give up early when the last 6 of >= N autodiff runs did not beat the best earlier one (saves tokens)')
    ap.add_argument('--escalate', default='', help='provider/model to resume with when the session stalls or loops (e.g. a stronger remote model)')
    a = ap.parse_args()
    project = find_project(a.project)
    addr = '%08x' % (int(a.addr, 16) & 0xffffffff)
    os.makedirs(os.path.join(project, 'work', 'agent'), exist_ok=True)
    raw = open(os.path.join(project, 'work', 'agent', addr + '.jsonl'), 'a')
    errf = open(os.path.join(project, 'work', 'agent', addr + '.err'), 'a')
    new = runner_cmd(a.runner)
    base = [a.runner, 'run'] + (['--standalone', '--auto'] if new else ['--dir', project]) + ['--format', 'json']
    env = dict(os.environ, DC_AGENT='1', DC_AGENT_ADDR=addr, DC_PROJECT_DIR=project)
    prompt = ('Task: decompile/port the SH-4 function at 0x%s to C: port/fn_%s.c, spec + wrapper in port/tests/. Load the skill `decomp-function` FIRST and follow it literally. '
              'The pinned project rules in your system prompt are authoritative. Write every fact you establish with `python3 -I tools/dc/notes.py add 0x%s "fact"` (it survives context compaction). '
              'You are done only when `python3 -I tools/dc/autodiff.py port/tests/spec_%s.json --final` prints `RESULT: PROVEN`; quote that literal line. '
              'Otherwise finish with `NOT DONE` and the last RESULT line. %s' % (addr, addr, addr, addr, a.prompt_extra))
    t0 = time.time()
    stats = collections.Counter()
    cmds = collections.Counter()
    events = []          # (reason, detail)
    session = None
    resumes = 0
    status = 'running'
    nudge = None
    soft_done = False
    escalated = False
    model_args = []
    while True:
        cmd = base + model_args + (['-s', session, nudge] if (session and nudge) else [prompt])
        p = subprocess.Popen(cmd, cwd=project, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=errf, text=True, bufsize=1, start_new_session=True)
        last_ev = time.time()
        reason_stop = None
        blocked_run = 0
        import selectors
        sel = selectors.DefaultSelector(); sel.register(p.stdout, selectors.EVENT_READ)
        while p.poll() is None and reason_stop is None:
            if not sel.select(timeout=5):
                if time.time() - last_ev > a.idle_min * 60:
                    reason_stop = ('idle', 'no event for %.0f min' % ((time.time() - last_ev) / 60))
                if time.time() - t0 > a.hours * 3600:
                    reason_stop = ('timeout', 'wall-clock limit %.1f h' % a.hours)
                continue
            line = p.stdout.readline()
            if not line:
                break
            last_ev = time.time()
            raw.write(line); raw.flush()
            try:
                e = json.loads(line)
            except ValueError:
                continue
            session = e.get('sessionID') or session
            part = e.get('part', {})
            t = e.get('type')
            if t == 'tool_use':
                stats['tool_calls'] += 1
                st = part.get('state', {})
                key = (part.get('tool'), json.dumps(st.get('input'), sort_keys=True)[:200])
                cmds[key] += 1
                out = str(st.get('output') or st.get('error') or '')
                if 'BLOCKED by dcguard' in out or 'LOOP GUARD' in out:
                    stats['blocked'] += 1; blocked_run += 1
                else:
                    blocked_run = 0
                if re.search(r"No such file|can't open|usage:|Traceback|command not found|unrecognized arguments", out[:3000]):
                    stats['error_calls'] += 1
                if 'autodiff.py' in str(st.get('input')):
                    stats['autodiff_calls'] += 1
                if 'autodiff.py' in str(st.get('input')) and not reason_stop:
                    sc = scores(project, addr)
                    if len(sc) >= a.stall_runs and min(sc[-6:]) >= min(sc[:-6] or [10 ** 9]) and not proven_final(project, addr):
                        reason_stop = ('stalled', 'the last 6 of %d autodiff runs (%s) did not beat the best earlier run (%s)' % (len(sc), sc[-6:], min(sc[:-6])))
                if blocked_run >= a.blocked_limit:
                    reason_stop = ('blocked', '%d plugin-blocked calls in a row' % blocked_run)
            elif t == 'step_finish':
                stats['steps'] += 1
                tk = part.get('tokens', {})
                if part.get('reason') == 'length' or tk.get('output', 0) > a.max_step_tokens:
                    reason_stop = ('length', 'one reply produced %s output tokens (reason=%s): a repetition loop' % (tk.get('output'), part.get('reason')))
            elif t == 'text':
                stats['text_parts'] += 1
            if time.time() - t0 > a.hours * 3600:
                reason_stop = ('timeout', 'wall-clock limit %.1f h' % a.hours)
            elif not soft_done and time.time() - t0 > a.soft_frac * a.hours * 3600:
                soft_done = True
                reason_stop = ('soft', '%.0f%% of the time budget used' % (a.soft_frac * 100))
        if reason_stop:
            try:
                os.killpg(p.pid, signal.SIGTERM); time.sleep(3)
                if p.poll() is None:
                    os.killpg(p.pid, signal.SIGKILL)
            except OSError:
                pass
            events.append(reason_stop)
            stats['kills'] += 1
        else:
            p.wait()
            events.append(('exit', 'agent process exited with code %s' % p.returncode))
        if proven_final(project, addr):
            status = 'PROVEN (final run in the ledger)'
            break
        if reason_stop and reason_stop[0] == 'timeout':
            status = 'STOPPED: wall-clock limit'
            break
        if reason_stop and reason_stop[0] == 'stalled':
            if a.escalate and not escalated:
                escalated = True
                model_args = ['-m', a.escalate]
                stats['escalations'] += 1
            else:
                status = 'GAVE UP EARLY (stalled: no improvement over the last 6 autodiff runs); best attempt: attempts.py best'
                break
        if resumes >= a.resumes or not session:
            status = 'NOT DONE (resume budget used up)' if session else 'NOT DONE (no session id was seen)'
            break
        resumes += 1
        why = events[-1]
        nudge = ('Supervisor message #%d (%s: %s). You are NOT done. Ledger: %s. ' % (resumes, why[0], why[1], ledger_line(project, addr)) +
                 {'length': 'Your last reply was cut off because you repeated yourself. Do NOT repeat reasoning. Run `python3 -I tools/dc/notes.py show 0x%s`, then take ONE concrete action with a tool.' % addr,
                  'idle': 'The previous step stalled. Re-read the notes (`notes.py show 0x%s`) and continue with one tool call.' % addr,
                  'blocked': 'Your last calls were blocked as repeats/invalid. Read the BLOCKED message, change approach, and record what you tried with notes.py tried.',
                  'soft': 'Time is nearly up. Stop exploring NOW. If the normal run has 0 mismatches: run `--mutate` then `--final`. Otherwise `python3 -I tools/dc/attempts.py restore 0x%s best` and write the report: NOT DONE, the last RESULT line, what you learned.' % addr,
                  'stalled': 'No progress over many autodiff runs. Restore the best attempt (`attempts.py restore 0x%s best`), read `notes.py show 0x%s`, and take a FUNDAMENTALLY different approach (re-read the brief and the annotated retail path in the last mismatch report; question one assumption in the notes).' % (addr, addr),
                  'exit': 'You stopped before a FINAL proof exists. Read the notes (`notes.py show 0x%s`), then continue: next step is `autodiff.py SPEC --final` once the normal run has 0 mismatches and all mutants killed; if you are truly stuck, write NOT DONE with evidence.' % addr}.get(why[0], 'Continue.'))
    dur = time.time() - t0
    rep = ['# agent run report: %s' % addr, '', '- status: **%s**' % status, '- duration: %.0f min, tool calls: %d, steps: %d, resumes: %d, watchdog kills: %d' %
           (dur / 60, stats['tool_calls'], stats['steps'], resumes, stats['kills']) + (', escalations: %d' % stats['escalations'] if stats['escalations'] else ''),
           '- calls that returned an error/usage text: %d; calls blocked by dcguard: %d; autodiff invocations: %d' % (stats['error_calls'], stats['blocked'], stats['autodiff_calls']),
           '- ledger: ' + ledger_line(project, addr), '- watchdog events: ' + ('; '.join('%s (%s)' % x for x in events) or 'none'),
           '- most repeated calls: ' + ('; '.join('%dx %s %s' % (n, k[0], k[1][:80]) for k, n in cmds.most_common(3) if n > 2) or 'none')]
    open(os.path.join(project, 'work', 'agent', addr + '.report.md'), 'w').write('\n'.join(rep) + '\n')
    print('\n'.join(rep))
    sys.exit(0 if status.startswith('PROVEN') else 1)


if __name__ == '__main__':
    main()
