## ADDED Requirements

### Requirement: Plan parts may be declared copies of another part

`src/build_plan_schema.json` SHALL accept an optional `copy_of` object on a part with required
`part` (a part id string) and optional `mirror` (one of `"X"`, `"Y"`, `"Z"`). No other keys
SHALL be accepted. Plans without `copy_of` SHALL validate unchanged.

#### Scenario: Mirrored copy validates
- **WHEN** part `wall_b` has `copy_of: {"part": "wall_a", "mirror": "X"}` and `wall_a` exists
- **THEN** `plan.py validate` reports no error

#### Scenario: Bad mirror axis rejected
- **WHEN** a `copy_of` has `mirror: "W"`
- **THEN** `plan.py validate` reports a schema error

### Requirement: copy_of references are validated

`plan.py validate` SHALL report a hard error when `copy_of.part` names a missing part, the part
itself, a part that is itself a copy, or a part that declares `unions`.

#### Scenario: Missing source
- **WHEN** `copy_of.part` is `ghost` and no such part exists
- **THEN** validate reports an error naming `ghost`

#### Scenario: Chained copy
- **WHEN** `c` is a copy of `b` and `b` is a copy of `a`
- **THEN** validate reports an error on `c`

### Requirement: Copies are exported from the source geometry

`model_export.export_model` SHALL NOT load a script for a copy part. It SHALL take the source
part's authored geometry, reflect it across the plane normal to `mirror` when present, apply the
copy's own placement (or mate-chain pose), and emit the copy as its own union, STL, and 3MF object.

#### Scenario: Mirrored copy bounding box
- **WHEN** `wall_a` spans x in [0, 10] and `wall_b` is `copy_of wall_a` with `mirror: "X"` and no placement
- **THEN** `wall_b.stl` spans x in [-10, 0] and no `wall_b.py` is read

#### Scenario: Identical copy with placement
- **WHEN** `wall_b` is `copy_of wall_a` with no `mirror` and `placement.translate_mm: [20, 0, 0]`
- **THEN** `wall_b.stl` equals `wall_a.stl` translated by 20 mm in x

### Requirement: Part loop does not author copies

The Phase 3 part loop, `quality_gate.py` per-script checks, and the freshness manifest SHALL skip
script authoring/lint for a copy part; a copy's manifest entry SHALL be keyed to the source
script's hash.

#### Scenario: Source edited after export
- **WHEN** `wall_a.py` changes after export
- **THEN** the freshness check reports both `wall_a` and `wall_b` stale
