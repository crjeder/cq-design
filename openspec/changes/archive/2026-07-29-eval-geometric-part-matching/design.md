## Context

`evals/run_evals.py` scores a run directory against `evals/cases/`. For each golden part it
calls `find_produced_stl(case_run_dir, part_id)`, which probes `stl/<part_id>.stl` and then
falls back to an unordered `rglob`. That lookup encodes an assumption that was never enforced
anywhere: **that the produced plan uses the same part ids as the golden plan.**

Nothing establishes that. No `request.md` names its parts; the planner invents ids from the
noun ("body", "lid", "stand"), and the corpus named them after the case slug
("enclosure_body", "sliding_lid", "phone_stand"). Agreement is coincidence, and the
coincidences are unstable run to run -- `l_bracket` became `bracket`, `u_clip` became `clip`
and back, `wall_hook` became `hook`. Because `aggregate()` drops `None` cases from the mean,
each scorecard reports the mean over a different set of cases. The proposal has the full
table and the three scorecards that demonstrate it.

Constraints on the fix:

- Score mode must stay model-free and cheap. It is meant to be run before and after every
  prompt/reference/routing change.
- The corpus is small: 10 cases, 1-2 parts each. Algorithms that would be too expensive at
  scale are free here, but the code should not encode an assumption that parts stay <= 2.
- `trimesh`, `numpy`, `scipy`, `rtree` are already declared dependencies. Adding one is a real
  cost (the eval harness is meant to be runnable from a clean checkout); not adding one is
  strongly preferred.
- `model_export` already defines a naming contract for what it writes into `stl/`. The scorer
  should consume that contract rather than guess at filenames.

## Goals / Non-Goals

**Goals:**

- Chamfer coverage does not depend on part naming, so successive scorecards measure the same
  case set and are comparable.
- A golden part with no produced counterpart fails the case rather than disappearing from the
  average.
- "Produced nothing" is distinguishable in the scorecard from "scorer could not locate it."
- The pairing the scorer chose is auditable from `scorecard.json` -- a reader can see which
  produced STL was scored against which golden mesh.
- No new dependencies.

**Non-Goals:**

- Rotation-invariant Chamfer. Deferred; see Open Questions.
- Changing the Chamfer metric itself (symmetric, point-to-surface, bbox-centered, 2000
  samples). Only correspondence and aggregation change.
- Changing golden part ids or `generate_goldens.py`. Ids stay; they stop being a scoring key.
- Judging whether a divergent decomposition is *wrong*. The scorer reports it against
  `case.json`'s `expected_parts`; interpretation is the reader's.
- Scoring assembly/relative pose between parts. Each part is scored independently, as today.

## Decisions

### D1: Correspondence by geometric assignment, not by identifier

Four candidates were considered:

| approach | why not |
|---|---|
| **Pin ids** -- declare `part_ids` in `case.json`, force the pipeline to use them | No channel exists to pass them. It would mean injecting "name the parts `box_body`, `box_lid`" into `request.md`, contaminating the exact prompt under A/B test, and it measures naming compliance rather than geometry. Breaks whenever the pipeline decomposes differently. |
| **Match through the produced `BUILD_PLAN.json`** by declared `dimensions`/`description` | Trusts what the plan *declares* over what was *built*. A plan claiming 80x50x30 while the script builds 80x50x3 mis-assigns -- precisely the failure class the eval exists to catch. |
| **Whole-model Chamfer** -- concatenate everything, one number | Goldens are per-part in authored frames with no relative pose; a model-level comparison would require inventing one. Also destroys per-part resolution. |
| **Geometric assignment** (chosen) | Names are not part of the deliverable spec -- nothing downstream of the eval cares what a part is called. The question the metric actually asks is "did the pipeline produce the right *set* of solids", which is a bipartite matching problem. |

### D2: Assignment cost uses an independent descriptor, not Chamfer

The obvious implementation builds the cost matrix out of pairwise Chamfer and minimizes it.
That is wrong in a subtle way: **it selects the pairing that makes the reported number look
best**, so the metric grades its own homework. With <= 2 parts the effect is small, but it is
free to avoid.

Cost is instead a scale-relative shape descriptor computed per mesh:

- the three bounding-box extents, **sorted descending**
- the mesh volume

paired as a sum of relative differences (`|a-b| / max(a,b)` per term), so a large part and a
small part contribute comparably instead of the large one dominating. Chamfer is then computed
**only on the assigned pairs**: n*m cheap descriptor comparisons plus n Chamfer computations,
rather than n*m Chamfer computations.

Sorting the extents makes the descriptor invariant to axis-aligned rotation. That is a
deliberate bonus: assignment keeps working on a rotated part even though Chamfer does not yet
(see Open Questions), so the rotation gap stays confined to the metric and does not also
corrupt the pairing.

Assignment itself is `scipy.optimize.linear_sum_assignment`, which handles rectangular
matrices and returns `min(n, m)` pairs. `scipy` is already declared (for `trimesh`'s
`CollisionManager`), so this adds nothing.

### D3: Produced solids come from `model_export`'s naming contract

Enumerate `<case>/stl/*.stl`, excluding:

- `plate_*.stl` -- fused multi-union plate duplicates; the constituent unions are already
  present individually, so including these would double-count geometry.
- `keep_out__*.stl` -- declared keep-out zones, never printed geometry.
- `export_manifest.json` is not an STL and needs no special handling.

