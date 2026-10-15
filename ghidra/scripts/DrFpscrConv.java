//Fix SH-4 float decompilation: import the calling convention that keeps FPSCR (SZ/PR) alive across calls and apply it to every function.
//Without it the decompiler assumes any call may flip FPSCR.SZ/PR, keeps both the single and double-precision paths ("cVar == 0" branches,
//CONCAT44 pairs in doubles) and the output is unreadable. Run AFTER DrFindCode/DrSdkRename. See docs/GHIDRA_SH4_FPU.md.
//Args: path to ghidra/stdcall_noclobber_fpscr.xml
//@category Dreamcast
import java.nio.file.*;
import ghidra.app.script.GhidraScript;
import ghidra.program.database.SpecExtension;
import ghidra.program.model.lang.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;
import ghidra.program.model.symbol.SourceType;
import java.math.BigInteger;

public class DrFpscrConv extends GhidraScript {
	@Override
	protected void run() throws Exception {
		String xml = new String(Files.readAllBytes(Paths.get(getScriptArgs()[0])));
		SpecExtension ext = new SpecExtension(currentProgram);
		try {
			ext.addReplaceCompilerSpecExtension(xml, monitor);
		} catch (Exception e) {
			println("spec extension import failed: " + e);
			return;
		}
		// FPSCR.SZ = 0 (32-bit fmov), FPSCR.PR = 0 (single precision): the Dreamcast SDK runs with these fixed
		Register sz = currentProgram.getLanguage().getRegister("fpscr_sz"), pr = currentProgram.getLanguage().getRegister("fpscr_pr");
		AddressSetView all = currentProgram.getMemory().getLoadedAndInitializedAddressSet();
		for (AddressRange r : all.getAddressRanges()) {
			if (sz != null) currentProgram.getProgramContext().setValue(sz, r.getMinAddress(), r.getMaxAddress(), BigInteger.ZERO);
			if (pr != null) currentProgram.getProgramContext().setValue(pr, r.getMinAddress(), r.getMaxAddress(), BigInteger.ZERO);
		}
		int n = 0;
		for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
			try {
				f.setCallingConvention("__stdcall_noclobber_fpscr");
				n++;
			} catch (Exception e) { /* keep going */ }
		}
		println("calling convention __stdcall_noclobber_fpscr applied to " + n + " functions; FPSCR.SZ/PR fixed to 0");
	}
}
