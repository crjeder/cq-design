## ADDED Requirements

### Requirement: Phase-file prose does not restate a guaranteed-in-context read
A `skill/phase*.md` file SHALL NOT restate the substantive content of a
document its own phase's Setup step already reads into context
unconditionally, before the content that would restate it is needed. Such
content SHALL instead be stated once in the source document and cited by
name from the phase file. This applies to technical explanations (e.g. a
CadQuery convention) and structured data (e.g. block metadata); it does not
apply to a short excerpt needed to make a decision tree self-contained, or to
content whose source is read conditionally (only on some branches), where
restating the needed piece keeps every branch correct without depending on
which branch already ran the conditional read.

#### Scenario: A technical explanation available from a Setup read is cited, not restated
- **WHEN** a phase file's step needs a CadQuery-convention fact that a
  reference document read at that phase's Setup already states in full
- **THEN** the phase file names that document and section instead of
  re-explaining the convention inline

#### Scenario: Structured metadata available from a Setup read is cited, not restated
- **WHEN** a phase file would otherwise tabulate data (e.g. name/use/params
  per block) that a machine-readable file the phase's Setup already reads
  into context also carries
- **THEN** the phase file points to that file instead of duplicating the
  table, unless the phase file also carries procedural instruction with no
  equivalent in the machine-readable source (in which case that instruction
  stays, and only the plain data restatement is cut)

#### Scenario: A conditionally-read document is not assumed in context
- **WHEN** a phase file's instruction would apply regardless of which branch
  of an earlier conditional read executed (e.g. an instruction useful on a
  fresh run, before a conditionally-read file would have been read)
- **THEN** the phase file states the needed content inline rather than citing
  a document that is not guaranteed to be in context on every path that
  reaches this instruction