This replaces per-golden-part filename probing, and incidentally makes **multi-union parts
scoreable for the first time**: `model_export` writes one STL per *union*, so a part declaring
`unions: [a, b]` produces `a.stl` and `b.stl` and never a `<part_id>.stl` -- it could not be
found even when ids agreed.

The `rglob` fallback is removed rather than kept as a safety net. It can return
`build/<id>.stl`, which is the **print-oriented** mesh; `chamfer_mm` does not solve rotation,
so that path silently scores a correct part as catastrophically wrong. `hits[0]` over an
unordered walk also makes which duplicate you get arbitrary. A missing `stl/` directory should
surface as "no artifacts", not be papered over with a mesh in the wrong frame.

### D4: Cardinality is reported and is load-bearing for pass/fail

| condition | behavior |
|---|---|
| `\|produced\| == \|golden\|` | all pairs matched and scored |
| `\|produced\| < \|golden\|` | unmatched golden parts recorded as misses; `within_tolerance` is `false` |
| `\|produced\| > \|golden\|` | all golden parts scored; surplus reported against `case.json`'s `expected_parts` |
| `\|produced\| == 0` | distinct `no_artifacts` state; Chamfer fields `null`, `within_tolerance` `false` |

The `within_tolerance` rule is the second half of the fix. Today it is
`all(c <= tol for c in measured) if measured else None`, and `measured` excludes parts with no
produced mesh -- so a run that built one of two parts, that one accurately, reports
`within_tolerance: true`. Missing geometry must fail.

The `no_artifacts` state exists because `evals/runs/post-agent-routing/` has entirely empty
case directories and currently reports every column `unavailable` -- the same cell a naming
miss produces. A total pipeline failure and a scorer lookup failure should not be the same
symbol.

### D5: Scorecard keeps golden part ids as its keys, and records the pairing

`chamfer_mm` stays a `{golden_part_id: value|null}` map so the markdown table and existing
readers keep their shape. A sibling `matched_to` map records which produced STL each golden
part was assigned, making the assignment auditable after the fact -- important because a
wrong-but-plausible pairing is otherwise invisible.

The aggregate additionally reports **how many cases contributed to the mean Chamfer**. The
original defect was a silently changing denominator; surfacing the count means it can never
again be mistaken for a moving metric.

## Risks / Trade-offs

- **Two golden parts with near-identical descriptors** (a case with two copies of one bracket)
  -> assignment between them is arbitrary. Benign: if the descriptors match that closely the
  meshes are near-identical, so Chamfer is materially the same either way.
- **Badly wrong produced geometry can be assigned to the "wrong" golden part** -> Chamfer is
  large under any pairing, so the case still reports as bad; only the attribution shifts.
  Mitigated by D5's `matched_to`, which makes the choice inspectable rather than hidden.
- **Existing scorecards become incomparable to new ones** -> unavoidable and intended; the old
  numbers were not comparable to *each other* either. See Migration Plan.
- **Removing the `rglob` fallback could turn a previously-scored case into `no_artifacts`** if
  some run wrote STLs outside `stl/`. Checked against all four run directories: every produced
  STL lives in `stl/` (with print-oriented duplicates in `build/`), so no case regresses. A run
  layout that does not populate `stl/` genuinely has no exportable artifacts.
- **Descriptor uses volume, which requires a watertight-ish mesh** -> `trimesh` reports volume
  for non-watertight meshes too, but the value is unreliable. The extents terms still carry the
  assignment in that case, and a non-watertight produced mesh is already a gate failure
  upstream.

## Migration Plan

1. Land the scorer change with tests; no run directory is modified.
2. Re-score `evals/runs/baseline-pre-claude5`, `before-citation`, and `after-citation` in score
   mode (no model invocation, no token cost) to regenerate their `scorecard.json` /
   `scorecard.md` on the new basis. This is the first comparable A/B the corpus has produced,
   and it directly informs the open `engineering-knowledge` section-4 item in `TODO.md`.
3. Note in the re-scored runs that pre-change scorecards are not comparable.

Rollback is reverting the commit; run directories are inputs and are never written by score
mode, so nothing needs undoing.

**Time-sensitivity**: `evals/runs/` is untracked (`git ls-files evals/runs` -> 0) and exists
only on the current machine. Step 2 is possible only while those directories survive; if they
are cleaned, re-scoring requires a fresh `--generate` run at full token cost.

## Open Questions

- **Rotation handling.** `chamfer_mm` centers both meshes by bbox center, so translation
  cancels (two-part-box's lid at `translate_mm: [0,0,22]` scores correctly) but rotation does
  not. Produced `stl/` meshes are the assembled pose; goldens are the authored frame. No corpus
  case currently rotates a part, so this is latent -- the first plan carrying
  `rotate: [{axis: "Y", angle_deg: 90}]` scores as a total mismatch. Two candidate fixes:
  invert the declared placement from the run's own `BUILD_PLAN.json` (exact, cheap,
  `placement.to_matrix` already exists, but reintroduces a dependency on what the plan
  declares); or search the 24 axis-aligned rotations and take the minimum (no plan dependency,
  but optimistically biased and 24x the Chamfer cost). Deliberately unresolved -- D2 keeps the
  gap confined to the metric so it can be closed later without touching correspondence.
- **Should a surplus produced part fail the case?** D4 reports it but does not fail on it. A
  pipeline that splits one golden part into two printable unions may be behaving correctly, and
  `expected_parts` is currently advisory metadata. Left as reported-only until there is a case
  that discriminates.
