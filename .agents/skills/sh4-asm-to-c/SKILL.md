---
name: sh4-asm-to-c
description: Instruction-level and idiom-level rules for turning Hitachi/Renesas SH-4 (Dreamcast, also SH-2/SH-3 mostly) assembly into correct C - operand order, sign extension, T-bit compares, constants, multiply/divide, shifts, bit tricks. Use whenever you read or lift any SH-4 asm, in any game.
---
Operand order is `op src,dst` (`sub r1,r2` = `r2 -= r1`). Everything below was checked against real Dreamcast code. Companion skills: `sh4-control-flow` (delay slots, switches, loops), `sh4-abi-and-structs` (args, frames, field offsets), `sh4-fpu-to-c` (floats). Verify any doubtful claim with the emulator differential, not by memory.

## 1. Loads, stores, constants
| asm | C | note |
|---|---|---|
| `mov #imm8,Rn` | `Rn = (int8)imm` | sign-extended: `mov #0xff,r1` is -1 |
| `mov.w @(disp,PC),Rn` / `mov.w 0x..,r1` | `Rn = (int16)LITERAL` | 16-bit literal, SIGN-extended. 0x8000..0xffff literals become negative; big struct strides/offsets load this way |
| `mov.l @(disp,PC),Rn` | `Rn = LITERAL32` | literal pool; usually a global's address, a function address, or a float bit pattern |
| `mova @(disp,PC),r0` | `r0 = &pool_or_table` | address of data (switch table, string). If the next instruction is `fmov.s @r0,frN` / `mov.l @r0,rN`, it is a LITERAL LOAD: the value stored at that pool address goes into frN/rN once (sh4_annotate prints it: `; => fr3 = -8192f (0xc6000000) [literal at ...]`). In the port it is just a constant (`0xc6000000`), not a memory read |
| `mov.b @Rm,Rn` | `Rn = *(int8_t*)Rm` | LOADS SIGN-EXTEND. `mov.b` alone = `int8_t`; `mov.b`+`extu.b` = `uint8_t` |
| `mov.w @Rm,Rn` | `*(int16_t*)` | same rule; `+extu.w` = `uint16_t` |
| `mov.l` | `*(int32_t*)` | |
| `mov.b Rm,@Rn` | `*(uint8_t*)Rn = Rm` | stores truncate; sign irrelevant |
| `@Rm+` / `@-Rn` | post-increment load / pre-decrement store | `mov.l r8,@-r15` = push; `mov.l @r4+,r0` = `r0=*p++` |
| `@(R0,Rm)` | `*(T*)(Rm + R0)` | R0 is the index/offset register |
| `@(disp,Rm)` | `disp` is SCALED: `.l` 0..60, `.w` 0..30, `.b` 0..15 | `.b`/`.w` disp forms require R0 as the data register |
| `@(disp,GBR)` | global-struct base in GBR (rare in games) | |
**Offset recovery rule:** a byte/word field at offset > 15/30 cannot use disp form; the compiler emits `mov #off,r0` or `mov.w =off,r1; mov.b @(r0,Rm),..`. So a `mov.w` literal followed by an `@(r0,..)` access is a struct field at that offset (e.g. +0x1f0), not an array index.

## 2. Compares set T; branches read T
`cmp/CC Rm,Rn` computes **Rn CC Rm** (second operand on the left):
- `cmp/eq Rm,Rn` Rn==Rm; `cmp/ge` signed Rn>=Rm; `cmp/gt` signed Rn>Rm; `cmp/hs` UNSIGNED Rn>=Rm; `cmp/hi` unsigned Rn>Rm
- `cmp/pl Rn` Rn>0; `cmp/pz Rn` Rn>=0 (signed); `cmp/eq #imm,r0` (r0 only, imm sign-extended); `cmp/str` any-byte-equal
- `tst Rm,Rn` T = ((Rn & Rm) == 0); `tst Rn,Rn` is `Rn == 0`; `tst #imm,r0` tests flag bits. `bt` after `tst` therefore branches when the bits are CLEAR.
- `bt`/`bt/s` branch when T=1, `bf`/`bf/s` when T=0. The compiler often emits the inverse of the C condition (`if (a<b) {...}` -> `cmp/ge; bt skip`).
- Unsigned range check idiom: `add #-1,r0; mov #N,r1; cmp/hs r1,r0; bf in_range` means `(unsigned)(x-1) < N`, i.e. `1 <= x <= N`. Same for switch bounds.
- Materialise a bool: `cmp/eq a,b; movt r0` -> `r0 = (a==b)`; `tst r0,r0; movt r0` -> `!x`; `movt r0; xor #1,r0` -> inverted.
- `cmp/gt` vs `cmp/ge` and `cmp/hi` vs `cmp/hs` are where ports go off by one. Write the condition with the operand order in a comment before translating.

