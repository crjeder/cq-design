# Design: plate-clearance-check

## Decision 1: Which poses to measure in

Measure on the **assembled-pose per-union STLs** (the ones the kinematic check already
consumes), not the print-oriented deliverables.

Rationale: `model_export.export_model` builds each multi-union plate by unioning the
co-plated unions in their assembled placements and then applying one shared
print-orientation rotation to the whole fused cluster (`model_export.py:124-138`). That
shared rotation is rigid (rotation only), so it preserves every pairwise surface distance.
The minimum gap between two co-plated unions is therefore identical in the assembled pose
and in print orientation. Measuring in the assembled pose means:

- no dependency on print-orientation having run,
- no new export artifact (reuse `stl_dir` the kinematic stage is already handed),
- the same inputs and failure modes as the existing kinematic stage.

Print-in-place joints are swept like any other pair -- no special case, matching
`kinematic_check.py`'s philosophy. A working print-in-place joint that the designer wants
to move *must* keep its clearance gap above one layer height anyway, so the check is
correct for it too rather than an exception to it.

## Decision 2: Distance backend

Use python-fcl's min-distance query between the two union meshes (the same `python-fcl`
already required by `kinematic_check.py`), wrapping trimesh-loaded meshes. fcl returns the
minimum separation directly and reports negative/zero on contact or interpenetration, which
maps cleanly onto "at or below threshold". trimesh's `trimesh.collision.CollisionManager`
provides `min_distance_internal` / a pairwise distance API over fcl, so no new dependency
is introduced beyond what the kinematic stage already needs.

When trimesh or fcl is unavailable, emit one `check_skipped` warning and return -- identical
to `kinematic_check.py`'s degrade path. Do not raise.

## Decision 3: Threshold

Threshold = one layer height = `nozzle_mm * 0.5`, the same derivation the gate uses for
`layer_height_mm` in its print recipe (`quality_gate.py:218`). A gap strictly greater than
one layer height is required to pass; a gap at or below it is flagged (`gap <= threshold`).

No per-pair or per-plate override is introduced in this change. If a future design needs a
larger designed clearance (e.g. a loose-fit joint), that is a separate plan field and a
separate change; the layer-height floor is the hard print-physics minimum and is the right
default to enforce now.

## Decision 4: Pairing and reporting

For each plate with `len(union_ids) > 1`, test every unordered pair. Emit one issue per
failing pair:

```
{
  "source": "geometry",
  "severity": "error",
  "type": "plate_clearance",
  "message": "Unions '<a>' and '<b>' on plate '<plate>' are <gap> mm apart "
             "(<= <threshold> mm layer height); they will fuse in the print.",
  "hint": "Increase the gap between these unions to more than one layer height, "
          "or move one to a separate plate.",
  "plate": "<plate>", "union_a": "<a>", "union_b": "<b>",
  "gap_mm": <gap>, "threshold_mm": <threshold>
}
```

Single-union plates contribute nothing. A clean plate contributes nothing (no
"all clear" issue), matching the overhang stage's convention.

## Decision 5: Wiring into the gate

Add `_run_plate_clearance_stage(plan, stl_dir)` mirroring `_run_kinematic_stage`
(`quality_gate.py:299`): no-op when fewer than two unions share any plate, otherwise call
`plate_clearance_check.run_plate_clearance_check(plan, stl_dir)`. Call it once, outside the
fix loop, next to the kinematic stage (`quality_gate.py:424-425`). Plate membership is
derived the same way `model_export._plate_of` derives it (explicit `plate`, else the part
id), so the gate and the exporter agree on what "co-plated" means.
