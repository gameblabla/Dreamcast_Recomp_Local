---
name: sh4-control-flow
description: SH-4 delay slots, branch forms, loops, switch jump tables, tail calls, function-pointer/callback calls and short-circuit patterns, with the C each lowers from. Use when a branch, loop or indirect jump in SH-4 asm does not read cleanly.
---
## Delay slots (the #1 source of wrong ports)
The instruction AFTER `bra, bsr, braf, bsrf, jmp, jsr, rts, bt/s, bf/s` executes BEFORE the transfer takes effect (shown as `_insn` in the project listing). Rules:
- Conditional `bt/s`/`bf/s`: the condition (T) was latched before the slot; the slot runs whether or not the branch is taken. A slot that writes a reg that the *fall-through* path or the target reads is a real side effect on both paths (loop post-increment is the usual case: `bt/s loop; _add #1,r4`).
- `jsr @Rn` / `bsr`: the target address in Rn is read before the slot; the slot runs before the callee starts, so **a slot that sets r4-r7 is an argument** (`jsr @r3; _mov r8,r4` = `f(r8)`). A `_nop` slot means the args were set earlier.
- `rts`: slot executes before returning; `rts; _mov r2,r0` returns r2; `_lds.l @r15+,PR` restores PR in the slot. The epilogue (`add #N,r15`, `mov.l @r15+,r8`...) before `rts` is cleanup, not logic.
- Branch instructions are not allowed in slots; PC-relative loads in a slot use the PC of the slot instruction.
- Never reorder the slot into "after the jump" when lifting; either hoist it before the branch (if it does not touch the compared regs) or emit it in both arms.

## Branch forms
- `bt/bf label` +-256 B only. Long jumps are `bf skip; bra target; _nop; skip:` - read it as `if (cond) goto target` with INVERTED sense at the bf (the C condition is "fall through to the bra"). A `bra` whose target lies before the branch is a loop back-edge.
- `bra`, `braf Rn` (PC+4+Rn), `jmp @Rn`, `jsr @Rn`, `bsr`, `bsrf`.
- Tail call: function ends with `jmp @rN`/`bra other` instead of `rts` (callee returns to our caller). In C: `return other(args);`. The args are still r4-r7.

## Loops
- Counted: `dt rN; bf/s top; _add ...` => `do { ... } while (--n != 0);` (executes at least once; a leading `tst n,n; bt end` guards `n==0`).
- Pointer walk: `mov.l @r4+,r0` => `*p++`; end compared by `cmp/hs end,p` (unsigned!) or `cmp/eq`.
- Index loops over arrays of structs keep BOTH an index (`add #1,r5; cmp/ge r3,r5`) and a base pointer (`add #stride,r4`) — the pointer is the strength-reduced index; port as `for (i...) s = base + i*stride`.
- Loop-invariant limits are reloaded from globals each iteration if the body calls anything (could be modified): keep the reload.

## Switch statements
```
add #-1,r0 ; mov #0x3a,r1 ; cmp/hs r1,r0 ; bf in_range ; bra default ; _nop   // (unsigned)(x-1) >= 0x3a -> default
in_range: shll r0 ; mov r0,r1 ; mova table,r0 ; mov.w @(r0,r1),r0 ; braf r0 ; _nop
table: .word off0, off1, ...        // 16-bit signed offsets, target = (address of braf)+4+off
```
- Case count = the `cmp/hs` constant (here 0x3a=58 cases for values 1..58); the add -k before it is the lowest case value. The table is 2 bytes/entry (`shll`) or 4 (`shll2`, `mov.l` table, then `jmp @r0` with absolute addresses).
- Duplicate offsets = shared case bodies (fallthrough groups); offset equal to the default = unlisted case. Decode the whole table with a script (read N entries, compute targets), name each target block `case_<v>`, and port as a real `switch`.
- A bounds check that jumps to the function epilogue is `default: return;`.

## Short-circuit / ternary shapes
- `a && b`: two `bf` to the same else label. `a || b`: first test `bt` to the body, second `bf` to else.
- `x = cond ? A : B` with no cmov: `bf L1; mov A,r0; bra L2; _nop; L1: mov B,r0; L2:`.
- min/max/clamp: `cmp/gt; bf; mov` pairs (note which operand is on which side; saturating clamp to int8/int16 = compare against literal limits).
- Early-out guards at the top: `tst r4,r4; bt/s ret; _mov #0,r0` => `if (!p) return 0;` (the slot loaded the return value on both paths).

## Calls
- Direct: `mov.l =func,rN; jsr @rN; _nop` (target comes from the literal pool, shown as a `PTR_FUN_` label). Library/SDK functions are recognised by address (signature file) or by being called from >100 sites with tiny bodies.
- Indirect via table: `mov.l @(r0,rK),rN; jsr @rN` = `table[i](...)` / vtable / callback struct. Record the table and treat each entry as a host callback when it is presentation.
- Return values: only r0 (and fr0 for float). A `jsr` whose r0 is never read is a `void`/ignored call; do not invent a result.
