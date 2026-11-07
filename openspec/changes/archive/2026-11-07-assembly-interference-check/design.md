## Context

Union STLs in assembly pose are written by `write_assembly.py` (`stl/<union_id>.stl`, plus `keep_out__*` which this check ignores). `interference.py` offers fcl broadphase plus `_intersection_volume` (manifold boolean). Existing stages share one shape: `run_*_check(plan, stl_dir, parts_dir=...)`, stale/missing handling via `freshness`, `run_stl_dir_check_cli`, and the shared issue contract.

## Goals / Non-Goals

**Goals:** catch any unintended rest-pose interpenetration between any two unions; let press fits through without hand-written entries.

**Non-Goals:** manual `allowed_overlaps[]` table; per-pair volume limits; near-miss clearance-gap detection; the PSEUDO placeholder-volume caller named in `interference.py`.

## Decisions

1. **Single fcl pass.** One `CollisionManager` over all non-stale unions; `in_collision_internal(return_names=True)` yields touching pairs; `_intersection_volume` runs only on those. Flush contact measures ~0 and passes. Alternative (N^2 `check_interference` calls) rebuilds managers needlessly.
2. **Fixed epsilon 0.1 mm^3**, the same constant as the kinematic and plate checks; not configurable, so findings stay comparable across stages. Severity: error.
3. **Press-fit exemption is derived, not declared.** A joint pair is exempt when its declared `params.clearance` is negative. An absent `clearance` does not exempt: every block that can back a joint (`dovetail_corner_joint`, `pin_hinge`) defaults to a positive gap. Positive-clearance joint pairs stay checked (an overlap there is a real bug, e.g. the pin_hinge zero-clearance case).
4. **Union granularity.** New optional `members[].union`; defaults to the part's single union; plan validation errors if the part has more than one union and `union` is absent, or if it names a union not in that part. Exemption keys are union ids.
5. **Every copy.** A `copy_of` part inherits the exemption for each union its source part's member names. Known limit: peg copy 1 vs hole copy 2 is also exempt. Mark with a `# ponytail:` comment; tighten when copies carry their own joint mapping.
6. **Co-plated pairs skipped**: `plate_clearance_check` already errors on gap <= layer height, which subsumes overlap.
7. **Kinematic pairs not skipped.** The sweep starts at the authored zero, so a rest overlap there reads as a confusing stop at 0. One duplicate report is accepted.
8. **Degrade path** mirrors `keep_out_check`: missing backend -> `check_skipped` warning; stale union -> `stale_artifact` error and that union excluded; missing STL -> `check_skipped`.
9. Resolvers `member_union(part, member)` and `part_union_ids(part)` in `units.py` serves both this stage and `_is_hinge_associated_union`.

## Risks / Trade-offs

- Copy exemption is over-broad -> documented limit, ponytail comment.
- Imported or undeflected snap geometry trips the gate with no escape hatch -> add `allowed_overlaps[]` when a real case appears.
- Tessellation noise slightly above 0.1 mm^3 on curved flush faces -> same epsilon already tolerated elsewhere; revisit only on a real false positive.
