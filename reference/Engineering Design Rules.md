# Engineering Design Rules

Numeric-only reference for the ENGINEERING RATIONALE block (see `prompts/part.md`).
Each `##` section is tagged `<!-- applies_to: ... -->`, same convention as
`FDM 3D Print Design Guidelines.md`: inject a section only if its tag is `always`
or lists a block in the part's `blocks_needed`, plus any load-relevant section when
the part declares a plan `load`. Tables and formulas only, no prose tutorials.

## Material Constants
<!-- applies_to: always -->

| Material | Allowable strain (snap-fit, %) | Flexural modulus (GPa) | Notes |
|---|---|---|---|
| PLA | 2.0 | 3.5 | stiff, brittle — lowest strain allowable |
| PETG | 4.0 | 2.1 | most common general-purpose choice |
| ABS | 3.0 | 2.3 | more ductile than PLA, less than PETG |
| TPU (95A) | 20.0 | 0.05 | flexible; not comparable to the others for stiffness checks |

Use the allowable strain as the right-hand side of a snap-fit check unless the plan
states a different material.

## Snap-Fit Strain Formula
<!-- applies_to: snap_hook_clip, snap_socket_receiver -->

For a cantilever snap arm of rectangular cross-section:

```
strain (%) = 1.5 * t * d / L^2 * 100
```

- `t` = arm thickness (mm, in the direction of deflection)
- `d` = deflection at full engagement (mm)
- `L` = arm length from root to tip (mm)

Pass when `strain <= allowable strain` for the declared material (see Material
Constants). Retention barb depth is not part of this check — see the FDM guide's
Snap-fit Design section for barb/thickness ranges.

## Rib / Boss / Gusset Ratios
<!-- applies_to: screw_boss, pcb_standoff, heat_set_boss, fillet_box, hollow_box -->

| Feature | Ratio | Limit |
|---|---|---|
| Rib thickness : adjoining wall thickness | rib / wall | <= 0.6 (thicker sinks the outer face) |
| Boss outer diameter : screw diameter | boss_OD / screw_d | >= 2.5 |
| Gusset thickness : wall thickness | gusset / wall | <= 0.75 |
| Boss wall thickness (boss_OD - hole_d) / 2 | boss wall | >= wall_min (no thinner than the part's own minimum wall) |

## Insert / Clearance Deltas
<!-- applies_to: screw_boss, pcb_standoff, heat_set_boss -->

Deltas not already in `hardware_dims.md`:

| Condition | Delta |
|---|---|
| Heat-set insert hole, PETG vs. PLA table value | +0.1 mm |
| Self-tapping pilot hole vs. screw major diameter | screw_d - 0.3 mm |
| Press-fit pin vs. socket (loose) | +0.2 mm clearance |
| Press-fit pin vs. socket (firm) | +0.05 mm clearance |

## Flush-Fold Hinge Standoff
<!-- applies_to: pin_hinge, living_hinge -->

Scope: a hinged (clevis/tongue) part that must close to an exact +-90deg fold and
land flush (coplanar) against a target plane. Does not apply to fold angles other
than 90deg, or to joints with no flush-close requirement.

```
standoff = perpendicular_distance(axis, target_plane)
```

`standoff` is the perpendicular distance from the pivot axis to the plane of the
folding face (in its flat, unfolded rest pose) - i.e. how far the clevis/tongue
knuckle sits proud of the face it's attached to. Rotation about the axis preserves
every point's distance to the axis; for the folded face to coincide with the
target plane (not just touch it at an angle), its own axis-standoff must equal the
axis's standoff from the target plane. Get either distance wrong and the fold
either overshoots past flush or stops short of it.

Worked example (C5 Phone-Holder cradle/plate hinge): target plane is the plate's
front face; axis is 5mm behind it. The folding leg's top face must therefore sit
5mm proud of the pivot axis (`PIVOT_Y = 5.0` standing off the leg's own attachment
plane) for the fold to close exactly flush at 90deg.
