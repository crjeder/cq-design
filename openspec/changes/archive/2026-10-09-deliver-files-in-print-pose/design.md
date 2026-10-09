## Context

`write_deliverables` (src/deliverables.py) builds `asm = assemble(...)` with `asm["authored"][uid]` (build pose) and `asm["placed"][uid]` (assembly pose, orientation-independent). Only `_write_3mf` rotates `authored` by the accepted `rotate`; plate STLs rotate the fused assembly-pose plate by the first union's `rotate`. Per-union STL is a copy of the `write_assembly` output (assembly pose) when `assembly_fresh`; extras export `placed`.

## Goals / Non-Goals

**Goals:**
- One rule: any requested format = print pose.
- Keep build pose (scripts) and assembly pose (checks) untouched.
- State that user-facing directions are build pose.

**Non-Goals:**
- No change to how the print rotation is chosen or to `orientations.json` format.
- No extra "assembled" deliverable option (assembly pose stays reachable via the assembly dir).

## Decisions

- **Single helper** `_print_pose(asm, orientations, uid)` returning `apply_cq(asm["authored"][uid], {"rotate": rotate})`, identity when no orientation; used by 3mf, stl, and extras. Replaces the inline `_deliverable` in `_write_3mf`. Alternative (rotate `placed`) rejected: `rotate` is defined build -> print, and placement is not guaranteed to commute with it.
- **Drop the per-union STL copy from `assembly_dir`.** Those files are assembly pose and must stay so for the checks. Per-union STLs are always exported (cost: one export per union; `assembly_fresh` remains for other callers/reporting). `union_stls_copied` is kept in the return dict as `False`.
- **Multi-union plates unchanged**: fused in assembled relative poses, then rotated by the first union's `rotate`. Per-union STLs in such a plate are each in their own print pose (alternates to the plate file, not parts of it).
- **No-orientation fallback is build pose**, not assembly pose, so output never silently mixes frames.
- **Direction convention** is documentation + spec only: `print_orientation.py` already takes `--load`/`--show-face` in the part-frame STL; no code change.

## Risks / Trade-offs

- [Consumers relying on assembly-pose STL/STEP from `build/out`] -> BREAKING noted; assembly pose remains in the `write_assembly` output dir.
- [Slower `build.py --formats stl` without the copy shortcut] -> acceptable; correctness over speed.
- [Rotation of `authored` for copies (`copy_of`)] -> verify `asm["authored"]` exists for copy parts; covered by a test.
