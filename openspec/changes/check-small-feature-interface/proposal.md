## Why

A feature joined to its support through a tiny footprint snaps off, even when every wall around it is thick. In the Silica-tray, the old version stacked posts directly on the grid. Each post touched the grid through about three patches of 0.2 x 1 mm (about 0.6 mm^2), and the posts broke off. The fix was a cylinder from the post down to the build plate, which gives a 3 mm diameter circle (about 7 mm^2) at the joint.

The existing thin-interface check does not see this. It measures wall thickness on the STL, so a thick post resting on a sliver of contact reads as thick everywhere. The interfaces are already known when the part is built: each placed block is unioned onto the body so far, so the join between the two is exactly what needs measuring. No mesh is needed.

## What Changes

- In `Part.place` (`src/blocks/part.py`), every `union` step measures the interface between the placed tool and the body so far, as exact B-rep area (contact face area when they touch, boundary area inside the other body when they overlap).
- A union whose interface area is below `interface_min_area_mm2` fails the step with a typed `small_interface` error carrying the area, the two instance ids, the location, and a remedy hint. The area is recorded on every union step in the step report.
- Add `interface_min_area_mm2` to the printer profile and plan constraints (default 4.0).
- Tell the planner and builder prompts to give a stacked feature a footprint at or above the minimum, for example a column down to the build plate.

## Capabilities

### New Capabilities
- `small-interface-detection`: B-rep interface area between a placed block and the body, the `small_interface` step error, and the per-step report entry.

### Modified Capabilities
- `printer-profile-config`: new `interface_min_area_mm2` constraint with a default and schema entry.

## Impact

- Code: `src/blocks/part.py`, new `src/interface_area.py`, `src/printer_profile_schema.json`, `src/build_plan_schema.json`, `src/profile.default.json`.
- Docs and prompts: `reference/scripts.md`, `prompts/planning.md`, `skill/phase3_build.md`, `FILES.md` (new file).
- Tests: new `tests/test_interface_area.py`, plus `tests/test_printer_profile_validate.py`.
- Step report contract: union steps gain an `interface` entry. No existing key is renamed or removed.
- Not covered: legacy scripts that do not use `Part` (they have no step list), and the STL-level checks, which are unchanged.
- No new dependencies.
