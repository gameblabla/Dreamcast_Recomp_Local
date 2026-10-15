# Research notes: what other decomp / recomp / agent projects do, and what we adopted (2026-10-15)

Reddit (r/decomps, r/LocalLLaMA, r/opencode ...) cannot be fetched by our web tools (domain blocked for the crawler), so this is from the blog posts, papers, READMEs and docs those communities link to. Each item: finding -> what we did.

## Matching decompilation with agents
Sources: [Using coding agents to decompile N64 games](https://blog.chrislewis.au/using-coding-agents-to-decompile-nintendo-64-games/), [The long tail of LLM-assisted decompilation](https://blog.chrislewis.au/the-long-tail-of-llm-assisted-decompilation/), [Can LLMs really do matching decompilation? (60 functions)](https://gambiconf.substack.com/p/can-llms-really-do-matching-decompilation), [Matching decompilation as a verifier-guided task (ICML 2026 workshop)](https://icml.cc/virtual/2026/82758).

| Finding | Adopted as |
|---|---|
| Show output only on request; verbose per-build output was ignored; exploring from the repo root burns tokens | `brief.py` is ONE page; the plugin pins the brief summary; tool output stays short |
| Every attempt in its own file so a good match cannot be degraded; prediction before a change, post-mortem after a failure; one hypothesis per change | `attempts.py` (autodiff snapshots every run, keeps the best, `restore best`); plugin `STALLED` steering after 3 runs without beating the best; `notes.py tried` |
| Similarity-based scheduling and retrieval beat easiest-first; up to 5 similar already-decompiled functions in the prompt (embedding of normalized asm) | `brief.py` section SIMILAR PORTED FUNCTIONS (opcode-sequence similarity vs `core/nd_*.c`, `port/fn_*.c`) |
| A programmatic first draft (m2c) goes into the prompt; permuter results only used if perfect | brief section GHIDRA DECOMPILE (structure hint) + HOW CALLERS PASS THE ARGUMENTS (call sites in the decompile show what pointer/scalar args really are; this exposed that 8c043680's 5th arg is a table index) |
| Permuters made agents optimise noise and loop | permute.py stays out of the agent flow (human tool for byte-matching) |
| Models claim a match without checking; duplicate submissions (49x) | agent cannot claim: ledger decides (`agentrun.py`), `--final`; plugin LOOP GUARD blocks identical commands on unchanged files |
| Timeouts: first-token 3 min, soft 7 min (nudge "submit now"), hard 10 min; 3 attempts without improvement -> nudge; nearly half of matches on attempt 1, ~1/4 chance after attempt 3 | `agentrun.py` idle watchdog + resume nudges; plugin warnings (25 calls without autodiff, 40 without a body, STALLED). Backlog: hard attempt budget with a FRESH session from best attempt + notes |
| Functions > ~1000 instructions: models give up; macro-heavy / matrix code is a long tail | Backlog: block-wise lift with retail path tracing (see below) |
| Cheaper model for mechanical cleanup, expensive for hard functions | Backlog (single local model today) |
| Rewrite brittle matches into idiomatic C so later references are good | Backlog: `cleanup` pass after PROVEN, re-proved by autodiff (the differential makes this safe) |

## Mizuchi (the downloaded repo `mizuchi/`) and its open issues
Sources: the repo in this project (read: `src/plugins/claude-runner`, `src/shared/prompt-builder`, `src/shared/mizuchi-db`, `mizuchi.example.yaml`), [issues](https://github.com/macabeus/mizuchi/issues), [Starting a decompilation project](https://gambiconf.substack.com/p/starting-a-decompilation-project).
Mizuchi = pipeline of plugins (get-context -> m2c -> claude-runner -> compiler -> objdiff -> decomp-permuter -> integrator), Claude sees only an MCP "compile and view assembly" tool, up to 25 retries per function, a perfect objdiff match is the only success. It already lists `dreamcast` and `saturn` (SuperH) as targets; its compiler step is a user script, so SHC under wine (our `shc.py`) could be plugged into it for BYTE matching, while our autodiff stays the BEHAVIOUR proof. Mizuchi is a byte-matcher (needs the original compiler), we have two verifiers: autodiff (emulator, always available) and bytematch (SHC, when the SDK is present).
| Mizuchi feature / issue | Our status |
|---|---|
| Tool-call limit per attempt; every tool result carries "tool calls remaining N/M"; at the limit the model must submit | plugin: footer `[dcguard] calls N/220 | phase | next` on EVERY tool result; hard limit (DC_CALL_LIMIT) blocks everything except `--final`, notes, attempts |
| TTFT timeout 3 min, soft timeout 7 min ("submit now"), hard timeout 10 min; after a hard timeout: "do NOT use the tool, write your best implementation" | `agentrun.py`: idle watchdog, SOFT deadline at 75% of the time budget (wrap-up nudge), hard stop; plugin warns at 25 calls without autodiff / 40 without a body |
| Issue #30 "Better stall action": after 3 attempts without improvement only a "think deeper" note is appended; the author wants a better strategy: stronger model, more reasoning, or give up early | `STALLED` steering restores the best attempt (`attempts.py`) and demands one new hypothesis; `agentrun.py --stall-runs 8` GIVES UP EARLY (no more tokens burned) and `--escalate provider/model` resumes the same session with a stronger model first |
| Issue #29 "Better compilation error": context prepended to the source shifts error line numbers (error at line 2500 for a 3-line snippet; negative lines) | We compile the real port file + wrapper (no prepended context), so gcc lines are true; autodiff prints the first 3000 chars of stderr. Keep this property: never concatenate hidden context in front of the agent's file |
| Issue #3 "automatically generate prompts and select the next function" (queue ordered by difficulty) | `rank.py` / `./dcre rank`: difficulty estimate x similarity to ported functions; `brief.py` is the prompt |
| Issue #4 `CodeQualityRefine` (iterate after a match to improve quality; re-verify with compiler+objdiff; metrics: complexity, `goto`, LLM score) | Backlog; the differential makes this safe (re-run `autodiff --final` after every refactor) |
| Issue #31 MCP to read the report file; #32 run pipeline in parallel | Backlog: parallel agents need separate sandboxes (`/tmp/nadi_sandbox*`) and ONE model slot per GPU (llama-server -np 1), so parallelism is limited by the local model |
| Prompt builder: up to 5 similar decompiled functions, signatures of callers/callees, types | `brief.py` SIMILAR PORTED FUNCTIONS + HOW CALLERS PASS THE ARGUMENTS + callee table |
| mizuchi-db: logistic regression on (instructions, branches, labels) -> difficulty percentile; Decomp Atlas function cloud | `rank.py` heuristic (also floats, calls, stack args, loop counts, indirect jumps); train a real model once enough ledger results exist |
| capped-output.ts: cap tool output | plugin caps shell output at 7000 chars (head+tail) |
| Permuter in the background on Claude's best attempts, output used only if perfect | Not used: author of the N64 posts removed the permuter (agents optimise noise) |

Lessons from "Starting a decompilation project" (GBA, but generic), mapped to Dreamcast:
- Function list = disassembler + Ghidra + AI search, merged and pruned; ~20% of functions are only reachable through function-pointer tables -> our `discover.py indirect` and the brief's INDIRECT callee marker; a misplaced boundary makes a fragment that falls into the next function -> backlog `discover.py fragments` (no `rts`/unconditional jump at the end).
- Separate data from code: literal pools / jump tables decoded as instructions inflate diffs and mislead agents -> `sh4_annotate` already resolves pools; keep `discover.py gaps` clean.
- Progress as share of code BYTES, not function count -> `triage.py summary` already reports bytes (done 11.4% / rules 26.8%).
- Do not cheat the compiler (forks, pinned registers, asm barriers) -> keep SHC from the SDK as the reference; GCC fallback is never a match.
- Order: small clean functions first, batches, match-review-merge-report -> `rank.py`, `agentrun.py` report per function.
- AI output is verbose and messy: cleanup pass after a match, cognitive debt -> keep the human-readable `notes.py` facts and the post-PROVEN cleanup backlog.

## Static recompilation of Dreamcast code
Sources: [chuchu (ChuChu Rocket! on dcrecomp)](https://raw.githubusercontent.com/sp00nznet/chuchu/HEAD/README.md), [flycast-wasm (SH-4 dynamic recompiler to WASM)](https://github.com/nasomers/flycast-wasm).
| Finding | Adopted as / backlog |
|---|---|
| One missing opcode cascaded into 5 symptoms (DIV0U/DIV1 -> tile grid 640x15, 32x display list ...). Sweep the generated source for unimplemented opcodes BEFORE debugging symptoms | brief HAZARDS lists SPECIAL OPCODES present (div0u/div1, fsca/ftrv/fipr, mac, privileged, indirect jumps). Backlog: `opcheck.py` that scans a function against the emulator's/oracle's supported set |
| Explicit, countable stubs; remove each when real behaviour exists | Our host callbacks (NdHost) already are explicit; backlog: a stub ledger `work/stubs.tsv` |
| Env-gated diagnostics (first-write register log, write watchpoints with call chain, indirect-call history in crash reports) | Backlog for the PC port: indirect-call history ring buffer in `ports/pc` |
| Run the real co-processor code (ARM7 interpreter booting the sound driver) instead of faking | Noted for the audio port phase |
| Validate against prior art (Flycast for register semantics; tbg-decomp SH-4 simulator) | Already: Flycast save states + differential; backlog: cross-check autodiff against a second emulator for FPU ops |

## opencode plugins
Sources: [opencode plugin docs](https://opencode.ai/docs/plugins.md), [opencode v2 todo/spec](https://upd.dev/anomalyco/opencode/src/branch/dev/specs/v2/todo.md), [OpenClaw loop detection](https://docs.openclaw.ai/vi/tools/loop-detection), [opencode-ralph-loop](https://socket.dev/npm/package/opencode-ralph-loop).
| Finding | Adopted as |
|---|---|
| Compaction hook can inject context or REPLACE the prompt | v2 `compaction` hook: the plugin supplies the summary itself (`result.summary`) from notes + ledger + failing commands + history, so a 27B model never summarises (it lost facts and wasted minutes). `DCGUARD_MODEL_SUMMARY=1` restores the model summary |
| `tool.execute.before` can mutate args or throw | blocking + autodiff timeout raise (v2: `input` is mutable) |
| OpenClaw: a second guard after a compaction-triggered retry aborts when the same tool+args+result repeats | Backlog: fingerprint (tool,args,result) across compaction boundaries; today LOOP GUARD keys on command + file state |
| Ralph loop: keep working until a completion promise is seen | `agentrun.py` already resumes until the LEDGER says FINAL PROVEN (promise-free) |
| Custom tools via the plugin (typed args, no invented flags) | Backlog: register `dc_brief`, `dc_autodiff(mode)`, `dc_readmem`, `dc_note` as native tools through `ctx.tool.transform(editor.add(...))` (v2 ToolEditor) so the model cannot invent flags |
| `shell.env` hook | Backlog: inject DC_AGENT/PYTHONHASHSEED=0 in every shell |
| v2 roadmap: agent loop and compaction being reworked | Re-test the plugin after each opencode update (`tests/test_dcguard.mjs` + the compaction smoke test in docs/GUARDRAILS.md) |

## Ghidra + local LLM stacks
Sources: [GhidrAssist](https://docsearch.algolia.com/mcp/docs/repo/symgraph/ghidrassist), [GhidraMCP/pyghidra-mcp workshop](https://ringzer0.training/countermeasure25-workshop-supercharging-ghidra-build-your-own-private-local-llm-re-stack-with-ghidramcp-ollama-and-openwebui/), [re-mcp (headless pyhidra)](https://pypi.org/project/re-mcp/).
Takeaways: local models are used mainly for renaming and summaries inside Ghidra; headless MCP servers exist. Our setup is different (differential proof instead of chat), but naming could be automated: after a function is PROVEN, a cheap pass can propose names/struct field names for `ghidra/names.tsv`, validated only by humans.

## Backlog ranked by expected value (not done yet)
1. Fresh-session attempts: after N autodiff runs without improvement, restart the session from `attempts best` + notes (agentrun).
2. Native typed tools in the plugin (no invented flags at all).
3. Block-wise lift for functions > 300 instructions: per-basic-block checkpoints using the retail path (T tokens) to localise the first diverging block.
4. `opcheck.py` (unsupported/special opcode sweep) and indirect-call resolution report in the brief.
5. Post-PROVEN cleanup pass (idiomatic C, re-proved) and name/field-name proposals.
6. Scheduling by similarity to PROVEN ports in `./dcre next`.

## Status of the Flycast / behavioural-check plan (2026-10-15 evening)
Mizuchi's unmerged `behavioral-match` branch (in the downloaded repo): `BehavioralMatchPlugin` runs original and candidate in a custom ARM7TDMI emulator (`@sgba/arm-emulator`) with the same seeded random scenarios and compares return value, memory writes (address/size/value), order-sensitive MMIO writes, external calls and completion (instruction limit); mismatches are fed back to the model (`buildBehavioralFollowUpPrompt`); `sgba` CLI = scriptable emulator with save-state loading; a GBA Debugger UI steps through scenarios.
- DONE step 1: write-trace comparison (`write_trace`), including order/count/width of stores, in autodiff (Ghidra emulator hook + port accessors + hints).
- DONE step 3: `dcprobe` over Flycast's own GDB stub (capture/hot/profile/peek), replay via `captured`; stub race fixed by a patch and a patched build.
- NOT DONE: own SH-4 interpreter (step 2), Flycast fork with no-window mode / deterministic time / override hook (step 4).
