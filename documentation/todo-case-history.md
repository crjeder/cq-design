# Case history and closed investigations

Write-ups behind closed or rejected tasks (linked from [DONE.md](DONE.md)), plus the open notes they still carry (for example `/retrofit` under C5 fixes did not take). Open tasks: [TODO.md](../TODO.md).

### C5 compass language

Investigate "compass language" `.\debug\image-1786538590774.png` shows the
problem: east should be right. Reason: mixing up "Viewed from South" and
"south facing" under observation.

**Re-confirmed 2026-09-08** (`debug/session-2026-09-08.md`, round 10). The user
asked for "fillet on the east side"; the skill had to stop and `AskUserQuestion`
which end is East, *again* -- the fifth round in this project's history to
re-litigate it (rounds 8, 9, 10 explicitly). The user's answer: "I am looking at
plate_preview.png 'Front' which per convention is 'viewing from south': the R8 is
on the left 'West' side. previously we mixed up the naming conventions."

Root cause, now pinned:
- `prompts/planning.md:3-14` hardwires **East = +X**, North = +Y, and defines the
  standard views by compass station.
- This project's real-world anchor is the *opposite*: `BUILD_PLAN.json`'s
  `request_log` carries "East = right side of the ashtray.jpg photo = X=0 (near
  the yellow mark), matching parameters.py convention", and `parameters.py` has
  `BEZEL_EAST_CORNER_FILLET_MM` commented "East (right/X=0 side)". So in this
  project East points in **-X**, 180 deg from the skill default.
- There is **no `BUILD_PLAN.json` field that records a project's resolved
  axis->compass binding.** The `feature-vocabulary` spec mandates that the skill
  *use* compass prose and echo ambiguous references back before acting (which the
  session did), but that is a per-turn patch: nothing persists the resolution, so
  every new correction round re-derives "East" from either the prompt default or
  the buried photo note and can land on either end. The `2026-08-07-rotation-clock-vocabulary`
  change fixed rotation *direction* words (clockwise/counterclockwise), not the
  base axis<->compass binding.
