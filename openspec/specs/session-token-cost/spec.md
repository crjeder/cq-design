# session-token-cost Specification

## Purpose

Record the billed token cost of a Claude Code session into `build/cost.json` in every
working directory the skill runs in -- not only eval-harness runs -- so any past run can
be cost-post-evaluated later. A running session cannot observe its own usage; this is a
post-hoc read of the session transcript, wired as a `Stop` hook.
## Requirements
### Requirement: Session token cost is recorded per working directory

The system SHALL provide `src/session_cost.py`, a stdlib-only tool that reads a
Claude Code session transcript JSONL and produces a billed-cost record. It SHALL
sum each assistant turn's reported usage -- input tokens, output tokens, cache
read tokens, and cache creation tokens -- grouped by model, and SHALL separate
turns produced by the main session from turns produced by spawned subagents
(transcript sidechain entries). It SHALL price the totals against the
`src/model_prices.json` table (input and output rates per model, unknown model
falling back to the `default` entry), with cache read priced as an approximate
0.1x of the input rate and cache creation as an approximate 1.25x, and SHALL
record the multipliers it used in the output.

#### Scenario: Main and subagent turns are attributed separately

- **WHEN** a transcript contains a main-session assistant turn on one model and a
  subagent (sidechain) assistant turn on a different model
- **THEN** the record's per-model breakdown carries both models, and its
  main-vs-subagent split assigns each turn's tokens and cost to the correct side

#### Scenario: Unknown model falls back to the default price

- **WHEN** a transcript turn names a model absent from the price table
- **THEN** its cost is computed from the table's `default` entry rather than
  raising

### Requirement: Cost record survives resume

`build/cost.json` SHALL be a mapping keyed by session id, holding one per-session
block plus a `combined` rollup over all recorded sessions. Recording a new
session's cost SHALL replace only that session's block and recompute `combined`,
never discarding blocks for other session ids.

#### Scenario: Resumed session does not erase the first

- **WHEN** `session_cost.py` records session B's cost into a `build/cost.json`
  that already holds session A's block
- **THEN** session A's block is unchanged, session B's block is present, and
  `combined` sums both

### Requirement: The cost hook is non-blocking and scoped

`session_cost.py` SHALL provide a hook mode that reads the Claude Code hook
payload from stdin (taking the transcript path and session id) and updates
`build/cost.json` in the current working directory. It SHALL write nothing and
SHALL exit 0 when `build/` does not exist in the working directory, when the
transcript cannot be read, or when the transcript does not match the expected
shape -- a cost recorder SHALL never cause a turn to fail.

#### Scenario: No active run in this directory

- **WHEN** the hook fires in a directory that has no `build/` subdirectory
- **THEN** `session_cost.py` exits 0 and creates no files

#### Scenario: Unreadable or unexpected transcript

- **WHEN** the hook fires but the transcript path is missing or its lines do not
  parse as the expected records
- **THEN** `session_cost.py` exits 0, and any existing `build/cost.json` is left
  unchanged

### Requirement: The cost record is not a pipeline artifact

`build/cost.json` SHALL be treated as session bookkeeping, not pipeline output:
it SHALL NOT be bundled into the self-contained build environment's `lib/`, SHALL
NOT be part of any deliverable, and SHALL be safe to delete without affecting a
re-run.

#### Scenario: Deliverable bundling skips the cost record

- **WHEN** the self-contained build environment is assembled for delivery
- **THEN** `build/cost.json` is not copied into `lib/` and does not appear in the
  delivered project tree

