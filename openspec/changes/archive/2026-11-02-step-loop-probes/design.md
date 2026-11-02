## Context

The builder sub-agent writes a whole part script, lints it, and runs
`run_cadquery_model.py` (subprocess, cold CadQuery import, full mesh checks, then
`render_preview.py` as a second subprocess that imports and runs the script again). On a
simple plate that is ~15 s, of which ~6 s is import and ~0.4 s geometry. The only
in-script intent checks are hand-placed `verify_stage` / `verify_boolean` calls. The
fresh-context auditor is the acceptance bar, and in the eval logs it is where most
failures come from, mostly on facts the kernel can measure (connected body,
through-hole depth). Blocks are plain functions returning a local-frame `Workplane`
and carry no description of their own intent.

Constraints: the part script is the deliverable and must run unchanged under
`build.py`, the quality gate and `CQ_PRINT_ROTATE` reloads; one builder per part, run
sequentially; no new third-party dependency; Windows is a first-class platform.

## Goals / Non-Goals

**Goals:**
- Catch a defect at the step that introduced it, by measurement, not by render review.
- Catch a later step that breaks an earlier feature (accumulating probes).
- Let the builder iterate on geometry without spending attempts; spend attempts only
  on plan revisions.
- Make the "stuck" decision deterministic (same probe fails again), not a judgment.

**Non-Goals:**
- Speed tuning beyond what the warm worker gives for free (in-process preview,
  parallel steps).
- User-facing snapshots or snapshot compare at checkpoints.
- Exposing the worker as an MCP server.
- Changing the deliverable pipeline (`write_assembly.py`, `build.py`, quality gate).

## Decisions

### D1. Script-first step list, not a REPL session
The builder edits `build/<part>.py` as today; the worker executes it as a step list and
caches results. Session state can never disagree with the file: a cache miss only costs
time. Alternative considered: REPL-first (snippets sent to a live namespace, script
written as a log). Rejected: namespace drift (dead variables, out-of-order re-runs)
breaks the "script is the deliverable" guarantee.

### D2. Three step kinds over one `Part` recorder
```python
from blocks import Part

part = Part("mounting_plate")
plate = part.select("box", id="plate")
part.resize(plate)
part.place(plate, op="base")

boss = part.select("screw_boss", id="boss")
part.resize(boss)
z = part.param("plate", "h")
part.place(boss, at=[(x, y, z) for x, y in part.positions("boss")], op="union")

result = part.result()
```
- `select(name, id=...)` resolves an inventory entry (block, template or primitive) and
  binds it to a plan instance id.
- `resize(handle)` takes no values: it binds the instance's `params` from the plan (D13).
  Unknown or missing params fail the step.
- `place(handle, at=..., rotate=..., op="base"|"union"|"cut", into=<union id>)`
  transforms and combines. `at` takes one point or a list (patterns). `into` targets a
  named union for multi-union parts.
- Outside the worker, `Part` executes each call eagerly, so the script is plain Python
  and every existing consumer runs it unchanged. Inside the worker, the same calls go
  through the cache.

Alternative considered: one `step(block, params, placement)` call. Rejected: the user
asked for select, resize and place as separate steps so each is checked on its own
(a bad parameter fails at `resize`, before any boolean).

### D3. No raw CadQuery in part scripts
`script_lint.py` enforces an allowlist: imports from `blocks`/`cq_verify`, `Part`
method calls, and plain arithmetic, comprehensions and loops for computing positions.
There is no `PARAMETERS` block and `resize` takes no arguments (D13). Any `cq.*` call or `Workplane` method is a lint error.
Geometry that no block covers is built from primitives (`box`, `cylinder`, `cone`,
`sphere`, `prism` from a 2D polyline, `revolve` from a 2D polyline), which are
inventory entries with probes like any block. Alternative considered: allow raw CQ with
generic checks only. Rejected: unprobed geometry is exactly what fails late.

### D4. Probes are declared by the block, in its local frame
Each inventory entry names a probe function `probes(**params) -> list[Probe]` living
next to the block. Probe kinds:

| kind | asserts |
|---|---|
| `solid_at(p)` | point inside material |
| `empty_at(p)` | point outside material |
| `ray(p, dir, hits)` | entry/exit count along a ray (through-hole, wall count) |
| `bbox(lo, hi, tol)` | body extents |
| `delta(sign)` | volume change of the `place` step (`union` > 0, `cut` < 0) |

`place` transforms the probes with the same `Location` as the solid and adds them to the
part's registry. A template is a step script over probed entries (amended during
implementation: not a single inventory entry), so every feature it builds is covered by
its entries' probes plus the plan probes of its archetype `part` in
`templates/archetypes.json`. Probes are tested with OCC point classification
(`BRepClass3d_SolidClassifier`) and line intersection, in-process, no mesh.

