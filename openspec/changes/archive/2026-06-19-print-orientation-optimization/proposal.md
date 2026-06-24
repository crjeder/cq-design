## Why

The pipeline designs the geometry but never decides *how it should sit on the bed*.
The print recipe hardcodes `"orientation": "flat_bottom_down"`, and the deliverable
3MF/STL is written in the part's assembled pose, which is chosen for display and
kinematics, not for print quality. On FDM the print orientation is the single biggest
lever on part strength (interlayer adhesion is the weak axis) and on support volume.
Leaving it unoptimized ships parts that are weak across their load path or buried in
support.

## What Changes

- Add a post-design optimization phase: after all unions pass the part loop, the skill
  loops to choose a **print orientation per union**, prioritizing **part strength first,
  minimal support second**.
- Add a deterministic scoring tool that enumerates candidate bed-down orientations and
  scores each on a strength metric (load path vs. layer-line / interlayer-weak axis) and
  a support metric (overhang area, support volume proxy, bed-contact area), with strength
  as the primary objective and support as the tiebreaker.
- The optimization is an LLM-driven loop: score orientations, optionally apply targeted
  geometry tweaks (e.g. chamfering a steep overhang) to reduce required support, re-score,
  and converge on a recommended orientation plus rationale.
- Record the chosen print orientation (a rotation transform) per union and the score
  breakdown, distinct from the assembled-frame `placement`.
- **BREAKING for the recipe field**: the print recipe's `orientation` becomes the
  computed orientation (axis/angle description + rationale) instead of the constant
  `"flat_bottom_down"`.
- The model export writes the deliverable 3MF and STL in the **recommended print
  orientation**, while still producing assembled-pose per-union meshes for the kinematic
  check.
- Add an optional per-part load hint to the build plan so strength scoring is driven by
  declared intent; fall back to a geometry heuristic when absent.

## Capabilities

### New Capabilities
- `print-orientation-optimization`: enumerate, score, and select a print orientation per
  union (strength-primary, support-secondary), driving an LLM optimization loop and
  emitting the chosen orientation transform with its score breakdown and rationale.

### Modified Capabilities
- `model-export`: deliverable 3MF/STL are written in each union's recommended print
  orientation (decoupled from the assembled pose), while the assembled-pose per-union
  meshes consumed by the kinematic check are still produced.
- `planning-phase`: the build plan carries an optional per-part load hint (principal load
  direction in the part frame) used to drive strength scoring.

## Impact

- **New code**: `src/print_orientation.py` (candidate enumeration + scoring + selection).
- **Modified code**: `src/model_export.py` (apply print orientation to deliverables,
  keep assembled-pose meshes for kinematics), `src/quality_gate.py` (`orientation` in the
  print recipe reflects the computed result), `src/build_plan_schema.json` (optional
  per-part `load` hint), `src/plan_validate.py` (validate the hint).
- **Pipeline / docs**: `SKILL.md` gains the optimization phase between Model export and
  Quality gate; `prompts/planning.md` notes the load hint.
- **Dependencies**: trimesh + numpy only (already required); no slicer or new dependency.
