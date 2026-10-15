// dcguard core: pure logic shared by the opencode (v2) plugin adapter and the node unit test (tests/test_dcguard.mjs).
// Goals (each one fixes a failure seen in the local-model runs):
//   1. re-inject AGENTS.md + skill rules + the notes file into EVERY request and into compaction, so a compaction summary can never erase them
//   2. block loops: the same command on unchanged files again and again
//   3. block invented tool scripts / flags the project does not have, hand-reads of the retail image, seed hunting, tiny --cases, AD_ALLOW_WEAKER
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

export const CALL_LIMIT = Number(process.env.DC_CALL_LIMIT || 220);
export const OUT_CAP = Number(process.env.DC_OUT_CAP || 7000);
export const SHELL_TOOLS = new Set(["shell", "bash"]);
const ERR_RE = /No such file|can't open|usage:|Traceback|command not found|SPEC LINT ERROR|SPEC ERROR|PORT RUN ABORTED|port build failed|Illegal|unrecognized arguments|LOOP GUARD|BLOCKED/i;

export function readSafe(p, max = 20000) {
  try { const s = fs.readFileSync(p, "utf8"); return s.length > max ? s.slice(0, max) + "\n...(truncated)" : s; } catch { return ""; }
}

export function sections(md, wanted) {
  // keep the "## ..." sections whose heading matches one of the regexes
  const out = [];
  const parts = md.split(/^(?=## )/m);
  for (const p of parts) {
    const head = (p.match(/^## .*/) || [""])[0];
    if (head && wanted.some((r) => r.test(head))) out.push(p.trim());
  }
  return out.join("\n\n");
}

function newestNotes(dir, addr) {
  const nd = path.join(dir, "work", "notes");
  try {
    if (addr) { const f = path.join(nd, `fn_${addr}.md`); if (fs.existsSync(f)) return [f, readSafe(f, 6000)]; }
    const files = fs.readdirSync(nd).filter((x) => x.endsWith(".md")).map((x) => path.join(nd, x))
      .sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs);
    if (files.length) return [files[0], readSafe(files[0], 6000)];
  } catch {}
  return [null, ""];
}

function ledgerLine(dir, addr) {
  try {
    const pd = path.join(dir, "work", "proofs");
    const f = addr ? path.join(pd, `${addr}.json`) : null;
    if (!f || !fs.existsSync(f)) return "no autodiff ledger yet";
    const led = JSON.parse(fs.readFileSync(f, "utf8"));
    const runs = led.runs || [];
    const last = runs[runs.length - 1];
    return last ? `${runs.length} autodiff runs so far; newest: ${last.result.slice(0, 220)}${last.final ? " [FINAL]" : ""}` : "ledger empty";
  } catch { return "ledger unreadable"; }
}

export class Guard {
  constructor(dir, env = process.env) {
    this.dir = dir; this.env = env;
    this.addr = (env.DC_AGENT_ADDR || "").replace(/^0x/, "").toLowerCase().slice(-8);
    this.calls = []; this.nCalls = 0; this.errStreak = 0; this.blocked = 0; this.sinceAutodiff = 0; this.history = []; this.failures = []; this.lastCmd = "";
  }

  pinned() {
    const agents = readSafe(path.join(this.dir, "AGENTS.md"), 40000);
    const rules = sections(agents, [/Headless/i, /Guard rails/i, /First thing/i, /Per function/i, /Hygiene/i, /Commands/i]) || agents.slice(0, 7000);
    const skill = readSafe(path.join(this.dir, ".agents", "skills", "decomp-function", "SKILL.md"), 30000) ||
                  readSafe(path.join(this.dir, ".claude", "skills", "decomp-function", "SKILL.md"), 30000);
    const [nf, notes] = newestNotes(this.dir, this.addr);
    const state = [
      `function: ${this.addr || "(not set)"}   tool calls so far: ${this.nCalls}   consecutive failing calls: ${this.errStreak}   blocked repeats: ${this.blocked}`,
      `autodiff ledger: ${ledgerLine(this.dir, this.addr)}`,
      nf ? `NOTES (${path.relative(this.dir, nf)}):\n${notes}` : "NOTES: none yet. Write each fact you establish with: python3 -I tools/dc/notes.py add 0xADDR \"fact\"",
    ].join("\n");
    const budget = this.nCalls > 150 ? "\nBUDGET: you have used >150 tool calls. Stop exploring: either finish the proof now or report NOT DONE with the evidence you have." :
                   this.nCalls > 90 ? "\nBUDGET: >90 tool calls used. Prefer finishing; every new idea must be recorded with notes.py tried." : "";
    return [
      "=== PINNED PROJECT RULES (re-injected by the dcguard plugin on every request and every compaction; they are authoritative and survive summaries) ===",
      rules,
      "--- skill decomp-function (full text) ---",
      skill,
      "=== NON-NEGOTIABLE REMINDERS ===",
      "1. The retail binary and Ghidra are right; if they look wrong YOU made an offset/width error. Read memory ONLY with `python3 -I tools/dc/readmem.py 0xADDR`. Never open 1ST_READ.BIN by hand.",
      "2. A mismatch is always a port bug. Never weaken the spec, never change --seed, never lower --cases. The judge run is `autodiff.py SPEC --final`.",
      "3. `PORT RUN ABORTED` / hangs are NOT emulator problems: an unbounded count argument. Add the suggested \"arg_limits\" to the spec.",
      "4. Do not repeat a command whose inputs did not change. After 2 failures of one approach, write `notes.py tried` and change approach. No debug prints in the port.",
      "5. Only the commands listed in the skill exist. Do not invent tools or flags; run `<tool> --help` once if unsure.",
      "6. If you cannot finish, say `NOT DONE` and quote the last RESULT line. Never claim PROVEN without the literal RESULT: PROVEN line of a --final run.",
      "=== FUNCTION BRIEF (tools/dc/brief.py; facts read from the asm, classifications are hypotheses) ===", this.briefSummary() || "(not generated yet)",
      "=== CURRENT STATE ===", state + budget,
      "=== STEERING ===", this.steering(),
    ].join("\n\n");
  }

  briefSummary() {
    if (!this.addr) return "";
    const t = readSafe(path.join(this.dir, "work", "brief", `fn_${this.addr}.md`), 60000);
    if (!t) return "";
    const cut = t.indexOf("## FULL ANNOTATED LISTING");
    const head = cut > 0 ? t.slice(0, cut) : t;
    return head.length > 7000 ? head.slice(0, 7000) + "\n...(see the full brief file)" : head;
  }

  // where the work stands, derived from files and the proof ledger only (never from what the model says)
  phase() {
    const a = this.addr; if (!a) return { name: "none", next: "" };
    const has = (rel) => fs.existsSync(path.join(this.dir, rel));
    const T = `python3 -I tools/dc/`;
    if (!has(`work/brief/fn_${a}.md`)) return { name: "brief", next: `Run \`${T}brief.py 0x${a}\` NOW: one page with inputs (pointers, stack args, loop counts), callees, constants, hazards. It replaces ~30 exploration calls. Do not read other ports or grep asm first.` };
    if (!has(`port/tests/spec_${a}.json`)) return { name: "spec", next: `Run \`${T}specgen.py 0x${a}\`: it writes the spec (pointer/stack regions, loop limits), a COMPLETE wrapper and the port skeleton port/fn_${a}.c. Do not write the spec or wrapper by hand.` };
    const port = readSafe(path.join(this.dir, `port/fn_${a}.c`), 200000);
    if (!port || /#\s*error\s+"port not written"/.test(port)) return { name: "write", next: `Write the BODY of port/fn_${a}.c now (the skeleton already has the inputs, constants as K_*/KF_* macros and call_<addr>() helpers). Translate the annotated listing block by block (\`${T}sh4_annotate.py 0x${a}\` or the listing at the end of work/brief/fn_${a}.md); remove the #error line; then run portlint and autodiff.` };
    let led = null;
    try { led = JSON.parse(fs.readFileSync(path.join(this.dir, "work", "proofs", `${a}.json`), "utf8")); } catch {}
    const last = led && led.runs && led.runs[led.runs.length - 1];
    if (!last) return { name: "first-run", next: `Run \`${T}portlint.py 0x${a} port/fn_${a}.c --spec port/tests/spec_${a}.json\` and fix its ERRORs, then \`${T}autodiff.py port/tests/spec_${a}.json\`.` };
    const r = last.result || "";
    if (/PORT RUN ABORTED|AD_LOOP_BOUND|AD_CASE_TIMEOUT/.test(r)) return { name: "loop", next: "The port/retail loop never ends for some generated value: ADD the \"arg_limits\" line autodiff printed (the count argument it bisected) to the spec, rerun." };
    if (/port build failed|SPEC LINT|SPEC ERROR/.test(r)) return { name: "build", next: "Fix the build/spec error printed by the last autodiff run (read its first lines), then rerun." };
    if (/mismatch/i.test(r)) return { name: "fix-mismatch", next: "Fix the PORT using the first MISMATCH block of the last run: it names the args, the first differing call/byte, the annotated RETAIL path and a HINT. Open the listing at those addresses; mirror compare kind, width, order of calls. Never touch the spec to make it pass." };
    if (/never executed/.test(r)) return { name: "coverage", next: "Retail instructions were never executed: make the inputs reach them (spec args list / word_choice / patch for the compared value), then rerun. The uncovered addresses are in the run output." };
    if (/mutants survived/.test(r)) return { name: "mutants", next: "Surviving mutants name file:line your inputs cannot tell apart: ADD inputs (boundary values, both outcomes, loop iterations, table ends at BOTH ends) per the printed hints, rerun with --mutate." };
    if (/RESULT: PROVEN/.test(r) && !last.final) return { name: "final", next: `Provisional PROVEN. Run \`${T}autodiff.py port/tests/spec_${a}.json --final\` and quote ITS result line.` };
    if (/RESULT: PROVEN/.test(r) && last.final) return { name: "done", next: "DONE: the FINAL judge run is PROVEN. Write the report (STATUS: PROVEN, the literal RESULT line, what autodiff covered, HYPOTHESES) and stop." };
    return { name: "continue", next: `Last result: ${r.slice(0, 160)}. Fix what it says, rerun autodiff (with --mutate once mismatches are 0).` };
  }

  scores() {
    try {
      const led = JSON.parse(fs.readFileSync(path.join(this.dir, "work", "proofs", `${this.addr}.json`), "utf8"));
      return (led.runs || []).map((r) => { const m = /(\d+) mismatches/.exec(r.result || ""); const f = /(\d+) emulator faults/.exec(r.result || ""); return (m ? +m[1] : 0) + (f ? +f[1] : 0) + ((r.result || "").includes("PROVEN") && !/NOT PROVEN/.test(r.result) ? 0 : 0); });
    } catch { return []; }
  }

  // deterministic compaction summary: facts, not a 27B model's recollection
  summary() {
    const a = this.addr; const [nf, notes] = newestNotes(this.dir, a);
    const sc = this.scores();
    return [
      `# Session summary (written by the dcguard plugin from files and tool history, NOT by the model; trust it)`,
      `Task: port retail function 0x${a || "?"} and prove it with python3 -I tools/dc/autodiff.py port/tests/spec_${a}.json --final. Tool calls so far: ${this.nCalls}.`,
      this.steering(),
      `## Notes you wrote (verbatim)`, notes || "(none)",
      `## Autodiff history (mismatch+fault count per run, oldest first)`, sc.length ? sc.join(", ") : "(no run yet)", `Ledger: ${ledgerLine(this.dir, a)}`,
      `Best attempt so far: python3 -I tools/dc/attempts.py list 0x${a}   (restore with attempts.py restore 0x${a} best)`,
      `## Last failing commands`, this.failures.length ? this.failures.map((f) => `- ${f.cmd}\n    -> ${f.err}`).join("\n") : "(none)",
      `## Recent distinct commands (oldest first)`, this.history.slice(-14).map((c) => "- " + c).join("\n") || "(none)",
      `## Files`, ["port/fn_" + a + ".c", "port/tests/spec_" + a + ".json", "work/brief/fn_" + a + ".md"].map((r) => `- ${r}: ${fs.existsSync(path.join(this.dir, r)) ? "exists" : "missing"}`).join("\n"),
      `Re-read work/brief/fn_${a}.md (inputs/hazards) and the notes before acting; do NOT re-derive facts that are in the notes.`,
    ].join("\n");
  }

  // one short line appended to every tool result: the freshest context is the strongest steering (Mizuchi appends the remaining tool calls the same way)
  footer() {
    const ph = this.phase();
    const left = Math.max(0, CALL_LIMIT - this.nCalls);
    let t = `\n\n[dcguard] calls ${this.nCalls}/${CALL_LIMIT}` + (left < 40 ? ` (ONLY ${left} LEFT: finish or report NOT DONE)` : "") + ` | phase: ${ph.name} | next: ${ph.next.replace(/\s+/g, " ").slice(0, 150)}`;
    return t;
  }

  // keep head and tail of a long tool output (unasked-for context was ignored by agents and burned tokens)
  cap(text) {
    if (typeof text !== "string" || text.length <= OUT_CAP) return text;
    const head = Math.floor(OUT_CAP * 0.55), tail = OUT_CAP - head;
    return text.slice(0, head) + `\n...[dcguard: ${text.length - OUT_CAP} chars omitted; narrow the query with grep -n / sed -n 'a,bp' / head]...\n` + text.slice(-tail);
  }

  steering() {
    const ph = this.phase();
    const out = [`PHASE: ${ph.name}`, `NEXT ACTION: ${ph.next}`];
    if (this.errStreak >= 3) out.push("WARNING: your last calls failed in a row. Stop guessing: re-read the BLOCKED/usage text, run the tool with --help ONCE, or follow the command list in the skill.");
    if (this.sinceAutodiff >= 25 && ["fix-mismatch", "first-run", "mutants", "coverage"].includes(ph.name)) out.push(`WARNING: ${this.sinceAutodiff} calls since your last autodiff run. Edit the port from what you already know and RUN it; autodiff takes ~20 s and is the only judge.`);
    const sc = this.scores();
    if (sc.length >= 4) {
      const last3 = sc.slice(-3), before = sc.slice(0, -3), bestBefore = Math.min(...before);
      if (before.length && Math.min(...last3) >= bestBefore && ["fix-mismatch", "continue"].includes(ph.name)) out.push(`STALLED: the last 3 autodiff runs (${last3.join(", ")}) did not beat the best earlier run (${bestBefore}). Restore it (python3 -I tools/dc/attempts.py restore 0x${this.addr} best), write ONE prediction + post-mortem with notes.py tried, then change ONE thing.`);
    }
    if (ph.name === "write" && this.nCalls > 40) out.push("WARNING: >40 calls and still no port body. A wrong first draft that autodiff can criticise beats more reading: write it now.");
    return out.join("\n");
  }

  compactionNote() {
    return "\n\nWHEN WRITING THE COMPACTION SUMMARY keep VERBATIM: (a) the full text of the NOTES section above, (b) the last failing command with its exact error, " +
           "(c) the list of approaches already tried and their result, (d) the exact next step. Do not summarise the pinned rules; they are re-injected automatically.";
  }

  fingerprint() {
    // state hash of the files the agent edits: an identical command is only a loop if none of them changed
    const h = crypto.createHash("sha1");
    for (const d of ["port", path.join("port", "tests"), path.join("work", "notes")]) {
      try {
        for (const f of fs.readdirSync(path.join(this.dir, d)).sort()) {
          const st = fs.statSync(path.join(this.dir, d, f));
          if (st.isFile()) h.update(`${d}/${f}:${st.size}:${Math.floor(st.mtimeMs)};`);
        }
      } catch {}
    }
    return h.digest("hex").slice(0, 12);
  }

  toolExists(rel) {
    return [rel, rel.replace(/^tools\/dc\//, "tools/"), rel.replace(/^tools\//, "tools/dc/")].some((r) => fs.existsSync(path.join(this.dir, r)));
  }

  listTools() {
    const useful = ["brief.py", "dcprobe.py", "sh4_annotate.py", "specgen.py", "portlint.py", "autodiff.py", "readmem.py", "notes.py", "triage.py", "dcfacts.py", "proofcheck.py", "bytematch.py", "discover.py", "shc.py"];
    return useful.filter((x) => this.toolExists(`tools/dc/${x}`));
  }

  // returns null (allow) or a string (block reason; thrown by the adapter)
  before(tool, input) {
    this.nCalls++;
    this.sinceAutodiff = (SHELL_TOOLS.has(tool) && /autodiff\.py/.test(String(input && (input.command ?? input.cmd) || ""))) ? 0 : this.sinceAutodiff + 1;
    if (!SHELL_TOOLS.has(tool) || !input) { this.track(tool, JSON.stringify(input || {})); return null; }
    const cmd = String(input.command ?? input.cmd ?? "");
    this.lastCmd = cmd.replace(/\s+/g, " ").trim().slice(0, 200);
    if (this.lastCmd && this.history[this.history.length - 1] !== this.lastCmd) { this.history.push(this.lastCmd); if (this.history.length > 40) this.history.shift(); }
    const reasons = [];
    if (this.nCalls > CALL_LIMIT && !/(autodiff\.py[^|;&\n]*--final|notes\.py|attempts\.py)/.test(cmd)) reasons.push(`Tool call limit reached (${CALL_LIMIT}). Stop exploring. Either run \`autodiff.py SPEC --final\` now, or write the final report: \`NOT DONE\` + the last RESULT line + what you learned (notes.py show). Mizuchi-style: submit the best you have.`);
    if (/AD_ALLOW_WEAKER/.test(cmd)) reasons.push("AD_ALLOW_WEAKER is a human-only override. Fix the port instead of weakening the proof.");
    if (/work\/proofs/.test(cmd) && /\b(rm|mv|truncate|sed\s+-i|>)\b/.test(cmd)) reasons.push("work/proofs/ is the proof ledger: it is append-only evidence. Do not edit or delete it.");
    if (/--seed\b/.test(cmd) && !/--final/.test(cmd)) reasons.push("--seed hunting is forbidden: a mismatch exists for other seeds too. The judge run is `autodiff.py SPEC --final` (fixed seed 7, 300 cases, 60 mutants).");
    const mc = cmd.match(/autodiff\.py[^|;&\n]*--cases\s+(\d+)/);
    if (mc && Number(mc[1]) < 40) reasons.push(`--cases ${mc[1]} is below the floor (40). A normal run takes ~20 s; use the default case count so the ledger and the weak-spec check stay meaningful.`);
    if (/1ST_READ\.BIN|Track_3\/|\.BIN['"]/.test(cmd) && !/(readmem|sh4_annotate|specgen|autodiff|bytematch|discover|dcre|triage|ls |stat |file |sha|md5)/.test(cmd)) {
      reasons.push("Do not open the retail image by hand (wrong offsets once convinced a model the binary was 'corrupt'). Use `python3 -I tools/dc/readmem.py 0x8cXXXXXX [len]` (takes the VIRTUAL address) or `sh4_annotate.py`.");
    }
    for (const m of cmd.matchAll(/\btools\/(?:dc\/)?([A-Za-z0-9_]+\.py)/g)) {
      const rel = `tools/dc/${m[1]}`;
      if (!this.toolExists(rel)) reasons.push(`tools/dc/${m[1]} does not exist. Existing tools: ${this.listTools().join(", ")}.`);
      if (m[1] === "nd_golden.py" && this.env.DC_AGENT === "1") reasons.push("nd_golden.py is the human-side differential for core/ ports; your proof tool is `autodiff.py` (see the skill).");
    }
    if (/\bdcre\.py\s+(disasm|disassemble|decompile)\b/.test(cmd)) reasons.push("dcre has no disasm/decompile command: use `python3 -I tools/dc/sh4_annotate.py 0xADDR`.");
    if (/--build-only|--no-emulator|--skip-emulator/.test(cmd)) reasons.push("autodiff has no such flag. Flags: --cases N --seed S --keep --mutate [N] --final.");
    if (!reasons.length) {
      const key = cmd.replace(/\s+/g, " ").trim() + "|" + this.fingerprint();
      const recent = this.calls.slice(-10).filter((k) => k === key).length;
      this.track(tool, key);
      if (recent >= 2) reasons.push(`LOOP GUARD: you ran this exact command ${recent + 1} times and no file in port/ or work/notes changed in between, so the output will be the same. ` +
        `Write down what you know (python3 -I tools/dc/notes.py tried ADDR "..."), then CHANGE something: edit the port/spec, or ask a different question. After a few blocked repeats, report NOT DONE with the evidence.`);
    } else this.track(tool, "blocked:" + cmd.slice(0, 80));
    if (reasons.length) { this.blocked++; return "BLOCKED by dcguard: " + reasons.join(" | "); }
    return null;
  }

  track(tool, key) { this.calls.push(key); if (this.calls.length > 40) this.calls.shift(); }

  after(tool, output) {
    const s = typeof output === "string" ? output : JSON.stringify(output || "");
    if (ERR_RE.test(s.slice(0, 4000))) { this.errStreak++; this.failures.push({ cmd: this.lastCmd, err: s.replace(/\s+/g, " ").slice(0, 280) }); if (this.failures.length > 6) this.failures.shift(); } else this.errStreak = 0;
  }
}
