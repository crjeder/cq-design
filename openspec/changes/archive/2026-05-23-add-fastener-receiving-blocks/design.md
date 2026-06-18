## Context

The `blocks/fasteners.py` module provides six functions covering self-tapping screw bosses, PCB standoffs, snap-fit clips, and alignment pins/sockets. Heat-set inserts, SHCS counterbores, flat-head countersinks, and captured hex nuts are the next tier of FDM fastener features that LLM-generated model scripts must currently hand-code. All four new blocks follow the existing pattern: pure CadQuery 2.x geometry, no dependencies beyond `cadquery`, function returns a `cq.Workplane`.

## Goals / Non-Goals

**Goals:**
- Add `heat_set_boss`, `counterbore_hole`, `countersink_hole`, `hex_nut_trap` to `blocks/fasteners.py`
- Register all four in `inventory.json` with correct `use`, `params`, `dimensions`, and `interfaces` fields
- Extend the `block-library` interface vocabulary with `nut_trap` and `sliding_interface`
- Add a hardware dimension reference table to `SKILL.md` so the planning LLM can look up correct values

**Non-Goals:**
- Named-size convenience API (`heat_set_boss(metric=3)` style lookup) — blocks stay purely parametric; reference tables live in SKILL.md
- Coupling blocks to `cq_warehouse` fastener objects — no runtime dependency between the two
- Side-slide nut channels — derivable from `hex_nut_trap` + a slot; not worth a dedicated block

## Decisions

### All blocks purely parametric (mm inputs only)

**Decision:** Every function takes raw float dimensions, no named-size lookup tables inside the function.

**Rationale:** The planning LLM reads SKILL.md before writing scripts; it can look up M3 insert OD from a table there. Encoding the table inside the block function would duplicate it and couple the block to a specific brand (CNC Kitchen inserts are standard but not universal). Keeping blocks parametric also means they work for non-metric or custom hardware without modification.

**Alternative considered:** Provide a helper dict `HEAT_SET_DIMS = {"M3": (4.6, 5.7)}` in the module. Rejected — adds lookup logic and brand dependency to what should be pure geometry.

---

### `heat_set_boss` exposes hole diameter directly (no built-in tolerance)

**Decision:** The `d_insert` parameter IS the hole diameter. The caller passes the target hole size (insert OD minus their desired press-fit tolerance).

**Rationale:** Press-fit tolerance varies by material (PLA vs PETG), printer calibration, and insert brand. For CNC Kitchen M3 inserts the recommended hole is 4.4 mm (0.2 mm under OD). Rather than hardcode a tolerance, let the caller specify the hole diameter. SKILL.md documents the typical `-0.2 mm` rule for PLA.

---

### `counterbore_hole` produces a two-cylinder subtraction solid

**Decision:** The returned solid is a union of a shallow wide cylinder (head pocket) and a deeper narrow cylinder (shaft clearance), both centered at origin, extruded in +Z.

**Rationale:** Two `.union()` calls on simple cylinders is the most direct CadQuery expression. The alternative (using `.cskHole()` or `.cboreHole()` workplane methods) operates on an existing face and cannot be stored as a standalone subtraction block.

---

### `hex_nut_trap` uses `.polygon(6, circumscribed_d)` for the hex cross-section

**Decision:** Hex prism via `cq.Workplane("XY").polygon(6, nut_flat / math.cos(math.pi / 6)).extrude(depth)`.

**Rationale:** CadQuery's `.polygon(n, d)` takes the circumscribed circle diameter (vertex-to-vertex). The ISO "across flats" dimension is the inscribed circle diameter. Converting: `d_circumscribed = nut_flat / cos(30°)`. This guarantees the printed flat-to-flat matches the spec. A naive pass of `nut_flat` as the diameter would produce a pocket that is ~15% too small.

---

### `nut_trap` added as a new interface type

**Decision:** Add `nut_trap` to the closed interface vocabulary in `block-library` spec. Also add `sliding_interface` which was introduced by the dovetail change but never registered in the spec.

**Rationale:** `hex_nut_trap` is a receiving socket for hardware — semantically distinct from `socket` (alignment feature) and `screw_hole` (cylindrical hole). A distinct type lets the orchestrator and future tooling identify nut-trap interfaces unambiguously.

## Risks / Trade-offs

- **Hex pocket rotation ambiguity** → In a top-drop trap, nut orientation is irrelevant as long as flat-to-flat is correct. No rotation parameter needed. If a future side-slide variant is added, rotation matters and can be added then.
- **`d_insert` semantics** → Callers who pass nominal insert OD without subtracting tolerance will get a loose fit. Mitigated by SKILL.md documentation and the inventory `use` field explicitly stating "pass hole diameter, not insert OD."
- **`countersink_hole` taper geometry** → CadQuery `.cskHole()` is workplane-bound. Standalone taper requires a truncated cone via `cq.Solid.makeCone(r1, r2, height)` combined with a cylinder. Two primitives unioned, nothing unusual.

## Open Questions

None — all design decisions resolved.
