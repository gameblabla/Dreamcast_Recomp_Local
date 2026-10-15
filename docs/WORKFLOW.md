# Workflow, end to end

```
disc ──./dcre extract──▶ game/1ST_READ.BIN
       ./dcre sdk      ▶ which SDK/compiler? ask the user if missing           (docs/SDKS.md)
       ./dcre import   ▶ Ghidra project (SuperH4:LE, base 0x8c010000) + export  (ghidra/scripts/Dr*.java)
       ./dcre export   ▶ work/research/{functions,callgraph,hw_access,strings,sdk_matches}.tsv, asm/, decompiled/
       ./dcre status / next / slice ADDR  ▶ pick the cheapest ready function (callees first)
 per function ──────────────────────────────────────────────────────────────
   A. matching  (if the original compiler exists)  ./dcre bytematch / permute      docs/BYTE_MATCHING.md
   B. behaviour (always)                           ./dcre autodiff SPEC --mutate   skill decomp-function
      -> RESULT: PROVEN, then record: file name contains the address (port/fn_8cXXXXXX.c) so `./dcre status` counts it
```
1. **Order**: bottom-up. Library/SDK/hardware functions are not decompiled (call through host callbacks: `triage` classes them sdk/lib/hw).
2. **Names**: curated names go in `names.tsv` (`address<TAB>name<TAB>func|data|label<TAB>comment`), re-applied on every `./dcre export`.
3. **Units**: for matching, a source file is the unit (shared literal pool). For behaviour, a function is.
4. **Local AI**: `./dcre agent 0x8cXXXXXX` starts opencode headless with the `decomp-function` skill on one function. Give it 1-2 h per function; a
   `RESULT: PROVEN` line is the only acceptable completion. Review UB (docs/UB_AND_OLD_COMPILERS.md) before trusting it.
5. **Never commit** the game, SDK files, `work/`, `game/`. `work/research` holds retail-derived dumps (asm, decompiled C, strings).
