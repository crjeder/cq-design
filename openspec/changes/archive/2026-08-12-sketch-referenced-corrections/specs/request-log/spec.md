## MODIFIED Requirements

### Requirement: BUILD_PLAN.json schema accepts an optional request_log
`src/build_plan_schema.json` SHALL define an optional top-level `request_log`
array. Each entry SHALL have `ts` (ISO-8601 UTC string), `kind` (one of
`initial`, `clarification`, `correction`), non-empty `text` (verbatim user
wording), and MAY have `images` (a non-empty array of non-empty repo-relative
path strings pointing to sketch/annotated-image files), with no other
additional properties. When the array is present it SHALL contain exactly one
`initial` entry, and that entry SHALL be first.

#### Scenario: Plan without request_log stays valid
- **WHEN** a `BUILD_PLAN.json` without `request_log` (e.g. an eval-corpus golden
  plan) is validated
- **THEN** validation passes unchanged

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
  `images` array, an empty-string path inside `images`, or an extra property - or
  the array has zero or multiple `initial` entries
- **THEN** `plan_validate.py` reports a schema validation error

## ADDED Requirements

### Requirement: A sketch referenced by a request_log entry is copied into the project and re-read on iteration
When the user attaches an image (a sketch or an annotated screenshot) to a
clarification or correction, the orchestrator SHALL copy that image into a
`sketches/` directory at the project root under a stable, descriptive name before
appending the `request_log` entry, and SHALL record the copied file's repo-relative
path in that entry's `images` field. When iterating on the feature a `request_log`
entry's `images` annotate -- during a correction round or Escalation -- the
orchestrator SHALL re-read the referenced sketch file(s) before re-authoring the
part, the same discipline `skill/phase3_build.md` already prescribes for preview
renders ("read the render before re-rendering").

#### Scenario: An attached sketch is copied and logged
- **WHEN** the user gives a correction accompanied by an annotated image during the
  Design approval checkpoint
- **THEN** the image is copied into `sketches/`, and the appended `correction` entry's
  `images` field names that copied path

#### Scenario: A referenced sketch is re-read before the next attempt
- **WHEN** the orchestrator re-authors a part in response to a correction whose
  `request_log` entry carries `images`
- **THEN** it reads the referenced sketch file(s) before writing the next attempt,
  not only the entry's `text`
