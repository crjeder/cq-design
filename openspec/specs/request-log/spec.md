# request-log

## Purpose

Defines how the cq-design pipeline preserves the user's original request and
every subsequent clarification or correction verbatim in `BUILD_PLAN.json`, so
the exact wording that shaped the design stays available across planning,
re-planning, and the part loop, independent of any session's context window.
Preserve the user's original request and every subsequent clarification or correction
verbatim alongside `BUILD_PLAN.json`, so the plan's provenance is auditable and re-planning
never loses history.

## Requirements

### Requirement: BUILD_PLAN.json schema accepts an optional request_log
`src/build_plan_schema.json` SHALL define an optional top-level `request_log`
array. Each entry SHALL have `ts` (ISO-8601 UTC string), `kind` (one of
`initial`, `clarification`, `correction`), non-empty `text` (verbatim user
wording), and MAY have `images` (a non-empty array of non-empty repo-relative
path strings pointing to sketch/annotated-image files), `level` (one of
`functional`, `operation`, `parameter` -- the intent granularity of the entry),
and `targets` (a non-empty array of non-empty strings, each naming an affected
part id or a `part.feature` / parameter name), with no other additional
properties. When the array is present it SHALL contain exactly one `initial`
entry, and that entry SHALL be first. `level` and `targets` are independent:
either MAY appear without the other, and entries written before typed
request_log carry neither and SHALL stay valid.

#### Scenario: Plan without request_log stays valid
- **WHEN** a `BUILD_PLAN.json` without `request_log` (e.g. an eval-corpus golden
  plan) is validated
- **THEN** validation passes unchanged

#### Scenario: An entry with level and targets validates
- **WHEN** a `request_log` entry carries `level: "parameter"` and
  `targets: ["cradle", "cradle.saddle_width"]` alongside its required fields
- **THEN** validation passes

#### Scenario: An untyped entry alongside typed entries validates
- **WHEN** a `request_log` array mixes entries that carry `level`/`targets` with
  entries that carry neither
- **THEN** validation passes

#### Scenario: Well-formed log validates
- **WHEN** a plan carries `request_log` with one `initial` entry first followed by
  `clarification`/`correction` entries, each with `ts`, `kind`, and non-empty
  `text`
- **THEN** validation passes

#### Scenario: An entry with images validates
- **WHEN** a `request_log` entry carries `images: ["sketches/ear-placement.png"]`
  alongside its required fields
- **THEN** validation passes

#### Scenario: Malformed entries are rejected
- **WHEN** an entry has an unknown `kind`, empty `text`, a missing field, an empty
  `images` array, an empty-string path inside `images`, an unknown `level` value,
  an empty `targets` array, an empty-string entry inside `targets`, or an extra
  property - or the array has zero or multiple `initial` entries
- **THEN** `plan.py validate` reports a schema validation error

### Requirement: Planning populates the initial request verbatim
The planning phase SHALL populate `request_log` when emitting a new plan: the
user's original request as the `initial` entry, plus one entry per clarification
gathered during requirements/planning, all verbatim. The `initial` entry SHALL keep
the user's unresolved opening wording even after Phase 1 resolves it -- the resolved
reading lives in `intent` (see the `approved-intent` spec), never in place of the
verbatim entry.

#### Scenario: Fresh plan from a clarified request
- **WHEN** the planner emits `BUILD_PLAN.json` after asking two clarifying
  questions
- **THEN** the plan's `request_log` holds the original request as `initial` and
  the two answers as `clarification` entries, in order, verbatim

#### Scenario: Vague opening is not rewritten by the reformulation
- **WHEN** Phase 1 reformulates "a stand for my laptop" into a fully resolved
  description the user approves
- **THEN** `request_log[0].text` still reads "a stand for my laptop" and the resolved
  description is written to `intent`

### Requirement: Mid-build clarifications are appended, never rewritten
When the user gives a clarification or correction after the plan is written, the
system SHALL append a dated entry to `request_log` and SHALL NOT edit, reorder,
or remove existing entries. When a correction triggers re-planning, the
regenerated plan SHALL carry the prior `request_log` forward verbatim with the
new entry appended.

#### Scenario: Correction during the part loop
- **WHEN** the user corrects a dimension while parts are being built
- **THEN** a `correction` entry with the user's wording is appended to
  `request_log` in `BUILD_PLAN.json`, and all prior entries are unchanged

#### Scenario: Re-plan preserves history
- **WHEN** a correction causes the planner to regenerate the plan
- **THEN** the new `BUILD_PLAN.json` contains every prior `request_log` entry
  unchanged, followed by the correction entry

