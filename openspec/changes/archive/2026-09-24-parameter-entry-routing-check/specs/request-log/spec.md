## MODIFIED Requirements

### Requirement: BUILD_PLAN.json schema accepts an optional request_log
`src/build_plan_schema.json` SHALL define an optional top-level `request_log`
array. Each entry SHALL have `ts` (ISO-8601 UTC string), `kind` (one of
`initial`, `clarification`, `correction`), non-empty `text` (verbatim user
wording), and MAY have `images` (a non-empty array of non-empty repo-relative
path strings pointing to sketch/annotated-image files), `level` (one of
`functional`, `operation`, `parameter` -- the intent granularity of the entry),
`targets` (a non-empty array of non-empty strings, each naming an affected
part id or a `part.feature` / parameter name), and `script_baseline` (an
object mapping part id to the SHA-256 hex digest of that part's script file
at the time this entry was appended, written by `log.py request add
--snapshot-scripts`), with no other additional properties. When the array is
present it SHALL contain exactly one `initial` entry, and that entry SHALL be
first. `level`, `targets`, and `script_baseline` are each independent: any
MAY appear without the others, and entries written before these fields
existed carry none of them and SHALL stay valid.

#### Scenario: Plan without request_log stays valid
- **WHEN** a `BUILD_PLAN.json` without `request_log` (e.g. an eval-corpus golden
  plan) is validated
- **THEN** validation passes unchanged

#### Scenario: An entry with level and targets validates
- **WHEN** a `request_log` entry carries `level: "parameter"` and
  `targets: ["cradle", "cradle.saddle_width"]` alongside its required fields
- **THEN** validation passes

#### Scenario: An entry with a script_baseline validates
- **WHEN** a `request_log` entry carries
  `script_baseline: {"cradle": "9f86d0...", "plate": "3b5d5c..."}` alongside
  its required fields
- **THEN** validation passes

#### Scenario: An untyped entry alongside typed entries validates
- **WHEN** a `request_log` array mixes entries that carry `level`/`targets`/
  `script_baseline` with entries that carry none of them
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
  an empty `targets` array, an empty-string entry inside `targets`, a
  `script_baseline` value that is not an object of string-to-string, or an
  extra property - or the array has zero or multiple `initial` entries
- **THEN** `plan.py validate` reports a schema validation error

### Requirement: A parameter-level entry is applied only within its targets
When the orchestrator acts on a `request_log` entry with `level: "parameter"`,
it SHALL change only literals in the part scripts named in that entry's
`targets`. A value that must agree across parts SHALL be routed through `joints`
/ `mate_chain.py` (a derived pose or a shared block parameter), NOT by
hand-editing the same literal into a sibling part the entry does not target.
This is orchestrator discipline stated in `skill/phase3_build.md`, and it is
mechanically checked after the fact: when the entry was appended with
`log.py request add --snapshot-scripts <dir>`, `quality_gate.py` diffs the
current part scripts against the stored `script_baseline` on the next gate
run and reports any changed part outside `targets` and not joint-linked to a
targeted part (see the `parameter-routing-check` spec). `plan.py validate`
itself still does not perform this check -- it operates on `BUILD_PLAN.json`
alone and has no access to part scripts.

#### Scenario: Shared dimension correction routes through the mate chain
- **WHEN** a `parameter` entry targeting `cradle` corrects an interface width
  that the `saddle` part must match
- **THEN** the orchestrator changes the literal in `cradle`'s script and derives
  `saddle`'s matching dimension through the joint / mate chain, rather than
  editing the same number into `saddle`'s script directly

#### Scenario: Single-part parameter change stays local
- **WHEN** a `parameter` entry targets only `lid` and names `lid.lip_height`
- **THEN** only `lid`'s script is edited

#### Scenario: A drift outside targets is now detectable
- **WHEN** a `parameter` entry targeting only `cradle` was appended with
  `--snapshot-scripts build/`, and the next build round also changes
  `plate.py`'s literals with no `joints` entry linking `cradle` and `plate`
- **THEN** the next `quality_gate.py` run reports a `routing_violation`
  finding naming `plate` as the unexpectedly-changed part
