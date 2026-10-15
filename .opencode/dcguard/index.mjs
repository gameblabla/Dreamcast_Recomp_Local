// opencode v2 plugin (directory package): `"plugins": ["./.opencode/dcguard"]` in opencode.json.
import fs from "node:fs";
import { Guard, SHELL_TOOLS } from "./core.mjs";

function mapContent(result, fn) {
  // Tool.Result.content is a string or an array of {type:"text",text} / {type:"file"}; keep every other field
  if (!result) return result;
  if (typeof result.content === "string") return { ...result, content: fn(result.content) };
  if (Array.isArray(result.content)) { const c = result.content.map((x) => (x && x.type === "text" ? { ...x, text: fn(x.text) } : x)); return { ...result, content: c }; }
  return result;
}
function appendText(result, extra) {
  if (!result) return result;
  if (typeof result.content === "string") return { ...result, content: result.content + extra };
  if (Array.isArray(result.content)) return { ...result, content: [...result.content, { type: "text", text: extra }] };
  return result;
}

export default {
  id: "dcguard",
  setup: async (ctx) => {
    const dir = ctx.location?.directory || ctx.location?.path || process.cwd();
    const g = new Guard(process.env.DC_PROJECT_DIR || dir);
    const dbg = (m) => { if (process.env.DCGUARD_LOG) { try { fs.appendFileSync(process.env.DCGUARD_LOG, new Date().toISOString() + " " + m + "\n"); } catch {} } };
    dbg("setup dir=" + dir);
    const addText = (system, text) => { system.push({ type: "text", text }); };
    await ctx.session.hook("context", (i) => { dbg("context hook, system parts=" + i.system.length + " msgs=" + i.messages.length); addText(i.system, g.pinned()); });
    await ctx.session.hook("compaction", (i) => { dbg("COMPACTION hook, system parts=" + i.system.length); addText(i.system, g.pinned() + g.compactionNote()); if (!process.env.DCGUARD_MODEL_SUMMARY) { try { i.result = { summary: g.summary() }; dbg("COMPACTION summary supplied by plugin (" + i.result.summary.length + " chars)"); } catch (e) { dbg("summary failed " + e); } } });
    await ctx.tool.hook("execute.before", (i) => {
      const why = g.before(i.tool, i.input);
      if (why) throw new Error(why);
      if (SHELL_TOOLS.has(i.tool) && i.input && /autodiff\.py/.test(String(i.input.command || "")) && !(i.input.timeout > 600000)) i.input.timeout = 900000;
    });
    await ctx.tool.hook("execute.after", (i) => {
      g.after(i.tool, i.status === "completed" ? JSON.stringify(i.result ?? "") : String(i.error?.message ?? i.error ?? "error"));
      if (i.status === "completed" && !process.env.DCGUARD_NO_FOOTER) {
        try {
          if (SHELL_TOOLS.has(i.tool)) i.result = mapContent(i.result, (t) => g.cap(t));
          i.result = appendText(i.result, g.footer());
          dbg("after " + i.tool + " footer appended");
        } catch (e) { dbg("after-hook mutation failed: " + e); }
      }
    });
  },
};
