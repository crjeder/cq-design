## Why

No gate stage tests every pair of unions for overlap at rest. `kinematic_check` covers only declared `kinematics` entries, `plate_clearance_check` only co-plated unions, `keep_out_check` only declared zones. A lid sitting 1 mm inside its box with no joint declared passes the gate. The overlap primitive (`interference.check_interference`, measuring boolean intersection volume) already exists.

## What Changes

- New whole-model stage `assembly_interference_check.py`: over every `write_assembly.py` union STL, find touching pairs (fcl broadphase) and report each pair whose intersection volume exceeds a fixed 0.1 mm^3 as an `assembly_interference` error.
- Skipped pairs: co-plated unions (owned by `plate_clearance_check`) and unions joined by a press-fit joint (declared `params.clearance` < 0), including every `copy_of` copy of either member part.
- Plan schema: optional `joints[].members[].union`, naming which union of the member part the member fuses into. Required by plan validation when the member's part has more than one union.
- `quality_gate.py` runs the stage once, outside the fix loop, after the keep-out stage.
- `_is_hinge_associated_union` switches to the same member-to-union resolver (it currently compares `member.part == union_id`, missing multi-union parts).
- No hand-written `allowed_overlaps[]` table: press fits are already declared in `joints[]`. Add it later when a real case does not fit (undeflected snap hook, imported STEP).

## Capabilities

### New Capabilities
- `assembly-interference-validation`: all-pairs rest-pose overlap check with press-fit exemption and the `assembly_interference` issue.

### Modified Capabilities
- `joint-mate-entity`: `joints[].members[]` gains an optional `union` field, validated against the member part's unions.

## Impact

- New `src/assembly_interference_check.py`; edits to `src/quality_gate.py`, `src/plan.py`, `src/build_plan_schema.json`, `src/units.py` (member-to-union resolver).
- Docs: `reference/scripts.md`, `FILES.md`; `interference.py` docstring gains a second caller.
- Existing designs with unintended rest overlap between parts on different plates now fail the gate (intended).
