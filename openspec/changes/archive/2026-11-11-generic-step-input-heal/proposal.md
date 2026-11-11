## Why

Four of the 32 CADGenBench edit inputs (202, 217, 240, 250) fail the grader's validity gate on `input.step` itself. `import_solid`'s three-rung ladder (drop slivers, defeature, filling patch) fixes only 217 and 250, so 202 and 240 still score 0. A 2026-11-11 survey of all 32 inputs found one generic cause: a loose-tolerance batch export (edge tolerances 0.005-0.09 mm in 31 of 32 files) folded tiny features into zero-width wire spikes, sub-tolerance edges and zero-area faces. OCC's dedicated fixes for those shapes are opt-in and were never switched on. With them enabled, one heal pass makes all four inputs pass the real grader script, with volume changes of at most 0.034 %.

## What Changes

- **BREAKING** (behaviour of `import_solid`): the repair trigger becomes the grader's own criterion. An input is repaired only when BRepCheck flags it or it fails `mesh_gate_error`. The "any face below 1e-3 mm²" trigger is removed: 242, 246 and 248 have such faces but pass the grader, and would have been rewritten for no reason.
- **BREAKING**: the three-rung ladder (`drop_slivers`, `defeature`, `patch`) is replaced by one staged heal pass:
  1. `ShapeFix_Shape` with the wire fixes for tails, notches, small edges and self-intersection switched on
  2. `ShapeFix_Wireframe` merging small edges
  3. `ShapeFix_FixSmallFace` removing spot and strip faces

  All three work at a heal tolerance derived from the shape's own maximum edge tolerance. The check runs after each stage, and the first passing result is returned.
- The heal never runs on an input that already passes. Healing the valid inputs 206, 215 and 238 makes them fail the grader.
- `mesh_gate.py` gains the grader check it currently lacks: each edge polygon's end nodes must coincide with the edge's BRep vertices, in the right order. That is the check that failed on the healed 206, 215 and 238, and today the wrapper cannot see it.
- The volume-deviation limit, the `step_unrepairable` typed error and the `[cq-design:step-repair]` report line stay. The `strategy` field now lists heal stages.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `step-import-repair`: the check criterion (grader gate instead of sliver area), the repair procedure (staged ShapeFix heal instead of the topological ladder), and the scenarios that name fixtures (202 and 240 move from unrepairable to repaired).
- `brep-validity-check`: the grader-equivalent mesh gate adds the edge-polygon/vertex consistency check.

## Impact

- `src/blocks/imported.py`: rewrite of the check and the repair. `_drop_slivers`, `_defeature`, `_patch`, `_slivers`, `_sew_solid` and `_solid_from_shells` are removed unless the heal still needs them.
- `src/mesh_gate.py`: one new validation in `_tessellate`/`_validate`.
- `tests/test_import_solid.py`: the synthetic sliver-slab tests change (a sliver that passes the gate is no longer repaired). Add a fixture-backed test for a tail defect.
- `commands/edit.md`, `skill/phase0_sourcing.md` and `reference/scripts.md`: wording about rungs and slivers.
- Runtime: every `import_solid` call now runs `mesh_gate_error` on the input (202: about 25-50 s). The step worker's prefix cache covers repeat runs within a session.
- No new dependencies (all APIs are in the installed OCP).
