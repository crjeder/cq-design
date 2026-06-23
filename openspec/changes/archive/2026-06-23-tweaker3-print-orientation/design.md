## Context

`print_orientation.py` enumerates bed-down candidates (convex-hull facets + 6 axis
faces, merged within `NORMAL_MERGE_DEG`) and scores each on strength, support, and
visual quality, selecting via `optimize_for` modes (`strength`, `min_support`,
`visual_quality`). The support term comes from `mesh_io.overhang_metrics(...)
["overhang_area_mm2"]` minus bed contact, i.e. a flat area sum above the angle limit.
That same `overhang_area_mm2` is consumed by the quality gate (`overhang-analysis`
capability) as a true physical area for user-facing reporting.

Tweaker-3 (GPL-3.0) documents three improvements we want: a severity-weighted overhang
cost, area-cumulation candidate generation, and a build-height objective. This project
is PolyForm Noncommercial; bundling GPL code is license-incompatible, so we reimplement
the formulas clean-room and do not copy Tweaker-3 source or its tuned constants.

## Goals / Non-Goals

**Goals:**
- Severity-weighted support cost so steeper overhangs rank worse than shallow ones of
  equal area, used for orientation ranking only.
- Area-cumulation candidate source supplementing the existing candidate set.
- A `min_build_height` optimization objective.
- First-layer-height band for bed-contact detection.
- Determinism preserved; repeated runs give identical recommendations.

**Non-Goals:**
- Changing `overhang_metrics`' `overhang_area_mm2` semantics or the `overhang-analysis`
  quality-gate behavior.
- Wrapping Tweaker-3 as a dependency or external MCP.
- Re-tuning or re-speccing the existing `min_support` / `visual_quality` modes (owned by
  the in-flight `print-optimization-modes` change).

## Decisions

### Severity-weighted support cost as a new metric, not a redefinition
Add a new helper (e.g. `mesh_io.support_cost(mesh, overhang_deg, exponent)`) returning a
severity-weighted scalar: per downward face, `area * |lean_past_limit| ** exponent`
where `lean_past_limit` is how far the face normal leans past the angle limit along
build -Z (0 at the limit, growing toward horizontal). `print_orientation` uses this for
the `support` ranking key. `overhang_metrics["overhang_area_mm2"]` is left untouched so
the quality gate keeps reporting true area.
- Alternative considered: redefine `overhang_area_mm2` to be severity-weighted.
  Rejected: it is a user-facing physical area in `overhang-analysis`; weighting it would
  break that contract and confuse the printability report.
- The exponent default is chosen by us (a value > 1 that makes near-horizontal faces
  dominate); we do not copy Tweaker-3's `OV_H = 2.574`.

### Area-cumulation supplements, not replaces, hull + axis candidates
Accumulate face normals weighted by face area into buckets, take the top-N by
accumulated area, and add them to the existing candidate list before the
`NORMAL_MERGE_DEG` dedup pass. The axis-aligned baseline and hull facets remain so small
flat faces are never lost.
- Alternative: replace hull enumeration entirely. Rejected: hull facets capture stable
  resting faces that area-cumulation can miss on faceted parts; supplementing is strictly
  safer and still bounded by the dedup pass.

### `min_build_height` as a fourth `optimize_for` mode
Add `min_build_height` to `OPTIMIZE_MODES`. Primary key: posed bounding-box Z extent
(lower is better) within a tolerance band; tiebreak by strength then support then `idx`,
mirroring the existing lexicographic `_select` structure. Build height is computed from
the candidate rotation applied to the mesh.
- Alternative: fold height into the support score. Rejected: height and support are
  distinct objectives; a separate mode keeps selection explainable.

### First-layer band for bed contact
Replace the tight `CONTACT_Z_EPS_MM` test in `_support_metrics` (and the matching
on-bed test in `_gentle_incline_fraction`) with a first-layer-height band constant so a
resting face within roughly one first-layer height of the floor counts as contact.
- Alternative: keep the tight epsilon. Rejected: a marginally non-coplanar resting face
  currently drops out of bed contact, understating contact area on real meshes.

## Risks / Trade-offs

- [Exponent/band defaults are hand-tuned, not evolutionarily optimized like Tweaker-3] →
  Pick conservative defaults, expose them as module constants, and lock behavior with
  targeted unit tests (synthetic meshes with known overhang severity / resting faces).
- [Severity weighting could change selected orientations on existing models] → It only
  affects the `support` ranking key and tiebreaks; strength-first selection is unchanged.
  Determinism tests and a before/after check on fixture meshes guard regressions.
- [Area-cumulation adds candidates, raising scoring cost on dense meshes] → Bound N
  (top-N) and rely on the existing dedup pass; scoring stays linear in candidate count.
- [Overlap with in-flight `print-optimization-modes` adding modes] → We only ADD
  `min_build_height` and refine support/candidate requirements; no edits to that change's
  mode definitions.
