## MODIFIED Requirements

### Requirement: request_log is searchable without reading the whole plan
The system SHALL provide `src/request_log_search.py`, a stdlib-only script that filters
`BUILD_PLAN.json`'s `request_log` array by a case-insensitive substring match against
`text` (`--query`), an exact `kind` match (`--kind`: `initial`, `clarification`,
`correction`), an exact `level` match (`--level`: `functional`, `operation`,
`parameter`), and/or a `targets` membership match (`--target`: case-insensitive
substring against any string in the entry's `targets` array), returning only the
entries matching every supplied filter as JSON -- without requiring the whole
`request_log` array (or the rest of `BUILD_PLAN.json`) to be read into context to find
them. An entry with no `level` never matches `--level`; an entry with no `targets`
never matches `--target`.

#### Scenario: Keyword search returns only matching entries
- **WHEN** `request_log_search.py BUILD_PLAN.json --query "hinge"` is run against a plan
  whose `request_log` has 12 entries, 2 of which mention "hinge"
- **THEN** the command prints exactly those 2 entries as JSON, not the full 12-entry array

#### Scenario: Kind filter narrows to corrections
- **WHEN** `request_log_search.py BUILD_PLAN.json --kind correction` is run
- **THEN** only entries with `kind: "correction"` are printed

#### Scenario: Level filter narrows to parameter-level entries
- **WHEN** `request_log_search.py BUILD_PLAN.json --level parameter` is run
- **THEN** only entries with `level: "parameter"` are printed, and entries with no
  `level` field are omitted

#### Scenario: Target filter matches a part id in targets
- **WHEN** `request_log_search.py BUILD_PLAN.json --target cradle` is run
- **THEN** only entries whose `targets` array contains a string matching "cradle"
  (case-insensitive substring) are printed

#### Scenario: Combined filters are ANDed
- **WHEN** `--query`, `--kind`, `--level`, and `--target` are given together
- **THEN** only entries matching all supplied conditions are printed

#### Scenario: No matches prints an empty result, not an error
- **WHEN** the filter combination matches no entries
- **THEN** the command exits 0 and prints an empty JSON array

#### Scenario: Absent request_log is handled gracefully
- **WHEN** `BUILD_PLAN.json` has no `request_log` field (an older or eval-corpus plan)
- **THEN** the command prints an empty JSON array rather than raising an error
