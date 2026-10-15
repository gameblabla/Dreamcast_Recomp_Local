---
name: ub-and-old-compilers
description: Checklist for turning old-compiler C (Hitachi SHC, GCC 2.x) or a byte-matched function into a portable, correct reimplementation: undefined behaviour the original relied on (signed overflow, shifts, array over-reads, uninitialised values, aliasing, unaligned/null access, float semantics) and how to keep it explicit. Use after a function matches or passes autodiff, before declaring it portable, and whenever a modern compiler "miscompiles" ported code.
---
# UB review (docs/UB_AND_OLD_COMPILERS.md has the full table)
For each ported function, walk the annotated asm and ask:
- **Arithmetic**: signed overflow wraps; shifts use `shad/shld` semantics (negative count = right shift, count mod 32); division has hardware/library conventions (`/0`, `INT_MIN/-1`); `char` is signed.
- **Memory**: does the code read past a table end, read a register/stack slot nobody wrote, rely on struct padding, use unaligned or low-address (null) reads, or write through an uncached P2 alias? Keep the behaviour by modelling the real memory layout; never "fix" it silently.
- **Aliasing/float**: pointer-cast float<->int -> `memcpy`/raw `uint32_t` bits; `ftrc` saturates, `fcmp` NaN rules, `fmac/fipr/ftrv` rounding; no fast-math, `-ffp-contract=off`.
- **Order**: argument/operand evaluation order, side effects in conditions -> explicit temporaries in the asm's order.
Verification: `AD_SANITIZE=1 ./dcre autodiff SPEC --mutate` must print `RESULT: PROVEN` (UBSan/ASan clean AND equal to retail). Build the port with `-fwrapv -fno-strict-aliasing -fno-delete-null-pointer-checks -ffp-contract=off` unless proven unnecessary.
Record every deliberate quirk as a comment `QUIRK: <what the retail code does>` next to the line that reproduces it. If you decide to deviate, say so and why (a deviation changes game behaviour).
