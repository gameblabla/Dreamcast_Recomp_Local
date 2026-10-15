//Rename functions that match Dreamcast SDK (Katana) library CRC32 signatures. Fast version of DreamcastRE.java.
//@category Dreamcast

import java.io.*;
import java.util.*;
import java.util.zip.CRC32;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.symbol.SourceType;

public class DrSdkRename extends GhidraScript {
	@Override
	protected void run() throws Exception {
		File f = new File(getScriptArgs().length > 0 ? getScriptArgs()[0] : "sdk-symbols.txt");
		// length -> (crc -> name)
		Map<Integer, Map<Long, String>> byLen = new TreeMap<>();
		try (BufferedReader r = new BufferedReader(new FileReader(f))) {
			String line;
			while ((line = r.readLine()) != null) {
				String[] s = line.split("@");
				if (s.length < 5) continue;
				int len = Integer.parseInt(s[1]);
				if (len <= 30) continue;
				byLen.computeIfAbsent(len, k -> new HashMap<>())
					.put(Long.decode(s[0]), s[2] + "." + s[3] + "." + s[4]);
			}
		}
		println("SDK signature lengths: " + byLen.size());
		CRC32 crc = new CRC32();
		int renamed = 0;
		PrintWriter out = new PrintWriter(new FileWriter(new File(getScriptArgs().length > 1 ? getScriptArgs()[1] : "sdk_matches.tsv")));
		out.println("address\told_name\tsdk_name\tlength");
		FunctionIterator it = currentProgram.getFunctionManager().getFunctions(true);
		while (it.hasNext()) {
			Function fn = it.next();
			if (!fn.getName().startsWith("FUN_")) continue;
			for (Map.Entry<Integer, Map<Long, String>> e : byLen.entrySet()) {
				byte[] b = new byte[e.getKey()];
				try {
					if (currentProgram.getMemory().getBytes(fn.getEntryPoint(), b) != b.length) continue;
				} catch (Exception ex) { continue; }
				crc.reset();
				crc.update(b);
				String name = e.getValue().get(crc.getValue());
				if (name != null) {
					String old = fn.getName();
					String clean = name.replaceAll("[^A-Za-z0-9_.]", "_");
					fn.setName(clean, SourceType.USER_DEFINED);
					out.println(fn.getEntryPoint() + "\t" + old + "\t" + clean + "\t" + e.getKey());
					renamed++;
					break;
				}
			}
		}
		out.close();
		println("Renamed SDK functions: " + renamed);
	}
}
