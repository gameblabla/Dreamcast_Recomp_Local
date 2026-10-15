# Agent rules for Dreamcast_Recomp_Local (read fully; applies to opencode and Claude Code)

Goal: reverse engineer / re-implement a Dreamcast (SH-4) game function by function, with proof for every function.

## Commands (everything goes through `./dcre`; `./dcre help`)
`doctor` · `extract` · `sdk` · `import` · `export` · `status` · `next [N]` · `slice ADDR` · `annotate ADDR` · `autodiff SPEC --mutate` · `cc` · `discover` · `bytematch` · `permute` · `emu` · `agent ADDR`

## First thing every session
1. Skill `dc-project-setup`: `./dcre doctor`. If `project.env`/`game/`/`work/research` are missing, set them up as that skill says.
2. **SDK rule**: `./dcre sdk` must have been run. If it says the matching SDK is missing (exit 3, `ASK THE USER:`), pass that request to the user verbatim and wait.
   You may continue without the SDK only if the user says to (or declines to provide it); say what that costs (no compiler, no exact headers, fewer names, slower).

## Per function
- Pick with `./dcre next` / `./dcre slice ADDR`. Load skill `decomp-function` and follow it literally.
- Original compiler available (`./dcre cc find`, SHC from the SDK)? also skill `byte-matching`; `bytematch` prints `compiler=SHC|GCC(fallback)`, only SHC counts as a match. Always finish with skill `ub-and-old-compilers`.
- Proof: `AD_SANITIZE=1 ./dcre autodiff SPEC --mutate` -> `RESULT: PROVEN`. Quote that line in your report. Anything else is NOT DONE.
- Never weaken a spec, change seeds/case counts, or delete an input to make a mismatch disappear. A mismatch is a port bug.
- Name the file with the address (`port/fn_8cXXXXXX.c`) so `./dcre status` counts it. Mark facts CONFIRMED (proven by a tool line) vs HYPOTHESIS.

- Skills live in `.agents/skills/` (`.opencode/skills` and `.claude/skills` are symlinks). Edit them there.

- An emulator/autodiff run silent for >10 min is a hang, not slowness. Each case now has a wall-clock limit (`ND_CASE_MS`, default 120 s) and fails with a FAULT hint; stub addresses (`skip=`, `callog=`, `callees`) are HEX. Do not re-run a hung job unchanged.

## Hygiene
- Trust the asm (`./dcre annotate`) over Ghidra's decompile for params, widths, signs, strides, delay slots, loop shapes.
- Read targeted (grep/head/sed -n); never print whole dumps. Temporaries in `work/` or `work/autodiff/`.
- Never commit `game/`, `work/`, `project.env`, SDK files, `third_party/flycast-bin`. Do not `git commit` unless asked.
- Ghidra project is locked while another headless job uses it; autodiff uses a private copy so it is safe to run in parallel.
