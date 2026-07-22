# Planning Phase (delta)

## ADDED Requirements

### Requirement: Plan records an optional per-part archetype

The `BUILD_PLAN.json` schema SHALL define an optional per-part `archetype` field (string). `prompts/planning.md` SHALL instruct the planner to set it to the name of the matching entry in `templates/archetypes.json` when a part fits an archetype's `use` description, and to omit the field otherwise; the archetype index SHALL be made available to the planning prompt for this purpose. `plan_validate.py` SHALL cross-check every present `archetype` value against the names in `templates/archetypes.json`, reporting an unknown name as a validation error, exactly as `blocks_needed` is checked against the block inventory. Plans without any `archetype` fields SHALL remain valid.

#### Scenario: Planner records a matching archetype

- **WHEN** the planner produces a plan containing a part that fits the enclosure-body archetype
- **THEN** that part entry carries `archetype: "enclosure-body"` and the plan passes validation

#### Scenario: Unknown archetype name is rejected

- **WHEN** a plan declares `archetype: "no-such-shape"` on a part
- **THEN** `plan_validate.py` reports a validation error naming the part and the unknown archetype

#### Scenario: Plans without archetypes stay valid

- **WHEN** a plan (including any pre-existing plan) declares no `archetype` field on any part
- **THEN** validation passes unchanged
