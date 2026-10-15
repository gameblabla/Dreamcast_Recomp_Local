//Apply curated names/comments from a TSV: address<TAB>name<TAB>kind(func|data|label)<TAB>comment
//@category Dreamcast
import java.io.*;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;

public class DrNames extends GhidraScript {
	@Override
	protected void run() throws Exception {
		File f = new File(getScriptArgs().length > 0 ? getScriptArgs()[0] : "names.tsv");
		int n = 0, bad = 0;
		try (BufferedReader r = new BufferedReader(new FileReader(f))) {
			String line;
			while ((line = r.readLine()) != null) {
				if (line.startsWith("#") || line.isBlank()) continue;
				String[] c = line.split("\t", 4);
				if (c.length < 2) continue;
				Address a = toAddr(Long.parseLong(c[0].trim().replace("0x", ""), 16));
				String name = c[1].trim(), kind = c.length > 2 ? c[2].trim() : "func";
				String cmt = c.length > 3 ? c[3].trim() : "";
				try {
					if (kind.equals("func")) {
						Function fn = getFunctionAt(a);
						if (fn == null) { createFunction(a, name); fn = getFunctionAt(a); }
						if (fn == null) { bad++; continue; }
						fn.setName(name, SourceType.USER_DEFINED);
						if (!cmt.isEmpty()) fn.setComment(cmt);
					} else {
						currentProgram.getSymbolTable().createLabel(a, name, SourceType.USER_DEFINED);
						if (!cmt.isEmpty()) currentProgram.getListing().setComment(a, CodeUnit.EOL_COMMENT, cmt);
					}
					n++;
				} catch (Exception e) { println("names: " + c[0] + " " + e.getMessage()); bad++; }
			}
		}
		println("applied names: " + n + " failed: " + bad);
	}
}
