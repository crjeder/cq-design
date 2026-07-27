## Why

A `kinematics` entry today must name an inventory `block` that carries a `dof`, and
`plan_validate.py`'s `_check_kinematics` (`src/plan_validate.py:255-295`) enforces the joint
contract against that block: the type must match `dof.type`, and the block's local
`dof.direction`/`dof.origin`, pushed through the moving union's `placement`, must be parallel
to (and for revolute, coaxial with) the declared `axis_dir`/`axis_origin_mm`. That contract
is sound for a joint actually built from a parametric block. It is unsatisfiable for a joint
built from raw CadQuery primitives, which is what a custom hinge normally is.

The C5 Phone-Holder project is the worked example. Its clevis/tongue hinge is hand-built
boxes and cylinders -- no `pin_hinge`, no `hinge_leaf`, no block at all. Its
`planning_notes` records the consequence in the plan itself: the `kinematics` entry was
**deliberately omitted**, because declaring one "would force a bogus block reference" and
"forcing that contract for a block whose geometry we don't actually call would require adding
a placement rotation that would misalign our already car-frame-authored geometry." So the one
model in the corpus with a genuinely interesting range-of-motion question ran with the
kinematic stage switched off.

What replaced it was seven rounds of hand-written, throwaway boolean fold sweeps -- and they
were not reliable. Rounds 4 through 7 each rebuilt a sweep from scratch (0.25 deg steps, plus
a manual binary search for the minimum notch height). In the final round the ad-hoc sweep
reported that the requested pivot position would jam "roughly 2-3mm deep into the solid 3mm
front cap for about 19 deg of the fold arc" and demanded the plate's notch grow from 17mm to
35mm, after an earlier pass had claimed 55mm. The user overrode both, kept the 17mm notch,
and **the printed part folds cleanly**. Reproducing the sweep against the shipped STLs shows
why the ad-hoc numbers were untrustworthy in detail, but the structural point stands on its
own: an ad-hoc sweep re-derived per round, in the main session, under token pressure, is the
worst place for this computation to live. It is exactly the kind of deterministic geometric
question `kinematic_check.py` exists to answer -- and the only thing keeping it out was a
schema contract written for a case this design isn't.

Tracked in `TODO.md` under the C5 Phone-Holder retrospective, "kinematics for custom
(block-free) hinges", part (a). Part (b) of that TODO item -- promoting the ad-hoc sweep into
a first-class reporting tool -- is the sibling `contact-limited-sweep` change; this change is
what makes the plan able to *declare* such a joint in the first place.

## What Changes

- Make `block` **optional** on a `kinematics` entry in `src/build_plan_schema.json`. An entry
  that omits it is a *block-less* (directly-declared) joint: `axis_origin_mm`, `axis_dir`,
  `type`, `required_range`, and `step` fully specify the motion, with no inventory backing.
  Entries that name a block are unchanged in every respect.
- Add an optional `mechanical_limit` field to a `kinematics` entry, so a block-less joint can
  still declare a nominal bound for the numeric check. Absent, the numeric check is simply
  skipped for that entry (there is nothing to compare against) and only the sweep runs.
  **Not** a silent pass: the emitted result records that the numeric arm did not apply.
- In `plan_validate.py`, skip the joint-contract arms (type match, axis parallelism, revolute
  coaxiality) for a block-less entry -- there is no block to contract against -- while keeping
  every check that does not depend on one: `moving_union` resolves to a real union id,
  `axis_dir` is a valid axis, `required_range` is well-formed, and the entry is validated at
  every `children` nesting depth exactly as today.
- In `kinematic_check.py`, source `mechanical_limit` from the entry when there is no block,
  and run the collision sweep for block-less entries identically to block-backed ones. The
  sweep already needs nothing from the block: it consumes only `axis_origin_mm`, `axis_dir`,
  `type`, `required_range`, and `step` (`src/kinematic_check.py:94-129`).
- Teach the planner (`prompts/planning.md`, `skill/phase2_planning.md`) that a custom joint
  built from raw primitives **declares its axis directly** rather than omitting `kinematics`.
  The phone-holder plan's own `planning_notes` is the anti-pattern to cite: omitting the entry
  because no block fits is the failure this change removes.

Deliberately **not** in scope: relaxing the contract for entries that *do* name a block (that
contract is load-bearing and catches real misalignment), and inferring an axis from geometry
(the axis stays author-declared, as the current spec requires).

## Capabilities

### New Capabilities

None. This widens an existing capability rather than introducing one.

### Modified Capabilities

- `kinematic-range-validation`: `block` becomes optional on a `kinematics` entry; a block-less
  entry declares its axis directly and carries an optional `mechanical_limit` of its own. The
  requirement "Required range is checked against the block mechanical limit" gains the
  block-less arm (entry-supplied limit, or numeric check not applicable); the sweep
  requirement is unchanged in behaviour but must state that it applies to block-less entries
  too.
- `joint-classification`: the joint contract (type/axis/origin agreement between a plan entry
  and a block's `dof`) applies only when the entry names a block. Needs a requirement stating
  that a block-less entry is out of the contract's scope by construction, so the absence of a
  contract check is specified behaviour rather than a gap.

## Impact

- `src/build_plan_schema.json` -- `kinematics_entry`: drop `block` from `required`, add
  optional `mechanical_limit`.
- `src/plan_validate.py` -- `_check_kinematics`: branch on presence of `block`; keep the
  union-id and axis-shape checks for every entry.
- `src/kinematic_check.py` -- `run_kinematic_check`: resolve the mechanical limit from block
  `dof` or entry field, tolerate its absence, sweep either way.
- `prompts/planning.md`, `skill/phase2_planning.md`, `skill/phase3_build.md` -- guidance that
  a custom/raw-primitive joint declares its axis directly instead of skipping `kinematics`.
- `tests/test_plan_validate.py` -- block-less entry validates; a block-backed entry still gets
  the full contract; a block-less entry with a bad `moving_union` still fails.
- `CLAUDE.md` -- `plan_validate.py` / `kinematic_check.py` row wording (the "referenced block
  exists, carries a `dof`" clause is now conditional).
- `TODO.md` -- mark part (a) of the "kinematics for custom (block-free) hinges" sub-item.
- No new dependency. No change to block-backed plans: every existing plan and eval case
  validates and sweeps exactly as before.
