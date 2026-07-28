# request-log-search

## Purpose

Defines how the cq-design pipeline lets Claude find specific prior context inside a
plan's `request_log` -- a keyword or kind filter -- without loading the entire
`request_log` array (or the rest of `BUILD_PLAN.json`) into context.

## Requirements

### Requirement: request_log is searchable without reading the whole plan
The system SHALL provide `src/request_log_search.py`, a stdlib-only script that filters
`BUILD_PLAN.json`'s `request_log` array by a case-insensitive substring match against
`text` (`--query`) and/or an exact `kind` match (`--kind`: `initial`, `clarification`,
`correction`), returning only the matching entries as JSON -- without requiring the whole
`request_log` array (or the rest of `BUILD_PLAN.json`) to be read into context to find
them.

#### Scenario: Keyword search returns only matching entries
- **WHEN** `request_log_search.py BUILD_PLAN.json --query "hinge"` is run against a plan
  whose `request_log` has 12 entries, 2 of which mention "hinge"
- **THEN** the command prints exactly those 2 entries as JSON, not the full 12-entry array

#### Scenario: Kind filter narrows to corrections
- **WHEN** `request_log_search.py BUILD_PLAN.json --kind correction` is run
- **THEN** only entries with `kind: "correction"` are printed

#### Scenario: Combined query and kind filter
- **WHEN** both `--query` and `--kind` are given
- **THEN** only entries matching both conditions are printed

#### Scenario: No matches prints an empty result, not an error
- **WHEN** the query/kind combination matches no entries
- **THEN** the command exits 0 and prints an empty JSON array

#### Scenario: Absent request_log is handled gracefully
- **WHEN** `BUILD_PLAN.json` has no `request_log` field (an older or eval-corpus plan)
- **THEN** the command prints an empty JSON array rather than raising an error

### Requirement: Phase 3 uses the search tool instead of re-reading the full log
`skill/phase3_build.md` SHALL instruct that when the orchestrator needs prior context
about a specific decision, feature, or correction during Escalation or a correction
round, it runs `request_log_search.py` with a relevant keyword rather than re-reading
`BUILD_PLAN.json`'s full `request_log` array into context.

#### Scenario: Escalation references a keyword search
- **WHEN** Phase 3 needs to recall why a dimension was corrected earlier in the build
- **THEN** it runs `request_log_search.py` filtered by a relevant keyword instead of
  re-reading the entire `request_log` array
