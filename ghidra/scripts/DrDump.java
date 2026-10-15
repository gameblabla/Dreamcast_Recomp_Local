//Dump functions, call graph, strings, hardware accesses, disassembly and decompiled C for the whole program.
//Args: outputDir
//@category Dreamcast

import java.io.*;
import java.util.*;

import ghidra.app.decompiler.*;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.*;
import ghidra.program.model.data.StringDataInstance;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.util.task.ConsoleTaskMonitor;

public class DrDump extends GhidraScript {
	private File out;

	private PrintWriter pw(String name) throws IOException {
		return new PrintWriter(new BufferedWriter(new FileWriter(new File(out, name))));
	}

	@Override
	protected void run() throws Exception {
		out = new File(getScriptArgs().length > 0 ? getScriptArgs()[0] : "dump");
		out.mkdirs();
		new File(out, "decompiled").mkdirs();
		new File(out, "asm").mkdirs();
		Listing listing = currentProgram.getListing();
		FunctionManager fm = currentProgram.getFunctionManager();
		ReferenceManager rm = currentProgram.getReferenceManager();

		// ---- functions + call graph ----
		List<Function> funcs = new ArrayList<>();
		for (FunctionIterator it = fm.getFunctions(true); it.hasNext();) funcs.add(it.next());
		println("functions: " + funcs.size());
		try (PrintWriter f = pw("functions.tsv"); PrintWriter cg = pw("callgraph.tsv")) {
			f.println("address\tname\tbytes\tinstructions\tcallers\tcallees\tsignature");
			cg.println("caller\tcaller_name\tcallee\tcallee_name\tcall_site");
			for (Function fn : funcs) {
				Set<Function> callees = new TreeSet<>(Comparator.comparing(Function::getEntryPoint));
				callees.addAll(fn.getCalledFunctions(monitor));
				int ni = 0;
				for (InstructionIterator ii = listing.getInstructions(fn.getBody(), true); ii.hasNext(); ii.next()) ni++;
				f.println(fn.getEntryPoint() + "\t" + fn.getName() + "\t" + fn.getBody().getNumAddresses() + "\t" + ni + "\t"
					+ fn.getCallingFunctions(monitor).size() + "\t" + callees.size() + "\t" + fn.getPrototypeString(false, false));
				for (InstructionIterator ii = listing.getInstructions(fn.getBody(), true); ii.hasNext();) {
					Instruction in = ii.next();
					if (!in.getFlowType().isCall()) continue;
					for (Reference r : in.getReferencesFrom()) {
						if (!r.getReferenceType().isCall()) continue;
						Function c = fm.getFunctionAt(r.getToAddress());
						cg.println(fn.getEntryPoint() + "\t" + fn.getName() + "\t" + r.getToAddress() + "\t"
							+ (c != null ? c.getName() : "?") + "\t" + in.getAddress());
					}
				}
			}
		}

		// ---- strings (defined data) with xrefs ----
		try (PrintWriter s = pw("strings.tsv")) {
			s.println("address\tlength\txrefs_from\ttext");
			for (DataIterator di = listing.getDefinedData(true); di.hasNext();) {
				Data d = di.next();
				if (!d.hasStringValue()) continue;
				StringDataInstance sdi = StringDataInstance.getStringDataInstance(d);
				String txt = sdi.getStringValue();
				if (txt == null) continue;
				StringBuilder xr = new StringBuilder();
				for (Reference r : rm.getReferencesTo(d.getAddress())) {
					Function c = fm.getFunctionContaining(r.getFromAddress());
					if (xr.length() > 0) xr.append(',');
					xr.append(r.getFromAddress()).append(c != null ? "(" + c.getName() + ")" : "");
				}
				s.println(d.getAddress() + "\t" + d.getLength() + "\t" + xr + "\t"
					+ txt.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t"));
			}
		}

		// ---- hardware / MMIO accesses ----
		try (PrintWriter h = pw("hw_access.tsv")) {
			h.println("function\tinstruction\ttarget\ttarget_symbol\ttype");
			for (Function fn : funcs) {
				for (InstructionIterator ii = listing.getInstructions(fn.getBody(), true); ii.hasNext();) {
					Instruction in = ii.next();
					for (Reference r : in.getReferencesFrom()) {
						long a = r.getToAddress().getOffset() & 0xffffffffL;
						boolean hw = (a >= 0xa05f0000L && a < 0xa0600000L) || (a >= 0xff000000L) || (a >= 0xa0700000L && a < 0xa0a00000L)
							|| (a >= 0xa4000000L && a < 0xa5000000L) || (a >= 0x10000000L && a < 0x12000000L) || (a >= 0xa0000000L && a < 0xa0200000L)
							|| (a >= 0xfe000000L && a < 0xff000000L) || (a >= 0xe0000000L && a < 0xe4000000L);
						if (!hw) continue;
						Symbol sy = currentProgram.getSymbolTable().getPrimarySymbol(r.getToAddress());
						h.println(fn.getName() + "@" + fn.getEntryPoint() + "\t" + in.getAddress() + "\t" + r.getToAddress() + "\t"
							+ (sy != null ? sy.getName() : "") + "\t" + r.getReferenceType());
					}
				}
			}
		}

		// ---- all labels / symbols ----
		try (PrintWriter y = pw("symbols.tsv")) {
			y.println("address\tname\ttype\tsource");
			for (SymbolIterator si = currentProgram.getSymbolTable().getAllSymbols(true); si.hasNext();) {
				Symbol sy = si.next();
				y.println(sy.getAddress() + "\t" + sy.getName() + "\t" + sy.getSymbolType() + "\t" + sy.getSource());
			}
		}

		// ---- disassembly + decompiled C, one file per 64 KiB window ----
		DecompInterface di = new DecompInterface();
		DecompileOptions opts = new DecompileOptions();
		opts.grabFromProgram(currentProgram);
		opts.setRespectReadOnly(true);
		di.setOptions(opts);
		di.openProgram(currentProgram);
		ConsoleTaskMonitor tm = new ConsoleTaskMonitor();
		Map<Long, PrintWriter> cWriters = new TreeMap<>();
		Map<Long, PrintWriter> aWriters = new TreeMap<>();
		int n = 0, fail = 0;
		for (Function fn : funcs) {
			long win = fn.getEntryPoint().getOffset() & 0xffff0000L;
			PrintWriter cw = cWriters.get(win);
			PrintWriter aw = aWriters.get(win);
			if (cw == null) {
				cw = pw(String.format("decompiled/%08x.c", win));
				cWriters.put(win, cw);
				cw.println("/* " + currentProgram.getName() + " - Ghidra decompilation, window " + String.format("%08x", win) + " */");
				cw.println("typedef unsigned char undefined; typedef unsigned char undefined1; typedef unsigned short undefined2; typedef unsigned int undefined4; typedef unsigned long long undefined8;");
				aw = pw(String.format("asm/%08x.asm", win));
				aWriters.put(win, aw);
			}
			// asm
			aw.println("\n; ===== " + fn.getName() + " @ " + fn.getEntryPoint() + " =====");
			for (InstructionIterator ii = listing.getInstructions(fn.getBody(), true); ii.hasNext();) {
				Instruction in = ii.next();
				StringBuilder cmt = new StringBuilder();
				for (Reference r : in.getReferencesFrom()) {
					if (r.getReferenceType().isFlow() && !r.getReferenceType().isCall()) continue;
					Symbol sy = currentProgram.getSymbolTable().getPrimarySymbol(r.getToAddress());
					cmt.append(' ').append(r.getToAddress());
					if (sy != null) cmt.append('<').append(sy.getName()).append('>');
					Data dd = listing.getDataAt(r.getToAddress());
					if (dd != null) { ghidra.program.model.mem.MemoryBlock mb = currentProgram.getMemory().getBlock(r.getToAddress()); if (mb == null || !mb.isInitialized()) dd = null; }
					if (dd != null && dd.hasStringValue()) cmt.append(" \"").append(String.valueOf(dd.getValue()).replace("\n", "\\n")).append('"');
					else if (dd != null && dd.getLength() == 4 && r.getReferenceType().isRead()) {
						Object v = dd.getValue();
						if (v instanceof ghidra.program.model.address.Address) cmt.append(" =").append(v);
						else if (v instanceof ghidra.program.model.scalar.Scalar) cmt.append(String.format(" =0x%08x", ((ghidra.program.model.scalar.Scalar) v).getUnsignedValue()));
						else { try { cmt.append(String.format(" =0x%08x", currentProgram.getMemory().getInt(r.getToAddress()))); } catch (Exception e) {} }
					}
				}
				aw.println(in.getAddress() + ":\t" + in + (cmt.length() > 0 ? "\t;" + cmt : ""));
			}
			// C
			DecompileResults res = di.decompileFunction(fn, 90, tm);
			cw.println("\n/* ===== " + fn.getName() + " @ " + fn.getEntryPoint() + " ===== */");
			if (res != null && res.decompileCompleted()) {
				cw.println(res.getDecompiledFunction().getC());
			} else {
				fail++;
				cw.println("/* decompile failed: " + (res != null ? res.getErrorMessage() : "null") + " */");
			}
			if (++n % 200 == 0) println("decompiled " + n + "/" + funcs.size());
		}
		for (PrintWriter w : cWriters.values()) w.close();
		for (PrintWriter w : aWriters.values()) w.close();
		println("decompile done: " + n + " functions, " + fail + " failed");
	}
}
