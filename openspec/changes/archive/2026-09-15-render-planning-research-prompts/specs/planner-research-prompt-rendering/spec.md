## ADDED Requirements

### Requirement: Planning prompt is rendered by render_prompt.py
`src/render_prompt.py` SHALL provide a `planning` subcommand taking `--request-file`
(required), `--plan` (optional prior `BUILD_PLAN.json`), `--profile` (default
`printer_profile.json`) and `--out` (default `build/planning_prompt.txt`). It SHALL render
`prompts/planning.md` with `{{USER_REQUEST}}` = the request file's text,
`{{BLOCK_INVENTORY}}` = one name + use line per `src/blocks/inventory.json` entry,
`{{ARCHETYPE_INDEX}}` = one name + file + use line per `templates/archetypes.json` entry,
`{{FDM_GUIDELINES}}` = `always`-tagged sections of
`reference/FDM 3D Print Design Guidelines.md` plus sections tagged with any
`blocks_needed` in `--plan`, and `{{PRINTER_PROFILE}}` = the `printer`, `material`,
`nozzle_mm`, `constraints` values of a schema-valid profile or a fixed no-profile note.
It SHALL write the prompt and print a JSON object with `out`, `chars`, and `profile`
(`loaded`, `absent`, or `invalid`).

#### Scenario: Fresh plan with a valid profile
- **WHEN** `render_prompt.py planning --request-file build/request.md` runs in a directory
  with a valid `printer_profile.json` and no `--plan`
- **THEN** `build/planning_prompt.txt` contains the request text, every inventory and
  archetype name, only `always` FDM sections, and the profile's `nozzle_mm`, and the
  printed JSON has `"profile": "loaded"`

#### Scenario: Re-plan pulls prior blocks' guidelines
- **WHEN** `--plan` names a plan whose parts need a block that tags an FDM section
- **THEN** that section is included alongside the `always` sections

#### Scenario: Missing or invalid profile
- **WHEN** `printer_profile.json` is absent or fails schema validation
- **THEN** the prompt carries the no-profile note and the printed JSON reports `absent`
  or `invalid`

### Requirement: Research prompt is rendered by render_prompt.py
`src/render_prompt.py` SHALL provide a `research` subcommand taking `--targets-file`
(required), `--known-file` (optional) and `--out` (default `build/research_prompt.txt`).
It SHALL render `prompts/research.md` with `{{LOOKUP_TARGETS}}` = the targets file text,
`{{KNOWN_CONTEXT}}` = the known file text or `(none)` when absent or blank, and
`{{SKILL_DIR}}` = the skill root as a POSIX path, then write the prompt and print
`{"out", "chars"}`.

#### Scenario: No known context
- **WHEN** `research --targets-file build/lookup_targets.md` runs without `--known-file`
- **THEN** the prompt contains the targets text, `(none)` under the known-context heading,
  and the absolute skill path in the `measure_stl.py` command

### Requirement: Rendering fails on an unfilled placeholder
The `planning` and `research` subcommands SHALL exit 1 with a stderr message naming the
placeholder when the template contains a `{{KEY}}` the renderer does not supply, and
SHALL NOT write the output file.

#### Scenario: Template gains a new placeholder
- **WHEN** `prompts/planning.md` contains a placeholder the `planning` renderer does not fill
- **THEN** the command exits 1 naming it and no prompt file is written

### Requirement: Main session does not assemble planner or research prompts
`skill/phase2_planning.md` and `skill/phase1_requirements.md` SHALL instruct the main
session to write the request (or lookup targets and known context) to a file, run the
matching `render_prompt.py` subcommand, and spawn the agent with
`Read <out> in full and follow it.` The docs SHALL NOT instruct the main session to read
`inventory.json`, `archetypes.json`, the FDM guidelines, `prompts/planning.md`, or
`prompts/research.md` to build these prompts.

#### Scenario: Phase 2 prompt construction
- **WHEN** the main session starts Phase 2
- **THEN** it renders the planner prompt with `render_prompt.py planning` and uses the
  printed `profile` status to decide whether to ask the user for printer values, without
  opening the source files
