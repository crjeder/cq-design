## Why

The Chamfer metric exists so prompt, reference, and model-routing changes are verified
empirically. It currently cannot do that: **the aggregate is computed over a case set that
changes between runs**, so two scorecards are not comparable.

`run_evals.py`'s `find_produced_stl` looks for `stl/<golden_part_id>.stl`. That lookup is
correct against `model_export`'s naming contract -- but the golden's part id and the produced
plan's part id are authored independently and were never required to agree. No `request.md`
names its parts; the planner invents ids from the noun. The corpus named them after the case
slug. When they happen to coincide, the case is scored; when they don't, it reports
`unavailable`.

| case | golden part id | baseline | before-citation | after-citation |
|---|---|---|---|---|
| adapter-ring | `adapter_ring` | `adapter_ring` OK | `adapter_ring` OK | `adapter_ring` OK |
| l-bracket | `l_bracket` | `l_bracket` OK | `l_bracket` OK | `bracket` miss |
| wall-hook | `wall_hook` | `wall_hook` OK | `wall_hook` OK | `hook` miss |
| u-clip | `u_clip` | `u_clip` OK | `clip` miss | `u_clip` OK |
| phone-stand | `phone_stand` | `stand` miss | `phone_stand` OK | `stand` miss |
| enclosure-body | `enclosure_body` | `body` miss | `body` miss | `body` miss |
| sliding-lid | `sliding_lid` | `lid` miss | `lid` miss | `lid` miss |
| snap-lid | `snap_lid` | `lid` miss | `lid` miss | `lid` miss |
| boss-plate | `boss_plate` | `mounting_plate` miss | `mounting_plate` miss | `mounting_plate` miss |
| two-part-box | `box_body`,`box_lid` | `body`,`lid` miss | `body`,`lid` miss | `body`,`lid` miss |

The coincidences are unstable run to run, so `aggregate()`'s `mean_of("mean_chamfer_mm")` --
which skips `None` cases -- silently reports a different measurement each time:

```
  baseline         adapter-ring l-bracket u-clip wall-hook     -> 5.119 mm
  before-citation  adapter-ring l-bracket phone-stand wall-hook -> 7.391 mm
  after-citation   adapter-ring                  u-clip        -> 2.202 mm
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                   different denominator set every run
```

"Chamfer went 7.391 -> 2.202" is not a geometry result. Fixing this before C2 leans on the
metric is the point.

Two defects ride along in the same lines:

- **Unmatched parts do not fail.** `within_tolerance` is `all(c <= tol for c in measured)`,
  and `measured` excludes parts with no produced mesh. A run that built one of two parts, that
  one accurately, reports `within_tolerance: true`. Missing geometry is invisible to pass/fail.
- **"Produced nothing" is indistinguishable from "scorer could not find it."**
  `evals/runs/post-agent-routing/` has completely empty case directories and reports every
  column `unavailable` -- the same cell a naming miss produces.

The signal being lost is real. `after-citation/sliding-lid` is recorded as a clean first-shot
pass; its produced mesh spans z 0..6 with volume 9808 mm3 against a golden spanning z -1..3
with volume 14512 mm3. A ~50% volume miss, unmeasured across three runs.

## What Changes

- **BREAKING (scorecard semantics)**: correspondence between a produced solid and a golden
  mesh is established by geometry, not by part id. Part ids no longer affect scoring. Existing
  `scorecard.json` files are not comparable to new ones; the run directories they were computed
  from are re-scoreable without invoking a model.
- Enumerate produced solids from `model_export`'s naming contract -- `<case>/stl/*.stl` minus
  `plate_*.stl` (fused plate duplicates) and `keep_out__*.stl` (never printed geometry) --
  instead of probing one filename per golden part. This also covers multi-union parts, whose
  STLs are named per union and so never matched a `<part_id>.stl` probe even when ids agreed.
- Remove the `rglob` fallback. It can return `build/<id>.stl`, the print-oriented mesh, which
  `chamfer_mm` (bbox-centered, no rotation solving) would score as catastrophically wrong; and
  `hits[0]` over an unordered walk makes which duplicate you get arbitrary.
- Solve a one-to-one assignment between produced and golden solids. **The cost matrix uses an
  independent descriptor (sorted bounding-box extents + volume), not Chamfer.** Minimizing
  Chamfer to choose the pairing would pick the best-case pairing and bias the reported number
  optimistically; an independent descriptor keeps the metric honest and costs n*m cheap
  comparisons plus n Chamfer computations instead of n*m. `scipy` is already a declared
  dependency, so `linear_sum_assignment` adds nothing.
