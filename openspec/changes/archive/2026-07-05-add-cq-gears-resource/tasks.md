## 1. Update the planning prompt

- [x] 1.1 Add a new rule to `prompts/planning.md` (after rule 12, `shadow_gap`) instructing the LLM: if the request or decomposition involves a gear/pinion/toothed-gear part and no inventory block covers it, note in `planning_notes` that no gear block exists yet and point to `https://github.com/lwidm/cq_gears` as a downloadable external resource.
- [x] 1.2 Confirm the rule does not suggest adding anything to `blocks_needed` or the schema -- it is a `planning_notes` prose instruction only.

## 2. Update the spec

- [x] 2.1 Verify `openspec/changes/add-cq-gears-resource/specs/planning-phase/spec.md` requirement/scenarios match the final prompt wording.

## 3. Update project docs

- [x] 3.1 `README.md`: add a `lwidm/cq_gears` row to the Prior art table (relevance `medium`), describing it as a parametric involute spur/helical gear generator for CadQuery with no stated upstream license, so it's referenced as an external resource rather than adopted into `blocks/`.
- [x] 3.2 `TODO.md`: remove line 51 (`- [ ] add https://github.com/lwidm/cq_gears`).
- [x] 3.3 `TODO.md`: add a short entry under "Prior-art ideas" recording the disposition -- strategy `optional external` (no license, so pinned dep / vendored snapshot are unavailable), surfaced via the planning-phase pointer rather than a gate check.

## 4. Verify

- [x] 4.1 Grep the repo for `cq_gears` to confirm the only references are in `prompts/planning.md`, `README.md`, and `TODO.md` -- no accidental `pyproject.toml` or `blocks/inventory.json` edits.
- [x] 4.2 Run `uv run pytest tests/` to confirm no regression (docs/prompt-only change).
- [x] 4.3 Run `openspec validate add-cq-gears-resource`.
