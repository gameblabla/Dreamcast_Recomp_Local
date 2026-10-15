#!/usr/bin/env bash
# build_flycast_probe.sh: build a Flycast with our small patches (patches/*.patch) WITHOUT touching the third_party/flycast submodule.
#   tools/build_flycast_probe.sh            -> third_party/flycast-bin/flycast-probe
# Patches: patches/flycast-gdb-send-queue.patch (the GDB stub drops stop replies that race with a '+' ack: queue outgoing packets).
# INPLACE=1 FLYCAST_SRC=/tmp/flycast-probe/clone builds in a fresh recursive clone (the submodule checkout in third_party/flycast has EMPTY nested submodules:
#   git clone --recursive --shallow-submodules --depth 1 https://github.com/flyinghead/flycast /tmp/flycast-probe/clone  at the commit pinned by the submodule).
# Build tree goes to /tmp (the root disk is full); needs cmake, ninja, a C++ compiler, SDL2 dev files (same as docs/FLYCAST_NOTES.md).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${FLYCAST_SRC:-$ROOT/third_party/flycast}"
WORK="${FLYCAST_BUILD_DIR:-/tmp/flycast-probe}"
mkdir -p "$WORK"
if [ "${INPLACE:-0}" = 1 ]; then WORK_SRC="$SRC"; else rsync -a --delete --exclude .git "$SRC/" "$WORK/src/"; WORK_SRC="$WORK/src"; fi
for p in "$ROOT"/patches/*.patch; do (cd "$WORK_SRC" && patch -p1 -N --silent < "$p" || patch -p1 -R --dry-run --silent < "$p") || { echo "patch $p failed"; exit 1; }; done
cmake -S "$WORK_SRC" -B "$WORK/build" -G Ninja -DCMAKE_BUILD_TYPE=Release -DUSE_HOST_SDL=ON -DENABLE_GDB_SERVER=ON >"$WORK/cmake.log" 2>&1 || { tail -20 "$WORK/cmake.log"; exit 1; }
cmake --build "$WORK/build" -j"${JOBS:-12}" >"$WORK/build.log" 2>&1 || { tail -30 "$WORK/build.log"; exit 1; }
mkdir -p "$ROOT/third_party/flycast-bin"
cp "$WORK/build/flycast" "$ROOT/third_party/flycast-bin/flycast-probe"
echo "built $ROOT/third_party/flycast-bin/flycast-probe"
