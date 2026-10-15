# Byte-matching: why, how, and what it does NOT give you

**Prefer byte-matching whenever the original compiler is obtainable.** A rebuilt function whose bytes equal the retail bytes is the
strongest proof there is: no emulator run, no test inputs, no "looks right". It also recovers the original source *shape* (types,
loop forms, struct layouts, which helper was inline), which is what makes the rest of the game readable.

Two tracks, used together (see WORKFLOW.md):

| track | oracle | needs | gives |
|---|---|---|---|
| **A. matching** | bytes equal retail | the SDK's own compiler (Hitachi SHC from the Katana SDK, or the GCC the game used) + libs/headers | exact source structure, a rebuildable executable |
| **B. behavioural** (`autodiff`) | emulator differential | nothing but the binary | a portable reimplementation that can be built by a modern compiler |

Matching without B proves nothing about portability; B without A leaves you guessing at structure. Do A first where possible, then run
B on the *same* function so the matched C is also shown behaviourally equal and free of UB (see UB_AND_OLD_COMPILERS.md).

## 0. Ask for the SDK before you start (and detect it)
`./dcre sdk` reads the library banners in the game (`Shinobi Ver 1.42 Build:...`), ranks the public SDK releases by how many of the game's
library builds they contain and tells you which release to get. If that release is not in `SDK_DIRS`, **stop and ask the user for it**
(exact wording is printed). You *can* proceed without it, but expect: no original compiler (no byte-matching), no exact headers/struct
layouts, only signature-based names from other releases (a near release names far fewer functions), and much more guessing. Say so.
Older SDK copies (e.g. 1.00J while the game used 1.42J) are still useful as header and name references, and their SHC runtime libs are
often byte-identical for small helpers (memcpy, divide, float helpers) but verify, never assume.

## 1. Identify compiler, version and flags
- Library banners give the SDK date; the SDK ships the compiler (`shc.exe`, `asmsh.exe`, `lnk.exe`; run with wine/wibo).
- Reference flags that reproduced Katana game code (from skills/dc-decomp-kickoff/references/matching-c.md):
  `-cpu=sh4 -endian=little -fpu=single -division=cpu -round=nearest -pic=0 -macsave=0 -optimize=1 -size -string=const`.
  `-optimize=0` looks very different (everything through the stack); `-align16` shows as `nop` runs before function starts (library code).
- SHC 5.1 releases 04/08/11 gave identical output on everything compared; 5.0 (SDK R4, 1.00J) allocates registers differently.
- Some games use GCC (2.x/3.x) instead: look for `GCC: (GNU) x.y` strings, `gcc2_compiled.`, a specific prologue (`sts.l pr,@-r15`), and the way
  constants/`mova` pools are laid out. `sdk_detect.py` prints what it finds.

## 2. The unit is the source FILE, not the function
SHC shares one literal pool across the functions of a file, and `bsr` only reaches same-file functions. Find a file's extent (starts after the
previous file's last pool, ends after its own last pool), make sure both ends are function boundaries, and match the whole file
(skills/dc-decomp-kickoff/references/matching-c.md has the details and `scripts/split_asm.py`, `missed_funcs.py`, `linkbase.py`).

## 3. The loop
1. `./dcre slice ADDR` -> annotated asm: literal values, call arguments, loops, signature.
2. Write C with the types the asm implies (`mov.w` = short, `extu.b` = unsigned char, `exts.w` = signed short...).
3. Compile with the original compiler (wrapper in `DR_CC` or by hand), extract the function bytes -> `./dcre bytematch --addr .. --len .. --src f.c --func f`
   (or `--cand-bin` for SHC output). `NORMALIZED` = same instructions, only pool layout/displacements differ.
4. Iterate: diff -> hypothesis (type? order of declarations? `if` vs `?:`? loop form? inline?) -> rewrite.
5. When stuck on a few instructions, `./dcre permute ...` random-walks neutral rewrites and keeps the lowest score.
6. Matched? Run `autodiff --mutate` on it too, then record it.

## 4. What a permuter does not solve (read this)
An automatic permuter ("keep guessing with a tool until it matches") gets you to a match, not to a correct reimplementation:
- the winning source is arbitrary among many that compile alike; names, types and meaning are still unknown (you must recover them from use);
- **old compilers exploit behaviour that modern GCC/Clang do not tolerate or define**. A permuted source can match under SHC and
  still be wrong under a modern compiler (signed overflow, shift counts, reading past array ends, uninitialised locals, type-punned
  floats, evaluation order). Matching is a property of the *old* compiler; portability is a property of defined behaviour;
- permuters overfit: random rewrites like `x*2` -> `x<<1` or reordering locals have no meaning, so strip them back to the most readable form
  that still matches before committing.
So: match first, then (a) restore the intended readable form, (b) run `AD_SANITIZE=1 ./dcre autodiff SPEC --mutate`, (c) read
UB_AND_OLD_COMPILERS.md and mark every place the original relied on UB.

## 5. Without an original compiler (fallback)
Use `sh-elf-gcc` as a *candidate* compiler for structure only (it will not byte-match SHC output; `bytematch` reports instruction-level
`NORMALIZED`/`DIFF`). Treat the result as HYPOTHESIS and prove behaviour with `autodiff`. Do not spend hours chasing register allocation
differences that come from the compiler, not your source.
