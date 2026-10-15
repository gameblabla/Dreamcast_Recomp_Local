//Discover SH-4 functions Ghidra's analyzers missed: entry jump, pointer-table targets, and gap code after function ends.
//Also types 4-byte words that point at function entries so xrefs/decompiler see them.
//@category Dreamcast
import java.util.*;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.app.cmd.function.CreateFunctionCmd;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.*;
import ghidra.program.model.data.PointerDataType;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.symbol.*;

public class DrFindCode extends GhidraScript {
	long LO, HI;                       // image range (set from the program in run())

	// the loaded game image = the first INITIALIZED memory block (the synthetic RAM/MMIO blocks are uninitialized)
	ghidra.program.model.mem.MemoryBlock imageBlock() {
		for (ghidra.program.model.mem.MemoryBlock b : currentProgram.getMemory().getBlocks()) if (b.isInitialized()) return b;
		return currentProgram.getMemory().getBlocks()[0];
	}
	List<long[]> codeRanges = new ArrayList<>();   // optional script arg "lo-hi,lo-hi" (hex); default: the whole image
	Listing l;
	Memory mem;

	// code windows of 1ST_READ.BIN (determined from per-64KiB coverage: the rest is rodata/data/bss)
	boolean inCode(long a) {
		for (long[] r : codeRanges) if (a >= r[0] && a < r[1]) return true;
		return false;
	}

	boolean undefinedAt(Address a) {
		CodeUnit cu = l.getCodeUnitContaining(a);
		return cu instanceof Data && !((Data) cu).isDefined() && cu.getMinAddress().equals(a);
	}

	// first halfword plausibly starts a function (gcc SH prologue or tiny leaf)
	boolean prologue(int hw) {
		int hi = hw & 0xff00;
		if ((hw & 0xf0ff) == 0x2006 && (hw & 0x0f00) >= 0x0f00 && (hw & 0xf000) == 0x2000) return true; // mov.l rN,@-r15
		if (hw == 0x4f22 || hw == 0x4f02 || hw == 0x4f12 || hw == 0x4f32 || hw == 0x4f52 || hw == 0x4f62) return true; // sts.l ...,@-r15
		if (hi == 0x7f00 && (hw & 0x80) != 0) return true; // add #-n,r15
		if ((hw & 0xf0ff) == 0x4f03 || (hw & 0xff00) == 0xe500) return false;
		if ((hw & 0xf0ff) == 0x2f06 || (hw & 0xf0ff) == 0x2f06) return true;
		if ((hw & 0xff00) == 0xd000 || (hw & 0xff00) == 0x9000 || (hw & 0xff00) == 0xe000) return true; // mov.l/w @(disp,pc), mov #imm
		if ((hw & 0xf00f) == 0x6003 || (hw & 0xf00f) == 0x2002 || (hw & 0xf00f) == 0x2000 || (hw & 0xf00f) == 0x2001) return true;
		if ((hw & 0xff00) == 0x8100 || (hw & 0xff00) == 0x8500 || (hw & 0xff00) == 0x8400 || (hw & 0xff00) == 0x8000) return true;
		if (hw == 0x000b) return true; // rts
		return (hw & 0xf000) == 0x4000 || (hw & 0xf000) == 0x6000 || (hw & 0xf000) == 0x7000 || (hw & 0xf000) == 0xf000;
	}

	boolean makeFunction(Address a) {
		if (!inCode(a.getOffset()) || !undefinedAt(a)) return false;
		DisassembleCommand dc = new DisassembleCommand(a, null, true);
		dc.applyTo(currentProgram, monitor);
		Instruction in = l.getInstructionAt(a);
		if (in == null) return false;
		Function f = getFunctionAt(a);
		if (f == null) {
			CreateFunctionCmd c = new CreateFunctionCmd(a);
			if (!c.applyTo(currentProgram, monitor)) return false;
		}
		return true;
	}

