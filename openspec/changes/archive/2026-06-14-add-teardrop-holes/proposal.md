## Why

Horizontal bores (holes whose axis lies in the build plane) print badly with a plain circular profile: the top of the circle is an unsupported overhang that sags, droops, or needs supports inside the hole. The FDM guidelines already advise "consider teardrop shape" for horizontal holes, but there is no block to produce one, so every model re-derives the geometry by hand. A reusable teardrop (drop-shaped) bore makes the recommended pattern a one-call primitive.

## What Changes

- Add a new subtractive block `teardrop_bore`: a horizontal through-bore whose lower portion is a circular profile and whose upper half is replaced by a `^` peak (two flat faces meeting at an apex, roof-of-a-house shape) so every internal face stays at or below the 45-degree overhang limit and the bore self-supports without internal supports.
- The peak angle defaults to 45 degrees from horizontal (the printable overhang limit); the profile is extruded along the bore axis and overcut by `_EPS` like the other subtractive blocks so it cuts clean through a wall.
- Register the block in `blocks/inventory.json` with a descriptor and export it from the `blocks` package.
- Document the block in the FDM reference as the concrete realization of the existing "horizontal holes -> teardrop" guidance.

## Capabilities

### New Capabilities
- `teardrop-bore`: a subtractive block producing a self-supporting drop-shaped horizontal bore (lower circular profile + upper `^` peak), with parametric diameter, depth, and peak angle, intended for `.cut()` against a wall so horizontal holes print without internal supports.

### Modified Capabilities
- `block-library`: the minimum-inventory requirement and the subtractive-blocks epsilon requirement are extended to include `teardrop_bore`.

## Impact

- Code: new function in `src/blocks/` (connectors module), new entry in `src/blocks/inventory.json`, new re-export in `src/blocks/__init__.py`.
- Tests: new geometry test asserting the bore is watertight, that the upper profile is a peak rather than an arc, and that overhang faces stay within the 45-degree limit.
- Docs: `reference/FDM 3D Print Design Guidelines.md` gains a pointer to the block.
- No breaking changes; purely additive. Interface type reuses the existing `axis` vocabulary entry, so the closed interface-type set is unchanged.