### Requirement: request_log is the sole record of round-by-round history
The system SHALL treat `request_log` as the only place round-by-round build history
(per-round corrections, superseded values, "what changed since the last attempt") is
recorded. `planning_notes`, per-part `part_notes`, and generated part-script comments
SHALL NOT contain a round-by-round changelog narrative (e.g. "ROUND 2", "SUPERSEDED by
round N below"); each SHALL describe only the current design state as of the present
plan/script.

#### Scenario: Correction narrative goes to request_log, not part_notes
- **WHEN** a part's geometry changes between build attempts due to a user correction
- **THEN** the correction is appended to `request_log` as a `correction` entry, and the
  part's `part_notes` is updated (or left as-is) to describe only the part's current
  design -- it does not gain a new dated paragraph describing the prior attempt

#### Scenario: Superseded part_notes content is deleted, not annotated
- **WHEN** a round of changes makes part of `part_notes` no longer true of the current
  design
- **THEN** that content is removed from `part_notes` rather than kept and marked
  "SUPERSEDED by round N"

### Requirement: A sketch referenced by a request_log entry is copied into the project and re-read on iteration
When the user attaches an image (a sketch, a photo, or an annotated screenshot) to
their opening request, a clarification, or a correction, the orchestrator SHALL copy
that image into a `sketches/` directory at the project root under a stable, descriptive
name before appending the `request_log` entry, and SHALL record the copied file's
repo-relative path in that entry's `images` field. This applies to the `initial` entry
written in Phase 1 exactly as it applies to a mid-build correction. When iterating on
the feature a `request_log` entry's `images` annotate -- during a correction round or
Escalation -- the orchestrator SHALL re-read the referenced sketch file(s) before
re-authoring the part, the same discipline `skill/phase3_build.md` already prescribes
for preview renders ("read the render before re-rendering").

#### Scenario: An attached sketch is copied and logged
- **WHEN** the user gives a correction accompanied by an annotated image during the
  Design approval checkpoint
- **THEN** the image is copied into `sketches/`, and the appended `correction` entry's
  `images` field names that copied path

#### Scenario: An image attached to the opening request is captured
- **WHEN** the user's first message attaches a photo of the object to be fitted
- **THEN** the photo is copied into `sketches/` and the `initial` entry's `images` field
  names that copied path

#### Scenario: A referenced sketch is re-read before the next attempt
- **WHEN** the orchestrator re-authors a part in response to a correction whose
  `request_log` entry carries `images`
- **THEN** it reads the referenced sketch file(s) before writing the next attempt,
  not only the entry's `text`

### Requirement: New request_log entries are typed at write time
When the planning phase populates `request_log` or the Phase 3 orchestrator
appends an entry, it SHALL set `level` and `targets` on that entry: `level` is
`functional` (adds/removes/reshapes a part or capability), `operation` (changes
how an existing feature is made -- a joint, a cut, a pattern), or `parameter` (a
dimension or literal change with the design otherwise fixed); `targets` names
every part id and, where the wording is feature- or parameter-specific, every
`part.feature` / parameter name the entry affects. The `initial` entry MAY omit
both when the original request is too broad to attribute. Existing entries in a
carried-forward log SHALL NOT be back-filled.

#### Scenario: Planner types a clarification entry
- **WHEN** the planner records a dimension-checkpoint correction of the cradle's
  saddle width as a `clarification` entry
- **THEN** that entry carries `level: "parameter"` and `targets` naming the
  cradle part and its saddle-width parameter

#### Scenario: Phase 3 types an appended correction
- **WHEN** the user asks during the Design approval checkpoint to add a drain
  slot to the base
- **THEN** the appended `correction` entry carries `level: "operation"` (or
  `functional` if it is a new part) and `targets` naming the base part

#### Scenario: Carried-forward entries are left untyped
- **WHEN** a re-plan carries forward an older `request_log` whose entries have no
  `level`/`targets`
- **THEN** those entries are copied verbatim without `level` or `targets` added

### Requirement: A parameter-level entry is applied only within its targets
When the orchestrator acts on a `request_log` entry with `level: "parameter"`,
it SHALL change only literals in the part scripts named in that entry's
`targets`. A value that must agree across parts SHALL be routed through `joints`
/ `mate_chain.py` (a derived pose or a shared block parameter), NOT by
hand-editing the same literal into a sibling part the entry does not target.
This is orchestrator discipline enforced in `skill/phase3_build.md`; it is not
checked by `plan.py validate`.

#### Scenario: Shared dimension correction routes through the mate chain
- **WHEN** a `parameter` entry targeting `cradle` corrects an interface width
  that the `saddle` part must match
- **THEN** the orchestrator changes the literal in `cradle`'s script and derives
  `saddle`'s matching dimension through the joint / mate chain, rather than
  editing the same number into `saddle`'s script directly

#### Scenario: Single-part parameter change stays local
- **WHEN** a `parameter` entry targets only `lid` and names `lid.lip_height`
- **THEN** only `lid`'s script is edited