## 3. Arithmetic and logic
- `add #imm,Rn` imm sign-extended (-128..127). `neg`, `not`, `negc/addc/subc` (carry chains = 64-bit add/sub or `x != 0` tricks), `addv/subv` overflow-T.
- `and/or/xor #imm,r0` imm is ZERO-extended 8-bit; `and Rm,Rn` register forms are full 32-bit. `extu.b/extu.w` zero-extend, `exts.b/exts.w` sign-extend; also appear as casts after arithmetic.
- `swap.b` swaps the low two bytes, `swap.w` swaps halves, `xtrct Rm,Rn` = `Rn = (Rm<<16)|(Rn>>16)` (middle 32 of a 64-bit; rotate-by-16 or 16.16 fixed-point extract).
- `dt Rn` = `Rn--; T = (Rn==0)` (loop counter). `movt Rn` = T. `clrt/sett`.

## 4. Shifts (multiplication by constants)
`shll/shlr/shar` shift by 1; `shll2/8/16`, `shlr2/8/16` fixed; `shar` is arithmetic (signed `>>`), `shlr` logical (unsigned `>>`). **Signed `/2^k` idiom:** C division truncates toward zero, `>>` floors; the compiler therefore adds a sign-derived bias before `shar` (sign bit via `cmp/pz`+`movt`/`addc`, or `shld` by -31, added to the value or `(1<<k)-1` when negative). Port that sequence as `/ (1<<k)` with truncation, not as `>>`; a bare `shar` is `>>` on a signed value. `shad Rm,Rn` / `shld Rm,Rn`: dynamic shift, Rm>=0 left, Rm<0 right (arithmetic / logical). Multiplication by constant is shifts+adds: `x*132 = (x<<7)+(x<<2)`, `x*228 = (x<<8)-(x<<5)+(x<<2)` etc.; recover the constant by summing, and then it is almost always a struct STRIDE (see `sh4-abi-and-structs`).

## 5. Multiply / divide
- `mul.l Rm,Rn` -> MACL (32x32 low), read with `sts MACL,Rn`; `muls.w/mulu.w Rm,Rn` 16x16 -> MACL (signed/unsigned, operands taken as 16-bit); `dmuls.l/dmulu.l` -> 64-bit MACH:MACL (`sts MACH`); a `dmuls.l` with a magic constant followed by `sts MACH` + shift is DIVISION BY A CONSTANT (`x / N`); decode with N = round(2^(32+s)/magic).
- There is NO hardware integer divide. Division is (a) a call to a library routine (`_divls`, `__sdivsi3`, `div_s32`, `__udivsi3`): find the ONE routine in the binary, decode its register convention ONCE (which reg is the dividend/divisor, which holds the result, behaviour for /0, signed truncation) and record it in the project notes; (b) an unrolled `div0s/div1` ladder (32x `div1`) inline; (c) a shift for powers of two. `%` is typically `x - (x/N)*N`.
- `mac.l/mac.w` = multiply-accumulate (dot products, rare in game logic).

## 6. Stack/regs conventions that matter when reading
`r0` return value + scratch; `r1-r3` scratch; `r4-r7` args; `r8-r14` callee-saved (compiler keeps loop pointers/this/state base here); `r15` SP; `PR` return address, saved with `sts.l PR,@-r15`. A value kept in r8-r14 across `jsr` calls is a local/pointer that outlives them.

## 7. Process
1. Annotate each reg's meaning on first use as a comment (`/* r8 = unit base */`). 2. Translate literally to C with explicit `int8_t/int16_t/uint8_t` casts per section 1. 3. Only then simplify. 4. Verify with an emulator differential (see `port-slice`, `sh4-lift-verify`). Do not trust a decompiler for types, parameter count, or signedness; trust it for control-flow structure as a hint only.
