# Undefined behaviour and old compilers (why a "match" is not a port)

1990s compilers (Hitachi SHC, GCC 2.x) happily compiled code that modern GCC/Clang may *optimise away* or mis-compile at -O1+. Original game
code relies on this, and the retail binary captures the exact behaviour the old compiler produced. A faithful port must keep that
behaviour explicitly instead of hoping a new compiler agrees.

## Checklist (what to look for in the asm, what to write)
| Area | Old compiler / hardware behaviour | In the port |
|---|---|---|
| signed overflow | wraps (add/mul in 32 bits) | do it in `uint32_t` and cast, or build with `-fwrapv` |
| shifts | `shad`/`shld`: count taken mod 32, **negative count = right shift**; C says shift >= width / negative is UB | wrapper helper `sh4_shad(x, n)` with the hardware definition |
| division | `div1` sequences or `__sdivsi3`; `/0` and `INT_MIN/-1` have a definite result | helper with the retail convention (e.g. `/0 -> 0`), test it with autodiff |
| `char` signedness | `char` is signed on SH; `mov.b` sign-extends | use `int8_t`/`uint8_t` explicitly |
| array bounds | reads past the end of a table hit whatever is next in memory | declare the real memory layout (struct/region) and keep the over-read, or document the quirk (e.g. ids >= table size read the following data) |
| uninitialised locals/registers | an uninitialised value is whatever the register held; the game may depend on it | find the real source of the value (caller's register / previous call's `r0`) and pass it explicitly |
| strict aliasing / type punning | `*(int*)&f` to get float bits | `memcpy` or a union; floats in a core that must be bit-exact: use raw `uint32_t` bit patterns |
| unaligned access | SH-4 raises an address error; x86 silently works | keep aligned accesses, assert on alignment in the wrapper |
| null / low addresses | address 0 and other low addresses are readable on the console (BIOS mirror) | model the region or remove the read; a modern compiler may delete the "impossible" check |
| P1/P2 mirrors | `0xA0000000 | addr` is the uncached alias of `0x80000000 | addr` | normalise addresses before comparing pointers |
| evaluation order | argument and operand evaluation order is unspecified and differs between compilers | sequence side effects with explicit temporaries in the order the asm shows |
| float | single precision, `fmac`/`fipr`/`ftrv` rounding, `ftrc` saturates, NaN compares, flush behaviour | `-ffp-contract=off`, no fast-math, use the bit-exact helpers (skills/skmp-sh4-fpu, `nd_f32`-style soft float) when the result must match bit-for-bit |
| `volatile`/hardware | PVR/AICA/MMIO registers, store queues, cache ops | keep behind a platform layer, never in core logic |
| calling convention | args r4-r7 / fr4-fr11, return r0 / fr0, callee-saved r8-r14; a callee may read a register the caller never set | model the real signature from the annotated asm, not the C prototype you guessed |

## Lessons from public SH-4 static recompilers (dcrecomp, DreamcastRecompiled, dream-recomp)
These lift the whole binary instead of porting function by function, so their pitfalls are the mirror image of ours; we keep the cheap checks:
- **Callee-saved registers / sp at return**: they run an `ABI_CHECK`. `autodiff` now does the same on the RETAIL function and prints `ABI NOTE` if r8-r14 or
  sp differ at return: such a function is not plain C (hand asm, register-passing helper) and the port signature must model it.
- **Misaligned access**: the SH-4 raises an address error, x86/ARM hosts silently work and hide the bug; `AD_SANITIZE=1` includes UBSan's alignment check.
- **Missed code**: static discovery reaches ~79-90% of a binary; the rest is behind computed jumps (switch tables, function-pointer tables, callbacks) or code copied
  to RAM. `./dcre discover` lists unresolved indirect calls and unexplained code bytes (`work/research/indirect.tsv`, `gaps.tsv`). Seed what you find.
- **Hand-written semantics are the error-prone part**: the division step (`div0s/div1`), `fipr/ftrv/fsca`, rounding. Do not trust a lift of these; verify with
  the emulator (autodiff) and the bit-exact models in skills/skmp-sh4-fpu.
- **Validate against a second implementation**, not by reading: emulator differential per function (autodiff), and for whole-program behaviour a rolling hash of
  memory writes per frame to find the first divergence.
- **Progress counter**: untranslated/unresolved call targets going to zero is a better completeness metric than "functions done".

## How the tools help
- `AD_SANITIZE=1 ./dcre autodiff SPEC --mutate` builds the port with UBSan+ASan: signed overflow, invalid shifts, out-of-bounds reads of the
  declared regions become failures. A port that matches the emulator *and* is sanitizer-clean does not depend on UB.
- autodiff compares behaviour to the retail binary, so a UB-dependent quirk you preserved shows up as "matches", and a quirk you "fixed"
  shows up as a mismatch: preserve first, then decide deliberately to deviate (record it).
- Compile the port with `-fwrapv -fno-strict-aliasing -fno-delete-null-pointer-checks -ffp-contract=off` unless you have proven it unnecessary.
- Byte-matched C (track A) is *compiler-specific source*. Keep it in `match/` and the sanitiser-clean behaviour-checked version in `port/`.

## The honest summary
Matching tells you "this source compiles to these bytes with that compiler". It does not tell you what the code means, nor that a different
compiler will give the same behaviour. Both questions need their own evidence.
