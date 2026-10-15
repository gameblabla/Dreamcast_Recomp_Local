---
name: byte-matching
description: Make C source compile to exactly the retail bytes of a Dreamcast (SH-4) function/file using the original compiler (Hitachi SHC from the SDK) or a candidate GCC, with bytematch.py and the permuter, and keep the result honest about undefined behaviour. Use when `./dcre sdk` reports the matching SDK is available, or when asked to "match" / "byte-match" a function.
---
# Byte-matching loop
Read docs/BYTE_MATCHING.md once. Short form:
1. `./dcre slice ADDR` (annotated asm). The unit is the whole source FILE when the original compiler shares a literal pool (see skills/dc-decomp-kickoff/references/matching-c.md).
2. Write C whose types follow the asm (`mov.w`=short, `extu.b`=unsigned char, `exts.w`=signed short, `mov.l`=int/pointer, delay slots are scheduling not source).
3. `./dcre bytematch --addr 8cXXXXXX --len N --src f.c --func f` compiles with the ORIGINAL SHC (tools/shc.py, wine, from SDK_DIRS) using the reference flags
   (`-cpu=sh4 -endian=little -fpu=single -division=cpu -round=nearest -pic=0 -macsave=0 -optimize=1 -size -string=const`; extra: `--shc-flags=-speed`).
   Globals/callees at fixed retail addresses: `//@sym NAME 0xADDR` lines in f.c + `extern` declarations (linked as absolute symbols). `./dcre cc asm f.c` = SHC's own asm.
   `EXACT`/`NORMALIZED` + `compiler=SHC` = match. `compiler=GCC(fallback...)` means NO SDK compiler was found: that is never a match.
   `DIFF n` prints the first differing instruction with context. The exact source shape matters (e.g. `r = a; else r = b; return r;` vs early returns).
4. Change ONE thing per iteration (type, declaration order, loop form, `if`/`?:`, inline helper, constant form) and re-compare. If stuck on a few instructions, `./dcre permute ...`.
5. A match is not done: re-read the source for readability, then prove behaviour with skill `decomp-function` (`AD_SANITIZE=1 ... autodiff SPEC --mutate`), and note any UB the old compiler relied on (skill `ub-and-old-compilers`).
Hard rules: never claim a match without the `BYTEMATCH ... EXACT|NORMALIZED` line; never keep permuter noise (`x*2`->`x<<1`, reordered locals) unless it is needed for the match, and say so; if the SDK/compiler is missing, say matching is impossible rather than approximating with GCC and calling it matched.
