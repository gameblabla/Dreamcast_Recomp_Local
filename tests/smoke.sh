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
echo "smoke ok"
