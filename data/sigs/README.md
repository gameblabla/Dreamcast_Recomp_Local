# Shipped library signatures (no SDK needed)

`katana-1.42J.sigs`: one line per function, `fullHash specificHash codeUnits name` (Ghidra function-ID hashes: one-way, relocation-masked).
`katana-1.42J.libs`: `symbol<TAB>library file` (module label for triage).
Contents: only hashes, sizes and public symbol names of Katana SDK 1.42J library functions (shinobi, ninja, sofdec, cri_adxs, sg_mw, sg_sd, sh4nlfzz,
nindows, sg_mwwav, duck_tm, mp1a_l2). No code, no instruction bytes, no library files, no documentation. `./dcre export` applies every `*.sigs` here
automatically, so users do not have to find an SDK. Add more releases with `./dcre sdk-index` on your own SDK and copy the two files here as
`katana-<release>.sigs/.libs`. Reproduce: `python3 -I tools/sdk_index.py build <SDK_DIR>`.
Not legal advice: names and hashes are facts about the libraries, in the same spirit as the public dc-re-ghidra table, but you decide what to publish.
