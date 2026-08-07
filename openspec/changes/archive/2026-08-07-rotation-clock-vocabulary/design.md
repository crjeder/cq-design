## Context

`placement.py`'s rotation math and OCCT's `gp_Ax1` both use the right-hand rule (RHR):
positive `angle_deg` rotates around a `direction` vector by RHR, full stop. The archived
`joint-contract` design deliberately dropped a stored "12 o'clock" reference vector for
`dof` -- zero comes from the authored pose, sign from `direction` + RHR (see
`openspec/changes/archive/2026-07-01-joint-contract/design.md`, "dof vector model (D4)").
That decision stands; this change does not touch it.

What's missing is a way to talk about a partial revolution in a checkpoint message without
either party knowing the authored frame or the RHR sign convention by heart. The obvious fix
-- "N degrees clockwise, looking down the axis" -- was checked against this project's own
shipped preview cameras (`preview.py`'s `MULTI_VIEW_PANELS`: South, West, above) by
projecting +X/+Y/+Z through each panel's actual camera matrix (not eyeballed):

| Panel   | Rotation axis (sight-line) | RHR-positive reads as |
|---------|-----------------------------|------------------------|
| above   | Z                           | counterclockwise       |
| South   | Y                           | clockwise              |
| West    | X                           | clockwise               |

The "above" panel places the camera beyond the +Z tip, looking back at the origin (plan-view
convention). "South" and "West" place the camera at the axis's tail, looking outward
(elevation-view convention). Same RHR, opposite screen handedness, because the viewer sits on
opposite sides of the axis. A single global "clockwise = positive" rule is therefore right for
X and Y and backwards for Z -- and Z is the axis most hinges, dials, and lids actually use.

## Goals / Non-Goals

**Goals:**
- Give the skill a way to state a target rotation position in checkpoint prose that a human
  can read unambiguously, without needing to know the authored frame or RHR.
- Avoid the axis-dependent sign trap above.
- Reuse the already-shipped, fixture-verified compass viewing stations rather than inventing
  a second, competing set of viewpoint names.

**Non-Goals:**
- No new `BUILD_PLAN.json` field. This is prose only, produced and consumed by the LLM and
  the user at checkpoints; it never round-trips through the schema.
- No change to `placement.py`, OCCT rotation calls, or the joint-contract `dof` sign
  convention. RHR stays the sole geometric source of truth.
- No general-purpose bearing/compass angle system for translation (that already exists
  implicitly via `placement.rotate`); this covers only how a *rotation feature* is described
  to a human.

## Decisions

**Decision: describe a target clock position, never a CW/CCW direction word.**
"Into the 90° position" (read off a named panel) needs no direction word at all, so it can't
inherit the axis-dependent CW/CCW sign trap. "Rotate 90° clockwise" would need a per-axis sign
table to stay correct, and that table is exactly the kind of thing that gets silently dropped
or mis-copied over time. Dropping the direction word instead of maintaining the table is the
smaller, more robust surface.

**Decision: the named view's sight-line must equal the rotation axis.**
A clock reading is only meaningful when the axis is perpendicular to the panel (so the sweep
traces a circle, not a foreshortened ellipse or line). This pairs each axis with exactly one
of the three shipped panels: Z <-> above, Y <-> South, X <-> West. The rule is stated
explicitly rather than left to be inferred, since picking an arbitrary named view (e.g. the
retired "front view" term) for an axis that isn't that view's sight-line produces a clock face
that doesn't correspond to anything drawn on screen.

**Decision: reuse South/West/above; do not introduce "front/side/top" or new names.**
Those compass names were chosen and fixture-verified in the `shared-feature-vocabulary`
change specifically to kill the ambiguous Front/Left/Top terms. Reintroducing "front view"
here would undo that fix's reasoning inside a different requirement.

**Alternative considered: state CW/CCW plus a per-axis conversion table.**
Rejected as the primary mechanism -- it keeps the ambiguous words in prose and relies on
whoever writes checkpoint text (the LLM, mid-conversation) correctly recalling a three-row
table with one inverted row. Clock-position phrasing removes the failure mode instead of
documenting around it. The table itself is still worth keeping in this design doc for anyone
who must explain *why* a given delta looks the way it does, but it should not appear in
checkpoint prose.

## Risks / Trade-offs

- **Sweep direction (not just endpoint) still needs disambiguation for full/near-full
  revolutions.** "12 o'clock to 9 o'clock" is ambiguous between a 270° and a 90° arc when
  nothing else constrains it. Mitigation: for the mechanisms this skill actually models
  (hinges, dials with `dof.limit`), the physical range bounds the arc, so the ambiguity is a
  net-new gap that only matters for a full unconstrained revolution -- not addressed by this
  change; falls out of scope per the proposal's Impact section, revisit if a real case needs
  it.
- **Three-panel coverage assumes the rotation axis is one of X/Y/Z.** An oblique hinge axis
  has no panel whose sight-line matches it exactly. Mitigation: none in this change -- prose
  guidance can note that an oblique axis falls back to naming start/end features directly
  ("from flush with `object a` to flush with `object b`") rather than a clock position.

## Open Questions

None -- scope is prose-only guidance in two skill-phase docs and one spec delta.
