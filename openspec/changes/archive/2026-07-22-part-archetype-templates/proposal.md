# Part Archetype Templates

## Why

Most from-scratch parts are variations of roughly a dozen shapes (enclosure body, lid, bracket, adapter ring, plate, hook, clip, stand), yet every one is currently authored as raw fluent CadQuery from a blank file, guarded only by a large reference dump and a 3-attempt retry loop. This is the root cause of both reported failure modes: clumsy OCC-fragile code gets re-invented per part, and topology is only confirmed after a full CadQuery run. A library of known-good, pre-verified parametric template scripts turns authoring into "match archetype, copy, edit parameters, modify deltas" - inheriting correct topology and safe idioms instead of regenerating them.

## What Changes

- New `templates/` directory of known-good, parametric, pre-verified CadQuery part scripts, one per archetype (initial set: enclosure body; sliding, snap, and screwed lids; flanged adapter ring; L-bracket with gusset; flat plate with boss pattern; hook; clip; stand). Each has a documented top-level parameter block and `cq_verify` guards already placed.
- New `templates/archetypes.json` machine-readable index (name, use description, parameter list, template file), schema-validated like `blocks/inventory.json`.
- Part loop gains a "Step 1.5 - match archetype" step in `skill/phase3_build.md`: before authoring, match the part spec against the index; on a match, copy the template and edit parameters/deltas; raw-fluent authoring from a blank file becomes the explicit fallback.
- `prompts/planning.md` gains a rule: the planner records a matched archetype per part (or none) in the plan, so the part loop's match step starts from the planner's judgment.
- Template scripts pass the existing pipeline as-is: `script_lint.py` clean and `run_cadquery_model.py` geometry-valid, enforced by a new test file.

## Capabilities

### New Capabilities

- `archetype-library`: the `templates/` script library, the `archetypes.json` index and its validation, the pre-verification bar every template must meet, and the part-loop archetype-matching step with its fallback to raw authoring.

### Modified Capabilities

- `planning-phase`: the planning prompt additionally records an optional per-part archetype reference (validated against the archetype index) that the part loop consumes.

## Impact

- New: `templates/*.py`, `templates/archetypes.json`, `templates/archetypes_schema.json`, `tests/test_templates.py`.
- Modified: `skill/phase3_build.md` (Step 1.5), `prompts/planning.md` (archetype rule), `src/build_plan_schema.json` (optional per-part `archetype` field), `src/plan_validate.py` (cross-check against the index).
- No changes to the wrapper JSON contract, blocks, or exporters. Acceptance is measured by the eval harness (first-shot pass rate on archetype-covered requests vs. the raw-authoring baseline).
