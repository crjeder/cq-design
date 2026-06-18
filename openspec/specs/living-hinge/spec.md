# Spec: living-hinge

## Purpose

Continuous FLEXURE hinge for FDM: a one-piece thin web that elastically bends, with no
pin and no moving parts. This is distinct from the `filament-hinge` mechanical pivot
(which threads a separate filament pin through rigid knuckles). Provides a `living_hinge`
CadQuery workplane factory that joins two panels with a single paper-thin web that bends
repeatedly, with a documented print orientation and material caveat.

## Requirements

### Requirement: Living hinge joins two panels with a thin continuous web
The system SHALL provide a `living_hinge` function in `blocks.joints` that returns a
`cq.Workplane` of two rectangular panels, each of width `panel_w` (X) and thickness
`panel_t`, bridged by a single continuous web of thickness `web_t` over width `web_w`
running the full `length` (Y, the fold axis). Its signature SHALL be
`living_hinge(length, panel_w, panel_t, web_t=0.6, web_w=2.0)`. The web SHALL be flush
with one panel face so the panels fold away from the web side.

#### Scenario: Web is thinner than the panels
- **WHEN** `living_hinge(length=40, panel_w=20, panel_t=3, web_t=0.6, web_w=2.0)` is generated
- **THEN** the result SHALL be one watertight body whose bridging web thickness (0.6 mm)
  is less than the panel thickness (3 mm) and spans the full length

### Requirement: Living hinge use string states orientation and material caveat
The `living_hinge` inventory `use` string SHALL state the required print orientation
(printed flat with the fold axis in the build plane and the web continuous along the
axis so filament paths cross the bend) and the material caveat that flexible/semi-rigid
materials (PP, PETG, TPU) survive repeated folding while PLA is brittle.

#### Scenario: Use string documents orientation and material
- **WHEN** the `living_hinge` inventory entry is read
- **THEN** its `use` string SHALL name both the print orientation and the material caveat

### Requirement: Living hinge is classified as a permanent flexure hinge
The `living_hinge` inventory entry SHALL declare `motion: hinge`, `reversible: false`
(one continuous piece that cannot separate non-destructively), and a single
`hinge_axis` interface oriented `+Y`.

#### Scenario: Inventory taxonomy for the living hinge
- **WHEN** the `living_hinge` entry is read
- **THEN** its `motion` SHALL be `hinge`, its `reversible` SHALL be `false`, and it SHALL
  declare a `hinge_axis` interface
