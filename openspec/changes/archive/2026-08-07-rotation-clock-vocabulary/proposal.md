## Why

The skill has no shared vocabulary for describing partial revolutions (hinge sweeps, dial
positions, screw-pattern layout) between the LLM and the user. `placement.rotate` and
`dof.direction` already have a fixed, tested sign convention (right-hand rule), but nothing
maps that to words a human can read at a checkpoint. A naive fix -- "clockwise, looking down
the axis" -- was checked against this project's own shipped preview cameras
(`Viewed from South/West/above`) and found to invert on the Z axis relative to X/Y: the
"above" panel places the camera beyond the +Z tip looking back at the origin, while "South"
and "West" place it at the tail looking outward, so right-hand-rule-positive reads
counterclockwise on one and clockwise on the other two. A bare clockwise/counterclockwise
rule would therefore be wrong exactly on the axis (vertical) most partial-revolution features
use, unless paired with an explicit axis-to-view rule.

## What Changes

- Extend the `feature-vocabulary` capability with a rotation-description convention: a
  partial revolution is described as a target clock position (`12`, `3`, `90°`, etc.) read
  off a **named compass viewing station whose sight-line is the rotation axis** (above <-> Z,
  South <-> Y, West <-> X) -- never a bare "clockwise"/"counterclockwise" word, which has no
  single correct sign across axes.
- `skill/phase2_planning.md` and `skill/phase3_build.md` state this rule wherever checkpoint
  prose describes a rotation, hinge sweep, dial, or angularly-positioned feature.
- Prose-only: no `BUILD_PLAN.json` schema field, no change to `placement.py`'s rotation math
  or the joint-contract `dof` sign convention. This is strictly a human/LLM communication
  convention layered on top of the existing, unchanged right-hand-rule geometry.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `feature-vocabulary`: adds a requirement for describing partial revolutions and rotation
  direction in user-facing prose, alongside the existing compass-direction requirement.

## Impact

- `openspec/specs/feature-vocabulary/spec.md` (delta)
- `skill/phase2_planning.md`, `skill/phase3_build.md` -- checkpoint prose guidance
- No changes to `src/`, `BUILD_PLAN.json`'s schema, or any geometry/kinematics code
