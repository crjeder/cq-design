## Why

The kinematic sweep asks one question -- *"is the entire declared range collision-free?"* --
and answers it with a measurement that does not survive contact. Both halves are wrong for
the most common kind of folding assembly, and the C5 Phone-Holder demonstrates each against
real, shipped, physically-verified geometry.

**The semantics are wrong for a joint whose closed position is a contact stop.** The
phone-holder cradle folds up until it rests against the plate's front face. That contact *is*
the design -- the user said so explicitly in the plan's `request_log`: "the fold has a natural
mechanical stop wherever the swept cradle first contacts the plate front face, not a forced
90deg angle." Sweeping the shipped STLs about the shipped pivot (car frame Y=5, Z=6) shows
first contact at **-53.5 deg**, and past that the two bodies interpenetrate in earnest:

| fold angle | intersection volume |
|---|---|
| -53 deg | 0 (0.13 mm gap) |
| -54 deg | 0.09 mm³ |
| -60 deg | 28.6 mm³ |
| -90 deg | 5557 mm³ |

Those overlaps are geometrically real, and completely irrelevant: the physical part stops at
-53.5 deg and never reaches them. **The printed part folds cleanly.** But a plan declaring the
natural `required_range: [-90, 0]` gets a `motion_collision` error citing a 5.5 cm³ overlap,
because the check evaluates poses the mechanism cannot occupy. A hinge whose closed position
is a contact stop can never pass a range-based pass/fail check -- and that describes most
folding designs. This is the actual mechanism behind "it saw collisions where none existed":
not a numeric error, a framing error. The useful report was never a boolean; it was *"reaches
-53.5 deg of the requested -90 deg, stopping against `plate`."*

**The measurement is wrong too.** `interference.colliding_names` thresholds fcl's per-contact
`depth` at `penetration_tol_mm` (default 0.1), intending to tolerate designed surface contact.
fcl's mesh-mesh contact depth does not support that: across the same sweep it reports a flat
**7.2 mm** at -54 deg, where the true overlap is 0.09 mm³ -- 72x the tolerance for a sliver --
and it is not even monotonic in the real overlap, reporting 39.9 mm at -80 deg (1337 mm³) but
30.0 mm at -90 deg (5557 mm³). Depth per intersecting triangle pair is ill-conditioned for the
large near-coplanar triangles that flat faces tessellate into. No value of
`penetration_tol_mm` fixes this, because the number it filters carries no reliable relation to
penetration. Any designed sliding or resting contact -- a print-in-place joint, a lid on a lip,
a hinge at its stop -- is at risk of a false `motion_collision` today.

