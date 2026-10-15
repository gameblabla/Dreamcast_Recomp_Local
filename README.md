# Dreamcast_Recomp_Local

A self-contained toolkit for **reverse engineering, matching decompilation and behaviour-verified re-implementation of Dreamcast (SH-4) games**,
built so that a **local AI agent (opencode + a local model)** can do the function-by-function work and *prove* each result, with a human supplying
only the disc image and (ideally) the SDK.

It contains no game code, data or SDK. Everything game-derived is generated from your own disc into `game/` and `work/` (git-ignored).

## 1. Quick start

```bash
git clone --recurse-submodules <this repo> && cd Dreamcast_Recomp_Local     # or: git submodule update --init
cp project.env.example project.env && $EDITOR project.env                    # DISC=... SDK_DIRS=...
./dcre doctor           # what is installed / missing
./dcre extract          # disc -> game/1ST_READ.BIN   (add --boot-only to skip the other ~1 GB of files)
./dcre sdk              # which SDK + compiler built the game? do you have it? (asks you for it if not)
./dcre import           # Ghidra project + full export (several minutes)  -> work/research/
./dcre status           # what is left
./dcre next 20          # cheapest functions that are ready (callees first)
./dcre agent 0x8c06fac4 # local opencode agent ports ONE function and proves it
```

### Pointing it at your disc (`DISC`)
`DISC` in `project.env` may be:
- a **`.gdi`** (GD-ROM dump, tracks listed in the file) — preferred;
- a **`.cue`** with its `.bin` tracks (the common Redump layout; the high-density track starting at LBA 45000 is detected automatically);
- a **`.iso`** (self-boot CD/CDI-converted) or a **folder** that already contains `1ST_READ.BIN`.
`.cdi`, `.mds`, `.chd` must be converted first (`cdi2iso`, `mdf2iso`, `chdman extractcd`). Sector sizes 2048 and raw 2352 (Mode 1/2) are handled.
The boot executable is written to `game/1ST_READ.BIN` (load address `0x8C010000`, set `DR_BASE` if yours differs).

### Pointing it at your SDKs (`SDK_DIRS`)
`SDK_DIRS="/path/DREAMCAST SDK Ver 1.42J:/path/Dreamcast SDK for Sega Library Ver.1.00J"` — folders, `.iso` or `.zip`, any number, `:`-separated.
Recommended: **Katana SDK R1.42J** and **1.00J** (what the Nadesico example used), plus whatever release your game actually needs. `./dcre sdk`:
1. reads the library banners in your game and ranks public SDK releases by how many of the game's library builds they contain;
2. scans your `SDK_DIRS` for the matching release, the Hitachi compiler (`shc.exe`, `asmsh.exe`, `lnk.exe`), `.lib` libraries and headers;
3. if the exact release is missing it prints **`ASK THE USER: please give me a copy of the Dreamcast SDK <release> ...`** and exits with code 3.
No SDK copy? `./dcre export` then runs `libtriage` automatically (docs/SDKS.md). You *can* continue without it (naming by signatures from other releases, behaviour-only work), but it takes much longer: no original compiler means
no byte-matching, no exact headers/structs, fewer library names. Agents must ask before proceeding (skill `dc-project-setup`).

## 2. What is in here

