# request-log-search

## Purpose

Defines how the cq-design pipeline lets Claude find specific prior context inside a
plan's `request_log` -- a keyword or kind filter -- without loading the entire
`request_log` array (or the rest of `BUILD_PLAN.json`) into context.

## Requirements

### Requirement: request_log is searchable without reading the whole plan
The system SHALL provide `src/request_log_search.py`, a stdlib-only script whose
`search` subcommand (`request_log_search.py search <plan> ...`) filters
`BUILD_PLAN.json`'s `request_log` array by a case-insensitive substring match against
`text` (`--query`), an exact `kind` match (`--kind`: `initial`, `clarification`,
`correction`), an exact `level` match (`--level`: `functional`, `operation`,
`parameter`), and/or a `targets` membership match (`--target`: case-insensitive
substring against any string in the entry's `targets` array), returning only the
entries matching every supplied filter as JSON -- without requiring the whole
`request_log` array (or the rest of `BUILD_PLAN.json`) to be read into context to find
them. An entry with no `level` never matches `--level`; an entry with no `targets`
never matches `--target`. Flag names, filter semantics, and JSON output are unchanged
from the pre-subcommand CLI; only the leading `search` subcommand is new.

#### Scenario: Keyword search returns only matching entries
- **WHEN** `request_log_search.py search BUILD_PLAN.json --query "hinge"` is run
  against a plan whose `request_log` has 12 entries, 2 of which mention "hinge"
- **THEN** the command prints exactly those 2 entries as JSON, not the full 12-entry array

#### Scenario: Kind filter narrows to corrections
- **WHEN** `request_log_search.py search BUILD_PLAN.json --kind correction` is run
- **THEN** only entries with `kind: "correction"` are printed

#### Scenario: Level filter narrows to parameter-level entries
- **WHEN** `request_log_search.py search BUILD_PLAN.json --level parameter` is run
- **THEN** only entries with `level: "parameter"` are printed, and entries with no
  `level` field are omitted

#### Scenario: Target filter matches a part id in targets
- **WHEN** `request_log_search.py search BUILD_PLAN.json --target cradle` is run
- **THEN** only entries whose `targets` array contains a string matching "cradle"
  (case-insensitive substring) are printed

#### Scenario: Combined filters are ANDed
- **WHEN** `--query`, `--kind`, `--level`, and `--target` are given together
- **THEN** only entries matching all supplied conditions are printed

#### Scenario: No matches prints an empty result, not an error
- **WHEN** the query/kind combination matches no entries
- **THEN** the command exits 0 and prints an empty JSON array

#### Scenario: Absent request_log is handled gracefully
- **WHEN** `BUILD_PLAN.json` has no `request_log` field (an older or eval-corpus plan)
- **THEN** the command prints an empty JSON array rather than raising an error

### Requirement: Phase 3 uses the search tool instead of re-reading the full log
`skill/phase3_build.md` SHALL instruct that when the orchestrator needs prior context
about a specific decision, feature, or correction during Escalation or a correction
round, it runs `request_log_search.py search` with a relevant keyword rather than
re-reading `BUILD_PLAN.json`'s full `request_log` array into context.

#### Scenario: Escalation references a keyword search
- **WHEN** Phase 3 needs to recall why a dimension was corrected earlier in the build
- **THEN** it runs `request_log_search.py search` filtered by a relevant keyword
  instead of re-reading the entire `request_log` array

### Requirement: An add subcommand appends a request_log entry with an automatic timestamp
`request_log_search.py`'s `add` subcommand (`request_log_search.py add <plan> --kind
<clarification|correction> --text <text> [--level <functional|operation|parameter>]
[--target <name>]...`) SHALL append one entry to `BUILD_PLAN.json`'s `request_log`
array with `ts` set to the current UTC time in ISO-8601 format, without requiring the
caller to supply or compute a timestamp. `add` SHALL reject `--kind initial` (the
`initial` entry is written once when the plan is first created, not appended). Before
writing, `add` SHALL validate the resulting `request_log` array against
`build_plan_schema.json` and SHALL make no change to the file if validation fails,
reporting the validation error on stderr and exiting 1. `add` SHALL append after the
existing array (or create a one-entry array if `request_log` is absent) and SHALL NOT
edit, reorder, or remove any existing entry.

#### Scenario: Appending a correction with a target
- **WHEN** `request_log_search.py add BUILD_PLAN.json --kind correction --text "make
  the lid 2mm taller" --level parameter --target lid` is run
- **THEN** a new entry `{"ts": "<current UTC ISO-8601>", "kind": "correction", "text":
  "make the lid 2mm taller", "level": "parameter", "targets": ["lid"]}` is appended to
  `request_log`, and every existing entry is unchanged

#### Scenario: Repeated --target produces a targets array
- **WHEN** `add` is run with `--target lid --target base`
- **THEN** the appended entry's `targets` is `["lid", "base"]`

#### Scenario: Omitting --level or --target leaves the field unset
- **WHEN** `add` is run with only `--kind` and `--text`
- **THEN** the appended entry has no `level` or `targets` key

#### Scenario: --kind initial is rejected
- **WHEN** `add` is run with `--kind initial`
- **THEN** the command exits 1 with an error and does not modify the plan

#### Scenario: A value that would fail schema validation is rejected before writing
- **WHEN** `add` is run with `--text ""` (empty text)
- **THEN** the command exits 1 with the schema validation error on stderr, and
  `BUILD_PLAN.json` is unchanged

#### Scenario: request_log is created when absent
- **WHEN** `add` is run against a `BUILD_PLAN.json` with no `request_log` field
- **THEN** the file gains a `request_log` array containing exactly the one new entry
