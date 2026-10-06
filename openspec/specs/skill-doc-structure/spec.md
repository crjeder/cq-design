# Skill Doc Structure

## Purpose

Defines how the `cq-design` skill's documentation is split across a small
always-loaded SKILL.md, per-phase detail files, and block-gated reference
data, so that the trigger-time load cost stays small while phase- and
block-specific detail remains fully available when actually needed.

## Requirements

### Requirement: Core SKILL.md stays under 10 KB
SKILL.md SHALL contain only always-needed content - trigger, overview, phase
overview with per-phase summaries and read pointers, prerequisites pointer,
a pointer to the plugin `commands/` directory, JSON contract, typed-error reference, DFM constraint
values, coordinate system, generated script rules, and the key-files quick
reference - and SHALL be under 10 KB.

#### Scenario: Trigger load cost
- **WHEN** the skill triggers for any invocation (`/cq-design:render`, `/cq-design:build`,
  `/cq-design:plan`, or a full design request)
- **THEN** the initially loaded SKILL.md is under 10 KB and contains no phase-local
  step-by-step procedures

---

### Requirement: Phase detail lives in per-phase files
The skill SHALL provide `skill/phase0_sourcing.md`, `skill/phase1_requirements.md`,
`skill/phase2_planning.md`, `skill/phase3_build.md`, and `skill/phase4_deliver.md`,
carrying the full moved content of their SKILL.md phase sections without loss.
`skill/phase0_sourcing.md` carries the sourcing-triage decision ladder and its
per-rung handling, referencing (not duplicating) the Phase 1 search workflow.

#### Scenario: Content preservation
- **WHEN** the split lands
- **THEN** every instruction removed from SKILL.md's phase sections appears
  verbatim in exactly one `skill/phase*.md` file

#### Scenario: Build-phase detail location
- **WHEN** the part loop, progressive build, orientation loop, or kinematic
  validation walkthrough is needed
- **THEN** it is found in `skill/phase3_build.md`

#### Scenario: Sourcing-triage detail location
- **WHEN** Phase 0 sourcing triage is entered
- **THEN** the decision ladder, license rules, and per-rung handling are found in
  `skill/phase0_sourcing.md`, and SKILL.md's phase overview lists Phase 0 with a
  mandatory read pointer to it

---

### Requirement: Mandatory read at phase entry
Each phase section in core SKILL.md SHALL consist of a short summary plus an
instruction that the corresponding `skill/phase*.md` file MUST be read in full
before executing that phase. Phase summaries SHALL NOT contain step numbers or
commands sufficient to run the phase without the file.

#### Scenario: Entering the build phase
- **WHEN** the pipeline transitions into Phase 3
- **THEN** SKILL.md directs reading `skill/phase3_build.md` in full before any part
  is authored

#### Scenario: Command-scoped invocation skips unrelated phases
- **WHEN** the user invokes `/render`
- **THEN** only the phase files relevant to rendering are read, and Phase 1-3
  procedure files are not loaded

---

### Requirement: Hardware dimension tables are block-gated reference data
Hardware dimension tables SHALL move from SKILL.md to `reference/hardware_dims.md`
and SHALL be read only when a fastener or hardware block appears in the plan's
`blocks_needed`.

#### Scenario: Plan with fastener blocks
- **WHEN** a part's `blocks_needed` includes a fastener/hardware block
- **THEN** `reference/hardware_dims.md` is read before authoring that part

#### Scenario: Plan without hardware
- **WHEN** no part uses a fastener/hardware block
- **THEN** `reference/hardware_dims.md` is never loaded in the session

---

### Requirement: Phase file paths resolve via SKILL_DIR
All `skill/*.md` and `reference/hardware_dims.md` reads SHALL use SKILL_DIR-relative
paths, consistent with the skill-invocation-path-resolution capability.

#### Scenario: Skill invoked from a foreign working directory
- **WHEN** the shell cwd is outside the skill root
- **THEN** phase files are still found via `$SKILL_DIR/skill/<file>.md`

