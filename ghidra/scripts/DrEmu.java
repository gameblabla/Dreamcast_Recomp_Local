//Run retail SH-4 functions in Ghidra's SLEIGH emulator to produce golden test vectors for the portable C core.
//Usage (headless postScript): DrEmu.java <cases.txt> <results.txt>
//Case line: call <hexaddr> [rN=<hex>] [fN=<hexbits>] [w8|w16|w32:<hexaddr>=<hex>] [wbytes:<hexaddr>=<hexbytes>]
//                          [skip=<hexaddr>] (treat the function at that address as an immediate return, r0 = 0)  [skipfr0=<hexaddr>:<hexbits>] (same, and fr0 = hexbits: float-returning callee)  [skipsin=<hexaddr>] / [skipcos=<hexaddr>] (same, and fr0 = (float) sin/cos of r4's low 16 bits as turns: FSCA model)  [callog=<hexaddr>:<nint>:<nfloat>] (skipped callee: log r4.. (nint) and fr4.. (nfloat) at entry as " C<addr>=v,..,")  [skipret=<hexaddr>:<hexval>] (same, but the first call returns hexval and later calls return -1: menu stub)  [fsca=<hexaddr>] (emulate the FSCA instruction at that address: sin/cos of FPUL as 16.16 turns)  [watch=<hexaddr>] (records r0..r7,r14 each time that address executes)  [stop=<hexaddr>] [r8|r16|r32:<hexaddr>] [rbytes:<hexaddr>:<len>]
//Result line: ret=<hex r0> [<read spec>=<hex> ...]   |   "FAULT <message>" if the emulator stops abnormally.
//@category Dreamcast
import ghidra.app.script.GhidraScript;
import ghidra.app.emulator.EmulatorHelper;
import ghidra.program.model.address.Address;
import ghidra.program.model.mem.*;
import java.io.*;
import java.math.BigInteger;
import java.nio.file.*;
import java.util.*;

public class DrEmu extends GhidraScript {
	static final long STACK_TOP = 0x8d000000L - 0x100;
	static final long STEP_LIMIT = Long.parseLong(System.getenv().getOrDefault("ND_STEP_LIMIT", "20000000"));
	static final long CASE_MS = Long.parseLong(System.getenv().getOrDefault("ND_CASE_MS", "120000"));   // per-case wall-clock limit: a looping case fails in 2 minutes instead of 15+
	static long RET_ADDR;   // an address inside the program (image base + 0xc0); a breakpoint here ends the call


	// the loaded game image = the first INITIALIZED memory block (the synthetic RAM/MMIO blocks are uninitialized)
	ghidra.program.model.mem.MemoryBlock imageBlock() {
		for (ghidra.program.model.mem.MemoryBlock b : currentProgram.getMemory().getBlocks()) if (b.isInitialized()) return b;
		return currentProgram.getMemory().getBlocks()[0];
	}
	private void ensureRam() throws Exception {
		Memory m = currentProgram.getMemory();
		long end = imageBlock().getEnd().getOffset() + 1;
		long lo = (end + 0xfffL) & ~0xfffL, hi = 0x8d000000L;   // RAM above the image up to the end of the 16 MiB
		if (lo < hi && m.getBlock(toAddr(lo)) == null) {
			MemoryBlock b = m.createUninitializedBlock("EMU_RAM", toAddr(lo), hi - lo, false);
			b.setPermissions(true, true, false);
		}
	}

	@Override
	protected void run() throws Exception {
		String[] a = getScriptArgs();
		RET_ADDR = imageBlock().getStart().getOffset() + 0xc0;
		ensureRam();
		List<String> cases = Files.readAllLines(Paths.get(a[0]));
		PrintWriter out = new PrintWriter(new BufferedWriter(new FileWriter(a[1])));
		EmulatorHelper emu = new EmulatorHelper(currentProgram);
		try {
			emu.setBreakpoint(toAddr(RET_ADDR));
			for (String line : cases) {
				line = line.trim();
				if (line.isEmpty()) { out.println(); continue; }
				out.println(runCase(emu, line));
				out.flush();      // progress is visible while a long run is going (a missing last line = the case that hangs)
			}
		} finally {
			emu.dispose();
			out.close();
		}
	}

