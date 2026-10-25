# Spike: plan-derived probes against the eval `visual_mismatch` failures

Run data: `build/eval_run/<case>/` in the main checkout (2026-09-18..20 eval run).
Scripts are the final `build/<part>.py` of each case; no attempt history is kept, but
every failed attempt below was rejected on a question about connectivity, and the
accepted script's geometry is the one the auditor could not confirm.

Probes were hand-seeded the way `probes.py plan` would (D5): `solids == 1`, envelope
bbox size from `dimensions`, and per `interfaces[]` entry with `position_mm` and
`diameter_mm`/`size_mm`: cut types (`clearance_opening`, `screw_mount`) ->
`empty_at(position)` + `ray` along the wall axis with 0 hits; boss types (`union`) ->
`solid_at(position)`; any other type -> `unprobed_interfaces`. Evaluated with
`BRepClass3d_SolidClassifier` and `IntCurvesFace_ShapeIntersector` on the BRep.

## Per part

| case | part | auditor's failed question | probes on rejected geometry | settled? | unprobed |
|---|---|---|---|---|---|
| adapter-ring | adapter_ring | U1 single connected body (no section across z=5 junction) | all pass (solids 1, bbox 80x80x20, bore empty, bore ray 0 hits) | yes | `flange` (face_mount) |
| boss-plate | mounting_plate | U1 single connected body (section above boss/plate junction) | all pass (solids 1, bbox, 4 bores empty + ray 0 hits) | yes | - |
| east-side-mount | plate | U1 single connected body (boss fused to slab) | all pass (solids 1, bbox, boss solid_at) | yes | - |
| two-part-box | body | U1 single connected body (section only at rim) | all pass (solids 1, bbox) | yes | `opening` (face_mount) |
| two-part-box | lid | U1 single connected body (section only at lip) | all pass (solids 1, bbox) | yes | `lip` (face_mount) |

All five rejections were the same question, and `solids == 1` answers it exactly.
**4 of 4 parts settled** -> gate passed, continue with section 2.

## Do the probes catch real defects?

Mutants of the same scripts (one defect each):

| mutant | script's own `verify_*` | probes |
|---|---|---|
| east-side-mount: boss lifted 0.5 mm off the slab (bbox unchanged) | passes | FAIL `solids` = 2 |
| two-part-box lid: lip lifted 0.5 mm off the plate (bbox unchanged) | passes | FAIL `solids` = 2 |
| boss-plate: bores cut through the bosses only, not the plate | n/a (cut removed) | FAIL `ray` = 2 hits on all 4 holes |
| adapter-ring: bore stops 5 mm short of the top | passes | FAIL `ray` = 2 hits |
| two-part-box body: floor thickness 0 (open bottom) | n/a | pass (not caught) |

## Findings for the design

- `face_mount` interfaces cannot be mapped to a probe by position alone: the adapter
  flange and the lid lip have empty material at `position_mm` (bore / lip ring
  interior), while the body opening is a cavity mouth. 3 of 8 interfaces in these
  plans are `face_mount`; they land in `unprobed_interfaces`, as designed.
- The open-bottom body mutant is not caught: its only interface is unprobed and the
  floor has no interface. Block probes (`hollow_box`: `solid_at` in the floor) are the
  layer that covers it, which supports D4.
- `verify_stage` (bbox + volume floor) and `verify_boolean` (volume sign) missed both
  detached-feature mutants; connectivity needs the solid count.

## Eval run 2026-10-25 (partial, 9.1 not complete)

Run dir `evals/runs/step-loop-probes` (gitignored), installed skill at c43fefa. Only 4 of
13 cases generated: the other 9 `claude -p` calls returned in under a second with zero
tokens (usage limit), so they have no artifacts. Rerun those with `--cases` before 9.2.

| case | 2026-09 attempts (validate runs) / visual_mismatch | 2026-10 attempts (plan revisions) / step runs / visual_mismatch | chamfer 09 -> 10 (mm) |
|---|---|---|---|
| adapter-ring | 2 / 1 | 1 / 1 / 0 | 0.000 -> 0.000 |
| boss-plate | 4 / 1 | 1 / 1 / 0 | 0.031 -> 0.015 |
| east-side-mount | 2 / 1 | 1 / 2 / 0 | 2.674 -> 2.613 |
| enclosure-body | 2 / 0 | 1 / 1 / 0 | 0.013 -> 0.000 |

On these 4 cases (3 of them the baseline's `visual_mismatch` parts) every part passed
first shot with no `visual_mismatch` and no `blocked`; billed cost per part was
2.13-2.88 USD (baseline 0.57-6.34). Not yet a comparison of rates: 9 cases missing.
