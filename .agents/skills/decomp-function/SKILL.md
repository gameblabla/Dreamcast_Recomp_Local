---
name: decomp-function
description: START HERE for any "decompile / port / lift function at ADDRESS" task on an SH-4 (Dreamcast/Naomi) binary, or any similar RISC binary with a Ghidra export. Fixed 7-step recipe whose output is proven by an automatic emulator differential. Written for small local models; follow it literally.
---
# Decompile ONE function and prove it (game-independent)

You are done only when `python3 -I tools/dc/autodiff.py SPEC.json --final` prints `RESULT: PROVEN` (the judge run: fixed seed 7, 300 cases, 60 mutants, sanitizers; a plain run that says PROVEN is only PROVISIONAL and prints `NOT YET QUOTABLE`). Any other RESULT line (NOT PROVEN) means NOT DONE, whatever the reason; do not explain it away in the report, fix it. A port that "looks right" or passes your own weak test is NOT done: in practice the first draft is wrong in strides, callee arguments or widths.

## Steps (run the commands, do not guess)
1. **Annotated asm**: `python3 -I tools/dc/sh4_annotate.py 0xADDR`. It prints the listing with literal-pool VALUES filled in (`=> r5 = 1584`; for `mova pool,r0` + `fmov.s @r0,fr3` the FLOAT: `; => fr3 = -8192f (0xc6000000) [literal at 8c04ca18]`), every call with its argument registers, the parameters (read-before-write r4-r7, fr4-fr7) and the loops. Everything below is derived from this output, never from memory of other functions.
2. **Classify callees** (`python3 -I tools/dc/triage.py slice 0xADDR` in the Nadesico project; elsewhere: the symbol names in the listing). Library/presentation/unported callees become **host callbacks** in the port; already-ported callees are called directly. Do not read callee bodies.
3. **Write the port** (`core/nd_<addr>.c/.h` or the project's equivalent). Rules:
   - Constants come from the `=>` literal values. A `mov.w` pool value (e.g. 1584) is a stride/size: use it exactly. NEVER substitute a stride you remember from another function.
   - Loops: the annotated `LOOPS` section lists the counter (`steps: add #1,r14`) and the compare constants (`r11=0x708`) and the exit rule. A counter stepped by `add #1` is a COUNT (iterations), not an address stride: do not merge it with a pointer/offset. Count iterations = bound unless the asm shows otherwise.
   - Replicate loop shape exactly (do-while vs while, `cmp/hs` unsigned vs `cmp/ge` signed, count = what the asm computes, not what seems natural). See skills `sh4-control-flow`, `sh4-asm-to-c`.
   - Host-callback signatures contain EVERY argument the call site sets (the CALLS table), including the first one (`r4=0x0` still counts) and float args (fr4). Pass them in register order.
   - Return type from the SIGNATURE section: if r0 is set before rts the function returns it (even a constant 0): keep it.
   - Memory the function touches is passed in as pointers (the wrapper maps retail addresses to them).
4. **Prove it**: start from the GENERATED spec: `python3 -I tools/dc/specgen.py 0xADDR` writes `port/tests/spec_<addr>.json` (args "auto" = boundary values from the asm, regions >= 8 strides filled with varied bytes, every callee incl. TAIL calls with ints 4) and a wrapper skeleton. Only ADD to the generated spec; autodiff keeps a ledger (`work/proofs/`) and refuses a spec weaker than an earlier run. Before the emulator run: `python3 -I tools/dc/portlint.py 0xADDR port.c --spec SPEC.json` (constants the asm loads but the port lacks, missing widths, wrapper/spec mismatch). Follow skill `autodiff-sh4` for the wrapper. Spec rules: the `SUGGESTED callees` block of step 1 is already in the generated spec (it carries the float args like fr4); a memset/memcpy-like callee is NOT a callee: delete it and do the work inline; use >= 40 cases and fill `edge`/`rand` (never all-zero); a `WEAK SPEC` line or `coverage` below 100% means you are not done (the port part for unexecuted retail instructions is untested). Loop bodies: mirror the asm exactly, including WHICH address is re-read each iteration (often the same fixed address, not an indexed one). Run it. Mismatch output names the first differing call argument / byte offset: fix the PORT using that evidence, rerun. Do not edit the spec to hide a mismatch.
5. **Mutants**: `python3 -I tools/dc/autodiff.py SPEC.json --mutate` (automatic: flips comparisons, operators and constants of your port, reuses the cached retail results). Every mutant must be KILLED; a `SURVIVED` line names the file:line your inputs cannot distinguish: add inputs for it (boundary values, both branch outcomes, loop iterations) and rerun. Do not use tools/mutate.py for this.
6. **Record**: header comment with the proven facts (what autodiff covered: regions, callees, N cases), mark anything autodiff cannot show (callee meaning, names) as HYPOTHESIS.
7. **Report** with the literal `RESULT:` line of the final `--mutate` run. Never write "CONFIRMED" or "retail differential" in a comment unless step 4 printed 0 mismatches for exactly that code.

## Hard rules (each one broke an earlier attempt)
- TAIL CALL (`jmp @rN` to another function; step 1 prints `TAIL`): the callee gets r4-r7 and fr4-fr7 as they are at the jmp, including registers the caller never set (inherited) and registers set on only one path. The spec compares `ints: 4`, the wrapper reports all four with `ad_call`, the port's callback receives all of them. autodiff prints `UNCHECKED CALLEE ARGUMENT` when a register that varies between cases is not compared; fix it by comparing it, never by `ignore_args` unless the callee's own asm does not read that register.
- Shared library sources (nd_f32.c etc.) in `port.sources` are NOT mutated by autodiff (one function cannot exercise a whole library); only the file named after the function is (override: `port.mutate`). Do not chase their mutants.
- Values read from a table and then used as an index/pointer (s16 ids, counts) must be constrained with `patch`/`word_choice` to sane ranges, or the retail code and your wrapper walk outside the declared regions (`outside every declared region` is a spec problem, not a port bug).
- `python3 -I tools/dc/proofcheck.py` lists every CONFIRMED/PROVEN claim that has no `RESULT: PROVEN` ledger entry (or whose port changed afterwards). Do not write such claims.
- A MISMATCH IS ALWAYS A PORT BUG (or a wrong region/callee declaration). Never delete a patch/choice/args entry because it makes the retail comparison fail: that input found your bug. Typical real bugs: reading a u8 where the asm uses `mov.w` (s16) or `mov.l`; calling a callback before vs after a compare; an indexed address where the asm re-reads one fixed address; an extra/missing call.
- autodiff keeps its case files in `work/autodiff/` inside the project (readable); never poke at /tmp/. A mismatch report already prints the args and first differing byte/call. A normal run takes ~20 s: always use the default case count (the plugin refuses `--cases` below 40).
- Surviving mutants are NOT "statistically similar": each one is an input your spec lacks. Add it.
- Keep the default `edge` fill for big tables; it is word-aware and already hits ==0/==0xfe/negative/max. Add `args`, `word_choice`, `patch` on top, never instead.
- Do not trust a width/offset you did not read in the annotated listing: `mov.b`=8-bit signed, `mov.w`=16-bit signed, `mov.l`=32-bit, `extu.b/w` unsigned.

- NEVER change `--seed`, lower `--cases`, or shrink/narrow the spec to make a mismatch disappear (seed hunting is cheating: the mismatch exists for other seeds too). The mismatch report prints `retail control-flow jumps`: the addresses where the retail code branched. Open the annotated listing at those addresses and mirror that exact order of compare / call / store.
- Off-by-one in call counts ("port made 2, retail 1") almost always means the asm compares BEFORE the call you placed first in a loop; re-read the loop entry address in the listing (loops are often entered in the middle).

## Stop rules
- If the same command fails 3 times, stop and report what failed instead of trying variations; never spend more than 5 calls on a tool you do not understand (read its `--help`/docstring once).
- Max ~25 tool calls per function. If autodiff FAULTs ("outside the declared regions"): add the missing region/callee to the spec (the FAULT message and the listing's pool addresses tell which). If a function has more than ~6 callees or a huge switch, port the state part and host-callback the rest; say so in the report.
- Floats: values are raw uint32 bit patterns (`0x3f800000` = 1.0f). Use `nd_f32_*` helpers if the project forbids C floats (check AGENTS.md).
- Do not `git commit` unless the task says so. Temporary files go to the scratchpad/tmp, not the repo.

## Commands that exist (exhaustive; anything else does not exist: do not invent tools or flags)
`python3 -I tools/dc/` + `sh4_annotate.py ADDR` | `specgen.py ADDR` | `portlint.py ADDR PORT.c --spec SPEC` | `autodiff.py SPEC [--mutate [N]] [--final] [--keep]` | `readmem.py ADDR [LEN] [--as f32|u32|s16..]` | `notes.py add|tried|show ADDR [text]` | `triage.py slice ADDR` | `dcfacts.py ADDR` | `proofcheck.py`. In the Local toolkit the same through `./dcre annotate|specgen|lint|autodiff|readmem|notes|slice|facts|claims`. There is NO `disasm`, NO `--build-only`, NO `nd_golden.py` for you. Unsure about a flag: run the tool with `--help` ONCE.

## Facts about the data (never doubt these; doubting them cost 70 tool calls once)
- The retail binary, the annotated listing and Ghidra's import are all CORRECT and consistent. If a value looks like garbage (NaN, wrong pointer), YOU used a wrong number space: the file offset of an address is `address - 0x8c010000` (not its low bits). Look at it with `readmem.py 0x8cXXXXXX` (takes the full virtual address) or read the `=>` values in the annotated listing. Never open 1ST_READ.BIN with python/xxd/dd.
- `mova pool,r0` then `fmov.s @r0,frN` / `mov.l @r0,rN` loads the VALUE stored at the pool address ONCE. The port uses that value as a number (e.g. `0xc6000000` as a float bit pattern). It never reads the pool address at run time, never declares a spec region over the function's own code/pool (autodiff refuses it), never dereferences the value again.
- The port prints nothing (no printf/fprintf), including while debugging: the mismatch report and `retail control-flow jumps` are your debugger.

## Notes survive context compaction; your memory does not
Your context WILL be summarised during a long run and facts disappear. After EVERY established fact or finished experiment run `python3 -I tools/dc/notes.py add 0xADDR "fact"` (calling convention, struct field, constant, "div_s32: dividend r1, divisor r0") or `notes.py tried 0xADDR "what I tried -> result"`. When you see a summary or feel lost: `notes.py show 0xADDR` FIRST, do not re-derive. The dcguard plugin re-injects AGENTS.md, this skill and the notes into every request, and blocks an identical command repeated on unchanged files.

## If `autodiff` prints `PORT RUN ABORTED` / hangs / FAULTs on a time limit
It is NOT the emulator. A count/length argument (digit_count, n, size) got a huge generated value, so the loop runs for ever (retail and port alike). autodiff bisects the culprit argument and prints the exact line to ADD to the spec: `"arg_limits": {"r7": [-2, 24]}` (real domain of that argument; coordinates, pointers and ids stay unlimited). Add it, rerun. Do not lower cases, do not change the seed, do not wait.

## Pitfalls seen in real runs of the local model (each cost many calls)
1. Reading the .BIN at the wrong offset -> "binary is corrupt" -> patching pointers in the spec. (Use readmem.py. See Facts.)
2. `ad_rd32(ad_rd32(0x8c04ca18))` / reading literal pools at run time / a spec region over the function's own code. (portlint and autodiff now refuse these.)
3. The same failing command 14-45 times. After 2 failures of one approach: `notes.py tried`, then change approach or report NOT DONE.
4. A reply that repeats one paragraph until the output limit. Think in <=10 lines, then ACT with a tool.
5. Blaming the emulator for a hang that was a huge loop-count argument (see above).
6. Re-deriving a known fact after a context summary (use notes.py show).
7. Inventing tools/flags (`dcre.py disasm`, `--build-only`).
8. Trusting a provisional PROVEN: boundary mutants at table ends survive a different seed. Always finish with `--final`; a survivor there names the table end/constant your spec lacks (patch/word_choice at BOTH ends).

## Report format
`STATUS: PROVEN|NOT DONE`, the literal last `RESULT:` line of the `--final` run (or the last RESULT line you have), what autodiff covered, HYPOTHESES (callee meanings, names). NOT DONE is an acceptable, honest answer; a claim without the literal RESULT line is a failure.