- Secondary contributor: "viewed from south" (a camera position) vs "south face"
  (a face whose outward normal is -Y) are distinct and were conflated in the
  reasoning. On the South viewing station (+X to the viewer's left) the photo's
  "right side" maps to -X, which is exactly the project's "East" -- the skill's
  own convention would call that West.

Fix (proposed): a `coordinate_frame` object in `build_plan_schema.json`, e.g.
`{"east": "-x", "north": "+y", "up": "+z"}`, written at Phase 1 exit whenever the
user's frame differs from the `prompts/planning.md` default, defaulting to the
standard binding when absent. Every checkpoint-prose and review step reads it
instead of assuming +X. `plan_validate.py` emits an advisory finding (the
`check_block_thinness` tier) when `planning_notes`/`request_log`/`intent` prose
contains a compass term and no `coordinate_frame` is recorded. This is prose- and
review-frame only; it does not touch `placement.rotate` / joint `dof.direction`
sign conventions, which stay right-hand-rule on the literal axes.

### C5 hinge ear center-vs-edge

The hinge ear shows an old problem: placing primitives with their center
aligning to the other part's edge -- see `.\debug\image-1786540203166.png`.

Investigated (transcript: session `b6ac548d...`, `session-export-1786538430013.zip`,
round 9's final `cradle.py`). Exact code:

    EAR_STANDOFF = 5.0
    PIVOT_Z = BAR_H + EAR_STANDOFF          # 8.5 + 5.0 = 13.5
    RISER_DEPTH = 4.0
    riser = car_box(x, TONGUE_WIDTH,
                    PIVOT_Y - RISER_DEPTH, RISER_DEPTH,   # Y 1.0 .. 5.0
                    BAR_H, EAR_STANDOFF)                  # Z 8.5 .. 13.5
    knuckle = ....center(PIVOT_Y, PIVOT_Z).circle(KNUCKLE_R)   # r=2.6 at (5.0, 13.5)

Both of the riser box's far faces land exactly on the disc's CENTER, not on its
tangent: top face Z=13.5 == PIVOT_Z, +Y face Y=5.0 == PIVOT_Y. The disc spans
Z 10.9..16.1 and Y 2.4..7.6, so its lower-rear quadrant is swallowed by the riser
and only the upper-front quarter stands proud -- the "half-buried disc on a boxy
step" in the render. Bbox Zmax 16.1 in the preview footer confirms this is the
shipped geometry.

The correct riser tops out at the tangent line: `PIVOT_Z - KNUCKLE_R` (10.9), i.e.
height `EAR_STANDOFF - KNUCKLE_R` = 2.4, and its Y-band should be centered on
PIVOT_Y rather than ending there. The error is not a missing constant -- it is
reusing the pivot literal for a boundary that owes it a +/- radius offset.

Notes for the fix: (1) nothing in the pipeline can see this -- the union is
watertight, volume/faces/bbox are all plausible, no DFM rule is violated; only
the rendered preview shows it, which is why it survived to round 9. (2)
`script_lint`'s AST pass cannot catch it either: `car_box` is a script-local
helper, so the checker would have to know that args 5+6 form a Z-band and that
the same name feeds a `circle()` center. (3) The tractable fix is the
`anchor()`/`place_at()` API in [BOSL2 attachables](#bosl2-attachables) -- make
"tangent of this body" the only way to express the join, so center-as-edge
cannot be typed. A cheap partial detector: after a union, flag when an added
body's overlap with the existing solid exceeds ~20% of its own volume (here the
knuckle loses ~25%), but that also fires on legitimately embedded pins.

**Re-confirmed 2026-09-08** (`debug/session-2026-09-08.md`). `verify_seated` was
merged Sep 1 (commit 51dc097) as a construction-time guard **the part script must
call**, plus a `prompts/part.md` rule routing knuckle hinges through
`blocks.joints.pin_hinge`. The Sep 8 re-run edited `EAR_STANDOFF` 5.0 -> 6.0 in
the same hand-rolled `cradle.py` and rebuilt clean. `grep -n "verify_\|pin_hinge"
build/cradle.py build/plate.py` -> zero matches: the script predates the fix, was
only ever edited in place, and was never regenerated under the new guidance.
Nothing in `script_lint.py` / `quality_gate.py` fails a script for *lacking* the
guard, so an old hand-rolled knuckle passes with the same center-vs-tangent bug
latent. Needs the retrofit lint in [C5 fixes did not take](#c5-fixes-did-not-take-2026-09-08).

### C5 knuckle pivot ping-pong

The llm totally did not get that making the knuckle stand of the cradle's
feet more does not mean that the plate's knuckle has to move upward (+Z).
Probable cause: in the authoring pose the inference is correct, but when the
cradle is moved into its assembled pose it's not.

Investigated (transcript: session `b6ac548d...`, `session-export-1786538430013.zip`):
the triggering request was "align the hole with the bore hole on the front plate
*when the leg lies flat on the front plate*" -- a folded/mounted-pose constraint --
but `cradle.py` and `plate.py` both hardcode `PIVOT_Y`/`PIVOT_Z` as independent
literals in the shared car frame (no `joints`/`mate_chain.py` root-derived pose).
Raising the cradle's own `EAR_STANDOFF` (intra-part, its own resting/authoring
pose) got mirrored into also raising the plate's `PIVOT_Z` (a separate, stationary
part whose bore is fixed by its own physical stack) -- treating a shared invariant
as something to copy-edit in lockstep, which is why PIVOT_Z ping-ponged between
13.5 and 6.0 across rounds 6/8/9. Two contributing causes, not mutually exclusive:
(1) hand-duplicated shared pivot constants across sibling part scripts instead of
going through `joints`/`mate_chain.py`, so nothing forced the second file's copy to
be *derived* rather than independently re-typed; (2) a conceived resting plane at
Z=0 (the authoring-pose XY plane) stood in for where the cradle's fold actually
bottoms out -- in reality the lower stop is below that plane and not flat (console
floor / hardware clearance), an external constraint neither script models, so
"the deployed pose sits flat on Z=0" was itself an unverified assumption feeding
the Z-stack-up math on both sides.
-> Ask clarifying question when parameters have the same value if they are the same or different measures. should they mate or not. e. g. 3 holes have the individually stated diameter of 5 mm. ask " should all holes have the same diameter (one parameters) or may they differ? Or a user asks for a rectangular feature and specifies both dimensions with the same value. ask if it should be constraint to quadratic or not.

**Re-investigated 2026-09-07** (same transcript, tool-call level). Three findings
sharpen the above; the first is the actual defect, the last is what is still
unfixed.

*The ping-pong is a within-round regression, not just a cross-round wobble.*
Round 9 authored three mutually incompatible geometries in a single session:
(9a, `Edit` at transcript line 128/133) keep `PIVOT_Z = 6.0` and add a
Y-direction neck `STANDOFF_Y = PIVOT_Y  # 5.0`; (9b, line 164/167) revert that
and restore a Z riser `EAR_STANDOFF`, moving `cradle.py`'s `PIVOT_Z` back to
13.5; (9c, line 179) hand-edit `plate.py`'s `PIVOT_Z` from 6.0 to 13.5 "to
match". Step 9c silently undid round 8's *user-requested* correction ("move the
hinge knuckles on the plate down to where they were, aprox 8mm from the lower
end") -- the round-8 rationale comment was deleted in the same edit. The final
message to the user states it plainly: "plate.py PIVOT_Z moved to 13.5 to match,
since it's the same shared pin -- I updated both files."

*The user's round-9 wording was relative; it was applied as absolute.* "they
need to extend up when viewed from west. 3mm (plate thickness) + 2 mm because
the bore hole sits 2 mm behind the plate" constrains the *standoff* (a 5 mm
offset derived from the plate's own stack). It was converted into a move of the
shared axle's absolute Z in the car frame, which is what dragged `plate.py`
along.

*The sanctioned mechanism existed and was never reached.* The strings `joints`,
`root_part`, `kinematics`, and `pin_hinge` appear **zero** times in the entire
session transcript, for a model whose two parts are joined by a real revolute
filament-pin hinge. `prompts/planning.md` rule 7 (cross-part matched pair ->
`joints` entry) and rule 9 (a folding leaf closing onto its plate ->
`kinematics` with `stop_on_contact: true`) both cover this case exactly, and
`blocks.joints.pin_hinge` carries `emits: [leaf_a, leaf_b]` plus a revolute
`dof` -- so `mate_chain.py` would have *derived* the plate's pose from the
cradle's, and the second `PIVOT_Z` literal would not exist. Nothing forced it:
rules 7 and 9 are prose only, and `plan_validate.py` can validate a `joints`
entry but cannot notice one is *missing*.

Cause (1) is now covered on the orchestrator side: the parameter-scope routing
rule added with typed `request_log` entries (`skill/phase3_build.md`,
`openspec/specs/request-log/`) forbids hand-editing a shared literal into a
sibling part and names this failure. What is still uncovered is the carrier that
made the hand-edit look necessary -- the duplicated literal itself, which is
established at *plan* time and is invisible to every gate: the plan declares the
same physical bore as an `interfaces[]` entry on both parts, `plan_validate.py`
explicitly permits the same interface `name` on two parts ("the part id
disambiguates them"), and `feature_presence_check.py` asserts each part's
`position_mm` only against *its own* authored frame, so two independently-typed
copies of one bore both pass. Fix (implemented,
`openspec/changes/archive/2026-09-07-shared-interface-derivation/`): a plan-time advisory finding
(`plan_validate.check_shared_interfaces`, printed after `BUILD_PLAN OK`, not a
hard error) when one interface `name` appears on two parts that no `joints` entry
links.

Still open: the folded-pose constraint itself. "when the leg
lies flat on the front plate" is a coincidence assertion (two bores coaxial) at
a pose that is not any part's authoring pose. `kinematic_check.py` sweeps for
interference and range, not for feature coincidence at a pose, so the assertion
was discharged by hand rotation math in prose -- which visibly failed inside the
transcript ("that requires sin(theta) = 2, which is impossible") and then got
re-derived differently each round. Cheapest future home for it: an assertion on
an existing `kinematics` entry evaluated at its `stop_on_contact` pose, reusing
`kinematic_check.iter_poses`. Deferred -- it depends on the plan carrying a
`kinematics` entry at all, which is what the advisory nudges toward.

**Re-confirmed 2026-09-08** (`debug/session-2026-09-08.md`). `check_shared_interfaces`
was merged Sep 7 (commit 814e329). It keys on **one `interfaces[].name` held by two
parts that no `joints` entry links**. The C5 plan:

    plate  interfaces = [None, None]      # interfaces[].name is null on every entry
    cradle interfaces = [None, None]
    joints = None   root_part = None   kinematics = None

so the check has no non-null name to match on and finds nothing. The Sep 8 re-run
then raised `cradle.py` `PIVOT_Z` 13.5 -> 14.5 (`EAR_STANDOFF` 5 -> 6) and left
`plate.py` at 13.5 per the user's explicit "don't touch plate!" -- producing two
non-coaxial bores for one physical pin, with no gate objection. This is the exact
class 814e329 was written to stop; it just cannot see an *unnamed* duplicated
literal. Needs the broadened check in
[C5 fixes did not take](#c5-fixes-did-not-take-2026-09-08). (Note: the "don't touch
plate" instruction is itself correct -- the plate bore is fixed by the plate's own
physical stack. The right resolution is a `joints` entry so the plate pose is
*derived*, making the second literal impossible, not a hand-mirror.)

**Eval coverage added** (`openspec/changes/expand-eval-corpus-hard-cases/`):
`evals/cases/hinged-latch` (joints+kinematics+shared pivot, guards the knuckle
pivot-ping-pong class), `evals/cases/lid-thickness-correction` (seeded round-2
correction), and `evals/cases/east-side-mount` (compass-wording conflation)
now give the scorecard a signal for this failure class. The product fixes
below (`coordinate_frame`, hand-rolled-hinge lint, broadened
`check_shared_interfaces`, `/retrofit`) are still unimplemented.

### C5 fixes did not take (2026-09-08)

`debug/session-2026-09-08.md` re-ran the C5 Phone-Holder skill (a small design
change: east-side fillet + raise the knuckle bore). All three C5 defects above
reproduced despite each having a merged fix. **One root cause:** every fix is
*prospective* -- it takes effect only when a part is re-planned or re-authored
under the new guidance. C5 is a long-lived plan edited incrementally since July;
its `BUILD_PLAN.json` and both part scripts predate all three fixes, and nothing
in `plan_validate.py` / `script_lint.py` / `quality_gate.py` fails a project for
*missing* the new guard. Evidence per fix is in each section above.

**Items 1-3 landed 2026-09-11** (`openspec/changes/archive/2026-09-11-absence-lints-and-coordinate-frame/`).
Item 4 (`/retrofit`) is still open.

Proposed retrofit work (all advisory, `check_block_thinness` tier -- printed after
`BUILD_PLAN OK`, never a hard `plan_invalid`):

1. **Per-project compass binding.** Add `coordinate_frame` to `build_plan_schema.json`
   (`{east,north,up}` each one of `+x/-x/+y/-y/+z/-z`, default = the
   `prompts/planning.md` standard binding). Write it at the Phase 1 exit
   checkpoint when the user's frame differs. `plan_validate` warns when compass
   terms appear in `intent`/`planning_notes`/`request_log` and no
   `coordinate_frame` is recorded. Checkpoint-prose and review steps read it.
   Prose/review only -- does not touch `placement.rotate` sign conventions.

2. **Hand-rolled-hinge lint.** In `script_lint.py` (or a `quality_gate` stage):
   when the plan describes a revolute/pin hinge (or two parts hold a round
   interface at the same world position) and a part script builds a cylinder
   union without `verify_seated` / `verify_backed` / `pin_hinge`, emit a warning
   naming `cq_verify.verify_seated` and the `blocks.joints.pin_hinge` route.
   Makes the opt-in guard's *absence* visible on a pre-existing script.

3. **Unnamed shared-literal detection.** Broaden `plan_validate.check_shared_interfaces`:
   also flag when two parts declare round interfaces of the same `diameter_mm` at
   the same world position (after `placement`) with no linking `joints` entry,
   even when `name` is null. Plus: warn when a multi-part plan whose
   `intent`/`request_log` describes a hinge/pivot/fold has `joints: null`.

4. **Retrofit prompt.** A `/retrofit` (or Phase 0 sub-step) that, on an existing
   project, runs 1-3, reports what the current plan/scripts lack, and offers to
   add the missing `coordinate_frame` / `joints` entry / `verify_*` calls before
   any correction round proceeds. Cheaper than re-planning from scratch and stops
   the "fix merged, still broke" loop for every project already in flight.

### C5 quality-gate overhang authored frame

`quality_gate._analyze_stl` ran `mesh_io.overhang_metrics` on the STL as written
by `write_assembly.py` -- the part's authored / `placement` frame -- and never
applied the chosen print orientation's rotation. `print_orientation.py` (run
earlier in Phase 3) evaluates overhang at the real print pose; the gate did not.
So whenever the optimizer rotates a part away from its authored pose, the gate's
`overhang_exceeded` warning describes a face that is bed-supported (or a vertical
wall) in the pose that actually prints. Logged in `MEMORY.md`
(`skill_gap_quality_gate_overhang_authored_frame`) since 2026-07-20, re-confirmed
six times, including both parts on the 2026-09-08 C5 re-run (plate: "Worst
overhang 90.0 deg over 466.1 mm2" on the cap underside that becomes a wall in the
cover-face-down print pose).

**FIXED 2026-09-08.** `_analyze_stl(stl_path, overhang_deg, rotate=None)` now
takes the orientation's `rotate` steps; `run_gate` threads
`(orientation or {}).get("rotate")` into it; the mesh is posed via
`placement.to_matrix({"rotate": rotate})` before `overhang_metrics`. Tests:
`tests/test_quality_gate.py::test_authored_frame_overhang_cleared_by_print_orientation`,
`::test_run_gate_threads_orientation_rotate_into_overhang`. Behaviour note:
`worst_location_xyz_mm` in the overhang issue is now reported in the build frame,
not the authored frame. The cradle's real overhang (elevated leg/ear undersides,
identity print orientation) is unaffected and still reported.