	@Override
	protected void run() throws Exception {
		l = currentProgram.getListing();
		mem = currentProgram.getMemory();
		int total = 0;
		// entry
		LO = imageBlock().getStart().getOffset();
		HI = imageBlock().getEnd().getOffset() + 1;
		String[] sa = getScriptArgs();
		if (sa.length > 0) for (String r : sa[0].split(",")) { String[] lh = r.split("-"); codeRanges.add(new long[] {Long.parseLong(lh[0], 16), Long.parseLong(lh[1], 16)}); }
		else codeRanges.add(new long[] {LO, HI});
		Address e = toAddr(sa.length > 1 ? Long.parseLong(sa[1], 16) : LO);   // entry (optional 2nd arg)
		if (makeFunction(e)) { total++; getFunctionAt(e).setName("_start", SourceType.USER_DEFINED); }
		for (int round = 0; round < 12; round++) {
			int found = 0;
			Set<Long> seeds = new TreeSet<>();
			// (a) 4-byte aligned words that look like code pointers
			for (long a = LO; a + 4 <= HI; a += 4) {
				Address ad = toAddr(a);
				long v = mem.getInt(ad) & 0xffffffffL;
				if (!inCode(v) || (v & 1) != 0) continue;
				Address t = toAddr(v);
				if (!undefinedAt(t)) continue;
				int hw = mem.getShort(t) & 0xffff;
				// words living in data (jump/handler/callback tables) are trusted; literal-pool words must look like a prologue
				boolean fromData = !inCode(a);
				if (hw == 0 || (!fromData && !prologue(hw))) continue;
				// word itself must not be inside instruction stream (literal pool/data only)
				CodeUnit cu = l.getCodeUnitContaining(ad);
				if (cu instanceof Instruction) continue;
				seeds.add(v);
			}
			// (b) code immediately following a function body (aligned 2) that begins with a prologue
			for (FunctionIterator it = currentProgram.getFunctionManager().getFunctions(true); it.hasNext();) {
				Function f = it.next();
				long end = f.getBody().getMaxAddress().getOffset() + 1;
				if (!inCode(end)) continue;
				for (long x = end; x < end + 64 && x < HI; x += 2) {
					Address xa = toAddr(x);
					CodeUnit cu = l.getCodeUnitContaining(xa);
					if (cu instanceof Data && ((Data) cu).isDefined()) { // skip literal pool words
						x = cu.getMaxAddress().getOffset() + (cu.getMaxAddress().getOffset() & 1);
						continue;
					}
					if (cu instanceof Instruction) break;
					int hw = mem.getShort(xa) & 0xffff;
					if (hw != 0 && (hw == 0x2fe6 || hw == 0x4f22 || (hw & 0xf0ff) == 0x2f06 || (hw & 0xff00) == 0x7f00) && (x & 3) == 0) {
						seeds.add(x);
						break;
					}
					if (hw != 0 && hw != 0x0009) break;
				}
			}
			for (long s : seeds) if (makeFunction(toAddr(s))) found++;
			println("round " + round + ": seeds=" + seeds.size() + " new functions=" + found);
			total += found;
			if (found == 0) break;
		}
		// (d) disassembled code that no function owns (jump/handler-table targets reached only indirectly)
		int orphans = 0;
		for (int pass = 0; pass < 4; pass++) {
			int n = 0;
			for (InstructionIterator it = l.getInstructions(true); it.hasNext();) {
				Instruction in = it.next();
				Address ia = in.getAddress();
				if (!inCode(ia.getOffset()) || currentProgram.getFunctionManager().getFunctionContaining(ia) != null) continue;
				if (new CreateFunctionCmd(ia).applyTo(currentProgram, monitor)) n++;
			}
			println("orphan code pass " + pass + ": created " + n);
			orphans += n;
			if (n == 0) break;
		}
		total += orphans;
		// (c) type words pointing at function entries (jump tables / callback tables) in non-code
		int ptrs = 0;
		for (long a = LO; a + 4 <= HI; a += 4) {
			Address ad = toAddr(a);
			CodeUnit cu = l.getCodeUnitContaining(ad);
			if (cu instanceof Instruction) continue;
			if (cu instanceof Data && ((Data) cu).isDefined()) continue;
			long v = mem.getInt(ad) & 0xffffffffL;
			if (v < LO || v >= HI || (v & 1) != 0) continue;
			if (getFunctionAt(toAddr(v)) == null) continue;
			try {
				l.createData(ad, PointerDataType.dataType);
				ptrs++;
			} catch (Exception ex) { }
		}
		println("new functions total=" + total + " function pointers typed=" + ptrs);
	}
}