- Report cardinality explicitly and let it fail the case:
  - `|produced| < |golden|` -- each unmatched golden part is a miss; `within_tolerance` is
    `false`, not `null` or `true`.
  - `|produced| > |golden|` -- a divergent decomposition, reported against `case.json`'s
    `expected_parts`.
  - `|produced| == 0` -- a distinct state from "scored", so a total pipeline failure is
    legible in the scorecard.
- Make the aggregate's coverage visible: report how many cases contributed to the mean Chamfer
  so a changing denominator can never again be mistaken for a moving metric.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `eval-harness`: the **Eval metrics** requirement changes. Chamfer is currently specified as
  "between each produced mesh and its golden mesh" with correspondence left implicit (and
  implemented as part-id equality). It gains an explicit geometric-correspondence rule, a
  cardinality-mismatch rule that fails `within_tolerance`, and an aggregate-coverage field.
  The "Missing telemetry degrades, not crashes" scenario is unaffected.

## Impact

- `evals/run_evals.py`: `find_produced_stl` is replaced by produced-solid enumeration plus
  assignment; `score_case`'s Chamfer loop, `within_tolerance`, and `aggregate` change.
- `tests/test_run_evals.py`: scoring-path tests; fast, no CadQuery.
- `evals/cases/*/case.json`: no change. `expected_parts` is already present and becomes load-bearing.
- `evals/cases/*/BUILD_PLAN.json`, `evals/generate_goldens.py`: no change. Golden part ids stay
  as they are; they simply stop being a scoring key.
- No new dependencies (`scipy`, `trimesh`, `numpy`, `rtree` all already declared).
- `evals/runs/` is untracked and exists only on the current machine. The three scoreable runs
  (`baseline-pre-claude5`, `before-citation`, `after-citation`) can be re-scored for free once
  this lands, but only while those directories survive.

## Re-score Results (2026-07-29)

Re-scored the three surviving run directories in score mode (no model invocation).
All ten cases now contribute to every scorecard -- previously the effective set was
4, 4, and 2 cases respectively (per the table above).

| run | old mean chamfer (cases) | new mean chamfer (cases) |
|---|---|---|
| `baseline-pre-claude5` | 5.119 mm (4) | 3.118 mm (10) |
| `before-citation` | 7.391 mm (4) | 4.123 mm (10) |
| `after-citation` | 2.202 mm (2) | 2.423 mm (10) |

The re-scored numbers move, as expected -- the old numbers were never measuring the
same case set to begin with, so "moved" isn't meaningful as a trend claim. Pre-change
`scorecard.json`/`scorecard.md` files in these run directories are **not comparable**
to the regenerated ones; treat any historical reference to their numbers (including
the table in "Why" above) as documentation of the bug, not as a metric baseline.

**Caveat for the open `engineering-knowledge` section-4 item (`TODO.md` item 5):**
despite the run names, none of these three directories is the "hooks on vs. off"
comparison that item wants. `before-citation`/`after-citation` predate the
engineering-rationale hooks entirely (attempts timestamped 2026-07-20, landed
2026-07-21 for item 13's reference-citation change; no part script in either run
carries an `ENGINEERING RATIONALE` block). `baseline-pre-claude5` is dated
2026-07-28, immediately before the Claude 5 migration commit, and looks like a
pre-migration baseline for that unrelated comparison. This fix makes a *future*
hooks-on/off A/B trustworthy for the first time, but item 5's section 4 still needs
that run to actually happen -- it is not satisfied by re-scoring what already
existed on disk.

## Deferred

- **Rotation.** `chamfer_mm` centers both meshes by bbox center, so translation cancels
  (two-part-box's lid at `translate_mm: [0,0,22]` scores correctly) but rotation does not. The
  produced `stl/` mesh is the assembled pose; goldens are the authored frame. No case in the
  corpus currently rotates a part, so this is latent -- the first plan carrying
  `rotate: [{axis: "Y", angle_deg: 90}]` will score as a total mismatch. Options when it
  surfaces: invert the declared placement from the run's own `BUILD_PLAN.json` (exact, cheap,
  `placement.to_matrix` already exists), or search the 24 axis-aligned rotations
  (optimistically biased, 24x cost). Not resolved here.
