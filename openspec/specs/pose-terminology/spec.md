## Purpose

One vocabulary for the three coordinate states a part moves through -- build pose, assembly pose, print pose -- across docs, prompts, schema descriptions, source text and specs, so builders and maintainers read the same terms.

## Requirements

### Requirement: Three poses are named build, assembly and print pose
The skill SHALL name its three coordinate states **build pose** (the frame a part script is authored in), **assembly pose** (build pose plus `placement`), and **print pose** (build pose rotated by the accepted orientation `rotate`) in every document, prompt, schema `description`, docstring, comment, CLI help text and user-facing message. `CLAUDE.md` SHALL remain the definition point and `SKILL.md` SHALL use the same three terms.

#### Scenario: SKILL.md and CLAUDE.md agree
- **WHEN** `SKILL.md` describes the coordinate states a part moves through
- **THEN** it uses "build pose", "assembly pose" and "print pose" with the same meanings as `CLAUDE.md`

#### Scenario: Builder prompt uses pose wording
- **WHEN** `render_prompt.py` renders a builder prompt from `prompts/part.md`
- **THEN** the frame definitions and the `placement` instruction use "build pose", "assembly pose" and "print pose"

### Requirement: Retired frame terms are not used
The phrases "part frame", "authored frame", "assembled frame", "print frame" and "build frame" (also hyphenated forms) SHALL NOT appear in documentation, prompts, schema or inventory descriptions, source comments or docstrings, tool output, or `openspec/specs/`. Archived changes, `documentation/DONE.md`, `TODO.md` and `documentation/todo-*.md` history entries are exempt. Identifier and file names (for example `src/blocks/print_frame.py`, `print_up()`) and the unrelated `coordinate_frame` plan field are exempt.

#### Scenario: Scan finds no retired term
- **WHEN** a scan runs over tracked docs, prompts, `src/`, `reference/`, `skill/`, `commands/` and `openspec/specs/` excluding the exempt paths
- **THEN** none of the retired phrases is found

#### Scenario: Ambiguous "build frame" resolved by sense
- **WHEN** a former "build frame" mention referred to the print-oriented frame (bed-relative classification, orientation-posed mesh)
- **THEN** it now reads "print pose", and a mention of the authored frame reads "build pose"

### Requirement: Wording change does not alter behavior
The terminology change SHALL NOT rename or remove any JSON key, CLI flag, function name, typed error name or file, and SHALL NOT change any computed result.

#### Scenario: JSON contract unchanged
- **WHEN** `run_cadquery_model.py` runs a model after the change
- **THEN** its JSON output keys and values are identical to before, apart from message strings that contained a retired term

#### Scenario: Existing tests pass
- **WHEN** the test suite runs
- **THEN** it passes with any message-string expectations updated to the pose wording
