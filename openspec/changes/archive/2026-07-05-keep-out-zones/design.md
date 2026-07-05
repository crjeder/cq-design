## Context

The archived `joint-contract` design capture (`openspec/changes/archive/2026-07-01-joint-contract/`)
scoped "Slice C -- annotation geometry" as future work independent of the joint blocks: a
printed/pseudo classification for geometry that guides the LLM and is checked but never fabricated.
Row 4 of that classification, `KEEP-OUT ZONE`, is an author-declared no-go volume distinct from the
two block-declared rows (mating area, assembly envelope), which remain out of scope here.

An `/opsx:explore` session worked through how a `keep_out` zone should actually be authored and
checked, landing on three decisions this design formalizes:

1. **Option B** -- a zone is declared inline, as a reserved key in whatever part script the author is
   already writing, rather than in a separate world-level entity.
2. **Named zones** -- zones are a `name -> Workplane` mapping (reusing the existing multi-union
   `result` shape), not one anonymous fused solid, so a violation names *which* zone and *why*.
3. **Self-exclusion** -- a zone is not checked against its own declaring part's other real unions,
   since a zone is typically anchored flush against the very feature it protects.

The existing `union` model (`src/units.py`: `iter_unions`/`resolve_unions`) already treats a part's
`result` as either a single `Workplane` or a `name -> Workplane` mapping. This change extends that
mapping with one reserved key rather than introducing a parallel data path.

## Goals / Non-Goals

**Goals:**
- Let a part's script declare one or more named keep-out zones inline, with no new plan-schema
  field.
- Zones inherit their declaring part's assembled pose (placement or derived mate-chain pose).
- A new whole-model gate stage rejects any union (outside the zone's own declaring part) that
  intrudes on a declared zone, using the existing structured issue contract.
- Zones are invisible to export, plate assignment, and the kinematic sweep.

**Non-Goals:**
- Block-declared mating-area keep-out and assembly-envelope keep-clear (rows 2-3 of the archived
  classification) -- separate, still-unspecified capabilities.
- Any plan-schema field naming or cross-referencing a zone. Zones are discovered from script output,
  not declared in `BUILD_PLAN.json`.
- A severity/priority system for zones (e.g. warning-only zones). Every violation is a hard reject
  for this slice; softer zones can be a later refinement if a real model needs one.
- World-level (not part-anchored) zones authored directly in assembled coordinates (the "Option A"
  alternative from the explore session). Can be revisited if a real model needs a zone with no
  natural owning part.

## Decisions

### Reserved key, not a new plan entity

A part's script `result` may include a `"keep_out"` key whose value is a `name -> Workplane` mapping,
alongside (or instead of) real union keys:

```
result = {
  "enclosure": wp,                              # real union
  "keep_out": {
    "screwdriver_clearance_boss1": wp_zone1,     # zone name IS the note-to-self
    "wire_route_reserve": wp_zone2,
  },
}
```

This reuses the existing multi-union `result` shape (`src/units.py`) instead of inventing a new
value type such as `{"reason": ..., "solid": ...}` -- the codebase already treats a name as doubling
for its description (`model_export` disambiguates duplicate union descriptions by suffixing the
union id). `plan_validate`'s "script keys must match declared `unions`" check is taught to ignore the
`keep_out` key entirely, and `keep_out` becomes a reserved word: no union anywhere in the model may
use it as an `id` (checked alongside the existing duplicate-union-id check).

Alternative considered: a dedicated pseudo-part with its own plan entry, authored directly in
world/assembled coordinates (Option A from the explore session). Rejected as the primary mechanism
because most zones are naturally anchored to a specific part's feature and should move with it; a
world-anchored escape hatch is deferred as a non-goal above rather than built speculatively.

### Zone collection lives next to union collection

`src/units.py` already owns "a part may produce several unions" (`iter_unions`, `resolve_unions`).
This change adds a sibling function, e.g. `iter_keep_out_zones(plan, part_results)`, that:

1. For each part, pulls its `result["keep_out"]` mapping if present.
2. Applies that part's `placement`, or its derived mate-chain pose (from
   `mate_chain.compute_mate_poses`) when the part is reached via a `joints` mate chain -- the exact
   same pose each of that part's real unions already receives.
3. Yields `(part_id, zone_name, posed_solid)` tuples for every declared zone in the model.

Cross-part name collisions (two parts both naming a zone `"clearance"`) are disambiguated for
reporting the same way `model_export` already disambiguates duplicate union descriptions: qualify by
declaring part id when two zone names collide.

### Export, plate, and sweep paths skip `keep_out` explicitly

`model_export.py` and `run_model_shim.py` already iterate a part's resolved unions; both are updated
to recognize and skip the reserved `keep_out` key rather than treating it as an unnamed union (which
would otherwise attempt to export/plate it). The kinematic sweep (`kinematic_check.py`) already
builds its "everything else" fixed set from the union list; since zones are never registered as
unions, they are excluded automatically once the export/resolve path stops surfacing them as such.

### New whole-model check: `keep_out_check.py`

Follows the established pattern of `kinematic_check.py` / `plate_clearance_check.py`: an in-process
trimesh + python-fcl check, run once in `quality_gate.py` outside the fix loop, degrading to a
`check_skipped` warning when the geometry backend is unavailable.

```
for zone (declaring_part, zone_name, zone_mesh) in all zones:
    for union in all unions:
        if union.part_id == declaring_part:
            continue                      # self-exclusion
        if intersects(union.mesh, zone_mesh):
            emit keep_out_violation(union, declaring_part, zone_name)
```

The self-exclusion is scoped to the *declaring part*, not just the specific real union the zone
happens to touch -- mirroring how `kinematic_check` excludes an entire swept subtree rather than one
union, since a part's several real unions (if it has more than one) are all "its own" geometry a
zone is expected to sit against.

Issue shape matches `plate_clearance_check`'s precedent: `source: "geometry"`,
`severity: "error"`, `type: "keep_out_violation"`, `message` naming the offending union and the
`(declaring_part, zone_name)` pair, `hint` pointing at the offending union's geometry (the zone is
never the thing to redesign).

## Risks / Trade-offs

- **[Risk] A zone accidentally shadows a real union id, or vice versa.** → Mitigated by making
  `keep_out` a reserved word checked at the same point as the existing duplicate-union-id check, so
  the conflict is caught at plan-validation time, not at export or check time.
- **[Risk] Self-exclusion is too coarse** (excludes a whole part when only one of its several unions
  is the zone's true anchor, potentially hiding a real clash between two *other* unions of the same
  part). → Accepted for this slice per the explore session's framing (a zone is a note about that
  part's own intent); revisit if a real model surfaces a same-part false negative.
- **[Risk] Performance**: an O(zones x unions) intersection sweep on top of the existing O(unions)
  kinematic sweep. → Same trimesh/fcl tooling and pairwise-check pattern already proven at
  `plate_clearance_check`'s O(pairs) scale; no new dependency, and expected zone/union counts are
  small (single-digit per model).

## Open Questions

- Should a zone ever be allowed to opt into checking against its own declaring part (for a same-part
  false-negative case), e.g. a per-zone flag? Deferred until a real model needs it.
