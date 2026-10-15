#!/usr/bin/env bash
# Game-independent smoke test: syntax of every tool + the byte-matching tools against a self-made target (needs sh-elf-gcc).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
for f in tools/*.py; do python3 -c "import ast,sys; ast.parse(open('$f').read())" && echo "syntax ok  $f"; done
bash -n tools/flycast_run.sh && echo "syntax ok  tools/flycast_run.sh"
if command -v sh-elf-gcc >/dev/null; then
  printf 'int f(int a,int b){return a*3+b;}\n' > "$T/t.c"
  sh-elf-gcc -O2 -m4-single-only -ml -c "$T/t.c" -o "$T/t.o"; sh-elf-objcopy -O binary -j .text "$T/t.o" "$T/t.bin"
  L=$(stat -c %s "$T/t.bin")
  python3 -I tools/bytematch.py --addr 0 --len "$L" --bin "$T/t.bin" --base 0 --src "$T/t.c" --func f | tail -1 | grep -q "EXACT" && echo "bytematch ok"
  printf 'int f(int a,int b){return b+3*a;}\n' > "$T/c.c"
  python3 -I tools/permute.py --addr 0 --len "$L" --bin "$T/t.bin" --src "$T/c.c" --func f --iters 20 | tail -1
else
  echo "skip bytematch/permute (no sh-elf-gcc)"
fi
# discovery tool syntax is covered above; original compiler path only when an SDK compiler is installed
if python3 -I tools/shc.py find >/dev/null 2>&1; then
  printf 'int f(int x){int r; if(x>=0) r=x+11; else r=-1; return r;}\n' > "$T/s.c"
  python3 -I tools/shc.py compile "$T/s.c" --func f -o "$T/s.bin" | head -1 | grep -q "compiler=SHC" && [ "$(stat -c %s "$T/s.bin")" -gt 0 ] && echo "shc ok"
else
  echo "skip shc (no SDK compiler / wine): bytematch falls back to sh-elf-gcc"
fi
python3 -I tests/test_tools.py | tail -1
echo "smoke ok"
