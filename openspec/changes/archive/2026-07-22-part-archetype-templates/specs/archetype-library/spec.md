# Archetype Library

## ADDED Requirements

### Requirement: Template library of known-good archetype scripts

The system SHALL provide a `templates/` directory containing one complete, runnable CadQuery part script per archetype. Each template SHALL be a standalone script that assigns its final geometry to a top-level `result` variable, declares all dimensions as named top-level parameters, imports blocks only via `from blocks import ...`, and includes `cq_verify` guards on computed-offset booleans and overhanging features. The initial archetype set SHALL cover: enclosure body, sliding lid, snap lid, screwed lid, flanged adapter ring, L-bracket with gusset, flat plate with boss pattern, hook, clip, and stand.

#### Scenario: Template is a valid part script

- **WHEN** any template script from `templates/` is executed through `run_cadquery_model.py` with its default parameters
- **THEN** it succeeds with valid, watertight geometry and an empty `errors` list

#### Scenario: Template passes the pre-flight lint

- **WHEN** `script_lint.py` is run against any template script
- **THEN** it reports `success: true` with zero findings

### Requirement: Machine-readable archetype index

The system SHALL provide `templates/archetypes.json`, an array of archetype descriptors validated against `templates/archetypes_schema.json` (JSON Schema draft-7). Each descriptor SHALL include: `name` (unique, kebab-case), `file` (path of the template script relative to `templates/`), `use` (plain-English description of what the archetype is for and when to match it), and `params` (object mapping parameter name to unit/description). Descriptors MAY include `aliases` (array of matching synonyms). Every descriptor's `file` SHALL exist, and every `.py` file in `templates/` SHALL have exactly one descriptor.

#### Scenario: Index validates against its schema

- **WHEN** `templates/archetypes.json` is loaded and validated against `templates/archetypes_schema.json`
- **THEN** validation passes and every listed `file` resolves to an existing template script

#### Scenario: Orphan template is rejected

- **WHEN** a `.py` file exists in `templates/` with no corresponding index descriptor
- **THEN** the template test suite fails identifying the unlisted file

### Requirement: Part loop matches an archetype before authoring

The Phase 3 part loop documentation (`skill/phase3_build.md`) SHALL define a "Step 1.5 - match archetype" executed before any part script is authored. When the part's plan entry carries an `archetype` value, Step 1.5 SHALL use it after confirming the archetype's `use` description fits the part spec; otherwise Step 1.5 SHALL attempt a match against the index's `use` and `aliases` fields. On a match, the part script SHALL be authored by copying the template and editing its parameter block and deltas, preserving the template's `cq_verify` guards. When no archetype fits, the part loop SHALL fall back to raw authoring and state the reason for the non-match in one line.

#### Scenario: Planned archetype is used

- **WHEN** a part's plan entry declares `archetype: "enclosure-body"` and the part spec is consistent with that archetype's `use` description
- **THEN** the part script is authored by copying `templates/` enclosure-body script and editing parameters and deltas, not from a blank file

#### Scenario: No archetype fits

- **WHEN** a part matches no index entry's `use` or `aliases`
- **THEN** the part loop authors the script raw as today and states in one line why no archetype matched

#### Scenario: Planned archetype contradicts the part spec

- **WHEN** a part's plan entry declares an archetype whose `use` description does not fit the part spec
- **THEN** Step 1.5 discards the planned value, attempts its own match, and falls back to raw authoring if none fits

### Requirement: Templates are enforced pre-verified by tests

The test suite SHALL include a test file that parametrizes over every descriptor in `templates/archetypes.json` and asserts, per template: the script passes `script_lint.py` with zero findings, and executing it with default parameters yields valid watertight geometry with no wrapper errors.

#### Scenario: Broken template fails the suite

- **WHEN** a template is edited such that it produces invalid geometry or a lint finding
- **THEN** the template test suite fails naming that archetype
