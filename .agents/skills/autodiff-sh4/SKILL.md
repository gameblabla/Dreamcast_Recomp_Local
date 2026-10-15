---
name: autodiff-sh4
description: Prove a C port of ONE SH-4 function equals the retail code by running both on random/boundary inputs (Ghidra SH-4 emulator vs your C). Needs only a JSON spec and a 15-line wrapper, no Python harness. Use after writing any port, before claiming it is correct.
---
# autodiff: retail function vs your C port

`python3 -I tools/dc/autodiff.py SPEC.json [--mutate [N]] [--final]` (takes ~20 s - 1 min; Ghidra project must be imported). `--final` = the judge run to quote: seed 7, >= 300 cases, >= 60 mutants, UBSan/ASan; a plain PROVEN prints `NOT YET QUOTABLE`. Do not use `--seed` (seed hunting) or small `--cases`.
Needs >= 40 cases and non-zero fills; a `WEAK SPEC` warning/tag in the summary means the proof is void.
Last line is the verdict: `RESULT: PROVEN` or `RESULT: NOT PROVEN -- reasons`. PROVEN requires: 0 mismatches, 0 faults, 100% retail-instruction coverage, spec not weak, AND a clean `--mutate` run. Always run it as `... SPEC.json --mutate`.
Prints `autodiff <addr>: N cases, M mismatches, F faults` plus the first differing case. Exit 0 only if M=F=0.

## Mutation check
`--mutate [N]` re-runs the cached retail results against N automatically mutated copies of your port sources (comparison/operator/constant flips). All must be killed.

## Coverage gate (read this)
autodiff also prints `coverage: K/N retail instructions executed`. Every retail instruction that NO case executed is listed under `WEAK SPEC ... NEVER executed` and the run exits 1: the matching part of your port is untested (a wrong loop body passes silently if the loop never iterates). Make the inputs reach those instructions: look at the compare/branch right before the first listed address and choose region contents / args that flip it. `fill: image` is usually all zeros for RAM tables: use `edge`/`rand` plus `patch`/`word_choice` so counters, flags and compared values take BOTH outcomes, and loops iterate more than once and also hit their exit. Only unreachable trap paths go in `allow_uncovered`.

## What it compares (all of it, per case)
return value (r0) | every stubbed callee call IN ORDER with its args (ints = r4.., floats = fr4.. bit patterns) | the final bytes of EVERY declared memory region.
That catches: wrong stride/count/width, dropped or reordered callee args, wrong return value, extra/missing stores, wrong signedness.

## 1. Spec (copy `examples/spec_06fefe.json`, edit)
- `func`: hex address. `port.wrapper`: your wrapper .c. `port.sources`: port .c files (+ `core/nd_f32.c` if used). `port.include`: dirs with your headers.
- `regions`: every address range the function reads or writes (find them in the annotated listing: the `=>` literal values that are used as pointers; add `len` = highest offset touched + width; a table walked by a loop: loop count * stride). `fill`: `edge` (default; word-aware boundary values, `rand` is an alias), `zero`, `image`, `rawrand` (real bytes from the binary: use for read-only tables/constants). Use `word_choice` to give a counter/bound/pointer word specific values (`[-1,0,1,N-1,N,N+1]`), `patch` for single bytes (flags: `[0,1,255]`).
- `args`: per register `[v1,v2,...]` | `"rand"` | `{"range":[lo,hi]}`; floats as `fr4: [bit patterns]`. Aim at boundaries (index = -1, 0, count-1, count), otherwise `>` vs `>=` mutants survive.
- `callees`: paste the `SUGGESTED autodiff callees` block printed by `sh4_annotate.py` (it counts int AND float argument registers; hand-counting dropped fr4 floats before). Each `jsr` target that is NOT run for real: `{"addr","ints":<how many of r4.. the call passes>,"floats":<fr4.. count>,"ret":[values returned in r0, in call order]}`. Take counts from the CALLS table of `sh4_annotate.py`. Its `ret` list matters if the function branches on the result.
- `real`: callees that should run as real retail code (memset/memcpy/strlen): your port then does that work inline and must NOT log a call for them. (Informational: anything not listed under `callees` runs for real.)
- `check_ret`: false for void functions.

## 2. Wrapper (copy `examples/wrapper_06fefe.c`, edit)
```c
#include "autodiff.h"      // ad_regs, ad_mem, ad_rd32, ad_call
#include "nd_xxxxxx.h"
void ad_wrapper(ad_regs *c) {
    // c->r[4..7], c->fr[4..11] = the retail arguments of this case
    // ad_mem(0x8c23e914) = host pointer to retail address 0x8c23e914 (inside a declared region)
    // host callbacks MUST call ad_call(callee_addr, ints, n_ints, floats, n_floats) with the SAME values the retail call passes
    // c->ret = value of r0 on return
}
```
For port-side host callbacks write one tiny function per callee that calls `ad_call` and returns its result (`ad_call` returns the spec's scripted `ret`). A callee whose retail args include a pointer argument: pass the retail ADDRESS (`0x8c259e54`) as the logged value, not the host pointer.

## 3. Reading failures
- `call log differs at call #k: retail=C8c103248=0,8, port=C8c103248=8,` -> your callback drops/reorders an argument (retail passes r4=0,r5=8).
- `first differing byte at offset 0xd3` -> divide by the stride you used; compare with the annotated literal (211 = 0x84 + 0x4f means you used stride 0x84, the asm says 0x630).
- `return value: retail r0=ffffffff port=0` -> a path you missed (usually a bounds check or sign).
- `FAULT` -> retail touched memory outside the declared regions, or called an undeclared function; add it to the spec.
- Mismatch only in some cases -> the condition differs at a boundary: print which args (shown) and re-read the compare instruction (`cmp/ge` signed, `cmp/hi|hs` unsigned, `cmp/pz|pl`).
Never "fix" a mismatch by loosening the spec or the wrapper unless the asm proves the stub/region is wrong.

## Notes
autodiff runs the emulator on a private copy of the Ghidra project (`work/autodiff/ghidra_proj`), so it never clashes with other Ghidra jobs; scratch files live in `work/autodiff/` (git-ignored).

## Limits (say so in notes, mark HYPOTHESIS)
Stubbed callees are not executed (their side effects on memory are not modelled; if the retail code reads memory a callee writes, use `real` or a scripted `ret`). Randomised inputs prove behaviour only on the explored region/args.


## New in this version (read once)
- Phases are printed (`[autodiff] phase 1/3 ... 3/3`); a silent run is a hang only after 10 minutes.
- `PORT RUN ABORTED: AD_LOOP_BOUND/AD_CASE_TIMEOUT case=N` = a count-like argument is huge. autodiff names the argument (`BISECTED: ... r7 is the loop COUNT`) and the line to add: `"arg_limits": {"r7": [-2, 24]}`. The port is not wrong and the emulator is not slow.
- `SPEC LINT ERROR ... overlaps the retail function itself`: a region covers the function's code/literal pool; remove it (constants are read from the image).
- The ledger records `final`; `proofcheck.py` accepts a claim only after a PROVEN `--final` run on an unchanged port.