### Silica Tray support claim

LLM claims "no support needed" despite "support score 654.1" which might be
wrong. Test result: small overhangs like this can be printed without support.

**Root cause found and FIXED 2026-09-15.** `quality_gate._emit_print_recipe`'s
`recipe["supports"]` was hardcoded `False`, unconditionally, regardless of
`orientation["support_score"]` (a weighted overhang-area cost from
`print_orientation.py`, not a support/no-support verdict) or of any
`overhang_exceeded` finding the gate had just emitted for the same STL. So the
delivered `print_recipe` always told the LLM "no support needed" even when the
gate had flagged an overhang moments earlier -- there was nothing to "get
wrong" downstream; the field simply never read the analysis. `support_score`
itself is left as a ranking signal only (used by `print_orientation.py` to pick
the least-overhang pose among candidates) and is not a support/no-support
threshold on its own -- a small nonzero score, as here, can still print clean,
matching the session's test result. Fix: `run_gate` now computes
`needs_support = any(overhang_exceeded warning in all_issues)` and threads it
into `_emit_print_recipe`; an `overhang_exceeded` downgraded to `info` by a
declared `clearance_opening` (see [Hitstertower oversupport](#hitstertower-oversupport))
does not set it. Tests:
`tests/test_quality_gate.py::test_print_recipe_supports_true_when_overhang_exceeded`,
`::test_print_recipe_supports_false_when_self_supporting`,
`::test_print_recipe_supports_false_when_overhang_downgraded_to_info`.

### Silica Tray re-export coincidence

"I just re-derived the print orientation and re-exported so the deliverables
and BUILD_PLAN.json match your hand-edited dimensions: 6mm triangle pitch,
1mm rib width, 20mm total height." Works, but is it by design or just
coincidence?

**Investigated and FIXED 2026-09-15.** Traced the deterministic pipeline
`skill/phase3_build.md` documents: Design approval -> Print-orientation
optimization -> Model export -> Quality gate -> Phase 4 deliver. Every step is
written as a linear, once-per-session sequence with no cross-reference for what
happens when a user asks for a change *after* Phase 4 already reported
delivery -- a very ordinary flow (this session, and the C5 sessions above, both
did it). Nothing in `skill/*.md` named that case, so whether the LLM re-ran
orientation/export/gate was pure judgment -- verified as it did here, but
nothing stopped a future session from hand-editing `build/<id>.py` and
reporting "done" against a stale `model.3mf`/STL/`print_recipe`. (The
mechanism that would have silently caught it for a *standalone*
`uv run python build/build.py` re-run -- `build_template.resolve_orientations`
comparing `orientations.json`'s `source_script_hash` stamp against the current
script -- only covers that later, out-of-session path; it says nothing about
what this session itself must do before calling a correction delivered.)
Fix: added a "Post-delivery corrections" section to
`skill/phase3_build.md` after the Quality gate section, naming the rule
explicitly -- a correction after delivery re-opens print-orientation (for the
affected union only), model export, and the quality gate before Phase 4's
delivery report repeats. Prompt-only change; no code to test.

### Hitstertower oversupport

LLM did not get the intent of the opening on the bottom of the tower (finger
can reach in to pull card out). Instead insisted on fully supporting the
south wall. This is not necessary because the load is the mobile phone on
top, which is hardly more than 200g. This weight can be supported by a 1cm
support on both sides of the wall.

**Investigated 2026-09-08 -- transcript not in `debug/`.** The two Hitster
exports on disk are `session-export-1786343198762.zip` (2026-08-10, an OpenSCAD
attempt interrupted right after the failure-mode question -- never reaches
planning) and `session-export-1786431095406.zip` (2026-08-12, the
dovetail-disassembly rebuild). Neither contains a bottom finger-access opening
or a south-wall support argument: the 08-12 rebuild reduced the base to
`plate + raised platform + 4 mortise sockets` (`build/base.py`, no card-exit
cut) and made every wall a plain flat panel, so the opening question never came
up. This item therefore records a takeaway from a session whose transcript
isn't archived -- attach it for a tool-call-level pass like the C5 items.

What can still be said from the design and the current pipeline:

*The opening is functional negative space, and nothing types it.* The HitScan
tower is a card dispenser: the arch-shaped cut at the bottom of one wall is a
hand-access / card-exit port, not a defect. `interfaces[]` only covers positive
mating features; an in-part void that must stay open (hand access, card exit,
vent, cable pass-through) has no typed home, so nothing in the plan tells the
gate "do not close this, do not bridge/support across it." Same shape of gap as
[assembly placeholder / keep-clear](todo-joints.md#blocks-assembly-placeholder) and the
keep-out-zone concept, but for a void inside a single part rather than a
between-parts clearance volume.

*The support verdict is purely geometric.* A wall with a large opening near its
lower edge presents the material spanning above the opening as an unsupported
overhang/bridge, so `mesh_io.support_cost` (weighted by `SUPPORT_EXPONENT`) and
`quality_gate.py`'s `overhang_exceeded` both push toward "add support."
`print_orientation.py` treats strength as orientation-neutral (always 1.0) and
has no load-vs-support trade-off, and the overhang checks carry no notion of
what actually carries the load. So the LLM, with no structured way to assert
"the opening is intentional and the ~200 g phone on top is carried in
compression by the two wall columns flanking it, ~10 mm each side is plenty,"
deferred to the gate's geometric finding and argued for full support.

*The load argument has a home already; the "keep it open" half does not.* The
structural claim (10 mm of column each side is enough for 200 g) is exactly a
`parts[].engineering_rationale` `load_path` entry (`prompts/part.md` block) --
state the assumption, don't add a gate. The missing piece is a way to mark the
opening as a required void so the support/overhang findings bounding it drop to
advisory.

Fix direction (cheapest first):
1. DONE (prompt-only): `prompts/planning.md` rule 5a records a user-described
   access/exit/clearance opening as an `interfaces[]` entry with
   `type: "clearance_opening"` plus a `part_notes` load-path note. No schema
   change (`interfaces[].type` is a free string; `feature_presence_check.py`
   skips unknown types). This alone gives Phase 3 the structured hook it was
   missing when it argued for support.
2. DONE 2026-09-15 (partial): `quality_gate._clearance_opening_zones` maps each
   `clearance_opening` interface's `position_mm` through the part's `placement`
   and the chosen print orientation's `rotate` into the same build frame as
   `overhang_metrics`' `worst_location_xyz_mm`; `_analyze_stl` downgrades an
   `overhang_exceeded` finding to `severity: "info"` when its worst face falls
   within the opening's radius (half-diagonal of `size_mm` + margin), and points
   the hint at the part's `engineering_rationale`/`part_notes` load path instead
   of "add chamfers or redesign". This reads the interface directly rather than
   routing through the keep-out-zone export (below) -- cheaper for the overhang
   check alone, since it only needs one point + radius, not a meshed zone. The
   `support_cost` / `print_orientation.py` half (excluding the zone from the
   orientation optimizer's ranking, not just the gate's report) is still open --
   that one plausibly does want the keep-out-zone route since it needs an actual
   volume to subtract, not just a point check.

### Project regeneration prompt

Export a prompt which allows the human user to re-generate the whole project
from scratch with a new LLM session (improved LLM, new skill, other skill,
etc). The prompt must include the latest changes, user intent, all
user-provided measurements, drawings and all other artifacts.

DONE. `src/regen_prompt.py` (stdlib only) serializes the approved `intent`,
the verbatim `request_log` (with each entry's `level`/`targets`/`images`),
`parameters.py` inlined whole, the `sketches/` file list, the print target,
and the previous parts/joints decomposition labelled reference-only, into
`REGENERATE.md`. Phase 4 step 6 runs it on every delivery, so the file always
reflects the latest corrections (`intent` is rewritten per correction by
Phase 3's intent-rewrite rule). Images cannot be inlined -- the prompt lists
their paths and tells the user to re-attach them.

### Engineering rationale consolidation

The engineering rationale lives only as an `ENGINEERING RATIONALE` comment block in
each part script, so an N-part model spreads it across N files. Nothing reads it:
`plan_validate.py`, `script_lint.py` and `quality_gate.py` have no notion of it, both
authoring paths (raw and archetype template) carry their own copy of the insertion
rule and the load-bearing trigger list, and it is absent from `README.md` /
`REGENERATE.md`, which are rendered from `BUILD_PLAN.json`.

DONE 2026-09-08: the rationale moves to `BUILD_PLAN.json`'s
`parts[].engineering_rationale`, written back in Phase 3 and validated at the
pre-export `plan_validate.py --require-rationale` run. Change:
`openspec/changes/archive/2026-09-08-consolidate-engineering-rationale/`.

### Export plate nesting

Automated 2D plate packing / bed nesting. Distinct from the print-plate item
above (that is about 3MF plate *structure*); this is about *deciding which
part goes on which plate and where*, which today is declared manually in the
plan. Prior art: thereprocase/cad-skill Phase 4 -- rasterize each union's XY
footprint at 0.5mm/px (PIL), precompute 0/90/180/270 rotations, bottom-left-
fill largest-area-first, keep uniform spacing via `scipy.ndimage.binary_dilation`
on the blocked bitmap, build compound plates with OCC (`BRep_Builder` +
`TopoDS_Compound`), export STL+STEP per plate, report bed utilization %.
Inputs we already have: per-union assembled/print-oriented STLs, `plate`
metadata, bed size (would need to come from `profile.json` -- not
currently a field). Decide scope: full nester, or just a utilization report +
overflow warning leaving assignment to the operator/slicer. Interacts with
print-orientation (footprint depends on chosen orientation) and the
plate-clearance check (spacing == the one-layer-height fuse rule).
Reimplement (PolyForm-safe; algorithm only). Additional prior art:
thereprocase/snuggle-demo (https://github.com/thereprocase/snuggle-demo) -- a
standalone "stuffing"/nesting algorithm demo, worth checking against the
bottom-left-fill approach above.
**REJECTED** -- this feature belongs into a slicer.

### cq assembly and massembly

Evaluated 2026-09-22. **REJECTED** for the pipeline's core.

`cadquery-massembly`: its feature is mates -- named coordinate systems snapped
together to derive poses down a chain. That is `mate_chain.compute_mate_poses`
(62 lines): `world(B) = world(A) @ dock_A @ inv(dock_B)`, walked outward from
`root_part`, with `plan_validate._check_joints` guaranteeing a tree first so no
cycle handling is needed. MAssembly's reason to exist is driving animations in
jupyter-cadquery; this pipeline has no viewer, it has trimesh sweeps
(`kinematic_check.py`). Trading 62 owned lines for a dep tied to an unused
viewer stack is a loss.

`cq.Assembly`: three reasons against.
1. Nothing to solve. `constrain()`/`solve()` is a numerical optimizer for
   under-specified constraints; `BUILD_PLAN.json` declares every `dock` and
   `placement` explicitly, so poses are exact composition. An optimizer would put
   a non-deterministic step underneath gates that are currently reproducible
   (`kinematic_check`, `plate_clearance_check`, `keep_out_check`).
2. Covers half the consumers. `placement.py` must yield both a CadQuery transform
   (`apply_cq`) and a numpy 4x4 (`to_matrix`) from one JSON dict, because
   everything downstream of `write_assembly` is trimesh, not OCCT. `to_matrix` stays
   either way. And `apply_cq` deliberately goes straight to
   `BRepBuilderAPI_Transform` on `.wrapped` to dodge the `cq_warehouse.extensions`
   deepcopy patch -- an Assembly `Location` path would re-enter that.
3. Wrong contract. Parts are authored by separate sub-agents into separate scripts
   whose `result` is a `Workplane` or `dict[str, Workplane]`, and each part prints
   separately. `plan_validate.py` already rejects a top-level `assembly` key on
   purpose.

One spin-off worth keeping: `cq.Assembly.save("x.step")` writes a
multi-component STEP with per-component names and colors. STEP is currently
per-part (`exporters/step.py`); there is no assembled STEP for CAD handoff. If
wanted, that is a standalone ~15-line exporter in `write_assembly.py` -- build a
throwaway `cq.Assembly`, `.add(wp, loc=Location(matrix), name=part_id)` using the
poses already computed, save. No constraints, no solver, no schema change. Add it
when someone actually asks to open the model in FreeCAD/Fusion.

### Bill of non-printed materials

Implemented via `openspec/changes/bill-of-non-printed-materials` (archived
once merged): a hand-authored top-level `bom` array (`item`, `spec`, `qty`,
`parts`, `note`), an `inventory.json` `supplied_hardware` marker on
hardware-consuming blocks driving an advisory validate finding, a Phase 2
summary table, and a Phase 4 "Hardware to buy" section. `planning_notes`
category (c) now holds the assembly procedure only.

### Mirrored parts dedup

Plan states that parts are pairwise mirrored. LLM generated two files:
"wall_a vs wall_b: You're right -- I over-built. wall_b.py is geometrically
identical to wall_a.py (same width, same tenon, same dovetail parameters,
both symmetric). I copied it into a separate file out of habit
(BUILD_PLAN.json lists 5 distinct part ids), but a symmetric flat panel
mirrored is the same printed part -- nothing to design twice. I should
delete wall_b.py and just have the export use wall_a's STL for both
positions (printed twice). Want me to do that now? It also means correcting
BUILD_PLAN.json so wall_b references wall_a's geometry instead of carrying
its own script."

### Intent-based prompt reformulation

DONE -- same artifact as the re-generation prompt above ([Project regeneration
prompt](#project-regeneration-prompt)) and as
`documentation/intent_recognition.md` item 4
([Canonical intent restatement](related_projects.md#canonical-intent-restatement)), which shipped
as `REQUIREMENTS.md` (`skill/phase1_requirements.md`, `openspec/changes/
capture-requirements-spec/`). No separate reformulation prompt needed --
resolved by that same artifact.

DONE. The reformulation itself is `BUILD_PLAN.json`'s `intent`: written and
approved at the Phase 1 exit checkpoint, copied verbatim by Phase 2, rewritten
in place whenever a Phase 3 correction changes the design, and used as the
request-conformance bar in review. Delivered by
`openspec/changes/approved-intent-reformulation/`; the export half is the
regeneration prompt above.

### Siebtragerhalter session (2026-11-04)


Project `D:\3D Druck\Siebträgerhalter` (IMS 58 mm basket drawer tower, 1 part,
session `bf64528b`). Figures below come from the deduplicated transcripts (main + 6
sub-agents), priced at one flat rate so the shares are comparable. Absolute dollars
depend on the real Opus 5.5 / Sonnet 5.5 rates, which are not in `model_prices.json`.

**a) Cost.** `build/cost.json` says $45.83. That number is wrong in ways that
partly cancel:

- `session_cost.parse_transcript` sums `usage` on every `type: assistant` line. One
  API call is written as several lines (one per content block) that repeat the same
  `message.id` and `usage`, so the main transcript's 96 calls were counted 159 times.
- Sub-agent turns live in `<session>/subagents/agent-*.jsonl`, not as `isSidechain`
  lines in the main transcript, so `main_vs_subagent.subagent` is 0 and about 57% of
  the session is missing.
- `claude-opus-5-5` and `claude-sonnet-5-5` are not in `model_prices.json`, so both
  fall back to `default` ($15 in / $15 out). The Sonnet builder is priced like Opus.
- `attempts.jsonl` / `--model` record `claude-sonnet-5` (from `part_author_model()`),
  but the builder actually ran `claude-sonnet-5-5`.

Fix: dedupe by `message.id`, also read `subagents/*.jsonl` (they are the sub-agent
side), add the 5.5 model ids to `model_prices.json`, and warn when a model falls back
to `default`. Add a test with a split-content transcript and a subagents dir.

Where the tokens went (flat-rate shares of the corrected total). 97% of input-side
tokens are cache reads, so cost is roughly calls x context size:

| Segment | Share | Note |
|---|---|---|
| Phase 0 + 1 (sourcing + research agents, main turns) | 26% | research agent: 40 calls for 7 basket dimensions |
| Work discarded by the re-plan (first plan, 62.5 mm resolve, first stub) | 22% | |
| The re-plan itself | 9% | planner resumed at ~150k context |
| New stub + 3 build stages + first audit | 18% | |
| "Raise bumps to 0.8" (one param change) | 12% | 6 hand-written Python plan edits in main, builder re-run, full Opus re-audit |
| "Drop the rounding" + export + delivery | 6% | |
| Cost/energy questions after a 4 h break | 5% | cache expired, 196k context re-created for one `cat` |

Across all segments, the main session alone is 43% (96 calls; context 84k at the
first call, 198k at the end, avg 142k).

The re-plan therefore accounts for about 30% (discarded work + redo). That is real,
but it came from a user design change at the first preview, not a pipeline fault.
The structural causes:

1. Main-session baseline: `/cq-design:init` and `/cq-design` ran in one session, and
   the system prompt carries every MCP tool and skill, so the first call was already
   84k. Main is a relay: 15 separate `log.py journal append` Bash calls, 13 `wrap_up`,
   10 `update_plan`, 7 `SendMessage`. Each one re-reads the whole context.
   Fix: fold the journal append into the script that completes the milestone
   (`plan.py validate`, `print_orientation.py`, `build.py`, ...) or batch it with the
   checkpoint's other call. Recommend a fresh session after init.
2. Sub-agent baseline: every spawn is `general-purpose` with the full tool list
   (browser, docs, Artifact, terminal, visualize, ...) = 61k tokens before it reads
   its prompt. Fix: ship plugin agent definitions (`agents/*.md`) with a minimal
   `tools:` list (builder/auditor/planner: Bash, Read, Write, Edit; research and
   sourcing also get web tools).
3. Model choice: sourcing, research, planner and both audits ran on the inherited
   Opus. Only the builder was spawned with `model: sonnet`. Fix: set `model:` per
   agent definition (Sonnet for sourcing, research and audit, Opus for the planner).
4. Small plan edits go through main-session Python heredocs that dump the plan
   (10k-char tool results). Fix: a `plan.py set <part>.<block>.params.h=0.8` command
   that validates and prints only the diff, and a lighter re-check for a pure param
   change (re-run probes and gate, skip the visual audit).
5. Late concept check: the dish-rack vs drawer-tower mismatch surfaced only at the
   profile stub, after planning and builder spin-up. A Phase 1 concept sketch (one
   cheap blocky render of the reformulation) would catch it before Phase 2.

**b) `parameters.py` is not imported.** That is by contract, not an accident:
`skill/phase1_requirements.md` (At approval) prescribes the docstring "Sourced
real-world measurements this design is based on (not imported by the build)", and
Phase 2 only amends it. The planner then writes literal numbers into
`BUILD_PLAN.json`: groove 71 (= `BASKET_RIM_OD_MM` 70 + 1), rail 4.25, cup cutout
62.5 (= ridge 60.5 + 2), level pitch 33.5 (= `BASKET_HEIGHT_MAX_MM` 28.5 + 5 gap).
Part scripts read `part.param(...)` from the plan, so Phase 0/1 results reach the
model only as a one-time manual copy. Changing `parameters.py` after a test print
does nothing, and nothing checks that the plan numbers still match the sources.

Possible fixes, in order of effort:
- Plan params may reference `parameters.py` names as expressions
  (`"w": "BASKET_RIM_OD_MM + 2*GROOVE_CLEARANCE_MM"`). `plan.py validate` evaluates
  them against the module's constants (names + arithmetic only, unknown names
  rejected), and `Part.param` returns the evaluated value. Design allowances
  (clearance, gap, wall) also go into `parameters.py`, marked `# design choice`, so
  each derivation is visible.
- Cheaper: a `source` expression per param (`"source": "BASKET_RIM_OD_MM + 1"`) that
  `plan.py validate` recomputes and flags on mismatch. Literals stay, drift is caught.
- Either way `export_standalone.py` already copies `parameters.py`, so the standalone
  bundle would then really be parametric on the sourced values.

**c) Cross-sections show nothing.** `preview/storage_shelf_preview_section_z_72mm.png`
is a uniform 110 x 100 blue rectangle. The real z = 72 cut is an 81 x 80 U with the
channel open. Causes:
- `preview._shade_triangles` is flat Lambert shading only. `render_section` views
  the kept half straight down the cut normal, so the cap, the base-plate top (z = 4)
  and the channel floor all have normal +z and get the same colour. With no edge
  lines or depth cue they merge into one silhouette: the base plate's footprint.
- Cut choice: `render_prompt.section_cuts` proposed `z=2` (through the base plate),
  `z=72.75` (cup_cutout centre along its `top` wall normal, which lands between rail
  levels 69.75 and 103.25) and `x=33.4`. The builder ignored the rendered command and
  passed its own `--extra-section z=72`. `section_select` found no bores or bosses,
  so `--auto-sections` added nothing. The informative cut for this part is `y=0`
  (the U profile with all 8 rail notches): across the slot run, not along the wall
  normal.
- Both audits passed with this image as evidence. Nothing flags a blank section.

Fixes: draw the section cap in a distinct colour with an outline (cap = triangles
lying on the cut plane) and add depth shading or edge lines to the section render;
for `slot` / `clearance_opening` interfaces pick the axis perpendicular to the
feature's long direction; have `render_section` report "uninformative" when the cap
silhouette equals the uncut silhouette (no hole, no notch), so the auditor knows the
image carries nothing; make the builder use the prompt's command verbatim (it may add
cuts, not replace them).

**d) Labels where the features cannot be seen.** `render_multi_view` puts callouts
"on the three orthographic panels only (not isometric)" by design. In this part:
- The orthographic panels have the same flat shading and no edge lines. The South
  view (looking into the open front) is one dark silhouette, the top view one light
  rectangle. Rails, channel and bumps are not visible in any of them.
- Callout anchors are projected without a visibility test, so badges point at hidden
  interior features. All 4 `rim_rails` levels and the 8 `front_bump`s project onto
  2-4 points in the top view, so badges pile up (3/4/5/6, 11/13, 12/14).
- The isometric panel is the only one where rails and the open front read, and it
  has no labels.
This is the same root issue as the open defect "every feature which is named in
prose has to be shown and named in preview".

Fixes: draw feature/silhouette edges in every panel (projected B-rep edges, or
depth-discontinuity lines from the z-buffer `zbuffer.rasterize` already builds); per
callout pick the panel where its anchor is visible (z-buffer depth test at the
projected point, with tolerance), allowing the isometric panel; if no panel shows it,
mark it "hidden" in the legend and render a `--detail` view for it; merge badges that
project within a few pixels of each other ("rim_rails x4").
