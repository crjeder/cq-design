## Context

`teardrop_bore` (connectors.py:87) cuts a self-supporting horizontal hole by
replacing the upper arc with a `^` peak. There is no dual for a horizontal solid
cylinder, whose problem surface is the underside. The two are geometric duals: same
half-circle-plus-peak profile, opposite apex direction, and additive vs subtractive.

The block is consumed two ways: a model script calls it directly, and the planner
selects it by reading the inventory `use` string. Both paths matter for how
small-feature guidance is delivered.

## Goals / Non-Goals

**Goals:**
- A `teardrop_post(d, length, angle=45, flat=1.2)` additive block producing a
  printable horizontal peg with a flat (not pointed) self-supporting underside.
- Share the cross-section with `teardrop_bore` via `_drop_profile`, leaving
  `teardrop_bore` output unchanged.
- Advisory-only small-feature handling; always builds, never raises.
- Planner-facing guidance (min diameter, mating redirect) in the inventory `use`.

**Non-Goals:**
- No geometry transform / auto-remediation of existing cylinders in a finished
  model (deferred; would require horizontal-cylinder detection, which
  `measure_stl._cylinders` does not do today).
- No mating socket block. Functional peg/hole pairs are redirected to a
  45-degree-rotated cube (diamond peg in diamond hole), documented, not implemented.
- No new JSON-contract field for warnings.

## Decisions

**Flat bottom, not a sharp point.** A true mirror of `teardrop_bore` ends in a knife
edge. For a solid peg that edge is fragile and starts the print on a single line. A
narrow flat (`flat=1.2 mm` default) is self-supporting, stronger, and bed-friendly.
Alternative (sharp apex) rejected for mechanical weakness.

**Geometry.** With `r = d/2` and `f = flat/2`, the two underside faces run from the
equator points `(±r, 0)` at `angle` from horizontal (this mirrors `teardrop_bore`'s
peak, which is an equator-to-apex construction, NOT a tangent construction — that is
exactly what lets the shared helper reproduce `teardrop_bore` byte-for-byte).
Truncated at half-width `f`, the flat sits at `z = −(r − f)·tan(angle)`. The inclined
faces exist while `f < r`, i.e. `flat < d`. The upper half is the circular arc.

**`_drop_profile(r, angle, apex)` branches on flat, not a pure mirror.**
`teardrop_bore` closes `arc → lineTo(apex) → close` (a point). The post needs
`arc → line → flat → line → close`. The helper takes apex direction and an optional
flat; `flat=0` reproduces the pointed teardrop path (so `teardrop_bore` is unchanged),
`flat>0` produces the truncated path. Alternative (two unrelated functions) rejected
to keep the dual explicit and the 45-degree math in one place.

**Advisory, never fatal (chosen earlier).** Clamp the effective flat (to `d/2`) when
`flat ≥ d`; `warnings.warn` when `d < ~3 mm` (module-level threshold).
Always returns a solid. Rationale: horizontal cylinders below ~2-3 mm self-bridge
untreated, so a hard failure would be user-hostile and unnecessary.

**Min-diameter guidance lives in inventory `use`, not the contract.** The `use`
string is what the planner reads to choose blocks, so encoding the threshold there
prevents the bad call up front; `warnings.warn` is only the runtime backstop. This
sidesteps adding a warnings channel to the `run_cadquery_model.py` JSON contract.
The `use` string also carries the mating-pair redirect to a rotated cube.

## Risks / Trade-offs

- [Refactoring `teardrop_bore` could change its output] → spec requires byte-for-byte
  equivalent geometry; add a regression assertion (diameter, extrusion length, peak
  not arc) in `tests/test_blocks.py`.
- [Clamped flat silently differs from requested] → the `warnings.warn` advisory names
  the clamp so the author can see why.
- [Pointed-vs-flat default surprises users expecting a true teardrop mirror] →
  documented in docstring and `use`; `flat=0` remains available for the pointed form.
- [stderr advisory is easy to miss] → accepted; the primary guidance path is the
  inventory `use` read at planning time, not the runtime warning.

## Open Questions

- Exact wording of the min-diameter threshold in the `use` string (~3 mm proposed).
- Whether `flat=0` (pointed form) should be a documented public option or left
  implicit via the helper. Leaning: documented, since the helper already supports it.
