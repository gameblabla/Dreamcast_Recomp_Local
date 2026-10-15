---
name: sh4-abi-and-structs
description: Recovering function signatures, stack frames, globals, struct layouts and arrays-of-struct strides from SH-4 asm (Dreamcast Shinobi/KallistiOS/SHC/GCC code). Use before declaring a C prototype or struct for any SH-4 function.
---
## Calling convention (SH GCC/SHC "standard"; confirm once per binary with 2-3 callers)
- Int/pointer args r4,r5,r6,r7; more args on the stack at `@(0,r15)`, `@(4,r15)` of the CALLER's frame at the call (inside the callee after its own pushes they appear at `@(frame_size + saved_regs*4 + n*4, r15)`).
- Return r0 (64-bit: r0 low, r1 high). Float args fr4-fr7 (further may follow), float return fr0. Struct return via hidden pointer in r2/r4 (check the first call site).
- Callee-saved: r8-r14 (+ fr12-fr15, xf). Scratch: r0-r3, r4-r7, fr0-fr11. `PR` saved by `sts.l PR,@-r15` when the function calls anything. Prologue = sequence of `mov.l rN,@-r15` (each 4 B) + `sts.l PR` + `add #-N,r15` (locals); epilogue mirrors it.
- **Argument count recovery:** the args are the r4-r7 (fr4..) that are READ before being written in the function (including inside delay slots). A function that never reads r5 has no 2nd param - a decompiler's extra parameters are noise; a missing one is a register copied away in the first instructions (`mov r4,r8`).
- Callee-saved regs holding r4-r7 copies at the top (`mov r4,r8; mov r5,r9`) name the params; use them as the parameter names.
- Varargs and unusual hand-written asm (BIOS/SDK) break the rule: check callers.

## Globals and pools
`mov.l =ADDR,r3; mov.l @r3,r2` => `r2 = *(int32_t*)ADDR`. Two-step `mov.l =PTRADDR,r3; mov.l @r3,r2; mov.l @(0x10,r2),r0` => `g_ptr->field_10` (a global POINTER; double indirection). The pool address is shown as `PTR_DAT_xxxx = 8c...`; resolve to the data address, give it one name in a shared names file, reuse everywhere. Pool constants are shared per function window (~±500 B), so equal pool slots in different functions are not necessarily the same variable.

## Struct layouts
1. Collect all `@(disp,Rn)`, `@(r0,Rn)` accesses on the same base register within a function and across callers; offsets + access width (b/w/l/f) + signedness (`extu` presence) form the field table: `+0x0c int8, +0x12 int16, ...`.
2. Width/sign are in the asm, never in the decompile. `mov.b` w/o `extu.b` = `int8_t`.
3. **Array stride** = the constant multiplied into the index: shifts+adds (`shll2`/`shll` combos), `mul.l` with a pool constant, or a repeated `add #stride,rP` in a loop. Sum the shift terms to get it (e.g. `(i<<7)+(i<<2)` = 132). Two different strides for the "same" thing usually mean two structs (template vs runtime copy).
4. Field `+off` accessed with `mov.b ... @(disp,r1)` after `add #0x64,r1` = base adjusted by 0x64: sum the adds (`add #0x64,r1; add r4,r1; @(3,r1)` = `base[+0x67]`).
5. Tables of records of fixed size indexed by id: base address in pool + `id*size`; record the table length from a bounds check (`cmp/hs #N`) or from the next symbol.
6. Alignment: `.l` accesses are 4-aligned, `.w` 2-aligned; misaligned access faults on SH-4 - an offset that looks odd for `.l` means the base is not what you think.
7. Strings: `mova` / pool pointers into the rodata; Shift-JIS text in Japanese games (decode with cp932).

## Writing the C
- Prefer `uint8_t *u` + explicit `r16(u+0x16)` / `w16()` helpers (endianness is little-endian on DC) over guessed struct types until the layout is CONFIRMED; the same bytes are what the emulator differential compares. Promote to a `struct` only when offsets/widths are proven.
- Mark each field CONFIRMED (asm address) or HYPOTHESIS. Name by role after seeing writers AND readers.
- Preserve the retail quirks: reads past table ends, uninitialised stack arrays that are constant, wrap-around of unsigned bytes (0-1 = 255). A port that "fixes" them is not a match; note them and keep the behaviour.