	private static byte[] le(long v, int n) {
		byte[] b = new byte[n];
		for (int i = 0; i < n; i++) b[i] = (byte) (v >> (8 * i));
		return b;
	}
	private static byte[] hex(String h) {
		byte[] b = new byte[h.length() / 2];
		for (int i = 0; i < b.length; i++) b[i] = (byte) Integer.parseInt(h.substring(2 * i, 2 * i + 2), 16);
		return b;
	}

	// Flycast's FSCA table (core/hw/sh4/fsca-table.h, hardware-derived): sin(i) for i<0x8000, -sin(i-0x8000) above; cos(i) = sin(i+0x4000).
	private static int[] fscaHalf;
	private static int fscaSin(int i) {
		i &= 0xffff;
		if (fscaHalf == null) {
			try {
				byte[] raw = java.nio.file.Files.readAllBytes(java.nio.file.Paths.get(System.getenv("ND_FSCA_TABLE")));
				fscaHalf = new int[0x8000];
				for (int k = 0; k < 0x8000; k++) fscaHalf[k] = (raw[4*k] & 0xff) | (raw[4*k+1] & 0xff) << 8 | (raw[4*k+2] & 0xff) << 16 | (raw[4*k+3] & 0xff) << 24;
			} catch (Exception e) { throw new RuntimeException("ND_FSCA_TABLE unreadable: " + e); }
		}
		return i < 0x8000 ? fscaHalf[i] : fscaHalf[i - 0x8000] ^ 0x80000000;
	}

