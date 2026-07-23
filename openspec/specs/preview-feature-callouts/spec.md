# Spec: preview-feature-callouts

## Purpose

Defines the deterministic feature-callout overlay on the multi-view preview tile:
numbered badges with leader lines projected from declared interface positions, and the
legend that maps badge numbers to plan names.

## Requirements

### Requirement: Preview tile supports deterministic feature callouts

`render_preview.py` SHALL accept a repeated `--callout "name=<n>;center=x,y,z"` flag
(authored-frame center, same spec conventions as `--detail`). For each callout, the
multi-view tile's three orthographic panels SHALL draw a numbered badge with a leader
line to the feature's projected 2D position, computed by projecting the 3D center
through the panel's own camera (no vision or heuristic placement). Badge numbers SHALL
follow the order the callouts were supplied. The isometric panel SHALL NOT carry
badges. `run_cadquery_model.py` SHALL forward callout specs to the renderer exactly as
it forwards `--extra-section`. A malformed callout spec SHALL be rejected with a
diagnostic naming the spec, as malformed `--detail` specs are.

#### Scenario: Callout badges appear at projected positions

- **WHEN** `render_preview.py` is invoked with `--views multi` and two `--callout`
  specs whose centers lie inside the part's bounding box
- **THEN** the tile's three orthographic panels each contain badges 1 and 2 with
  leader lines, and the isometric panel contains none

#### Scenario: No callouts renders the unchanged tile

- **WHEN** `render_preview.py` runs without any `--callout` flag
- **THEN** the tile is rendered with no badges and no legend row beyond the existing
  caption

#### Scenario: Malformed callout spec is a diagnostic error

- **WHEN** a `--callout` spec is missing its `center=` field
- **THEN** `render_preview.py` exits non-zero with a message naming the offending spec

### Requirement: Callout legend maps badges to plan names

When at least one callout is supplied, the tile SHALL include a legend row in the
caption area mapping each badge number to its feature name (e.g. `1 handle
2 cable_slot`). The skill SHALL thread one callout per part interface that declares
both `name` and `position_mm`, in plan order; interfaces declaring a `name` but no
`position_mm` SHALL still be listed in the legend, unbadged and marked as not located,
so the tile carries the part's complete agreed vocabulary.

#### Scenario: Legend lists badged and unlocated names

- **WHEN** a part declares three named interfaces, two with `position_mm` and one
  without
- **THEN** the legend shows badges 1 and 2 with their names and lists the third name
  marked as not located, without a badge

#### Scenario: Names in legend match the plan verbatim

- **WHEN** the legend is rendered from callouts threaded from `BUILD_PLAN.json`
- **THEN** every legend name is byte-identical to the corresponding
  `interfaces[].name` value
