---
name: sh4-lift-verify
description: Game-independent workflow for lifting an SH-4 function to C and proving it equal to the original by running the original in an emulator on generated inputs (differential testing + mutants). Use when starting any SH-4 decompilation/port, or when a lift keeps mismatching.
---
## Pipeline
1. **Triage** functions into rules (state/logic), presentation (camera, UI, draw), SDK/library (identify by signature/address; never port), data. Bottom-up: leaves first, then callers.
2. **Read** the asm (sh4-asm-to-c, sh4-control-flow, sh4-abi-and-structs). Write the argument/register/field table in your notes BEFORE any C.
3. **Lift literally** into C with explicit-width types and a host-callback struct for every callee you will not port (record: call order, args, returns). Keep the original basic-block order; do not "clean up" yet.
4. **Differential**: run the retail function in an SH-4 emulator (Ghidra SLEIGH emulator, Flycast, or unicorn/QEMU-SH4) on N generated states: set arg regs + memory, stub callees (immediate return with scripted values, log args), run to return, read back registers/memory/call log. Run the C lift on the same states. Compare: return value, every written byte, callee call sequence and args. One summary line: `N cases, M mismatches, F faults`.
5. **Fix the port, not the harness**, in this order of suspects: (1) delay-slot effect missed, (2) operand order of cmp/sub/fsub, (3) load sign/zero extension, (4) `cmp/hs` unsigned vs `cmp/ge`, (5) literal `mov.w` sign extension, (6) shift arithmetic vs logical or signed-division rounding, (7) struct stride/offset, (8) callee actually writes the state you ignored (promote it from presentation to rules), (9) stub returned a value the real callee never returns (scripted sequence wrong).
6. **Bias generators to boundaries** (thresholds +-1, 0, 255->0 wraps, ids at table end, exact-tie rolls, NaN/inf/denormal floats). Random bytes alone leave comparison off-by-one mutants alive.
7. **Mutate** the lift (flip each comparison, constants +-1, swap call order, drop guards). All must be killed or documented equivalent.
8. **Freeze** vectors (inputs + retail outputs) into a text file checked by a plain C test so CI needs no emulator. Unknown or malformed vector lines must fail.
9. **Document** CONFIRMED / HYPOTHESIS / OPEN, retail quirks preserved (reads past end, constant stack garbage), and names with confidence marks.

## Emulator harness checklist
- Memory map: code image at its link base (Dreamcast 1ST_READ.BIN at 0x8C010000), RAM mirror 0x8C000000..0x8D000000, stack near the top, a return-sentinel address with a breakpoint.
- Set `PR` to the sentinel so `rts` ends the run. Initialise r15. Pass stack args at `@r15`.
- Hardware registers/MMIO reads in a rules function mean it is not pure: stub or mark as platform.
- FPSCR: set the same mode the game runs in (PR=0, SZ=0, RM=nearest, DN as the game's init sets it).
- Cap instruction count; a FAULT/timeout is a harness bug or a bad generated state, count it and keep it below 1%.
- Compare writes by diffing a memory snapshot of the touched region, not only the fields you expect.

## Decompiler use
Ghidra/IDA output is for control-flow shape and finding callees. Never take parameter count, types, signedness or field widths from it; it merges `extu`-less byte loads into wrong types and drops delay-slot argument setup. Where it disagrees with the asm, the asm wins (and the emulator wins over your reading of the asm).

## Matching-decompilation (byte-exact rebuild) note
If the goal is a bit-identical rebuild rather than a behavioural port, also identify the compiler (SHC/Hitachi vs GCC) from prologue style and library calls, set the original optimisation flags, and iterate on C shape against a diff of the assembly; `references/` has matching examples. A behavioural port (this project) does not need that.


## Tools (game-independent, in tools/dc/)
- `sh4_annotate.py ADDR`: listing with literal-pool values, per-call argument table, parameter/return recovery, loop list.
- `autodiff.py SPEC.json`: automatic emulator-vs-C differential (skill `autodiff-sh4`); the end-to-end procedure is skill `decomp-function`.
