#!/usr/bin/env bash
# build_flycast.sh: build Flycast FROM UPSTREAM + our patches (patches/*.patch) and install it into third_party/flycast-bin/.
#
#   tools/build_flycast.sh                 build both variants (normal, automation)
#   tools/build_flycast.sh normal          only the normal SDL build   (-> flycast, flycast-probe)
#   tools/build_flycast.sh automation      only the TEST_AUTOMATION build (-> flycast-automation)
#   tools/build_flycast.sh --check         is the installed binary built from the CURRENT patches? (exit 1 when stale)
#   tools/build_flycast.sh --clean         delete the clone and the build trees in $WORK
#
# Why not third_party/flycast? That submodule checkout has EMPTY nested submodules (glslang, SPIRV-Cross, SDL, ...), so it cannot be built, and we never modify it.
# This script makes its own recursive clone of upstream at the commit the submodule pins, resets it, applies every patches/*.patch, builds with Ninja and installs:
#   flycast, flycast-probe   normal SDL build with the GDB server (-DUSE_HOST_SDL=ON -DENABLE_GDB_SERVER=ON) + patches
#   flycast-automation       same + -DTEST_AUTOMATION=ON (muted audio, frame dump, input replay)
# The previous binaries are kept once as *.stock. BUILD_INFO records the upstream commit, the patch hashes and the date (used by --check). The directory is git-ignored.
#
# Environment: WORK (default /tmp/flycast-build; the root disk is usually full, ~2.5 GB needed), JOBS (default nproc), FLYCAST_URL, FLYCAST_REF (default: the commit pinned
#   by the submodule), FLYCAST_CLONE (reuse an existing recursive clone), VARIANTS. Needs: git, cmake, ninja, a C++17 compiler, patch, SDL2 + the usual Flycast
#   build dependencies (zlib, libcurl, alsa/pulse, libzip ...), network access for the first clone (~1 GB).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="${WORK:-/tmp/flycast-build}"
JOBS="${JOBS:-$(nproc)}"
URL="${FLYCAST_URL:-https://github.com/flyinghead/flycast}"
BIN="$ROOT/third_party/flycast-bin"
CLONE="${FLYCAST_CLONE:-$WORK/clone}"

pinned_ref() {
  # the commit the parent repo pins for the submodule (gitlink), else the submodule's own HEAD
  local r
  r="$(git -C "$ROOT" ls-tree HEAD third_party/flycast 2>/dev/null | awk '{print $3}')"
  [ -n "$r" ] || r="$(git -C "$ROOT/third_party/flycast" rev-parse HEAD 2>/dev/null || true)"
  echo "$r"
}
REF="${FLYCAST_REF:-$(pinned_ref)}"

patch_hashes() { (cd "$ROOT/patches" && sha256sum *.patch 2>/dev/null | sort) ; }

case "${1:-}" in
  --clean) rm -rf "$WORK"; echo "removed $WORK"; exit 0;;
  --check)
    [ -f "$BIN/BUILD_INFO" ] || { echo "STALE: $BIN/BUILD_INFO missing (never built with this script): run tools/build_flycast.sh"; exit 1; }
    want="$(patch_hashes)"; have="$(sed -n '/^patches:/,$p' "$BIN/BUILD_INFO" | tail -n +2)"
    if [ "$want" = "$have" ] && grep -q "^upstream: $REF" "$BIN/BUILD_INFO"; then echo "OK: flycast-bin was built from upstream $REF + the current patches"; exit 0; fi
    echo "STALE: patches or upstream commit changed since the last build: run tools/build_flycast.sh"; exit 1;;
esac

VARIANTS="${VARIANTS:-${*:-normal automation}}"
for t in git cmake ninja patch c++; do command -v "$t" >/dev/null || { echo "missing tool: $t"; exit 1; }; done
[ -n "$REF" ] || { echo "cannot determine the upstream commit (set FLYCAST_REF)"; exit 1; }
mkdir -p "$WORK" "$BIN"

# ---- 1. recursive clone of upstream at the pinned commit
if [ ! -d "$CLONE/.git" ]; then
  echo "[flycast] fetching $URL @ $REF into $CLONE (first time only; shallow, then submodules, ~1 GB)"
  mkdir -p "$CLONE"; git -C "$CLONE" init -q; git -C "$CLONE" remote add origin "$URL"
  git -C "$CLONE" fetch -q --depth 1 origin "$REF" || git -C "$CLONE" fetch -q origin
fi
git -C "$CLONE" cat-file -e "$REF^{commit}" 2>/dev/null || git -C "$CLONE" fetch -q --depth 1 origin "$REF"
git -C "$CLONE" checkout -q -f "$REF"
git -C "$CLONE" reset -q --hard "$REF"
git -C "$CLONE" clean -q -f -- "*.rej" "*.orig" || true
git -C "$CLONE" submodule update --init --recursive --depth 1 --jobs 8

# ---- 2. patches (the tree was reset above, so they always apply to pristine upstream)
for p in "$ROOT"/patches/*.patch; do
  [ -f "$p" ] || continue
  (cd "$CLONE" && patch -p1 --silent < "$p") || { echo "patch $p does not apply to upstream $REF"; exit 1; }
  echo "[flycast] applied $(basename "$p")"
done
if git -C "$CLONE" status --porcelain | grep -qE "\.(rej|orig)$"; then echo "a patch left reject files in $CLONE"; exit 1; fi

# ---- 3. build + install
build() {   # build NAME EXTRA_CMAKE_FLAGS...
  local name="$1"; shift
  echo "[flycast] building variant '$name' with $JOBS jobs (log: $WORK/$name.log)"
  cmake -S "$CLONE" -B "$WORK/build-$name" -G Ninja -DCMAKE_BUILD_TYPE=Release -DUSE_HOST_SDL=ON -DENABLE_GDB_SERVER=ON "$@" >"$WORK/$name.cmake.log" 2>&1 || { tail -25 "$WORK/$name.cmake.log"; exit 1; }
  cmake --build "$WORK/build-$name" -j"$JOBS" >"$WORK/$name.log" 2>&1 || { tail -40 "$WORK/$name.log"; exit 1; }
}
install_bin() {   # install_bin BUILT_FILE DEST_NAME...
  local built="$1"; shift
  for d in "$@"; do
    [ "$d" != flycast-probe ] && [ -e "$BIN/$d" ] && [ ! -e "$BIN/$d.stock" ] && cp -p "$BIN/$d" "$BIN/$d.stock" || true
    cp -p "$built" "$BIN/$d"; chmod +x "$BIN/$d"
    echo "[flycast] installed $BIN/$d"
  done
}
for v in $VARIANTS; do
  case "$v" in
    normal)     build normal;                              install_bin "$WORK/build-normal/flycast" flycast flycast-probe;;
    automation) build automation -DTEST_AUTOMATION=ON;     install_bin "$WORK/build-automation/flycast" flycast-automation;;
    *) echo "unknown variant '$v' (normal | automation)"; exit 1;;
  esac
done

{
  echo "upstream: $REF"
  echo "url: $URL"
  echo "built: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "variants: $VARIANTS"
  echo "patches:"
  patch_hashes
} > "$BIN/BUILD_INFO"
(cd "$BIN" && sha256sum flycast flycast-probe flycast-automation 2>/dev/null > SHA256SUMS || true)
echo "[flycast] done. $("$0" --check || true)"
