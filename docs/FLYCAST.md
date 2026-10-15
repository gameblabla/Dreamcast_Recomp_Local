# Flycast (emulator) in this project

Why: ground truth for behaviour that the Ghidra SH-4 emulator (used by `autodiff`) cannot give: whole-game runs, save states, GDB-stub
breakpoints, PVR/AICA effects, BIOS-dependent paths. `autodiff` stays the unit-level oracle; flycast confirms system-level facts.

- `third_party/flycast/` : upstream source as a **git submodule** (pinned commit; `git submodule update --init third_party/flycast`).
  Only needed to rebuild or to read the emulator code (e.g. the hardware-derived FSCA table in `core/hw/sh4`).
- `third_party/flycast-bin/` : **precompiled copies** (not committed to git, 100 MB; copy them from your machine or rebuild):
  | file | build | use |
  |---|---|---|
  | `flycast` | `-DUSE_HOST_SDL=ON -DENABLE_GDB_SERVER=ON` | normal emulator, GDB stub on demand |
  | `flycast-automation` | + `-DTEST_AUTOMATION=ON` | scripted/CI runs (muted audio, framebuffer dump, input replay, fail-fast) |
  | `flycast_libretro.so` | `-DLIBRETRO=ON` | headless libretro core for harnesses / RetroArch |
- Run headless with an isolated config: `./dcre emu GAME.cue --seconds 60`, or `tools/flycast_run.sh GAME --automation --gdb 3263`.
  It uses `xvfb-run`, `UseReios=yes` (boots without a BIOS) and a private `XDG_CONFIG_HOME` under `work/flycast_cfg` so your normal flycast config is untouched.
- Rebuild: see FLYCAST_NOTES.md (cmake flags above; build tree in /tmp; GCC 14 Release).
- Save states can be unpacked to a RAM image with the flycast source's state format (write a small reader once; the RAM block starts at offset
  after the header — verify against `core/serialize.h`); the RAM image + `DrEmu` can be diffed against `autodiff` outputs.

Gotchas (details in FLYCAST_NOTES.md): `-config config:<ExactKey>=value` (wrong section silently does nothing); the GDB stub only listens while a game
is running; `-config` values are transient and ignored on first run (no emu.cfg yet: run once normally first).
