#!/usr/bin/env bash
# flycast_run.sh: run the precompiled flycast headless (xvfb) with an ISOLATED config, optional GDB stub.
#   tools/flycast_run.sh GAME.cue|.gdi|.cdi [--automation] [--gdb PORT] [--seconds N] [-- extra flycast args]
# Binaries: third_party/flycast-bin/{flycast,flycast-automation,flycast_libretro.so} (see docs/FLYCAST.md; rebuild from third_party/flycast).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN="$ROOT/third_party/flycast-bin/flycast"
GAME="${1:?usage: flycast_run.sh GAME [--automation] [--gdb PORT] [--seconds N]}"; shift
SECS=0; GDB=""; EXTRA=()
while [ $# -gt 0 ]; do case "$1" in
  --automation) BIN="$ROOT/third_party/flycast-bin/flycast-automation";;
  --gdb) GDB="$2"; shift;;
  --seconds) SECS="$2"; shift;;
  --) shift; EXTRA=("$@"); break;;
esac; shift; done
export XDG_CONFIG_HOME="$ROOT/work/flycast_cfg/config" XDG_DATA_HOME="$ROOT/work/flycast_cfg/data"
mkdir -p "$XDG_CONFIG_HOME" "$XDG_DATA_HOME"
CFG=(-config config:UseReios=yes)    # boot without a BIOS dump; put dc_boot.bin/dc_flash.bin in $XDG_DATA_HOME/flycast/ to use the real BIOS
[ -n "$GDB" ] && CFG+=(-config config:Debug.GDBEnabled=yes -config "config:Debug.GDBPort=$GDB")
CMD=("$BIN" "${CFG[@]}" "${EXTRA[@]}" "$GAME")
if [ "$SECS" != 0 ]; then exec timeout "$SECS" xvfb-run -a "${CMD[@]}"; else exec xvfb-run -a "${CMD[@]}"; fi
