## MODIFIED Requirements

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

