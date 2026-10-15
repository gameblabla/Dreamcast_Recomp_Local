# Agent rules for Dreamcast_Recomp_Local (read fully; applies to opencode and Claude Code)

Goal: reverse engineer / re-implement a Dreamcast (SH-4) game function by function, with proof for every function.

## Commands (everything goes through `./dcre`; `./dcre help`)
`doctor` · `extract` · `sdk` · `import` · `export` · `status` · `next [N]` · `slice ADDR` · `annotate ADDR` · `brief ADDR` · `specgen ADDR` · `lint` · `autodiff SPEC [--mutate] [--final]` · `readmem ADDR` · `notes` · `claims` · `cc` · `discover` · `bytematch` · `permute` · `emu` · `agent ADDR`

## First thing every session
1. Skill `dc-project-setup`: `./dcre doctor`. If `project.env`/`game/`/`work/research` are missing, set them up as that skill says.
2. **SDK rule**: `./dcre sdk` must have been run. If it says the matching SDK is missing (exit 3, `ASK THE USER:`), pass that request to the user verbatim and wait.
   You may continue without the SDK only if the user says to (or declines to provide it); say what that costs (no compiler, no exact headers, fewer names, slower).

## Per function
- Pick with `./dcre next` / `./dcre slice ADDR`. Load skill `decomp-function` and follow it literally.
- Original compiler available (`./dcre cc find`, SHC from the SDK)? also skill `byte-matching`; `bytematch` prints `compiler=SHC|GCC(fallback)`, only SHC counts as a match. Always finish with skill `ub-and-old-compilers`.
- Start with `./dcre brief ADDR` (one page of facts: pointer / stack / count inputs, callees, constants, hazards), then `./dcre specgen ADDR` (spec + complete wrapper + typed port skeleton `port/fn_<addr>.c`; write only the body). The dcguard plugin shows PHASE / NEXT ACTION in your system prompt.
- Start the spec with `./dcre specgen ADDR` (never hand-write a weaker one), run `./dcre lint ADDR PORT.c --spec SPEC` before the emulator. A tail call (`TAIL` in `./dcre annotate`) hands r4-r7/fr4-fr7 to its callee: compare every register the callee reads. Details and every failure it prevents: docs/GUARDRAILS.md.
- Proof: `./dcre autodiff SPEC --final` (seed 7, 300 cases, 60 mutants, sanitizers) -> `RESULT: PROVEN`. Quote THAT line; a plain run that says PROVEN prints `NOT YET QUOTABLE`. Anything else is NOT DONE (say so, with the last RESULT line).
- Never open the game image by hand: `./dcre readmem 0xADDR [LEN]` takes the VIRTUAL address (file offset = address - 0x8c010000). The binary, the annotated listing and Ghidra agree; garbage means you used the wrong number space.
- Write each established fact: `./dcre notes add 0xADDR "fact"` / `notes tried 0xADDR "approach -> result"`; after a context summary run `./dcre notes show 0xADDR` first. The `.opencode/dcguard` plugin re-injects this file, the skill and the notes into every request and blocks repeated/invented commands.
- `PORT RUN ABORTED` / hang = an unbounded count argument, not the emulator: add the `"arg_limits"` line autodiff prints.
- Run an agent with the watchdog: `./dcre agent 0xADDR` (resumes the same session on output-limit loops and stalls; report in work/agent/).

- `./dcre claims` must list nothing: never write CONFIRMED/PROVEN without a PROVEN ledger entry. `AD_ALLOW_WEAKER` is for humans.
- Never weaken a spec, change seeds/case counts, or delete an input to make a mismatch disappear. A mismatch is a port bug.
- Name the file with the address (`port/fn_8cXXXXXX.c`) so `./dcre status` counts it. Mark facts CONFIRMED (proven by a tool line) vs HYPOTHESIS.

- Skills live in `.agents/skills/` (`.opencode/skills` and `.claude/skills` are symlinks). Edit them there.

- An emulator/autodiff run silent for >10 min is a hang, not slowness. Each case now has a wall-clock limit (`ND_CASE_MS`, default 120 s) and fails with a FAULT hint; stub addresses (`skip=`, `callog=`, `callees`) are HEX. Do not re-run a hung job unchanged.

## Hygiene
- Trust the asm (`./dcre annotate`) over Ghidra's decompile for params, widths, signs, strides, delay slots, loop shapes.
- Read targeted (grep/head/sed -n); never print whole dumps. Temporaries in `work/` or `work/autodiff/`.
- Never commit `game/`, `work/`, `project.env`, SDK files, `third_party/flycast-bin`. Do not `git commit` unless asked.
- Ghidra project is locked while another headless job uses it; autodiff uses a private copy so it is safe to run in parallel.
- Round 4 (research-driven; docs/RESEARCH_NOTES.md in Dreamcast_Recomp_Local): `attempts.py list|best|restore ADDR` (autodiff snapshots every run, best kept), plugin supplies a DETERMINISTIC compaction summary (notes, ledger scores, failing commands, history) instead of a model-written one, `STALLED` steering, brief sections SIMILAR PORTED FUNCTIONS / HOW CALLERS PASS THE ARGUMENTS / GHIDRA DECOMPILE / SPECIAL OPCODES, and index vs pointer classification (a parameter that is shifted/multiplied or added to a table base is an INDEX, not a pointer).
- Round 5 (Mizuchi review, details in Dreamcast_Recomp_Local/docs/RESEARCH_NOTES.md): every tool result ends with `[dcguard] calls N/220 | phase | next`, shell output is capped at 7000 chars, a hard call limit forces the final report; `agentrun.py` has a soft deadline (75%), gives up early when 6 autodiff runs in a row do not beat the best (`--stall-runs`), and can resume with a stronger model (`--escalate provider/model`); `rank.py` (`./dcre rank`) picks the next function by difficulty x similarity.
- Round 6 (Mizuchi behavioural check + Flycast): autodiff compares the retail STORE SEQUENCE (spec `write_trace`, on in generated specs; the emulator script logs every store with a MemoryAccessFilter, the port logs `ad_wr8/16/32`), and `dcprobe.py` (`./dcre probe`) captures real arguments/stack/pointer bytes from Flycast save states through its GDB server; the spec key `captured` replays them as extra cases. `patches/flycast-gdb-send-queue.patch` + `tools/build_flycast.sh` fix the stub's dropped stop replies. See Dreamcast_Recomp_Local/docs/FLYCAST_NOTES.md (dcprobe section) for what works and the stub's quirks.
