# Spec: finger-joint

## Purpose

Parametric finger (box/comb) joint block. Provides a `finger_joint` CadQuery workplane factory whose two complementary halves interlock to form an edge joint.

## Requirements

### Requirement: Finger joint produces an interlocking comb
`finger_joint(width, thickness, fingers, length, clearance=0.1, start_high=True)` SHALL
return a `cq.Workplane` of `fingers` evenly spaced rectangular fingers spanning `width`
in X, each of height `thickness` in Z and depth `length` in the mate (Y) direction.
`start_high` SHALL select which alternating set of finger positions is solid, so that
two calls with opposite `start_high` interlock.

#### Scenario: Complementary combs are disjoint and tile the full width
- **WHEN** `finger_joint(width=24, thickness=3, fingers=6, length=10, start_high=True)`
  and the same call with `start_high=False` are generated
- **THEN** their solids SHALL occupy disjoint X bands
- **AND** the union of both SHALL span the full `width` of 24 mm (minus clearance gaps)

#### Scenario: Clearance shrinks each finger per side
- **WHEN** a finger joint is generated with `clearance=0.1`
- **THEN** each finger's X width SHALL be reduced by `2*0.1` from its nominal pitch slot

#### Scenario: Finger count and dimensions hold
- **WHEN** `finger_joint(width=24, thickness=3, fingers=6, length=10)` is generated
- **THEN** the bounding box height SHALL equal 3 mm and depth SHALL equal 10 mm