### D5. Plan-derived probes at step 0, and the retirement rule
`probes.py plan` derives step-0 probes from the part's plan entry: `solids == 1` after
every step from the first `place`; an envelope `bbox` when dimensions are declared; and
for each `interfaces[]` entry with `position_mm` and `diameter_mm`/`size_mm`, an
`empty_at`/`ray` (cut-type interfaces) or `solid_at` (boss-type) set. The interface type
-> probe mapping is a table in `probes.py`, not builder judgment.

Arming (amended during implementation): a cut or boss feature probe cannot hold before
its feature is built. A plan feature probe whose interface names an `instance` (the
`blocks_needed` id whose `place` builds it) is checked from that instance's `place`
step onward; one with no `instance` is checked only at `result()`. The envelope bbox
(size-bounded until `result()`, exact there) and `solids == 1` apply after every step.

Retirement: a later step legitimately changes an earlier block's region (a counterbore
cut into a boss removes the boss's wall probe). A **block** probe whose point lies inside
a later step's tool envelope is retired by that step and listed as `retired` in the
report, not as a failure. **Plan** probes never retire. That is what still catches "a
rib fills the screw-boss bore": the bore is a plan interface. Alternative considered:
builder-declared `replaces=` on steps. Rejected: the builder would author its own
exemptions.

### D6. Warm worker, one per project, with cold fallback
`src/step_worker.py` has a server mode and a client CLI. The client starts the server
on demand (`multiprocessing.connection.Listener` on 127.0.0.1, random port, authkey;
address and key in `build/.step_worker.json`), sends `run <script>`, and prints the JSON
report. The server imports CadQuery once, executes the script with `Part` in cached mode,
and exits after an idle timeout. If the server dies (OCC segfault) or exceeds the
timeout, the client kills it, runs the script cold in a subprocess with the same report
format, and the next call starts a fresh server. The cache is in memory only; losing it
is never a correctness problem (D1).

### D7. Prefix-hash cache
Step i's key is `sha256(key[i-1] + kind + resolved args + block source hash)`. On run,
the worker reuses the longest cached prefix and executes from the first miss. Resolved
args include the plan values `resize` and `param` read, so a plan edit invalidates
exactly the steps that use the changed value and everything after them.

### D8. Report contract and tiers
Per run: `{success, part_id, steps: [{index, kind, block, ok, cached, volume, delta,
solids, probes: {checked, failed: [...], retired: [...]}}], failed_step,
diff_vs_last_good, snapshot, probe_stuck}`. The cheap tier (validity, solid count, all
registry probes) runs after every step. When every step passes, the client runs the
existing `run_cadquery_model.py` validate+preview command for the full tier (mesh
checks, thin walls, preview), so that JSON contract and the auditor's inputs are
unchanged. In-process full tier is a later optimization, not part of this change.

### D9. Builder-only snapshots
After each passing step the worker keeps the body and registry as `last_good`.
`snapshot save <name>` writes `build/snapshots/<part>/<name>.brep` plus the step-list
source and registry JSON. `snapshot restore <name>` rewrites the script's step list from
the stored source, so the file stays the truth. Snapshots never touch the plan: values
are plan-owned (D13), so restoring cannot roll back a parameter.
`snapshot compare <a> <b>` reports volume, bbox, solid count, face count and probes
whose state differs. Snapshots never appear in user checkpoints.

### D10. `probe_stuck` is decided by the program
The worker keeps per-part probe failure history in `build/<part>.steps.jsonl`. Probe
identity is `(owner, kind, rounded location)`. When a probe that already failed fails
again after a snapshot restore or after the failing step's content changed, the report
sets `probe_stuck: true` with both occurrences. The builder must then return `blocked`
with reason `probe_stuck`; it may not keep looping. There is no step-failure budget
otherwise.

### D11. Attempt = plan revision
An attempt number is the count of plan revisions that touched the part (a `request_log`
entry targeting it, or the initial plan). `run_cadquery_model.py --attempts-log` on the
full-tier run writes the attempt record as today, keyed by that number; step reports go
to `build/<part>.steps.jsonl`, not `attempts.jsonl`. Eval scorecards that count attempts
change meaning; they are updated in the same change.

### D12. Auditor scope
When the builder contract carries a passing step report, `render_prompt.py audit` drops
the connectedness invariant and the position-based feature-presence questions (they are
settled by `solids == 1` and plan probes) and keeps intent, proportion and request-
conformance questions.

### D13. Resize reads parameters from the plan
Each `blocks_needed` object gains `id` (instance handle, unique in the part) and
`params` (name -> value, matching the inventory entry's `params`). Every selected
instance, primitives included, must have a plan entry. `resize(handle)` binds exactly
those values; `part.param(id, name)` exposes them for position arithmetic and
`part.positions(id)` returns the instance's planned positions (from its interfaces'
`position_mm`, when declared). Consequences:
- Plan and script cannot drift: there are no dimension literals in the script, so
  `plan.py import-params` has nothing to reconcile for step scripts.
