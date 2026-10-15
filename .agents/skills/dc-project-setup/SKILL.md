---
name: dc-project-setup
description: Set up or resume a Dreamcast reverse-engineering/decomp project in this repo (disc image -> Ghidra project -> research dumps), including the rule to detect the game's SDK/compiler and ASK THE USER for a copy before proceeding. Use at the start of any session, when `./dcre doctor` reports MISSING items, or when the user gives a new disc/SDK path.
---
# Project setup (run these, in order, and read each result)
1. `./dcre doctor` : lists tools/files. Required MISSING items must be fixed (Ghidra/java/cc/submodule). Optional ones are explained inline.
2. `project.env` (copy `project.env.example`): `DISC=` (.gdi/.cue/.iso/folder), `SDK_DIRS=` (`:`-separated folders/.iso/.zip of Dreamcast SDKs, e.g. 1.42J and 1.00J).
3. `./dcre extract --boot-only` (or without the flag for all disc files; check free disk first: discs are ~1 GB) -> `game/1ST_READ.BIN`.
4. `./dcre sdk` : MANDATORY before any naming/matching work.
   - exit 0 and "exact SDK available": proceed, byte-matching is possible.
   - exit 3 and an `ASK THE USER:` line: **stop and send that request to the user verbatim** (which SDK release, why). Offer to proceed without it and state the cost
     (no original compiler, no exact headers, fewer library names, much slower). Continue without the SDK only after the user agrees or declines to provide it.
   - If banners are absent (stripped), ask which SDK/compiler the game used.
   - SDK present: run `./dcre sdk-index` once (local hashes of its libraries; needs wine/wibo), then `./dcre export` names the library code. Stripped headers: `include/sdk_stripped_*`.
   - No SDK (user declined/unavailable): `./dcre export` runs `libtriage` (no-SDK fallback only; skipped if the SDK is present). Library functions become class `sdk` in `next`/`status`; `python3 -I tools/libtriage.py why ADDR` shows the evidence; `unknown` = treat as game code. Do not port `lib-*` functions; call them via host callbacks.
5. `./dcre import` (Ghidra project + full export, several minutes) -> `work/research/*.tsv`, `asm/`, `decompiled/`. Re-run `./dcre export` after editing `names.tsv`.
6. `./dcre status`, `./dcre next 20`, `./dcre slice ADDR` to choose work; then skill `decomp-function` (behaviour proof) and, if the original compiler exists, `byte-matching`.
Rules: never commit `game/`, `work/`, SDK files or `project.env`; work in this repo only; temporaries in `work/` or `work/autodiff/`; do not print huge dumps (`head`, `grep`).
