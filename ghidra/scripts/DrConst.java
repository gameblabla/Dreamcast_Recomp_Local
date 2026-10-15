//Mark literal-pool words (only ever read) as constant so the decompiler folds PTR_xxx into direct calls/addresses.
//@category Dreamcast
import ghidra.app.script.GhidraScript;
import ghidra.program.model.data.MutabilitySettingsDefinition;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;

public class DrConst extends GhidraScript {
	@Override
	protected void run() throws Exception {
		Listing l = currentProgram.getListing();
		ghidra.program.model.mem.MemoryBlock img = null;
		for (ghidra.program.model.mem.MemoryBlock b : currentProgram.getMemory().getBlocks()) if (b.isInitialized()) { img = b; break; }
		long lo = img.getStart().getOffset(), hi = img.getEnd().getOffset() + 1;
		int marked = 0, skipped = 0;
		for (DataIterator it = l.getDefinedData(true); it.hasNext();) {
			Data d = it.next();
			long a = d.getAddress().getOffset();
			boolean pool = a >= lo && a < hi;   // literal pools live inside the image
			if (!pool || d.getLength() > 4) continue;
			boolean allRead = true, any = false;
			for (Reference r : currentProgram.getReferenceManager().getReferencesTo(d.getAddress())) {
				any = true;
				if (!r.getReferenceType().isRead()) { allRead = false; break; }
			}
			if (any && allRead) {
				MutabilitySettingsDefinition.DEF.setChoice(d, MutabilitySettingsDefinition.CONSTANT);
				marked++;
			} else skipped++;
		}
		println("constant literal words: " + marked + " (left mutable: " + skipped + ")");
	}
}
