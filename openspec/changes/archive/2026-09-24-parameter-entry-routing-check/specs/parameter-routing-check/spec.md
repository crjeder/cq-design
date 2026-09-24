## ADDED Requirements

### Requirement: A parameter-level correction can be snapshotted at append time
`log.py request add` (the CLI documented by the `request-log-search`
capability) SHALL accept a `--snapshot-scripts <dir>` flag. When present, and
the entry being appended carries `level: "parameter"`, the command SHALL hash
every `<part_id>.py` file found directly in `<dir>` (via `freshness.
script_hash`) and write the resulting `{part_id: sha256}` mapping to the
appended entry's `script_baseline` field. When the entry does not carry
`level: "parameter"`, or the flag is omitted, no `script_baseline` is
written.

#### Scenario: Snapshot recorded for a parameter-level correction
- **WHEN** `log.py request add PLAN --kind correction --level parameter
  --target cradle --text "..." --snapshot-scripts build/` is run and `build/`
  contains `cradle.py` and `plate.py`
- **THEN** the appended entry's `script_baseline` maps `cradle` and `plate`
  each to their current script's SHA-256 digest

#### Scenario: Flag has no effect without a parameter level
- **WHEN** the same command is run with `--level operation` (or no `--level`)
  and `--snapshot-scripts build/`
- **THEN** the appended entry has no `script_baseline` field

#### Scenario: Flag omitted
- **WHEN** a `parameter`-level entry is appended without `--snapshot-scripts`
- **THEN** the appended entry has no `script_baseline` field, and the
  drift check (below) has nothing to compare against for this entry

### Requirement: quality_gate detects a script change outside a parameter entry's targets
When `quality_gate.py`'s `run_gate` runs for any part, it SHALL locate the
newest `request_log` entry that carries a `script_baseline` (by `ts`) and, for
every part id present in that baseline, compare the baseline's stored hash
against the current hash of that part's script file (same directory as the
script being gated). For each part whose hash differs from its baseline, is
absent from the entry's `targets` (matching a bare part id or a
`part.<name>`-prefixed target the same way `render_prompt.scoped_request`
does), and is not linked to any part named in `targets` by a `joints` entry's
`members`, the gate SHALL add a `routing_violation` finding using the shared
quality-gate issue contract, naming the entry's `text`, the targeted part(s),
and the drifted part.

#### Scenario: Untargeted sibling script drift is flagged
- **WHEN** the newest `script_baseline`-carrying entry targets only `cradle`,
  and `plate.py`'s current hash differs from its baseline, with no `joints`
  entry linking `cradle` and `plate`
- **THEN** `run_gate`'s issues include a `routing_violation` finding naming
  `plate`, `cradle`, and the entry's text

#### Scenario: Targeted part's own drift is not flagged
- **WHEN** the newest `script_baseline`-carrying entry targets `cradle`, and
  only `cradle.py`'s hash differs from its baseline
- **THEN** no `routing_violation` finding is added for `cradle`

#### Scenario: Joint-linked sibling drift is not flagged
- **WHEN** the newest `script_baseline`-carrying entry targets `cradle`,
  `plate.py`'s hash differs from its baseline, and a `joints` entry's
  `members` includes both `cradle` and `plate`
- **THEN** no `routing_violation` finding is added for `plate`

#### Scenario: No baseline present
- **WHEN** no `request_log` entry carries a `script_baseline`
- **THEN** `run_gate` performs no routing check and adds no `routing_violation`
  findings

#### Scenario: Part script absent from the directory
- **WHEN** a part named in the baseline has no corresponding `<part_id>.py`
  file in the script directory (not yet built this round)
- **THEN** that part is skipped, not treated as evidence of drift

### Requirement: routing_violation findings are non-blocking
A `routing_violation` finding SHALL be reported at `severity: "warning"` --
the same shared quality-gate issue contract's non-blocking tier used
elsewhere (e.g. `check_skipped`). `run_gate` treats only `severity: "error"`
issues as failing (see its existing `errors = [i for i in all_issues if
i["severity"] == "error"]` filter), so a `routing_violation` alone SHALL NOT
fail `run_gate`, block delivery, or consume a fix-round. Promoting
`routing_violation` to `error` by default SHALL first be justified by
`evals/run_evals.py` evidence, matching the same eval-gate rule the
`request-relative-acceptance` capability already states for its own advisory
findings.

#### Scenario: Warning finding does not fail the gate
- **WHEN** `run_gate` produces only a `routing_violation` finding and no other
  `error`-severity issues
- **THEN** `run_gate`'s `passed` is `true`

#### Scenario: Default severity
- **WHEN** this change ships
- **THEN** `routing_violation` findings are `severity: "warning"`, and
  promoting them to `error` requires eval evidence
