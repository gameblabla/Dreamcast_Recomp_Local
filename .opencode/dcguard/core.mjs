// dcguard core: pure logic shared by the opencode (v2) plugin adapter and the node unit test (tests/test_dcguard.mjs).
// Goals (each one fixes a failure seen in the local-model runs):
//   1. re-inject AGENTS.md + skill rules + the notes file into EVERY request and into compaction, so a compaction summary can never erase them
//   2. block loops: the same command on unchanged files again and again
//   3. block invented tool scripts / flags the project does not have, hand-reads of the retail image, seed hunting, tiny --cases, AD_ALLOW_WEAKER
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

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
    this.calls = []; this.nCalls = 0; this.errStreak = 0; this.blocked = 0;
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
      "=== CURRENT STATE ===", state + budget,
    ].join("\n\n");
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
    const useful = ["sh4_annotate.py", "specgen.py", "portlint.py", "autodiff.py", "readmem.py", "notes.py", "triage.py", "dcfacts.py", "proofcheck.py", "bytematch.py", "discover.py", "shc.py"];
    return useful.filter((x) => this.toolExists(`tools/dc/${x}`));
  }

  // returns null (allow) or a string (block reason; thrown by the adapter)
  before(tool, input) {
    this.nCalls++;
    if (!SHELL_TOOLS.has(tool) || !input) { this.track(tool, JSON.stringify(input || {})); return null; }
    const cmd = String(input.command ?? input.cmd ?? "");
    const reasons = [];
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
    if (ERR_RE.test(s.slice(0, 4000))) this.errStreak++; else this.errStreak = 0;
  }
}
