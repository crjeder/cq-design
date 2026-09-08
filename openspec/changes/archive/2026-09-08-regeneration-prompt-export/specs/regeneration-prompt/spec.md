## ADDED Requirements

### Requirement: Delivery exports a regeneration prompt
Phase 4 SHALL write `REGENERATE.md` at the project root by running
`src/regen_prompt.py` against the project's `BUILD_PLAN.json`, and SHALL NOT hand-author
the file. The export SHALL run on every delivery, overwriting any previous copy, so the
prompt reflects the corrections that landed since the last one. The delivered `README.md`
SHALL point at it.

#### Scenario: A delivered project carries the prompt
- **WHEN** Phase 4 completes delivery of a project
- **THEN** `REGENERATE.md` exists at the project root and `README.md` names it

#### Scenario: A re-delivery after a correction refreshes the prompt
- **WHEN** a correction lands in Phase 3 and the project is delivered again
- **THEN** `REGENERATE.md` is regenerated from the current plan, and its request history
  includes the correction entry

#### Scenario: The prompt is not a build dependency
- **WHEN** the deliverable's `lib/` tooling is bundled
- **THEN** `regen_prompt.py` is not copied into it, and no pipeline step reads
  `REGENERATE.md` back

### Requirement: The prompt states the current intent and the verbatim request history
`REGENERATE.md` SHALL open with an instruction identifying the file as a complete request
for a fresh session, followed by the plan's approved `intent` as the statement of what to
build, followed by every `request_log` entry in order with its verbatim `text` and, when
present, its `kind`, `ts`, `level`, `targets` and `images`. The exported text SHALL be
reproduced unchanged -- neither summarized nor paraphrased.

#### Scenario: Verbatim history survives the export
- **WHEN** the plan's `request_log` holds an `initial` entry and a later `correction`
  entry
- **THEN** both appear in `REGENERATE.md` in order, quoting the user's own wording, with
  the correction's `targets` named

#### Scenario: A stale intent is caught before reporting
- **WHEN** the exported `What to build` section reads as a bare noun phrase rather than
  the approved reformulation
- **THEN** the orchestrator corrects `BUILD_PLAN.json`'s `intent` and re-runs the export,
  rather than editing `REGENERATE.md`

### Requirement: The prompt carries the measurements and drawings the design rests on
`REGENERATE.md` SHALL inline the project's `parameters.py` verbatim when present, so the
sourced real-world measurements and their provenance comments travel with the prompt, and
SHALL list every file under `sketches/`, instructing the user to re-attach those images to
the new session. It SHALL also state the print target: printer, material, nozzle,
`optimize_for` when set, and every entry of the plan's `constraints`.

#### Scenario: Measured values travel with the prompt
- **WHEN** the project's `parameters.py` records a measured bore diameter with its source
  comment
- **THEN** that assignment and its comment appear verbatim in `REGENERATE.md`

#### Scenario: Drawings are referenced for re-attachment
- **WHEN** the project's `sketches/` holds a user-supplied photo
- **THEN** `REGENERATE.md` names that file's path and tells the user to re-attach it

### Requirement: The previous decomposition is reference, not requirement
`REGENERATE.md` SHALL include the previous session's parts (id, description, dimensions)
and joints, labelled explicitly as reference to re-derive rather than copy, so a fresh
session is free to decompose the request differently.

#### Scenario: Decomposition is framed as reference
- **WHEN** the plan holds three parts joined by a dovetail
- **THEN** `REGENERATE.md` lists the parts and the joint under a heading marking them
  reference-only

### Requirement: Absent sources omit their sections
The exporter SHALL omit a section whose source is absent rather than emitting an empty
heading: no request history when the plan carries no `request_log`, no measurements
section when the project has no `parameters.py`, and no drawings section when `sketches/`
is absent or empty.

#### Scenario: A minimal plan exports without empty scaffolding
- **WHEN** the export runs against a plan with no `request_log`, alongside no
  `parameters.py` and no `sketches/`
- **THEN** `REGENERATE.md` carries the intent, the print target and the decomposition,
  and none of the three omitted headings
