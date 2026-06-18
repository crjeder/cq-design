## Why

The building-block library has primitives and fasteners but no joint primitives. Designing a box with a sliding dovetail lid currently requires writing the joint geometry inline, as a monolithic model. Extracting the dovetail joint as two reusable blocks (`dovetail_groove` and `dovetail_tongue`) lets the assembly layer compose the joint from standard parts, consistent with how snap hooks, alignment pins, and hollow boxes are already composed.

## What Changes

- **New file** `blocks/joints.py` with two functions: `dovetail_groove` and `dovetail_tongue`
- **New entries** in `blocks/inventory.json` for both functions
- No changes to existing blocks, schema, or tooling

## Capabilities

### New Capabilities

- `dovetail-joint`: A matched pair of sliding dovetail geometry primitives — a groove to subtract from a body and a tongue to use as a sliding lid panel. The tongue fits flush (adds exactly `depth` to height). Parameters: `width`, `depth`, `length`, `angle`, `clearance`.

### Modified Capabilities

## Impact

- `blocks/joints.py` (new)
- `blocks/inventory.json` (two entries added)
- Consumers: any assembly script that builds a box-with-sliding-lid using the building-block approach