Notably, the ad-hoc sweeps the phone-holder session hand-wrote each round used **boolean
intersection volume** and produced trustworthy relative numbers ("Z=15 still binds by 0.14
mm³"). The measure that worked by hand is the one the pipeline does not use.

Together these are `TODO.md`'s "kinematics for custom (block-free) hinges" part (b) --
promoting the ad-hoc sweep into a first-class tool that reports binding angle, colliding body,
and clearance. This change is that tool. Part (a) has already shipped (archived change
`blockless-kinematics`): `block` is optional, so a custom hinge can now *declare* the entry
that reaches this sweep. That makes part (b) the remaining blocker -- a phone-holder-style
plan can finally be written, and would immediately hit the pass/fail framing described above.

## What Changes

**Penetration measured by intersection volume.**

- Add `manifold3d` as a project dependency and use it as the boolean engine for interference
  measurement. No fallback path: a single measure keeps findings comparable across runs, and a
  silently-degraded second measure with different sensitivity is worse than a clear failure.
- Change `src/interference.py` so fcl is used only as the broadphase ("do these touch at
  all?"). On a hit, compute the boolean intersection of the two meshes and threshold its
  **volume** against a `penetration_tol_mm3` budget, replacing the `penetration_tol_mm`
  depth threshold. Keep `penetration_tol_mm3=None` meaning "any contact counts" for the
  keep-out caller, whose any-contact semantics are correct and unaffected.
- **BREAKING** (internal): `colliding_names` / `check_interference` take a volume tolerance
  instead of a depth tolerance; `kinematic_check.py`'s `--penetration-tol` CLI flag changes
  units. Both are internal tool boundaries with no plan-schema surface.
- Report the measured overlap volume on the finding, so a `motion_collision` says how badly it
  binds instead of only where.

**Contact-limited sweep semantics.**

- Add an optional `stop_on_contact` boolean to a `kinematics` entry (default `false`, so every
  existing plan keeps today's pass/fail behaviour). When set, the sweep does not fail at first
  real interference; it **stops** there and reports the achieved range.
- For a contact-limited entry, emit an informational/advisory finding carrying
  `achieved_range`, the union it stopped against, and the minimum clearance observed over the
  travelled arc -- e.g. "reaches -53.5 deg of the requested -90 deg, stopping against `plate`".
  Falling short of `required_range` is a `warning`, not an `error`: the designer decides
  whether the achieved stop is acceptable, exactly as the phone-holder user did.
- Refine the reported stop angle by bisection between the last clear step and the first
  binding step, so the answer does not depend on `step` granularity. This is the manual
  binary search the phone-holder session ran by hand, made part of the tool.
- Report `achieved_range` on **every** sweep, contact-limited or not. Even a hard-fail
  `motion_collision` becomes more actionable when it states how far the joint got.

Deliberately **not** in scope: a declared separating/stop *plane* (see below); minimum-cutout
search (the "how tall must the notch be" question -- a search loop over geometry edits, a
distinct capability worth its own change); and any change to keep-out or plate-clearance
semantics beyond the shared tolerance-parameter rename.

**On the separating-plane idea.** The explore session considered letting the author declare a
plane splitting free space from populated space (here, the plate's front face) as a cheap
exact test. It is deferred, for a reason worth recording: on this very model it fails as a
global certificate, because the cradle's hinge knuckle legitimately lives *behind* the plate's
front-face plane, between the ears and through the notch. Its real value is narrower and more
interesting -- the plate face is not merely a separator, it is the **physical stop surface** --
which is the semantics `stop_on_contact` captures directly from geometry, with nothing for the
author to declare or get wrong. A declared stop plane may still earn its place later as an
optimisation or as a way to name the expected stop; it should not be the correctness
mechanism.

## Capabilities

### New Capabilities

None. Both halves modify existing capabilities.

### Modified Capabilities

- `interference-primitive`: penetration is measured as boolean intersection volume via
  `manifold3d`, with fcl demoted to broadphase; the tolerance parameter becomes a volume
  budget. Requires a stated dependency on the boolean engine (no graceful degradation to a
  second measure).
- `kinematic-range-validation`: adds `stop_on_contact` to the plan entry; adds the
  achieved-range report (with bisection refinement and minimum-clearance reporting) as a
  first-class output of every sweep; a contact-limited joint that falls short of its required
  range is a `warning`, not an `error`.

## Impact

- `pyproject.toml` / `uv.lock` -- add `manifold3d`. Verified importable and correct against the
  phone-holder STLs during exploration; `trimesh.boolean.intersection(..., engine="manifold")`
  produced the volume table above.
- `src/interference.py` -- `colliding_names` / `check_interference`: fcl broadphase then
  volume measurement; tolerance parameter renamed and re-unitised.
- `src/kinematic_check.py` -- `_sweep_collision` returns achieved range + minimum clearance +
  overlap volume; bisection refinement; `stop_on_contact` branch; `--penetration-tol` unit
  change (its `--help` text still says "penetration depth (mm)"). This lands on top of the
  already-shipped `blockless-kinematics` and `build-artifact-freshness` work: the entry loop
  now also resolves `mechanical_limit` from the entry, emits `range_check_not_applicable`, and
  filters `stale_artifact` unions out of the sweep. None of that changes, but the new
  achieved-range reporting must compose with it -- in particular a `stale_artifact` entry is
  skipped before the sweep, so it produces no achieved-range finding.
- `src/keep_out_check.py` -- call-site update only; any-contact semantics preserved. It and
  `kinematic_check.py` are the *only* two callers of the primitive (`plate_clearance_check.py`
  measures minimum surface distance and does not go through `interference.py`), so the
  tolerance re-unitisation has a blast radius of exactly two call sites.
- `src/build_plan_schema.json` -- `stop_on_contact` on `kinematics_entry`.
- `tests/test_interference.py`, `tests/test_kinematic_check.py` (both already exist) --
  flush-contact-is-not-binding must become a regression test; the phone-holder fold is the
  natural fixture (a known-good assembly that today's check fails and the fixed check must
  report as stopping at -53.5 deg). A synthetic two-box tangency fixture covers the same
  property without shipping 300KB of STL, and is the better default.
- `skill/phase3_build.md`, `prompts/planning.md` -- when to declare `stop_on_contact`, and how
  to read an achieved-range finding.
- `CLAUDE.md` -- `interference.py` and `kinematic_check.py` rows.
- `TODO.md` -- mark part (b) of the "kinematics for custom (block-free) hinges" sub-item done;
  note the minimum-cutout search as still open. Part (a) is already marked done there.
- Sequencing: no dependency left. Part (a) shipped, so this change completes the sub-item and
  the two together are what would have let the phone-holder session answer its fold question
  with a tool instead of seven hand-written sweeps.
