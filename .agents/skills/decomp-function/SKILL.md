---
name: decomp-function
description: START HERE for any "decompile / port / lift function at ADDRESS" task on an SH-4 (Dreamcast/Naomi) binary, or any similar RISC binary with a Ghidra export. Fixed 7-step recipe whose output is proven by an automatic emulator differential. Written for small local models; follow it literally.
---
# Decompile ONE function and prove it (game-independent)

You are done only when `python3 -I tools/dc/autodiff.py SPEC.json --mutate` prints `RESULT: PROVEN`. Any other RESULT line (NOT PROVEN) means NOT DONE, whatever the reason; do not explain it away in the report, fix it. A port that "looks right" or passes your own weak test is NOT done: in practice the first draft is wrong in strides, callee arguments or widths.

## Steps (run the commands, do not guess)
1. **Annotated asm**: `python3 -I tools/dc/sh4_annotate.py 0xADDR`. It prints the listing with literal-pool VALUES filled in (`=> r5 = 1584`), every call with its argument registers, the parameters (read-before-write r4-r7, fr4-fr7) and the loops. Everything below is derived from this output, never from memory of other functions.
2. **Classify callees** (`python3 -I tools/dc/triage.py slice 0xADDR` in the Nadesico project; elsewhere: the symbol names in the listing). Library/presentation/unported callees become **host callbacks** in the port; already-ported callees are called directly. Do not read callee bodies.
3. **Write the port** (`core/nd_<addr>.c/.h` or the project's equivalent). Rules:
   - Constants come from the `=>` literal values. A `mov.w` pool value (e.g. 1584) is a stride/size: use it exactly. NEVER substitute a stride you remember from another function.
   - Loops: the annotated `LOOPS` section lists the counter (`steps: add #1,r14`) and the compare constants (`r11=0x708`) and the exit rule. A counter stepped by `add #1` is a COUNT (iterations), not an address stride: do not merge it with a pointer/offset. Count iterations = bound unless the asm shows otherwise.
   - Replicate loop shape exactly (do-while vs while, `cmp/hs` unsigned vs `cmp/ge` signed, count = what the asm computes, not what seems natural). See skills `sh4-control-flow`, `sh4-asm-to-c`.
   - Host-callback signatures contain EVERY argument the call site sets (the CALLS table), including the first one (`r4=0x0` still counts) and float args (fr4). Pass them in register order.
   - Return type from the SIGNATURE section: if r0 is set before rts the function returns it (even a constant 0): keep it.
   - Memory the function touches is passed in as pointers (the wrapper maps retail addresses to them).
4. **Prove it**: follow skill `autodiff-sh4` (spec + 15-line wrapper). Spec rules: copy the `SUGGESTED callees` block of step 1 verbatim (it carries the float args like fr4); a memset/memcpy-like callee is NOT a callee: delete it and do the work inline; use >= 40 cases and fill `edge`/`rand` (never all-zero); a `WEAK SPEC` line or `coverage` below 100% means you are not done (the port part for unexecuted retail instructions is untested). Loop bodies: mirror the asm exactly, including WHICH address is re-read each iteration (often the same fixed address, not an indexed one). Run it. Mismatch output names the first differing call argument / byte offset: fix the PORT using that evidence, rerun. Do not edit the spec to hide a mismatch.
5. **Mutants**: `python3 -I tools/dc/autodiff.py SPEC.json --mutate` (automatic: flips comparisons, operators and constants of your port, reuses the cached retail results). Every mutant must be KILLED; a `SURVIVED` line names the file:line your inputs cannot distinguish: add inputs for it (boundary values, both branch outcomes, loop iterations) and rerun. Do not use tools/mutate.py for this.
6. **Record**: header comment with the proven facts (what autodiff covered: regions, callees, N cases), mark anything autodiff cannot show (callee meaning, names) as HYPOTHESIS.
7. **Report** with the literal `RESULT:` line of the final `--mutate` run. Never write "CONFIRMED" or "retail differential" in a comment unless step 4 printed 0 mismatches for exactly that code.

## Hard rules (each one broke an earlier attempt)
- A MISMATCH IS ALWAYS A PORT BUG (or a wrong region/callee declaration). Never delete a patch/choice/args entry because it makes the retail comparison fail: that input found your bug. Typical real bugs: reading a u8 where the asm uses `mov.w` (s16) or `mov.l`; calling a callback before vs after a compare; an indexed address where the asm re-reads one fixed address; an extra/missing call.
- autodiff keeps its case files in `work/autodiff/` inside the project (readable); never poke at /tmp/. A mismatch report already prints the args and first differing byte/call; use `--cases 3` for quick iterations.
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
