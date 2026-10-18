## Why

An over-large `.fillet()` / `.chamfer()` reaches the OCC kernel and comes back as
`Standard_ConstructionError` / `StdFail_NotDone`, which the wrapper can only report as
a generic `occ_exception` with no feature named. `script_lint.py` is AST-only, so it
cannot relate a radius to an edge length, and the existing `cq_verify` helpers fire
after an operation, not before it. A pre-kernel check that measures the selected edges
names the offending feature and the limit it broke, so the author fixes it in one pass.

## What Changes

- Add three pre-kernel predicates to `src/cq_verify.py`:
  - `check_fillet(body, radius, selector=None, label="")` -- measures the edges the
    fillet would touch and raises a marked `fillet_radius` error when the radius
    reaches the geometric limit set by an adjacent edge.
  - `check_chamfer(body, length, selector=None, label="")` -- same rule for a chamfer,
    kind `chamfer_size`.
  - `check_ligament(wall_mm, hole_d_mm, min_mm, label="")` -- pure arithmetic: raises
    `thin_ligament` when the material left on each side of a centered hole in a wall is
    below `min_mm`.
  - Each returns its first argument unchanged on success, so it sits inline like the
    existing `verify_*` helpers.
- Register `fillet_radius`, `chamfer_size`, `thin_ligament` in `_VERIFY_HINTS` in
  `src/run_cadquery_model.py`, so the marker becomes a typed error with a hint instead
  of an `occ_exception`.
- Document the helpers, and the edge-length rule they enforce, in the
  "Construction-time verification" section of `prompts/part.md`.

Note: the backlog entry says to reuse a "fillet/chamfer safety line" already in
`prompts/part.md`. No such line exists today, so this change defines the rule (a
geometric limit, see design.md) and adds it to the prompt.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `runtime-boolean-verification`: adds pre-kernel fillet/chamfer/ligament predicates,
  their wrapper mapping to typed errors, and the authoring guidance for them.

## Impact

- `src/cq_verify.py` (three new functions, no new dependency)
- `src/run_cadquery_model.py` (`_VERIFY_HINTS` gains three keys; no JSON contract change)
- `prompts/part.md` (Construction-time verification section)
- `tests/test_cq_verify.py`, `tests/test_run_wrapper.py`
- Bundled `lib/` copies pick up the change on the next `/cq-design:update`; no new file.
