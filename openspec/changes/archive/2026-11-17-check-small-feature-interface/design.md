## Context

`measure_stl._thin_regions` finds thin walls by casting rays inward from the STL surface. It cannot see a neck: a post that is 6 mm thick resting on three 0.2 x 1 mm patches reads as thick at every face. Slicing the STL at z-levels was considered and rejected: it samples at arbitrary heights, misses interfaces that are not horizontal (a cone on a cube edge versus a cube face), and guesses at something the build already knows.

The build knows it. `blocks.Part.place` (`src/blocks/part.py`) builds a part one step at a time: each `union` step fuses a placed tool onto the body so far, and probes already run on that exact B-rep (`src/probes.py`: `classify`, `face_distance`). The interface between two features is the join between that tool and that body, available at the moment of the union.

## Goals / Non-Goals

**Goals:**
- Measure the interface area of every union step exactly, in B-rep, in the pose it was authored in.
- Fail the step when the area is below `interface_min_area_mm2`, with a typed error and a remedy hint.
- Catch the touching, sunk-in, and edge-contact cases the same way.

**Non-Goals:**
- Meshes, slicing, or any tessellation-based check. The STL thin-region check is unchanged.
- Legacy scripts that do not use `Part`. They have no step list; `unprobed_interfaces` already marks that gap.
- Load or stress analysis (`fem-stress-advisor`), and contact between separate parts of an assembly.
- Automatic repair. The hint names the remedy; the builder applies it.

## Decisions

**Measure at the union step, per placed copy.** In `Part.place`, for `op == "union"`, measure each entry of `tools` against `before` (the body, or `unions[into]`). A multi-point `at` list becomes several tools, so a bad copy is not hidden by good ones. `cut` and `base` steps are skipped.

**Interface area is a face area, not the intersection volume.** The volume of the intersection is 0 for the usual "placed on a face" case, and for a sunk-in tool it grows with sink depth rather than footprint, so it cannot say how wide the join is. Instead, intersect each face of one shape with the other solid and sum the resulting face areas: `S_b_in` (the body's faces inside the tool) and `S_t_in` (the tool's faces inside the body). The interface is `min(S_b_in, S_t_in)`. A spike on CadQuery showed this handles touching and overlap uniformly: coplanar contact is returned as a face, so no separate touching branch is needed. Measured: cone on a cube face 28.27 (its base), cone sunk 0.1 mm 27.34 (its cross-section at the cube top, not the 30.36 sunk surface), cone centred on a cube edge 14.14 (half the base), cone fully beyond the edge 0, post on three 0.2 x 1 slivers 0.6, post on a 3 mm column 7.07. Only faces whose bounding box overlaps the other shape are tested.

Alternative: `(A_before + A_tool - A_fused) / 2`. Rejected: it counts the tool's sunk surface as interface, so a deeply sunk post looks well joined.

**Failure style follows existing step checks.** `Part._error(step, "small_interface", ...)` fails the step like `probe_failed` does, so the builder sees it in the step report in the same loop and fixes it before the part is built. The error dict follows the existing `{type, message, hint}` shape plus the numeric fields.

**Threshold 4.0 mm^2, a profile constraint.** About a 2.3 mm diameter circle. It sits between the failed 0.6 mm^2 joint and the working 7 mm^2 joint. It is one data point plus judgement, so it is configurable, not a constant.

**Implementation lives in `src/interface_area.py`.** A pure function `interface_area(before, tool) -> (area, centroid)` over cadquery shapes, called from `Part.place`. This keeps `part.py` from growing a geometry routine and lets tests call it directly with plain CadQuery solids.

**The step cache stores the result.** The `interface` entry is part of the step dict that the cache already deep-copies, so cached runs return the same value. The threshold changes `interface_min_area_mm2`, so it is added to the key chain for `place` steps.

**Remedy hint.** Offer a footprint at or above the threshold, for example a column from the feature down to the build plate, naming the instance. No guarantee is claimed.

## Risks / Trade-offs

- [OCC booleans of a face with a solid may return degenerate results on tangent or curved arrangements] -> the spike passed on the named fixtures; a failing boolean on one face is skipped and counted as 0 for that face, and the through-pin and tangent fixtures in the tests guard it.
- [A deliberate small joint, such as a breakaway tab, will fail] -> lower `interface_min_area_mm2` in the plan constraints for that part. A per-instance waiver is not added until a real case needs it.
- [A tool that overlaps several places at once (a through-pin) sums its faces inside the body, which can overestimate the load-bearing section] -> accepted; the error is on the low side, the check does not produce false failures from it.
- [Steps run often under the warm worker] -> the check is a bounded number of booleans on bounding-box-filtered faces, and cached steps skip it.

## Open Questions

- Should a waiver per instance exist from the start? Left out until needed.
- Should the area scale with what the tool carries (a heavy tray needs more than a light post)? The first version uses a fixed area and leaves load to `fem-stress-advisor`.
