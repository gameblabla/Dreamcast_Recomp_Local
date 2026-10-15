# Worked example: Nadesico the Mission (Japan), GD-ROM `.cue`

`DISC` = the Redump `.cue` (Track 1 CD part, audio, Track 3 high-density data at LBA 45000). `./dcre extract --boot-only` finds the volume that holds
`1ST_READ.BIN` (the CD-part volume is skipped), writes a 1,655,300-byte executable byte-identical to the one extracted by other tools.
`./dcre sdk`: 41 library builds in the binary; **R1.42J (and "Release 8 Europe") contain all 41** -> a 1.42J SDK is the exact match; the older
1.00J contains none of them (no banner match) but is still useful for headers and as a name reference (79 unique signature matches).
`./dcre import` + export: 3,614 functions, 664 named from SDK signatures (`third_party/dc-re-ghidra/sdk-symbols.txt`), call graph, 1.6 MB of asm,
decompiled C per 64 KiB window.
Results of the local-model trials (opencode, qwen 27B): simple leaf and loop functions proven with `autodiff --mutate`; see the AGENTS.md of the
originating project for the details and the failure modes that shaped the skills.
