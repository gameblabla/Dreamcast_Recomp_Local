# Guard rails: how a weak local model is kept from "proving" a wrong port

Origin: a 27B local model (opencode) ported a float + tail-call + indirect-table function (Nadesico 8c073f72) and ended after 235 tool calls with 19 of 24 mutants alive.
Failures seen in that run and in the easier ones, and the tool that now answers each:

| failure | answered by |
|---|---|
| guessed stride 0x84 instead of the asm's 0x630; u8 where the asm reads an s16; dropped callee arguments | `portlint` (constants/offsets/widths the asm loads but the port lacks), `sh4_annotate` literal values and CALLS table |
| the tail call (`jmp @rN`) was not listed as a call at all, so no callee list was suggested | `sh4_annotate` now marks `TAIL`, shows registers set on SOME path only, and `lint` demands as many compared registers as the callee itself reads (from the callee's asm) |
| hand-written spec: 8 argument values, tables zero-filled, too few elements | `specgen` (args `auto` = boundary values harvested from the asm and weighted towards compared constants, regions of >= 8 strides with varied bytes, index fields bounded), spec `lint` (params without values, < 4 distinct values, unstubbed callees, data pointers outside every region, check_ret vs return kind) |
| 19 "surviving mutants" were in the SHARED soft-float library listed in `port.sources`, which one function can never exercise | `autodiff` mutates only the file named after the function (`port.mutate` overrides) |
| survivors without guidance | each `SURVIVED` line prints a hint (equal operands for `<=`, one-of-two for `&&`, non-zero tables for shift/offset constants...) |
| callee registers that vary but are not compared | `UNCHECKED CALLEE ARGUMENT` (retail full-register log `fullog=` vs the compared ints/floats; excused only when the callee's own asm does not read the register, or by `ignore_args` + a written reason) |
| "CONFIRMED by retail differential" written when nothing had run | proof ledger `work/proofs/<func>.json` + `./dcre claims` (a claim is backed only by a PROVEN run whose port hashes still match) |
| the spec was weakened (fewer cases, narrower inputs, `equivalent_mutants` added) to hide a mismatch | ledger ratchet: a run weaker than the strongest earlier run (cases, mutants, argument values, regions, varied regions, callee registers, equivalents, allow_uncovered, check_ret) is `SPEC WEAKENED` and cannot be PROVEN; hard floors 40 cases / 24 mutants |
| typos in the spec (decimal stub address, unknown key, overlapping regions, patch outside region) failing silently or hanging | `validate_spec` prints every error with the fix |
| port crashed / emulator faulted with a bare message | `explain_fault` (nearest region and a suggested `{"addr","len"}`, or "a callee that should be stubbed is running for real"), port-side UBSan/outside-region hints |
| mismatch printed as raw hex | call-log mismatches are decoded ("region 8c23e914+0x630", "literal 0x.. at ..", "float 32768") |
| a hung emulator run re-run for hours | per-case time limit (`ND_CASE_MS`, 120 s) and overall timeout; stub addresses are validated as hex |

Commands: `./dcre specgen ADDR` · `./dcre lint ADDR PORT.c --spec S.json` · `./dcre autodiff SPEC --mutate` · `./dcre claims` · `./dcre facts ADDR` · `./dcre selftest [--emulator]`.
Environment: `AD_ALLOW_WEAKER=1` disables the ratchet and is for humans only (an agent must never set it).

Self-test: `tests/test_tools.py` (pure checks, asm checks, and with `--emulator` the real regression: the saved 27B-model spec for 8c073f72 is NOT PROVEN and reports the surviving mutants, the generated spec PROVES a reference port, and a weakened spec is rejected). Fixtures in `tests/fixtures/073f72_*` are the model's original attempt and a judge port written from the asm.
Honest limits: the lint reasons from instructions, not from intent (an index field must still be bounded by a `patch`, which specgen does for the `mov.w` + `muls.w` pattern only); a function whose behaviour depends on state the spec never sets is still only as proven as its regions are rich.

## Trial record (2026-10-15)
- Before: Nadesico 8c073f72 (float + tail call + indirect table), local qwen3.8-27b, 235 tool calls, NOT PROVEN (19/24 mutants alive: most were in the shared soft-float library, the rest zero-filled tables).
- After these guard rails (same model, fresh sandbox, port deleted): PROVEN in 134 tool calls (about 70 min). It started from `specgen`, fixed 6 -> 2 -> 0 real mismatches in the port without touching the spec, then only ADDED inputs (larger table, more patches) to kill the last mutants. Independent judge: same port, seed 7, 300 cases, 60 mutants, UBSan+ASan: PROVEN, 0 equivalents declared.
- `proofcheck` over a whole old tree reports hundreds of "unbacked" claims: ports verified before the ledger existed (nd_golden differentials, mutcheck) have no ledger entry. Scope it to the directory you are working on (`./dcre claims port/`).

## Second trial and the fixes (2026-10-15, evening)
Three fresh functions on the local qwen3.8-27b (8c04c938, 8c081798, 8c043680). Result: one PROVEN (8c081798, but a stronger judge run still had 1 surviving boundary mutant), two failures. What went wrong and what now prevents it:

| Failure | What happened | Fix |
|---|---|---|
| False hypothesis "the binary is corrupt" | model opened 1ST_READ.BIN at the low bits of an address (0x4ca24 instead of 0x3ca24), read NaN, then "trusted Ghidra over the binary" and patched pointers (~70 calls) | `readmem.py` (virtual addresses, explains the offset mistake); `sh4_annotate` prints `mova`+`fmov.s` float literals (`fr3 = -8192f`); skill "Facts about the data"; plugin blocks hand-reads of the image |
| Wrong port idioms | `ad_rd32(ad_rd32(pool))`, a spec region over the function's own literal pool (the emulator overwrote the constants), `fprintf` debug output | `portlint` ERRORs (debug prints, run-time reads inside the function's range, nested ad_rd); `adcheck.lint` ERROR for a region over the code. NOTE: autodiff computed lint errors and never acted on them; now it exits on them |
| Runaway reply | one reply of 31,488 tokens repeating one paragraph; opencode ended the run with exit code 0 | opencode.json `limit.output` 8192; `agentrun.py` treats `reason: length` / >6000 output tokens as a loop and resumes the same session with a nudge |
| Hang misdiagnosed | autodiff printed `timeout` (it was the PORT binary: a digit-count argument of 0x70d3da1f) and the model blamed the emulator | per-case alarm + callee-hit cap in `autodiff_main.c`; on abort autodiff BISECTS the culprit argument and prints the `arg_limits` line; phases are printed |
| Context-compaction amnesia | after each summary the model re-derived `div_s32`'s convention and re-ran one command 45 times | `notes.py` + plugin re-injects AGENTS.md, the skill and the notes on every request and in the compaction hook; plugin blocks the 3rd identical command on unchanged files |
| Provisional PROVEN | 150 cases / seed 1 hid a table-end boundary | `autodiff --final` (seed 7, 300 cases, 60 mutants, sanitizers); `proofcheck` only backs a claim whose newest run is a PROVEN `--final` on an unchanged port |
| Invented commands/flags | `dcre.py disasm`, `autodiff --build-only`, guessing nd_golden arguments | plugin blocks nonexistent `tools/dc/*.py` and lists the real ones; skill has an exhaustive command list |
| Seed hunting / tiny runs | `--cases 3` 15x, ledger polluted | plugin refuses `--seed` (outside `--final`) and `--cases` < 40 |

opencode notes (v2.0.29): plugins are DIRECTORY packages (`package.json` with `main`/`exports`) listed in `opencode.json` as `"plugins": ["./.opencode/dcguard"]`; hooks used: `session.hook("context"|"compaction")` (push a `{type:"text",text}` system part), `tool.hook("execute.before"|"execute.after")` (throwing blocks the call and the message goes back to the model). The v1 `.opencode/plugin/*.js` format is not loaded. Shell tool is called `shell`. JSON events: `step_start` / `tool_use` / `step_finish{reason,tokens}` / `text`.

