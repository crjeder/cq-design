## Context

The grader scores topology by comparing Betti numbers, b1 being the through-hole count
(genus of the solid's boundary). The pipeline has no notion of through vs blind: interfaces
carry `position_mm`/`diameter_mm`/`size_mm`, and `feature_presence_check.py` skips the
in-place hole family entirely (#340). The plan already holds one `interfaces[]` entry per
placed copy, so the planned hole count is already countable from the plan; what is missing is
whether each one goes through.

## Goals / Non-Goals

**Goals:**
- Make through vs blind an explicit plan decision for every hole-like interface.
- Fail the gate when the built solid's b1 differs from the planned total.

**Non-Goals:**
- Locating which hole is wrong (that is #340's per-hole presence check).
- Checking blind-hole depth or thread modelling.
- Making `through_count` required in the schema for every plan.

## Decisions

1. **One integer field, `through_count`, not `through: bool` + `count`.** The plan already has
   one interface per placed copy, so a separate `count` would duplicate it, except for
   multi-hole blocks like `vent_grid` where one interface cuts N holes. An integer covers all
   three cases (0 blind, 1 through, N grid) in one field.
   Alternative: part-level `genus` integer. Rejected: it does not force the per-hole
   through/blind decision that caused the failures, and does not tell the builder which
   holes are blind.

2. **b1 from the mesh: `g = c - chi/2`** where `chi = mesh.euler_number` and `c` is the number
   of connected surface components (`mesh.split(only_watertight=False)`). For a closed
   orientable surface with c components, chi = 2c - 2g. This handles multi-body parts and
   internal voids (a void adds a sphere component, chi +2, c +1, genus unchanged). Computed
   only on a watertight mesh; a non-watertight mesh already fails with `non_watertight`, so the
   check is skipped there rather than reporting a meaningless count. Lives in `mesh_io.py`
   next to the other mesh metrics.

3. **Gate placement: inside `run_gate`'s geometry stage, summed over the part's
   non-sacrificial union STLs.** Interfaces are per part, not per union, so the comparison is
   part-level. Sacrificial unions (support fins) are excluded, matching the overhang check.
   Pose is irrelevant to genus, so no rotation is applied.

4. **Opt-in per part.** The check runs when any interface on the part has `through_count`.
   Older plans and parts with no hole interfaces see no change. The planning prompt makes the
   field mandatory for hole, slot and cutout interfaces, so new plans opt in.

5. **Issue shape:** `{source: "geometry", severity: "error", type:
   "through_hole_count_mismatch", planned_b1, built_b1, message, hint}`. The hint names both
   directions: too many -> a planned blind (tapped/depth) hole was cut through, or a cut broke
   through a wall; too few -> a planned through hole stops short or was merged.

## Risks / Trade-offs

- [Handles that are not interfaces (a hanging loop, a through-slot between two bosses) add to
  b1 without a plan entry] -> The prompt rule says every closed through opening gets an
  interface entry; a mismatch then surfaces at the gate rather than at the benchmark.
- [An edge notch or a slot open to an edge is not a handle] -> Prompt rule: `through_count`
  counts only openings closed by material all round; an edge notch is 0.
- [Coincident-face tessellation can split a mesh into extra components or leave it
  non-watertight] -> Non-watertight skips the check; `trimesh.split` on a watertight mesh is
  stable.
- [Assembly openings formed between two parts are not counted per part] -> Out of scope; the
  check is per part.