| path | what |
|---|---|
| `dcre` | single entry point (`./dcre help`) |
| `tools/disc_extract.py` | .gdi/.cue/.iso -> files, stdlib only |
| `tools/sdk_detect.py` | SDK release + compiler fingerprinting, asks for missing SDKs |
| `ghidra/scripts/Dr*.java` | headless Ghidra: SH-4/Dreamcast memory map + MMIO (`DrSetup`), missed-code discovery (`DrFindCode`), SDK signature naming (`DrSdkRename`), curated names (`DrNames`), literal-pool constants (`DrConst`), asm/C/callgraph/strings dump (`DrDump`), FPSCR calling-convention fix (`DrFpscrConv`), SH-4 emulator for tests (`DrEmu`) |
| `tools/sh4_annotate.py` | listing with literal-pool **values**, per-call argument registers, signature, loop counters/bounds |
| `tools/sdk_index.py` | builds a local relocation-tolerant signature table from your SDK libs (hashes/names only; libs deleted after use) |
| `tools/sdk_headers_strip.py`, `include/` | stripped SDK headers (declarations only) |
| `tools/libtriage.py` | no-SDK fallback: marks linked library code (callee closure + same-module runs from the few exact CRC matches) so it is not decompiled; skipped when the exact SDK is present |
| `tools/triage.py` | classify functions (sdk/lib/hw/done/todo) and pick the next ready one |
| `tools/autodiff.py` + `tools/autodiff/` | **retail vs your C** differential in the Ghidra SH-4 emulator: return value, callee calls in order, all memory; coverage gate; automatic mutants; `RESULT: PROVEN` |
| `tools/bytematch.py`, `tools/permute.py` | compare compiled C with retail bytes; small source permuter |
| `tools/flycast_run.sh` | run flycast headless (xvfb, isolated config, GDB stub) |
| `third_party/dc-re-ghidra` | submodule: SDK symbol table (`sdk-symbols.txt`) + the original `DreamcastRE.java` |
| `third_party/flycast` | submodule: flycast source (pinned) |
| `third_party/flycast-bin/` | precompiled headless flycast copies (`flycast`, `flycast-automation`, `flycast_libretro.so`); not in git, see docs/FLYCAST.md |
| `skills/` | verbatim copies of the existing skills: `dc-decomp-kickoff` (SHC matching build, SDK scanning, asm split), `dcrecomp` (SH-4->C recompiler oracle), `skmp-sh4-fpu` (bit-exact FIPR/FTRV/FSCA models) |
| `.claude/skills/` | what agents load (opencode and Claude Code both read this folder): `dc-project-setup`, `decomp-function`, `autodiff-sh4`, `byte-matching`, `ub-and-old-compilers`, `sh4-*` references, and links to `skills/*` |
| `docs/` | WORKFLOW, BYTE_MATCHING, UB_AND_OLD_COMPILERS, SDKS, GHIDRA_SH4_FPU, FLYCAST (+ the saved Ghidra SH-4 float notes) |
| `AGENTS.md`, `opencode.json` | agent rules; example local-model config |

## 3. Advice (the short version)

- **Prefer byte-matching** when the original compiler is available: equality of bytes is the strongest possible proof. `docs/BYTE_MATCHING.md`.
- **Ask for the SDK first.** Detect it (`./dcre sdk`), ask the user for the exact release, and only then decide to go on without it.
- **A match is not a port.** Automatic permutation ("guess until it matches") reaches matching but not meaning, and old compilers exploit UB that
  modern compilers do not tolerate. Always run `AD_SANITIZE=1 ./dcre autodiff SPEC --mutate` and review the UB checklist (`docs/UB_AND_OLD_COMPILERS.md`).
- **Trust the asm over the decompiler** for parameter meaning, widths, signs, strides and delay slots. Use `./dcre annotate ADDR`.
- **Proof or it did not happen**: a function is finished only when `autodiff` prints `RESULT: PROVEN` (and, if you matched, `BYTEMATCH ... EXACT|NORMALIZED`).
- SH-4 floats in Ghidra look awful until FPSCR is pinned: `./dcre export` applies the fix (`docs/GHIDRA_SH4_FPU.md`).
- Disk: a disc is ~1 GB, the Ghidra project ~40 MB, `work/research` ~50 MB. `--boot-only` extraction avoids the rest.

## 4. Running the local agent
`opencode.json` points opencode at a local OpenAI-compatible server (`http://127.0.0.1:8080/v1`, e.g. llama.cpp). `./dcre agent 0xADDR` runs
`opencode run` on one function with the `decomp-function` skill; expect 20-60 min for a leaf and 1-2 h for harder functions with a 27B local model.
In trials (Nadesico), simple functions were proven; the hardest (float + tail call + indirect table) needed more time — the tools refuse to say
`PROVEN` until coverage, mutants and behaviour all agree, so a stuck agent reports honestly instead of claiming success.

## 5. Legal
Bring your own disc and SDK. Nothing here downloads or redistributes copyrighted material; the SDK release lists in `skills/dc-decomp-kickoff/references/`
are search terms only. Never commit game data, SDK files, `work/` or `project.env`.
