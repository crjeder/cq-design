## Context

A part is one script; `units.iter_unions` expands parts to unions and `model_export.export_model`
loads `<part_id>.py` for every part. Nothing lets a part borrow another's geometry. Placement is
per part (`placement` / mate-chain pose), applied after the authored geometry.

## Goals / Non-Goals

**Goals:**
- One script, one audit, one gate run for a mirrored/identical pair.
- Copy still appears as its own union, plate object, and STL with its own placement.

**Non-Goals:**
- Copies of multi-union parts (source must be a single-union part).
- Chained copies, parametric divergence between source and copy, or automatic detection of
  duplicate parts in an existing plan.

## Decisions

**Field on the part, not a new top-level array.** `copy_of` sits on the part so the part id stays
the union id and every consumer keyed by id (plates, kinematics, joints, bom) keeps working.
Alternative (top-level `instances`) would need a second id namespace.

**Mirror is a reflection of the authored geometry, before placement.** In export, the source's
authored Workplane is mirrored (`Workplane.mirror("YZ"|"XZ"|"XY")` for X/Y/Z) then posed by the
copy's own placement. Reflection is the one transform `placement` (rotations only) cannot express,
which is why it belongs in the new field.

**Skip, don't stub, in the part loop.** Copy parts are filtered where the loop and the gate
enumerate scripts, rather than generating a wrapper script. Alternative (generate `wall_b.py`
that imports `wall_a`) keeps one code path but re-creates the file the TODO wants gone.

**Print orientation: computed per copy.** A mirrored solid has different overhang geometry in
principle; running the optimizer on the exported copy STL costs nothing extra and stays correct.

## Risks / Trade-offs

[Consumers that open `<part_id>.py` directly break on a copy part] -> grep every script-loading
site (`export_model`, `quality_gate`, `freshness`, `render_prompt`, `build_template`) and route
through one `is_copy(part)` helper in `units.py`.
[Mirrored copy fails a check the source passed (chirality-dependent features, e.g. embossed text)]
-> gate runs the export-time STL checks on the copy too; per-part script lint/feature checks run
on the source only. Text/emboss on a mirrored copy is documented as unsupported in the planner rule.
[Stale copy when the source script changes] -> `freshness` manifest for a copy hashes the
source script.
