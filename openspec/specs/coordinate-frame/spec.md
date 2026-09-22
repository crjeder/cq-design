## Purpose

Per-project compass-to-axis binding: a plan may record which world axis "East"/"North"/
"Up" resolve to, and `plan.py validate` nudges a plan that uses compass language without
recording one. Prevents the same "which side is East" question from being re-derived
differently on every correction round when a project's binding diverges from the
standard table in `prompts/planning.md`.

## Requirements

### Requirement: Plan may declare a resolved compass binding
`BUILD_PLAN.json` SHALL accept an optional root-level `coordinate_frame` object with
`east`, `north`, and `up` fields, each one of `+x`, `-x`, `+y`, `-y`, `+z`, `-z`. When
absent, the project uses the standard binding (`east: "+x"`, `north: "+y"`, `up: "+z"`,
per `prompts/planning.md`'s Coordinate vocabulary table). `coordinate_frame` governs
prose and review interpretation of compass language only; it SHALL NOT alter
`placement.rotate` or joint `dof.direction` sign conventions, which remain
right-hand-rule on the literal declared axes regardless of this field.

#### Scenario: Plan without coordinate_frame uses the standard binding
- **WHEN** a plan has no `coordinate_frame` field
- **THEN** the plan validates, and any prose referencing "East" is
  interpreted as `+x`

#### Scenario: Plan with a non-standard binding is honored
- **WHEN** a plan declares `coordinate_frame: {"east": "-x", "north": "+y",
  "up": "+z"}`
- **THEN** the plan validates, and prose/checkpoint review interpret "East"
  in that project as `-x`

#### Scenario: Invalid axis token is rejected
- **WHEN** a plan declares `coordinate_frame: {"east": "sideways", ...}`
- **THEN** schema validation fails

### Requirement: Unrecorded compass usage is flagged
`plan.py validate` SHALL emit an advisory finding, at the same tier as
`check_block_thinness` (printed after `BUILD_PLAN OK`, never part of
`validate_plan`'s blocking error list), when a plan's `intent`,
`planning_notes`, or any `request_log[].text` contains a compass direction
word (`north`, `south`, `east`, or `west`, case-insensitive, word-boundary
matched) and the plan has no `coordinate_frame` field.

#### Scenario: Compass word in intent with no coordinate_frame
- **WHEN** a plan's `intent` is "add a fillet on the east side" and
  `coordinate_frame` is absent
- **THEN** `plan.py`'s advisory findings include one noting compass
  language was used with no recorded binding

#### Scenario: Compass word in request_log with no coordinate_frame
- **WHEN** no compass word appears in `intent`/`planning_notes` but a
  `request_log` entry's `text` contains "West", and `coordinate_frame` is
  absent
- **THEN** the same advisory finding is emitted

#### Scenario: coordinate_frame recorded silences the finding
- **WHEN** a plan's `intent` uses compass language and `coordinate_frame` is
  present
- **THEN** no compass-usage advisory finding is emitted, regardless of which
  binding was recorded

#### Scenario: No compass language needs no coordinate_frame
- **WHEN** a plan's `intent`, `planning_notes`, and `request_log` entries
  contain no compass direction word
- **THEN** no compass-usage advisory finding is emitted, whether or not
  `coordinate_frame` is present
