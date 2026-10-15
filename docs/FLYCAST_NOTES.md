# Flycast builds & debug notes

Source repo: `../flycast/` (built 2026-09-23, Void Linux, GCC 14, Release).
Binaries: `./flycast-bin/`

## Binaries

| File | CMake flags | Purpose |
|---|---|---|
| `flycast-bin/flycast` | `-DUSE_HOST_SDL=ON -DENABLE_GDB_SERVER=ON` + `patches/flycast-gdb-send-queue.patch` | Normal SDL emulator, GDB stub available on demand. PATCHED 2026-10-15 (stop replies are no longer dropped); the original is kept as `flycast.stock`; `flycast-probe` is the same build |
| `flycast-bin/flycast-automation` | `-DUSE_HOST_SDL=ON -DTEST_AUTOMATION=ON -DENABLE_GDB_SERVER=ON` | Scripted/CI runs (muted audio, framebuffer dump, input replay, fail-fast) |
| `flycast-bin/flycast_libretro.so` | `-DLIBRETRO=ON` | Headless libretro core for AI harnesses / RetroArch |

Rebuild (build trees were in `/tmp`, gone on reboot):
```
cmake -S ../flycast -B /tmp/flycast-build -DCMAKE_BUILD_TYPE=Release \
  -DUSE_HOST_SDL=ON -DENABLE_GDB_SERVER=ON
cmake --build /tmp/flycast-build -j16
# automation: add -DTEST_AUTOMATION=ON ; libretro: -DLIBRETRO=ON instead
```

## GDB server (SH4)

Enable at runtime (no rebuild needed):
```
flycast -config config:Debug.GDBEnabled=yes,config:Debug.GDBPort=3263 <rom>
```
- `config:Debug.GDBWaitForConnection=yes` halts boot until a debugger attaches.
- Default port 3263. Verified working: booted `SABER_RIDER.cdi`, port opened,
  stub answered `$?` with `+$S02#b5` (valid GDB RSP).
- **Listener starts only when a game is actually running** (emulator Resume
  event). Closed port at the menu / with no game loaded is expected.
- Not compiled into the libretro core (use RetroArch's own debug tools there).

## `-config` key gotcha

Option names keep their `Debug.` prefix **as keys under the `[config]` section**.
Correct:
```
-config config:Debug.GDBEnabled=yes      # [config] Debug.GDBEnabled
-config config:UseReios=yes              # [config] UseReios (boot without BIOS)
-config config:rend.ThreadedRendering=no
```
So the pattern is always `-config config:<ExactKeyName>=<value>`
(use the exact key spelling from `emu.cfg` / `core/cfg/option.cpp`).
Wrong section (`-config Debug:GDBEnabled=yes`) **silently does nothing**.
- Bools accept `yes`/`no` (also `true`/`on`/`1`), saved back as `yes`/`no`.
- `-config` values are transient: applied in memory, never written to `emu.cfg`.
- Transients only apply when a config file exists/loads; first-run onboarding
  (no `~/.config/flycast/emu.cfg`) ignores them.

## Headless operation

- No X server needed with Xvfb + Mesa software rendering (llvmpipe):
  ```
  xvfb-run -a ./flycast-bin/flycast -config config:UseReios=yes game.cdi
  ```
- BIOS-less boot works via Reios (`config:UseReios=yes`); game ID + `REIOS:
  Booting up` in the log confirms the boot path.
- Truly headless (no window at all): use `flycast_libretro.so` — the frontend
  owns video/audio/input via the `retro_*` API (`retro_api_version` = 1).
- Lua scripting (`core/lua/lua.cpp`: memory R/W, input injection, frame
  callbacks) is compiled into the SDL binaries; point it at a script with
  `flycast.lua` in the config path (see `config::LuaFileName`).

## TEST_AUTOMATION mode (`flycast-automation`)

Compile-time behavior changes (`-DTEST_AUTOMATION=ON`), from `core/`:
- Audio muted; stdout/stderr unbuffered (`nullDC.cpp`).
- Each presented frame dumped as raw RGB to the file in `record:rawvid`
  (`rend/gles/gles.cpp:do_swap_automation`, also Vulkan path).
- Input replayed from the record file; when input runs out a `screenshot.png`
  is written and the process exits (`input/gamepad_device.cpp`).
- Game load failure is fatal (`die()`) instead of returning to the menu.
- 5 s watchdog: `die("Automation time-out...")` if no input events arrive.

## dcprobe: real runtime inputs through the GDB server (2026-10-15)
`tools/dcprobe.py` (also `./dcre probe ...`) drives Flycast headless under xvfb from a save state and talks to its GDB stub with a small RSP client (no gdb binary needed):
- `peek ADDR LEN`, `hot ADDR... --seconds N` (breakpoint hit counts), `profile --seconds N` (PC sampling mapped to functions.tsv: which functions a scene really executes), `capture ADDR --hits K --spec SPEC` (registers, 16 stack words, fixed spec regions and the bytes behind pointer arguments at every entry -> `work/probe/fn_<addr>.json`; autodiff replays it via the spec key `captured`).
- Verified on this machine: state 3 runs `sprite_set_pos` ~20x in 14 s, `8c07d5a8` 6 hits in a few seconds; the captured json replays as `case N (REAL game input)`.

Facts about the stock stub that dcprobe works around (all verified):
1. Only SOFTWARE breakpoints (`Z0`, the stub patches `trapa #0x20` into the code); `Z1` (hardware) answers with an empty packet. Watchpoints (`Z2-Z4`) exist. Read the original opcode BEFORE inserting a breakpoint (memory reads show the trap).
2. `c` at a breakpoint does not step over it and `s` jumps unpredictably (pc left the function): dcprobe steps over with a temporary breakpoint on the next instruction (entry instructions that are branches are refused: `thunk` functions).
3. RACE: the stub drops a stop reply that is produced while the `+` ack of the previous packet is still being written ("Message dropped: $S05#b8. Already sending: +" in the flycast log), which happens whenever a trap is one instruction away. The stock binary is handled by interrupting after 0.6 s (the target is already stopped there and answers S02). `patches/flycast-gdb-send-queue.patch` queues outgoing packets instead: build with `INPLACE=1 FLYCAST_SRC=/tmp/flycast-probe/clone tools/build_flycast_probe.sh` (needs a recursive clone: the submodule checkout has empty nested submodules) -> `third_party/flycast-bin/flycast-probe`, which dcprobe prefers. With it: 0 dropped messages, ~2 hits/s.
4. The listener is created only when a game runs; right after it opens the first connection can be reset: dcprobe retries the whole handshake.
5. States 5, 7, 8, 9 crash this build when breakpoints are armed (states 1-4 are fine); a state that crashes is reported, not hung.
6. Registers: `g` returns 59 words: r0-r15, pc(16), pr, gbr, vbr, mach, macl, sr, fpul, fpscr(24), fr0-fr15 (25-40), ssr, spc, r0-r7, bank r0-r7.
What a full Flycast fork would still add (not done): a no-window mode, deterministic time, a state-load flag, a function-override hook for in-situ tests.
