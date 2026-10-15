# Flycast builds & debug notes

Source repo: `../flycast/` (built 2026-09-23, Void Linux, GCC 14, Release).
Binaries: `./flycast-bin/`

## Binaries

| File | CMake flags | Purpose |
|---|---|---|
| `flycast-bin/flycast` | `-DUSE_HOST_SDL=ON -DENABLE_GDB_SERVER=ON` | Normal SDL emulator, GDB stub available on demand |
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