- A dimension change is a plan edit, which is an attempt (D11). This lines up the
  retry rule with where values live.
- `Part` locates `BUILD_PLAN.json` from `CQ_PLAN`, else by walking up from the script's
  directory; the bundle and `export_standalone.py` ship the plan next to the scripts.
- Cross-part agreement keeps going through `joints` / `mate_chain.py`, now on plan
  values only.

Alternative considered: keep literals in `PARAMETERS` with `import-params` round-trip.
Rejected: it keeps two homes for one value and lets the builder change a dimension
without a plan revision.

### D14. Edge treatments are applied after the print pose is known
Whether an edge is chamfered or filleted depends on its bed-relative direction
(`edge_treatment_check.py`'s rule: chamfer horizontal edges, fillet vertical ones), so
treatments are not steps in the build loop. A plan instance may declare `edges`
(edge-set name -> size in mm); each inventory entry names its edge sets
(`box`: `top_outer`, `bottom_outer`, `vertical`, ...) as curves in its local frame.
- During the step loop `Part.result()` returns the untreated body; orientation is chosen
  on it.
- In the existing finishing pass (`CQ_PRINT_ROTATE` set: `write_assembly.py`,
  `build.py`), `Part.result()` maps each declared edge set to final-body edges lying on
  the placed set's curves, picks chamfer or fillet per edge from its print-pose
  direction (diagonal edges: fillet), and applies them.
- After treatment the registry is re-checked. Plan probes must still pass; block probes
  inside a treated edge's zone retire. A failure is a typed `finishing_probe_failed`
  error with action `ask_user`, since edge sizes are plan values.
- The existing pose-stability guard re-scores orientation on the treated body.
- Functional radii (a hook root fillet for strength, a bore) are block geometry and block
  parameters, not edge treatments. Blocks lose their cosmetic edge options
  (`fillet_box`'s `corner_r` becomes a `box` instance with an `edges` entry).

`edge_treatment_check.py` stays for legacy scripts; for step scripts its rule is applied
by construction.

## Risks / Trade-offs

- [Block coverage gap: a shape needs geometry no block or primitive can express] ->
  `prism`/`revolve` from 2D polylines cover most profiles; a missing primitive is a
  library addition, surfaced by the builder as `blocked` with reason `missing_block`.
- [Probe authoring cost on ~40 blocks and 13 templates] -> probes are small (2-6 per
  block); a test asserts every inventory entry has a probe function whose probes pass on
  its own default build.
- [Retirement hides a real regression of a block probe] -> plan probes never retire, and
  the report lists every retired probe so the auditor can see it.
- [Edge-set mapping fails after booleans split or trim an edge] -> map by "lies on the
  placed curve" rather than edge identity, so a trimmed edge still maps; an edge set that
  maps to no final edge is a `finishing_probe_failed` error, never silently skipped.
- [Untreated body chooses the orientation, treated body may prefer another] -> the
  existing pose-stability guard reports `pose_shift`; the accepted pose is kept.
- [Planner now owns every dimension, including primitives' sizes] -> the plan gets
  larger and the planner prompt must emit instance `params`; `plan.py validate` checks
  each instance against its inventory entry's `params` so a missing value fails at
  planning, not in the build loop.
- [Worker lifecycle on Windows (orphaned processes, port reuse)] -> idle timeout, address
  file rewritten on each start, client kill on timeout, cold fallback always available.
- [OCC point classification tolerance near faces] -> probes are placed at least
  `max(0.1 mm, 10 * tolerance)` from any declared face; probe functions get a helper that
  enforces it.
- [BREAKING script format] -> existing user projects keep building (cold path runs any
  script); only new builder edits require the step form.

## Migration Plan

1. Land the plan schema additions (`blocks_needed[].id/params/edges`), `probes.py`,
   `Part` (eager mode, plan-bound `resize`) and primitives with tests; no prompt change.
2. Add probes to every block and template; inventory schema gains `probes`.
3. Convert `templates/*.py` to the step form; regenerate eval part scripts.
4. Land `step_worker.py` and the lint allowlist.
5. Switch `prompts/planning.md` (instance params and edges), `prompts/builder.md`,
   `prompts/part.md`, `prompts/audit.md`, `skill/phase3_build.md` and the telemetry
   semantics in one commit.
6. Run the eval suite; compare `visual_mismatch` rate and blocked rate with the
   2026-09 baseline.

Rollback: revert step 5; steps 1-4 are additive and harmless with the old prompts.

## Open Questions

- Placement values: positions in `place(at=...)` may still be script arithmetic over
  `part.param` / `part.positions`. Should rotations and positions with no plan interface
  also move into the plan, or is script arithmetic over plan values enough?
