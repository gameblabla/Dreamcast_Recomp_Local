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
