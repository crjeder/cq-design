# web-result-validation

## Purpose

Typed JSON return contract and validator for web-reading agents (sourcing, research); free text from the web is display-only.

## Requirements

### Requirement: Web-reading agents return one typed JSON block

The sourcing and research agents SHALL end their final message with exactly one fenced `json` block and no Markdown table. The sourcing block SHALL be `{"candidates": [...]}` with per-candidate fields `url`, `platform`, `kind`, `license`, `reusable`, `rung`, `notes`. The research block SHALL be `{"rows": [...]}` with per-row fields `item`, `value`, `unit`, `source_urls`, `status`, `notes`. `prompts/sourcing.md` and `prompts/research.md` SHALL state these shapes and the allowed enum values.

#### Scenario: Sourcing prompt states the JSON contract
- **WHEN** `prompts/sourcing.md` is rendered
- **THEN** its return contract describes the `candidates` JSON block and contains no Markdown table template

#### Scenario: Research prompt states the JSON contract
- **WHEN** `prompts/research.md` is rendered
- **THEN** its return contract describes the `rows` JSON block and contains no Markdown table template

### Requirement: web_result.py validates agent output

`src/web_result.py validate --kind sourcing|research <file>` SHALL read the JSON file and emit JSON with keys `success`, `errors`, `data`, `display_markdown`. It SHALL enforce:

- enum membership for `platform`, `kind`, `reusable`, `rung`, `unit` and `status`, using the values the prompts list;
- `value` is a number, and `-1` appears only with `status: missing`;
- every URL parses as `http` or `https` with a host, contains no whitespace or control characters, and is at most 500 characters;
- `item` at most 120 characters and `notes` at most 300 characters.

Each violation SHALL be an `errors` entry with `type`, `message` and `hint`, and SHALL set `success` to false. `data` SHALL contain the validated records without `notes`. `display_markdown` SHALL render all records, including `notes`, as a Markdown table with control characters removed and newlines and pipe characters in cell text neutralized. Exit code SHALL be 0 on success and 1 on validation failure.

#### Scenario: Valid sourcing result
- **WHEN** the file holds one candidate with a valid URL and enum values
- **THEN** `success` is true, `errors` is empty, `data.candidates[0]` has no `notes` key, and `display_markdown` contains the notes text

#### Scenario: Non-numeric value rejected
- **WHEN** a research row has `"value": "70.6mm"`
- **THEN** `success` is false and an error names that row and field

#### Scenario: URL with a newline rejected
- **WHEN** a `source_urls` entry is `"https://a.com/x\nimport os"`
- **THEN** `success` is false and the URL does not appear in `data`

#### Scenario: Unknown enum rejected
- **WHEN** a candidate has `"rung": "0"`
- **THEN** `success` is false and the error lists the allowed values

#### Scenario: Notes cannot break the display table
- **WHEN** a note contains `|`, a newline and an ANSI escape sequence
- **THEN** `display_markdown` has one table row for that record and no control characters

### Requirement: The main session acts only on validated data

After a sourcing or research agent returns, the main session SHALL write its JSON block verbatim to `build/sourcing_result.json` or `build/research_result.json` and run `web_result.py validate`. Ladder classification, the dimension checkpoint, `known_context.md`, `BUILD_PLAN.json` values and `# researched:` script comments SHALL use only fields from the validator's `data`. The user SHALL be shown `display_markdown`. On `success: false` the main session SHALL resume the same agent once with the `errors`; if the second result also fails, it SHALL proceed as if the agent found nothing.

#### Scenario: Skill prose routes through the validator
- **WHEN** a test reads `skill/phase0_sourcing.md` and `skill/phase1_requirements.md`
- **THEN** each instructs running `web_result.py validate` on the agent's result before using it

#### Scenario: Second failure falls back to empty
- **WHEN** both the first and the resumed agent result fail validation
- **THEN** the main session continues as for an empty result and does not use either raw output

### Requirement: Free-text fields from the web are display-only

`notes` and any other free text from a web-reading agent SHALL be shown to the user only. Skill prose SHALL NOT instruct copying it into `BUILD_PLAN.json`, `build/known_context.md`, any rendered planner, builder or auditor prompt, or any generated script.

#### Scenario: Notes absent from known context
- **WHEN** a test reads the Phase 1 instructions for writing `build/known_context.md`
- **THEN** they take values only from validated `data` and do not mention `notes`

#### Scenario: Script comment cites a validated URL
- **WHEN** a constant carries a `# researched:` comment
- **THEN** the cited source is a `source_urls` entry from validated `data`