---

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

---

### Requirement: Prose does not restate a code-enforced contract
A `SKILL.md` or `skill/phase*.md` file SHALL NOT restate the substantive
content of a fact that a JSON Schema, a validator/runner script's typed
output (e.g. error names, hint text, contract keys), an AST lint check, or a
machine-readable inventory file (e.g. `blocks/inventory.json`) already
defines or enforces at run time. Such prose SHALL instead name the enforcing
file and, at most, a short category summary, rather than duplicating the
enumerated values, exact wording, or full field list. This is distinct from
the existing requirement against restating a guaranteed-in-context document
read: this requirement applies even when the enforcing file is not read into
context during the phase, because the enforcing file -- not the doc -- is
the source of truth and the one that changes first when behavior changes.

#### Scenario: Typed error table restated in prose
- **WHEN** a phase file or SKILL.md lists typed error names together with
  their exact remediation hint text
- **THEN** the list is replaced with a short category summary plus a pointer
  to the script (e.g. `run_cadquery_model.py`'s `errors[].hint`,
  `cq_verify.py`) that generates the names and hints, so a new or renamed
  error type does not require a matching doc edit to stay accurate

#### Scenario: Lint-check list restated in prose
- **WHEN** a phase file spells out the AST lint checks a lint script
  implements (e.g. by describing each check in prose)
- **THEN** the phase file instead points to the single authoritative list of
  check names (in `reference/scripts.md`, itself describing
  `script_lint.py`) rather than carrying its own restatement

#### Scenario: Inventory data restated in prose
- **WHEN** a phase file tabulates block names, uses, or parameters that a
  machine-readable inventory file (`blocks/inventory.json`) already carries
- **THEN** the table is removed and only the procedural instruction to
  consult the inventory file remains, unless the phase file's row carries
  procedural guidance absent from the inventory file itself

#### Scenario: A schema-owned field is described only by name
- **WHEN** a phase file or SKILL.md needs to mention a JSON contract field
  whose shape (subfields, enum values, aggregation behavior) is defined by
  a runner script or JSON Schema
- **THEN** the doc names the field and the file that defines its shape,
  and does not reproduce the field's internal structure

---

### Requirement: Phase-file prose does not restate itself
A `skill/phase*.md` file SHALL NOT state the same substantive rule more than
once within its own body. Where a later section needs the reader to recall a
rule already stated earlier in the same file, it SHALL reference the earlier
statement by section name rather than repeating the rule's content. This is
distinct from the existing requirements against restating a
guaranteed-in-context read or a code-enforced contract: those cover content
whose source of truth lives outside the phase file; this one covers a phase
file duplicating its own text.

#### Scenario: A rule stated in one section is needed again in a later section
- **WHEN** a phase file's later section (e.g. an approval or exit-checkpoint
  step) depends on a constraint already stated in full earlier in the same
  file (e.g. in an "Ask vs. assume" or eligibility section)
- **THEN** the later section names the earlier section instead of restating
  the constraint's full wording

#### Scenario: Two adjacent sentences make the same point
- **WHEN** a section's opening states a rule and the very next sentence
  restates the same rule in different words with no new information
- **THEN** the section keeps a single statement of the rule

---

### Requirement: SKILL.md body does not restate frontmatter-owned trigger content
SKILL.md's body SHALL NOT restate, summarize, or gesture at the natural-language
trigger phrases carried by the frontmatter `description` field. The frontmatter
`description` is the sole source of truth the dispatcher matches against to decide
whether the skill triggers; the body is only loaded into context after that decision
has already been made, so any body text referring to "natural-language triggers" or
similar cannot influence triggering and only duplicates content that lives in the
frontmatter.

#### Scenario: Command table row referencing natural-language triggering
- **WHEN** SKILL.md's command-reference table lists the `/cq-design` entry point
- **THEN** the row names only the slash command itself, with no phrase pointing back
  to natural-language trigger phrases already enumerated in the frontmatter
  `description`