	private String runCase(EmulatorHelper emu, String line) throws Exception {
		String[] t = line.split("\\s+");
		long entry = Long.parseLong(t[1], 16);
		List<String> reads = new ArrayList<>();
		Set<Long> stops = new HashSet<>();
		Set<Long> watches = new HashSet<>();
		Set<Long> frWatches = new HashSet<>();   // watchfr=: watch that also logs fr5 (second float argument) after fr0
		Set<Long> fr4Watches = new HashSet<>();   // watchfr4=: watch that also logs fr4 after any fr5 (rts delay-slot result for 07043e)
		Set<Long> fscas = new HashSet<>();
		Set<Long> skips = new HashSet<>();
		Map<Long, Integer> argStack = new HashMap<>();   // argstack=<addr>:<n>: entry args of a skipped callee (r4..r7, n stack words)
		Map<Long, long[]> statFlg = new HashMap<>();   // skipstat=<addr>:<v1>,<v2>,..: skipped callee writes m_Flg (+0x18 of the r5 buffer) per hit; last value repeats
		Map<Long, Integer> statHits = new HashMap<>();
		Map<Long, long[]> seqRet = new HashMap<>();     // skipseq=<addr>:v0,v1,..: n-th call of the skipped callee returns v[n] in r0 (last value repeats)
		Map<Long, Integer> seqHits = new HashMap<>();
		Map<Long, String[]> derefLog = new HashMap<>();   // deref=<addr>:<reg>:<nbytes>: on entry of a skipped callee log the nbytes at the address held in <reg> as " D<addr>=<hex>"
		Map<Long, Long> skipFirst = new HashMap<>();   // skipret: first call returns the value, later calls return -1 (menu cancel)
		Map<Long, Integer> skipHits = new HashMap<>();
		Map<Long, Long> skipFr0 = new HashMap<>();   // skipfr0=<addr>:<bits>: skipped callee returns with fr0 = bits
		Set<Long> skipSin = new HashSet<>(), skipCos = new HashSet<>();   // skipsin / skipcos: skipped callee returns with fr0 = FSCA-model sin / cos of r4
		Map<Long, int[]> callLog = new HashMap<>();   // callog=<addr>:<nint>:<nfloat>: entry values logged for a skipped callee
		StringBuilder watchLog = new StringBuilder();
		boolean cover = false;                        // cover: log every distinct executed (non-stubbed) pc as " X=<hex>,<hex>,.." (instruction coverage for autodiff)
		TreeSet<Long> covered = new TreeSet<>();
		boolean trace = false;                        // trace: log control-flow jumps (pc != previous pc + 2) as " T=<hex>,.." (max 400)
		StringBuilder traceLog = new StringBuilder(); long lastPc = -10; int traceN = 0;
		stops.add(RET_ADDR);
		for (int i = 0; i < 16; i++) emu.writeRegister("r" + i, BigInteger.ZERO);
		emu.writeRegister("FPSCR", BigInteger.ZERO);
		for (int i = 2; i < t.length; i++) {
			String s = t[i];
			int eq = s.indexOf('=');
			String k = eq < 0 ? s : s.substring(0, eq);
			String v = eq < 0 ? "" : s.substring(eq + 1);
			if (k.equals("cover")) cover = true;
			else if (k.equals("trace")) trace = true;
			else if (k.equals("stop")) stops.add(Long.parseLong(v, 16));
			else if (k.equals("watch")) watches.add(Long.parseLong(v, 16));
			else if (k.equals("watchfr")) { watches.add(Long.parseLong(v, 16)); frWatches.add(Long.parseLong(v, 16)); }
			else if (k.equals("watchfr4")) { watches.add(Long.parseLong(v, 16)); fr4Watches.add(Long.parseLong(v, 16)); }
			else if (k.equals("fsca")) fscas.add(Long.parseLong(v, 16));
			else if (k.equals("skip")) skips.add(Long.parseLong(v, 16));
			else if (k.equals("skipfr0")) { int c = v.indexOf(':'); long a = Long.parseLong(v.substring(0, c), 16); skipFr0.put(a, Long.parseLong(v.substring(c + 1), 16)); skips.add(a); }
			else if (k.equals("skipsin")) { long a = Long.parseLong(v, 16); skipSin.add(a); skips.add(a); }
			else if (k.equals("skipcos")) { long a = Long.parseLong(v, 16); skipCos.add(a); skips.add(a); }
			else if (k.equals("callog")) { String[] p = v.split(":"); callLog.put(Long.parseLong(p[0], 16), new int[] {Integer.parseInt(p[1]), Integer.parseInt(p[2])}); }
			else if (k.equals("argstack")) { int c = v.indexOf(':'); argStack.put(Long.parseLong(v.substring(0, c), 16), Integer.parseInt(v.substring(c + 1))); }   // argstack=<addr>:<n>: on entry of a skipped callee log r4..r7 and n words at [SP] (stack args 5..)
			else if (k.equals("skipstat")) {
				int c = v.indexOf(':');
				long a = Long.parseLong(v.substring(0, c), 16);
				String[] parts = v.substring(c + 1).split(",");
				long[] vals = new long[parts.length];
				for (int j = 0; j < parts.length; j++) vals[j] = Long.parseLong(parts[j], 16);
				statFlg.put(a, vals); skips.add(a);
			}
			else if (k.equals("deref")) { String[] p = v.split(":"); derefLog.put(Long.parseLong(p[0], 16), new String[] {p[1], p[2]}); }
			else if (k.equals("skipseq")) {
				int c = v.indexOf(':'); long a = Long.parseLong(v.substring(0, c), 16);
				String[] parts = v.substring(c + 1).split(",");
				long[] vals = new long[parts.length];
				for (int j = 0; j < parts.length; j++) vals[j] = Long.parseLong(parts[j], 16);
				seqRet.put(a, vals); skips.add(a);
			}
			else if (k.equals("skipret")) { int c = v.indexOf(':'); skipFirst.put(Long.parseLong(v.substring(0, c), 16), Long.parseLong(v.substring(c + 1), 16)); }
			else if (k.matches("r\\d+")) emu.writeRegister(k, new BigInteger(v, 16));
			else if (k.matches("fr\\d+")) emu.writeRegister(k, new BigInteger(v, 16));
			else if (k.startsWith("w8:")) emu.writeMemory(toAddr(Long.parseLong(k.substring(3), 16)), le(Long.parseLong(v, 16), 1));
			else if (k.startsWith("w16:")) emu.writeMemory(toAddr(Long.parseLong(k.substring(4), 16)), le(Long.parseLong(v, 16), 2));
			else if (k.startsWith("w32:")) emu.writeMemory(toAddr(Long.parseLong(k.substring(4), 16)), le(Long.parseLong(v, 16), 4));
			else if (k.startsWith("wbytes:")) emu.writeMemory(toAddr(Long.parseLong(k.substring(7), 16)), hex(v));
			else reads.add(s);
		}
		emu.writeRegister("r15", BigInteger.valueOf(STACK_TOP));
		emu.writeRegister("PR", BigInteger.valueOf(RET_ADDR));
		emu.writeRegister("pc", BigInteger.valueOf(entry));
		long steps = 0;
		final long deadline = System.nanoTime() + CASE_MS * 1_000_000L;
		String[] abiRegs = {"r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15"};   // callee-saved by the SH-4 C ABI (r15 = sp): checked at return
		long[] abiIn = new long[abiRegs.length];
		for (int i = 0; i < abiRegs.length; i++) abiIn[i] = emu.readRegister(abiRegs[i]).longValue() & 0xffffffffL;
		StringBuilder sb = new StringBuilder();
		try {
			emu.writeRegister(emu.getPCRegister(), BigInteger.valueOf(entry));
			while (true) {
				long pcNow = emu.getExecutionAddress().getOffset();
				if (stops.contains(pcNow)) break;                       // a skip can return onto a stop address; stop before the next instruction (else the epilogue runs on an empty stack)
				if (skipFirst.containsKey(pcNow)) {                // menu stub: forced result once, then cancel so a retry loop ends
					int hit = skipHits.merge(pcNow, 1, Integer::sum);
					if (argStack.containsKey(pcNow)) {                 // skipret stubs log entry args too (same format as the skip path below)
						watchLog.append(" A").append(Long.toHexString(pcNow)).append("=");
						for (String rn : new String[] {"r4","r5","r6","r7"}) watchLog.append(Long.toHexString(emu.readRegister(rn).longValue() & 0xffffffffL)).append(",");
						long spr = emu.readRegister("r15").longValue() & 0xffffffffL;
						for (int i = 0; i < argStack.get(pcNow); i++) {
							byte[] b = emu.readMemory(toAddr(spr + 4L * i), 4);
							watchLog.append(Long.toHexString((b[0] & 0xffL) | ((b[1] & 0xffL) << 8) | ((b[2] & 0xffL) << 16) | ((b[3] & 0xffL) << 24))).append(",");
						}
					}
					if (callLog.containsKey(pcNow)) {                  // callog also applies to skipret (scn_arg stub): same " C<addr>=" entry-value format
						int[] nn = callLog.get(pcNow);
						watchLog.append(" C").append(Long.toHexString(pcNow)).append("=");
						for (int i = 0; i < nn[0]; i++) watchLog.append(Long.toHexString(emu.readRegister("r" + (4 + i)).longValue() & 0xffffffffL)).append(",");
						for (int i = 0; i < nn[1]; i++) watchLog.append(Long.toHexString(emu.readRegister("fr" + (4 + i)).longValue() & 0xffffffffL)).append(",");
					}
					emu.writeRegister("r0", BigInteger.valueOf(hit == 1 ? skipFirst.get(pcNow) : 0xffffffffL));
					emu.writeRegister(emu.getPCRegister(), emu.readRegister("PR"));
					steps++;
					if (watches.contains(emu.getExecutionAddress().getOffset())) {   // a watch on the return address counts here too (skip/skipret return to PR without a step)
						watchLog.append(" W").append(Long.toHexString(emu.getExecutionAddress().getOffset())).append("=");
						for (String rn : new String[] {"r0","r1","r2","r3","r4","r5","r6","r7","r8","r9","r10","r11","r12","r13","r14","fr0"}) watchLog.append(Long.toHexString(emu.readRegister(rn).longValue() & 0xffffffffL)).append(",");
					if (frWatches.contains(emu.getExecutionAddress().getOffset())) watchLog.append(Long.toHexString(emu.readRegister("fr5").longValue() & 0xffffffffL)).append(",");
					if (fr4Watches.contains(emu.getExecutionAddress().getOffset())) watchLog.append(Long.toHexString(emu.readRegister("fr4").longValue() & 0xffffffffL)).append(",");
					}
					continue;
				}
					if (skips.contains(pcNow)) {                       // stub out presentation code: return immediately
					if (argStack.containsKey(pcNow)) {                 // argstack: log the entry args before the stub returns
						watchLog.append(" A").append(Long.toHexString(pcNow)).append("=");
						for (String rn : new String[] {"r4","r5","r6","r7"}) watchLog.append(Long.toHexString(emu.readRegister(rn).longValue() & 0xffffffffL)).append(",");
						long sp = emu.readRegister("r15").longValue() & 0xffffffffL;
						for (int i = 0; i < argStack.get(pcNow); i++) {
							byte[] b = emu.readMemory(toAddr(sp + 4L * i), 4);
							watchLog.append(Long.toHexString((b[0] & 0xffL) | ((b[1] & 0xffL) << 8) | ((b[2] & 0xffL) << 16) | ((b[3] & 0xffL) << 24))).append(",");
						}
					}
					if (statFlg.containsKey(pcNow)) {                  // skipstat: fake sdMidiGetStat, m_Flg at +0x18 of the buffer in r5
						long[] seq = statFlg.get(pcNow);
						int h = statHits.merge(pcNow, 1, Integer::sum) - 1;
						long buf = emu.readRegister("r5").longValue() & 0xffffffffL;
						emu.writeMemory(toAddr(buf + 0x18), le(seq[Math.min(h, seq.length - 1)], 4));
					}
					if (callLog.containsKey(pcNow)) {                  // callog: entry values of the callee, integer args (r4..) then float args (fr4..)
							int[] nn = callLog.get(pcNow);
							watchLog.append(" C").append(Long.toHexString(pcNow)).append("=");
							for (int i = 0; i < nn[0]; i++) watchLog.append(Long.toHexString(emu.readRegister("r" + (4 + i)).longValue() & 0xffffffffL)).append(",");
							for (int i = 0; i < nn[1]; i++) watchLog.append(Long.toHexString(emu.readRegister("fr" + (4 + i)).longValue() & 0xffffffffL)).append(",");
						}
						if (derefLog.containsKey(pcNow)) {
							String[] dr = derefLog.get(pcNow);
							long ap = emu.readRegister(dr[0]).longValue() & 0xffffffffL;
							byte[] db = emu.readMemory(toAddr(ap), Integer.parseInt(dr[1]));
							watchLog.append(" D").append(Long.toHexString(pcNow)).append("=");
							for (byte bb : db) watchLog.append(String.format("%02x", bb & 0xff));
						}
						if (skipFr0.containsKey(pcNow)) emu.writeRegister("fr0", BigInteger.valueOf(skipFr0.get(pcNow)));
						if (skipSin.contains(pcNow) || skipCos.contains(pcNow)) {   // FSCA model: fr0 = (float) sin/cos of the 16-bit turn count in r4 (65536 = 2*pi)
							int ai = (int) (emu.readRegister("r4").longValue() & 0xffffL);
							emu.writeRegister("fr0", BigInteger.valueOf(fscaSin(skipSin.contains(pcNow) ? ai : ai + 0x4000) & 0xffffffffL));
						}
						if (seqRet.containsKey(pcNow)) { long[] sq = seqRet.get(pcNow); int h = seqHits.merge(pcNow, 1, Integer::sum) - 1; emu.writeRegister("r0", BigInteger.valueOf(sq[Math.min(h, sq.length - 1)] & 0xffffffffL)); }
						else emu.writeRegister("r0", BigInteger.ZERO);
					emu.writeRegister(emu.getPCRegister(), emu.readRegister("PR"));
					steps++;
					if (watches.contains(emu.getExecutionAddress().getOffset())) {   // a watch on the return address still counts
						watchLog.append(" W").append(Long.toHexString(emu.getExecutionAddress().getOffset())).append("=");
						for (String rn : new String[] {"r0","r1","r2","r3","r4","r5","r6","r7","r8","r9","r10","r11","r12","r13","r14","fr0"}) watchLog.append(Long.toHexString(emu.readRegister(rn).longValue() & 0xffffffffL)).append(",");
					if (frWatches.contains(emu.getExecutionAddress().getOffset())) watchLog.append(Long.toHexString(emu.readRegister("fr5").longValue() & 0xffffffffL)).append(",");
					if (fr4Watches.contains(emu.getExecutionAddress().getOffset())) watchLog.append(Long.toHexString(emu.readRegister("fr4").longValue() & 0xffffffffL)).append(",");
					}
					continue;
				}
				if (fscas.contains(pcNow)) {                       // FSCA FPUL,DR0: fr0 = sin, fr1 = cos
					int ai = (int) (emu.readRegister("FPUL").longValue() & 0xffffL);
					emu.writeRegister("fr0", BigInteger.valueOf(fscaSin(ai) & 0xffffffffL));
					emu.writeRegister("fr1", BigInteger.valueOf(fscaSin(ai + 0x4000) & 0xffffffffL));
					emu.writeRegister(emu.getPCRegister(), BigInteger.valueOf(pcNow + 2));
					steps++;
					continue;
				}
				if (cover) covered.add(pcNow);
				if (trace) { if (pcNow != lastPc + 2 && traceN < 400) { traceLog.append(Long.toHexString(pcNow)).append(','); traceN++; } lastPc = pcNow; }
				boolean ok = emu.step(monitor);
				steps++;
				if (!ok) return "FAULT " + emu.getLastError() + " from=" + Long.toHexString(pcNow) + " PR=" + Long.toHexString(emu.readRegister("PR").longValue() & 0xffffffffL) + " r8=" + Long.toHexString(emu.readRegister("r8").longValue() & 0xffffffffL) + " r9=" + Long.toHexString(emu.readRegister("r9").longValue() & 0xffffffffL) + " r2=" + Long.toHexString(emu.readRegister("r2").longValue() & 0xffffffffL) + " r4=" + Long.toHexString(emu.readRegister("r4").longValue() & 0xffffffffL) + watchLog;
				if (watches.contains(emu.getExecutionAddress().getOffset())) {
					watchLog.append(" W").append(Long.toHexString(emu.getExecutionAddress().getOffset())).append("=");
					for (String rn : new String[] {"r0","r1","r2","r3","r4","r5","r6","r7","r8","r9","r10","r11","r12","r13","r14","fr0"}) watchLog.append(Long.toHexString(emu.readRegister(rn).longValue() & 0xffffffffL)).append(",");
					if (frWatches.contains(emu.getExecutionAddress().getOffset())) watchLog.append(Long.toHexString(emu.readRegister("fr5").longValue() & 0xffffffffL)).append(",");
					if (fr4Watches.contains(emu.getExecutionAddress().getOffset())) watchLog.append(Long.toHexString(emu.readRegister("fr4").longValue() & 0xffffffffL)).append(",");
				}
				if (stops.contains(emu.getExecutionAddress().getOffset())) break;
				if (steps > STEP_LIMIT) return "FAULT step-limit (" + steps + " steps; a callee that should be stubbed is running for real? skip=/callog=/skipret= addresses are HEX)";
				if ((steps & 0xfff) == 0 && System.nanoTime() > deadline) return "FAULT time-limit (" + CASE_MS + " ms, " + steps + " steps; ND_CASE_MS to raise; check that every callee is stubbed and the skip= addresses are HEX)";
			}
		} catch (Exception e) {
			return "FAULT " + e;
		}
		sb.append("ret=").append(Long.toHexString(emu.readRegister("r0").longValue() & 0xffffffffL)).append(watchLog);
		StringBuilder abiBad = new StringBuilder();
		for (int i = 0; i < abiRegs.length; i++) if ((emu.readRegister(abiRegs[i]).longValue() & 0xffffffffL) != abiIn[i]) abiBad.append(abiBad.length() > 0 ? "," : "").append(abiRegs[i]);
		if (abiBad.length() > 0) sb.append(" ABI=").append(abiBad);
		if (trace) sb.append(" T=").append(traceLog);
		if (cover) { sb.append(" X="); for (long cv : covered) sb.append(Long.toHexString(cv)).append(','); }
		for (String r : reads) {
			String[] p = r.split(":");
			long addr = Long.parseLong(p[1], 16);
			sb.append(' ').append(r).append('=');
			if (p[0].equals("r8")) sb.append(Long.toHexString(emu.readMemory(toAddr(addr), 1)[0] & 0xffL));
			else if (p[0].equals("r16")) { byte[] b = emu.readMemory(toAddr(addr), 2); sb.append(Long.toHexString((b[0] & 0xffL) | ((b[1] & 0xffL) << 8))); }
			else if (p[0].equals("r32")) { byte[] b = emu.readMemory(toAddr(addr), 4); sb.append(Long.toHexString((b[0] & 0xffL) | ((b[1] & 0xffL) << 8) | ((b[2] & 0xffL) << 16) | ((b[3] & 0xffL) << 24))); }
			else if (p[0].equals("rbytes")) { byte[] b = emu.readMemory(toAddr(addr), Integer.parseInt(p[2])); for (byte x : b) sb.append(String.format("%02x", x & 0xff)); }
		}
		return sb.toString();
	}
}
