## ADDED Requirements

### Requirement: Missing telemetry detected at the gate
The quality gate SHALL check for a per-attempt telemetry log and emit a
`warning` finding (`source: "telemetry"`, `type: "telemetry_missing"`) when the
log is absent, empty, or contains no parseable JSON record. The finding SHALL
NOT be an `error`: an unwritten log never blocks delivery, since the geometry it
would have described is unaffected.

#### Scenario: Log file absent
- **WHEN** the gate runs and no `attempts.jsonl` exists at the resolved path
- **THEN** the report's `issues` include one `telemetry_missing` finding with
  severity `warning`, and `passed` is unchanged by it

#### Scenario: Log file present but empty
- **WHEN** `attempts.jsonl` exists but is zero-length or holds only blank lines
- **THEN** one `telemetry_missing` warning is emitted

#### Scenario: Log file holds no parseable record
- **WHEN** `attempts.jsonl` exists and is non-empty but no line parses as JSON
- **THEN** one `telemetry_missing` warning is emitted

#### Scenario: Populated log is silent
- **WHEN** `attempts.jsonl` holds at least one parseable JSON record
- **THEN** no telemetry finding is emitted

### Requirement: Telemetry log path resolution
The gate SHALL resolve the telemetry log to `attempts.jsonl` in the directory
holding the part scripts (the same `build/` directory the part loop appends to),
and SHALL accept an explicit override path on the CLI.

#### Scenario: Default resolution alongside the part scripts
- **WHEN** the gate is run with `--script build/lid.py` and no override
- **THEN** it checks `build/attempts.jsonl`

#### Scenario: Explicit override
- **WHEN** the gate is run with an explicit attempts-log path
- **THEN** it checks that path instead of the default

### Requirement: Missing telemetry reported at delivery
Phase 4 delivery SHALL surface a `telemetry_missing` finding to the user in the
status report, naming the log that was expected, so a session that skipped the
Step 5 appends is visible rather than silently unmeasured.

#### Scenario: Delivery with no telemetry written
- **WHEN** the gate report carries a `telemetry_missing` warning at delivery
- **THEN** the delivery status names the missing `build/attempts.jsonl` and that
  this session produced no measurement data
