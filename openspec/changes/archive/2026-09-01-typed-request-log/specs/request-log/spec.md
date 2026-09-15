## MODIFIED Requirements

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
either MAY appear without the other, and entries written before this change
carry neither and SHALL stay valid.

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

#### Scenario: An entry with level and targets validates
- **WHEN** a `request_log` entry carries `level: "parameter"` and
  `targets: ["cradle", "cradle.saddle_width"]` alongside its required fields
- **THEN** validation passes

#### Scenario: An untyped entry alongside typed entries validates
- **WHEN** a `request_log` array mixes entries that carry `level`/`targets` with
  entries that carry neither
- **THEN** validation passes

#### Scenario: Malformed entries are rejected
- **WHEN** an entry has an unknown `kind`, empty `text`, a missing field, an empty
  `images` array, an empty-string path inside `images`, an unknown `level` value,
  an empty `targets` array, an empty-string entry inside `targets`, or an extra
  property - or the array has zero or multiple `initial` entries
- **THEN** `plan_validate.py` reports a schema validation error

## ADDED Requirements

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
checked by `plan_validate.py`.

#### Scenario: Shared dimension correction routes through the mate chain
- **WHEN** a `parameter` entry targeting `cradle` corrects an interface width
  that the `saddle` part must match
- **THEN** the orchestrator changes the literal in `cradle`'s script and derives
  `saddle`'s matching dimension through the joint / mate chain, rather than
  editing the same number into `saddle`'s script directly

#### Scenario: Single-part parameter change stays local
- **WHEN** a `parameter` entry targets only `lid` and names `lid.lip_height`
- **THEN** only `lid`'s script is edited
