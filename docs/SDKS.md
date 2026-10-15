# SDKs and libraries: what to provide, how it is detected

Point `SDK_DIRS` (project.env) at as many Dreamcast SDK copies as you have, `:`-separated. Folders, `.iso` and `.zip` are all scanned.
Typical set: **Katana SDK R1.42J** (the release many 1999 games were built with) and **1.00J** (older reference).

Roles:
- **matching release** (found by `./dcre sdk`): original compiler `shc.exe`/`asmsh.exe`/`lnk.exe`, exact `.lib` libraries (function names via signatures
  through `third_party/dc-re-ghidra` + `skills/dc-decomp-kickoff/scripts`), exact headers (struct layouts, enums, constants).
- **other releases**: headers/names as hints; runtime helper libs may be byte-identical, middleware (Shinobi/Ninja/MW) often differs: treat matches as hints.

Detection (`tools/sdk_detect.py`, backed by skills/dc-decomp-kickoff/scripts/sdk_scan.py + references/sdk-banners.tsv):
1. library banners in the game -> which releases contain *all* its library builds;
2. compiler fingerprints (GCC / SHC / Hitachi strings);
3. what is actually inside your SDK_DIRS (compiler tools, `.lib` count, headers, images).
If the matching release is missing the tool prints `ASK THE USER: ...` and exits 3. **Ask before proceeding.** Proceeding without it is allowed
but slower: say what you lose (compiler, exact headers, library names).

Where public releases are listed, with file names to search for: skills/dc-decomp-kickoff/references/sdk-releases.md. Nothing in this repo
downloads or redistributes SDKs; the user decides what they are entitled to use. Never commit SDK files or SDK-derived tables.

Libraries other than the SDK (CRI ADX/SFD/Sofdec, middleware, game-specific libs) are detected by the same banner scan; if a library
has no preserved copy it stays a black box: call it through a host callback and port around it.

## No SDK copy: library triage (`./dcre libtriage`)
Only used when `./dcre sdk` does not find the exact release in SDK_DIRS (with the SDK present it is skipped, `--force` overrides). `./dcre export` runs it automatically then.
Nothing is bundled: the built-in CRC table (third_party/dc-re-ghidra) only knows R8/R10/R11, so a 1.42J game exact-matches ~3% of its library code (Nadesico: 153 functions).
`tools/libtriage.py` spreads those matches over the rest of the library using structure that survives a version change (details in its docstring):
`lib-callee` (called by a library function: libraries cannot link-call game code), `lib-run` (between two functions of one module), `lib-hint` (name guess by size),
`game-likely` (below the first library function: game objects link first), everything else `unknown` = treat as game. `triage.py` then skips the proven library
classes. Nadesico (R1.42J, no SDK): 25% of function bytes identified as library (2035 functions), 0 of 552 already-ported game functions mislabelled;
`libtriage.py validate` hides 30-70% of the exact matches and rediscovers ~48% of them (module label can be wrong at module boundaries: trust the class, not the module).
Check one function with `libtriage.py why ADDR`. It is conservative: false "unknown" costs time, false "lib" would hide game code, so only chains from exact matches are used.
