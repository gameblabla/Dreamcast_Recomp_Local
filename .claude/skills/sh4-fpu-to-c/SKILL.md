---
name: sh4-fpu-to-c
description: SH-4 FPU asm to C: operand order, fcmp/T-bit patterns, int<->float, constants as IEEE bit patterns, fsca/fipr/ftrv/fsrra, FPSCR modes. Use for any function containing fmov/fadd/fmul/fcmp/ftrc/float/fsca/fipr/ftrv. Bit-exact ports use integer soft-float.
---
## Basics
- 16 single regs `fr0-fr15`, paired `dr0,dr2,..` (if SZ/PR modes), vectors `fv0,fv4,fv8,fv12`, a second bank `xf0-xf15` (`frchg` swaps banks; `xmtrx` is the 4x4 matrix in the XF bank). `fr0` = float return; `fr4-fr7` args (verify per binary).
- `fmov.s @Rm,FRn` load, `fmov.s FRm,@-r15` spill, `@(r0,Rm)` indexed; `fmov FRm,FRn` reg copy; `fschg`/`frchg` toggle SZ/bank, `fmov.d`/dr forms appear only when SZ=1: a function containing `fschg` is moving 64-bit pairs (double or two floats) until the second `fschg`.
- **Binary ops are `FRn = FRn op FRm`**: `fsub fr1,fr2` => `fr2 = fr2 - fr1`; `fdiv fr1,fr2` => `fr2 /= fr1`. `fmac fr0,FRm,FRn` => `FRn += fr0 * FRm` (fr0 mandatory; single-rounded multiply-add, differs from separate fmul+fadd in the last bit - port exactly).
- Compares: `fcmp/gt FRm,FRn` => T = (FRn > FRm); `fcmp/eq`. There is no `>=`; `a >= b` is emitted as `fcmp/gt b,a; bt` or `fcmp/eq` + `fcmp/gt`. NaN compares false; `!(a<b)` is not `a>=b` when NaN is possible.
- Constants: `fldi0` 0.0, `fldi1` 1.0; others from pool: `mov.l =0x43960000,r1` then `fmov.s @r1,..` or `lds r1,fpul; fsts fpul,fr0`. Decode bit patterns, don't guess: 0x3f800000=1.0, 0xbf800000=-1.0, 0x40000000=2.0, 0x3f000000=0.5, 0x42c80000=100.0, 0x43960000=300.0, 0x447a0000=1000.0, 0x40490fdb=pi, 0x38d1b717=1e-4. `python3 -c "import struct;print(struct.unpack('<f',struct.pack('<I',0x43960000)))"`.
- `fneg`, `fabs`, `fsqrt` (IEEE exact), `fsrra` (approx 1/sqrt, NOT exact: model with the hardware table), `fsca FPUL,DRn` (sin/cos of FPUL interpreted as 16.16 turns = 65536 per revolution, results into fr(n),fr(n+1); approximate, use an emulator-derived table such as Flycast's), `fipr FVm,FVn` (4-D dot into FR[n+3]), `ftrv XMTRX,FVn` (4x4 matrix times vector), `fmul` etc. Any of these in a function => the function is float-HEAVY presentation math (camera/projection/matrix); park it rather than port (project policy) unless it feeds game state.

## Conversions
- int -> float: `lds Rm,FPUL; float FPUL,FRn` => `(float)(int32)Rm`.
- float -> int: `ftrc FRm,FPUL; sts FPUL,Rn` => `(int)f` TRUNCATING toward zero, saturating at INT_MIN/INT_MAX, NaN -> INT_MAX-ish (check). Common wrongly-assumed rounding: there is no `round`; `+0.5f` before `ftrc` is explicit in asm.
- `flds/fsts` move bits between FPUL and FRn WITHOUT conversion (used for loading bit-pattern constants and passing float bits through int regs).
- 16.16 / angle conventions: multiply by 65536.0 (0x47800000) or 1/65536 (0x37800000) / 182.044 (0x43360b61, deg->bam) around `ftrc`.

## Porting rules for a bit-exact core
- Use an integer soft-float on raw uint32 (`nd_f32_add/sub/mul/div/lt/gt/from_i32/trunc`, add `fneg/fabs/fmac/fsqrt/fcmp_eq` there with a spec test + mutant if missing). Round-to-nearest-even, flush-denormals depends on FPSCR.DN (check the boot/FPSCR setup; the emulator is authoritative).
- Keep the order of float operations from the asm (float add is not associative); keep intermediate values in 32-bit.
- Never compare float results with epsilon in tests; compare raw bits.
- In an emulator differential, float-returning callees that you stub need `skipfr0=addr:bits`; sin/cos stubs `skipsin/skipcos`; `fsca` instruction emulated via `fsca=addr`.
