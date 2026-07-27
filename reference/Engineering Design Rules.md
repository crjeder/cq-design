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
