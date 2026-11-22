## Why

In the CADGenBench submission `cq-design v0.1.0 (merged best-of)`, 24 of 49 generation
fixtures were built with the wrong through-hole count (b1): 11 with too many, 13 with too
few. The grader multiplies its per-axis topology scores, so a single wrong count is
expensive, and misplaced or wrong holes also cost interface match. Two causes: nothing tells
the planner how to tell a through hole from a blind one (tapped M4/M6 callouts in fixtures
120 and 150 were built through, but are blind in the ground truth), and nothing checks the
built solid's hole count against the plan (#395, related #340).

## What Changes

- `BUILD_PLAN.json` `parts[].interfaces[]` gains an optional integer `through_count`: the
  number of closed through openings this interface cuts (1 for a through hole, 0 for a blind
  or tapped hole, N for a vent grid of N holes).
- The planning prompt gets a drawing rule: a hole is through only when a section view shows
  it through or its callout says THRU. A tapped or depth-dimensioned callout without THRU is
  blind (`through_count: 0`). Every hole, slot or cutout interface on a part from a drawing
  states `through_count`.
- The quality gate computes each part's built b1 (genus of the watertight mesh, from its
  Euler characteristic and component count, as the grader's `topo_match` does) and emits a
  blocking `through_hole_count_mismatch` error when it differs from the plan total. The check
  runs only when at least one interface on the part declares `through_count`, so older plans
  are unaffected.

## Capabilities

### New Capabilities
- `through-hole-count-check`: plan field for planned through openings per interface, the
  drawing rule for through vs blind, and the gate's b1 comparison against the built mesh.

### Modified Capabilities
<!-- none: the gate gains a new stage; no existing requirement changes -->

## Impact

- `src/build_plan_schema.json`: new `through_count` property on `interfaces[]` items.
- `src/mesh_io.py`: new `genus(mesh)` helper.
- `src/quality_gate.py`: new check in the geometry stage of `run_gate`.
- `prompts/planning.md`: through/blind rule and `through_count` instruction.
- `reference/scripts.md`: `quality_gate.py` entry documents the new issue type.
- Tests: `tests/test_mesh_io.py`, `tests/test_quality_gate.py`, `tests/test_plan.py`.
