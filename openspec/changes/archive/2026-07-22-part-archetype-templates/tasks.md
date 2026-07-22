# Tasks: Part Archetype Templates

## 1. Index infrastructure

- [x] 1.1 Create `templates/archetypes_schema.json` (JSON Schema draft-7 for the index: name, file, use, params, optional aliases; unique names)
- [x] 1.2 Create `templates/archetypes.json` with the ten initial descriptors (enclosure-body, lid-sliding, lid-snap, lid-screwed, adapter-ring-flanged, l-bracket-gusset, plate-boss-pattern, hook, clip, stand)

## 2. Template scripts

- [x] 2.1 Write `templates/enclosure_body.py` (hollow box, wall/floor params, optional boss pattern via blocks, cq_verify guards)
- [x] 2.2 Write the three lid templates: `templates/lid_sliding.py`, `templates/lid_snap.py`, `templates/lid_screwed.py`
- [x] 2.3 Write `templates/adapter_ring_flanged.py` and `templates/l_bracket_gusset.py`
- [x] 2.4 Write `templates/plate_boss_pattern.py`, `templates/hook.py`, `templates/clip.py`, `templates/stand.py`
- [x] 2.5 Run `script_lint.py` and `run_cadquery_model.py` over every template; fix until all are lint-clean and geometry-valid with default parameters

## 3. Pre-verification tests

- [x] 3.1 Create `tests/test_templates.py`: index validates against its schema, every listed file exists, every `templates/*.py` is listed
- [x] 3.2 Add parametrized per-template tests: lint reports zero findings; execution with defaults yields watertight geometry with empty `errors`
- [x] 3.3 Run the full suite (`uv run pytest tests/`) and fix any fallout

## 4. Plan integration

- [x] 4.1 Add optional per-part `archetype` (string) to `src/build_plan_schema.json`
- [x] 4.2 Extend `src/plan_validate.py` to cross-check present `archetype` values against `templates/archetypes.json` names (mirroring the `blocks_needed` inventory check)
- [x] 4.3 Add `tests/test_plan_validate.py` cases: valid archetype passes, unknown archetype fails naming part and value, archetype-free plans unchanged

## 5. Skill and prompt wiring

- [x] 5.1 Add the planning rule to `prompts/planning.md`: set `archetype` when a part fits an index entry's `use`, omit otherwise; substitute the archetype index into the planning prompt alongside the block inventory
- [x] 5.2 Add "Step 1.5 - match archetype" to `skill/phase3_build.md`: use planned value after confirming fit, else match against use/aliases; on match copy template and edit params/deltas preserving guards; on non-match fall back to raw authoring with a one-line reason
- [x] 5.3 Update SKILL.md pointer text and CLAUDE.md file-layout section to mention `templates/`

## 6. Verification

- [x] 6.1 Run `openspec validate --change part-archetype-templates` and the fast test subset; confirm all spec scenarios have a covering test or documented skill behavior
