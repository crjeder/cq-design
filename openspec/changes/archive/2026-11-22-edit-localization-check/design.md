## Context

`/cq-design:edit` verifies an edit with `diff_models.py` (input A vs result B, same frame). Today the command rejects `identical` and sign/bbox contradictions only. #394 shows edits that change volume by 0.0-0.3% yet lose 0.23-0.44 shape similarity: the change landed on the wrong feature or leaked elsewhere, and the diff numbers alone cannot tell. The CADGenBench grader scores the no-op about 0.4 and a wrong edit as low as 0.17.

Split by the program-vs-prompt rule: *which feature the description names, and how big the change should be* is judgment (the LLM). *Whether the changed material sits in that region and the volume matches* is deterministic and belongs in `diff_models.py`.

## Goals / Non-Goals

**Goals:**
- Fail an edit whose changed material is not inside a region the caller measured from the input.
- Fail an edit whose net volume change is outside the range the caller derived from the description.
- Deliver the unchanged input when the edit cannot be verified in the retry budget.

**Non-Goals:**
- Finding why edits miss the feature (#394 did not verify it).
- Visual diff of edits (#347).
- A grader-equivalent shape score (`compare_step_files` timed out at over 25 min).

## Decisions

**Region and range are CLI inputs, not inferred.** `--region xmin,ymin,zmin,xmax,ymax,zmax` and `--expect-volume LO,HI`. The command computes both from the imported input (`BoundingBox()` of the named face/edge/feature, padded by 2 mm or the feature size, whichever is larger) and from arithmetic on the description (blend radius, height delta, diameter delta). Alternative: have the script guess the feature from the description; rejected, that is interpretation of intent.

**Outside-region volume via mesh boolean.** `outside_volume` = volume of (only_a + only_b) minus a box, using the same manifold3d booleans already in `diff_models.py`. `localized` is `outside_volume <= outside_tol * volume_a` with `--outside-tol` default 0.005, absorbing tessellation noise on untouched faces. Alternative: bbox of the changed pieces inside the region; rejected, a thin sliver far away would stretch it, and a bbox cannot tell sliver from collateral change by volume.

**Reported keys, not exit codes.** New keys `outside_volume`, `changed_bbox`, `volume_delta` (`only_b - only_a`), `localized`, `volume_in_range`, `region_fraction`. A check not requested is `null`. `success` still means "diff computed"; the command reads the booleans. This keeps the existing contract and exit codes.

**`region_fraction` guards a lazy region.** The fraction of A's bbox volume the region covers; the command treats above 0.5 as no localization evidence and re-measures a tighter region. Without it, passing the whole bbox always passes.

**Fallback delivers the input bytes.** After 5 failed iterations, or when the checks cannot be satisfied, the command copies the original input file to `out/<stem>_edited.step` (never overwriting the input) and reports "edit unverified, input delivered unchanged" with the last errors and diff. Not the repaired body: the no-op the grader compares against is the file as given. A `step_unrepairable` input still delivers nothing, as before.

## Risks / Trade-offs

- [Tessellation differences between input and edited meshes inflate `outside_volume` on B-spline parts] -> `--outside-tol` default 0.5%; calibrate on fixtures 202, 208, 244 before accepting the default.
- [The LLM picks the wrong region and then confirms its own wrong edit] -> the check only catches edits inconsistent with the named feature; `region_fraction` and the report quoting the region let a reviewer see it. Residual risk accepted.
- [A correct edit is replaced by the no-op because a check is too strict] -> the no-op scores about 0.4 against 0.17 for a wrong edit; a strict gate loses less than a lax one on this metric. Tolerances are flags, not constants.
- [Legitimate edits that ripple (a raised face moves attached features)] -> the region must include the ripple; stated in `edit.md`.

## Open Questions

- Default `--outside-tol` after calibration on the 32 edit fixtures.
