#!/usr/bin/env python3
"""notes.py: a tiny durable scratchpad that survives context compaction. Stdlib only.

  python3 -I tools/dc/notes.py add 0x8c043680 "div_s32: dividend in r1, divisor in r0, quotient in r0 (CONFIRMED: asm 8c08b258)"
  python3 -I tools/dc/notes.py show 0x8c043680
  python3 -I tools/dc/notes.py tried 0x8c043680 "arg_limits r7 [-2,24] -> run completes, 33 mismatches"   # something you TRIED and its result

File: work/notes/fn_<addr>.md (inside the project). When the agent's context is compacted, the opencode plugin (.opencode/plugin) re-injects
AGENTS.md AND the newest notes file, so everything written here is still in front of you after the summary replaced the old messages.
WRITE A NOTE EVERY TIME you learn a fact (calling convention, struct field, constant) or finish an experiment. One line each.
"""
import os, sys, time

HERE = os.path.dirname(os.path.realpath(__file__))


def root():
    d = os.getcwd()
    for _ in range(5):
        if os.path.isdir(os.path.join(d, 'work')) or os.path.isdir(os.path.join(d, 'port')):
            return d
        d = os.path.dirname(d)
    return os.getcwd()


def path(addr):
    a = '%08x' % (int(addr, 16) & 0xffffffff)
    return os.path.join(root(), 'work', 'notes', 'fn_%s.md' % a)


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ('add', 'show', 'tried'):
        sys.exit(__doc__)
    cmd, addr = sys.argv[1], sys.argv[2]
    p = path(addr)
    if cmd == 'show':
        print(open(p).read() if os.path.exists(p) else '(no notes yet for %s)' % addr)
        return
    if len(sys.argv) < 4:
        sys.exit('notes.py %s ADDR "one line"' % cmd)
    text = ' '.join(sys.argv[3:]).strip().replace('\n', ' ')
    os.makedirs(os.path.dirname(p), exist_ok=True)
    old = open(p).read() if os.path.exists(p) else '# Notes for %s (facts you established; newest last)\n' % addr
    tag = 'TRIED' if cmd == 'tried' else 'FACT'
    line = '- %s [%s] %s\n' % (time.strftime('%H:%M'), tag, text)
    if line.split('] ', 1)[1] in old:
        print('already noted')
        return
    open(p, 'w').write(old + line)
    print('noted (%d lines) -> %s' % (old.count('\n') + 1, os.path.relpath(p)))


if __name__ == '__main__':
    main()
