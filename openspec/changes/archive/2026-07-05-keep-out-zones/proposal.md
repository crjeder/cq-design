## Why

Blocks can declare joint contracts, but there is no way for the LLM (or a human) authoring a part to
mark a volume that must stay free of geometry for a reason no block captures -- clearance to swing a
screwdriver into a boss, a wire run reserved for a part not yet designed, a margin around a heat-set
insert. Today the only way to protect such a volume is to remember it and eyeball every future part
against it. This was scoped as "Slice C" annotation geometry in the archived `joint-contract` design
capture and worked through in an `/opsx:explore` session: authors declare zones inline, in whichever
part script they're already writing (Option B), each zone individually named as its own note-to-self
rather than fused into one anonymous volume, and a zone is not checked against its own declaring
part's other real geometry (since a zone is usually anchored flush against the very feature it
protects).

## What Changes

- A part's script MAY emit a reserved `"keep_out"` key in its `result` dict, alongside any real
  unions, mapping zone name -> `Workplane`. The zone name doubles as the human-readable reason (e.g.
  `"screwdriver_clearance_boss1"`), matching the existing convention where a union id also serves as
  its description.
- `"keep_out"` is exempt from the existing "script result keys must match the part's declared
  `unions`" well-formedness check -- it needs no plan-level declaration.
- Every declared zone inherits its declaring part's `placement` (and derived mate-chain pose, if the
  part is mated), so a zone anchored to a feature moves rigidly with that feature.
- Keep-out zones are collected into one world-level, per-model view but are never printed, exported,
  assigned a plate, or included in the kinematic sweep -- they exist purely for the new check below.
- A new whole-model gate stage intersects every union's assembled-frame geometry against every
  declared keep-out zone, **excluding a zone's own declaring part's other real unions**, and emits a
  structured `keep_out_violation` error (naming the offending union and the violated zone) that
  blocks a clean pass.

## Capabilities

### New Capabilities
- `keep-out-zones`: the reserved `keep_out` result key, named-zone semantics, placement inheritance,
  and exclusion from export/plate/sweep.
- `keep-out-validation`: the whole-model gate stage that intersects unions against declared keep-out
  zones (with declaring-part self-exclusion) and reports violations via the structured issue contract.

### Modified Capabilities
- `printable-unit-model`: add the reserved `keep_out` key as a documented exception to the "a build
  unit may produce multiple named unions" requirement -- it is discovered the same way a multi-union
  `result` mapping is, but is never itself a union.

## Impact

- `src/units.py`: new helper to collect and pose keep-out zones per part (mirrors `iter_unions`).
- `src/plan_validate.py`: reserved-key exemption in the result/`unions` cross-check.
- `src/model_export.py`, `src/run_model_shim.py`: exclude `keep_out` from every export/print/plate
  path.
- New `src/keep_out_check.py`: whole-model gate stage (trimesh + python-fcl, same tooling as
  `kinematic_check.py`/`plate_clearance_check.py`), wired into `src/quality_gate.py`.
- New tests covering: reserved-key exemption, placement inheritance, self-exclusion, and the
  violation/pass scenarios for the new check.
