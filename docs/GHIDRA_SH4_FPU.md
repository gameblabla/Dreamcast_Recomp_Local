# Ghidra and SH-4 floating point (making the decompiler readable)

Symptom: functions that use floats decompile with branches on constants (`cVar19 = '\0'; if (cVar19 == '\0') ...`), `double`
variables built from `CONCAT44` pairs, and code twice as long as it should be. Cause: the decompiler cannot prove `FPSCR.SZ`/`FPSCR.PR`
stay 0 across calls, so it keeps the double-precision / paired-move paths alive.

Fix (from a Ghidra user's solution, saved verbatim in Ghidra_sh4_notes.txt): give calls a calling convention that leaves FPSCR alone and pin
SZ=PR=0.

**Automated here:** `ghidra/stdcall_noclobber_fpscr.xml` is that convention (the stock `__stdcall` prototype plus `fpscr`, `fpscr_sz`, `fpscr_pr`
under `<unaffected>`), and `ghidra/scripts/DrFpscrConv.java` imports it into the program, pins `fpscr_sz`/`fpscr_pr` to 0 over the whole image and
applies the convention to every function. `./dcre export` runs it when the file exists; to run it by hand:

    analyzeHeadless work/ghidra_project drproject -process 1ST_READ.BIN -scriptPath ghidra/scripts -postScript DrFpscrConv.java ghidra/stdcall_noclobber_fpscr.xml

In the GUI: Edit > Options for <program> > Specification Extensions > Import the XML, then set each function's calling convention.
Remember: SDK code (libm, math helpers, `fsca`/`fipr`/`ftrv` users) may legitimately switch precision; check the asm before trusting a decompile that
touches FPSCR (`lds Rn,FPSCR`, `sts FPSCR`, `fschg`, `frchg`).

Measured on the Nadesico example (3,614 functions): `CONCAT44` pair artifacts in the decompiled C dropped from 13,819 to 1,074 and float-heavy functions
(e.g. FUN_8c019140) turned from 150 lines of FPSCR_SZ/PR branches into straight struct-field code. Caveat: with the changed calling convention Ghidra
infers fewer register parameters (`void f(void)` where the asm reads r4): always take the signature from `./dcre annotate ADDR`, not from the decompile.
Set `DR_NO_FPSCR_FIX=1` to export without the fix.
