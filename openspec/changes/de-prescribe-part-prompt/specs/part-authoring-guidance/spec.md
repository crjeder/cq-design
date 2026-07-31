## ADDED Requirements

### Requirement: Authoring guidance states goals, not enumerated craft steps

`prompts/part.md` SHALL express how the part should be authored as goal and constraint
statements, not as an enumerated list of craft steps. Guidance about code quality
(maintainability, "Design as Code" philosophy, CadQuery best practices, selector use,
build order such as "primary shape first, then details") SHALL be stated once, compactly,
and SHALL NOT be enumerated as numbered directives.

This applies only to behavioral guidance. Contract rules keep their enumerated form
(see "Contract rules stay enumerated and machine-checkable").

#### Scenario: Craft advice is not enumerated

- **WHEN** `prompts/part.md` is rendered for any part in either render mode
- **THEN** the prompt contains no numbered list item directing the model toward
  maintainability, "Design as Code", CadQuery best practices, selector use, or build
  ordering; that guidance appears as prose if it appears at all

#### Scenario: Contract rules survive the collapse

- **WHEN** `prompts/part.md` is rendered for any part
- **THEN** the flat `from blocks import ...` rule, the `result` binding rule, the
  PARAMETERS-section rule, the no-`cq.exporters.export` rule, the no-OpenSCAD rule, and
  the no-changelog-comment rule are each still stated unambiguously

### Requirement: Contract rules stay enumerated and machine-checkable

A rule in `prompts/part.md` SHALL remain in enumerated, imperative form when it is a
contract the pipeline consumes or enforces mechanically. The contract set is: the flat
`from blocks import <function>` import form; binding the final geometry to a top-level
`result` (a `Workplane`, or a dict keyed by declared union ids for a multi-union part);
defining dimensions in a PARAMETERS block rather than as magic numbers in the geometry;
not calling `cq.exporters.export()`; not emitting OpenSCAD; not writing round-by-round
changelog narrative in comments; and placing `cq_verify` guards at the documented
risk points.

#### Scenario: Lint-enforced rules are stated as rules

- **WHEN** a rule in `prompts/part.md` corresponds to a finding type `src/script_lint.py`
  can detect (`submodule_import`, `missing_result`, `magic_number`, `direct_export`,
  `unguarded_boolean`, `unanchored_feature`)
- **THEN** that rule is stated as an explicit directive, not softened into goal prose

### Requirement: Comments carry constraints, not narration

`prompts/part.md` SHALL instruct that a comment in a generated part script exists to
record a constraint, intent, or derivation the code itself cannot show, and SHALL
instruct that comments do not restate what the following line does. The prompt SHALL NOT
instruct the model to produce "commented" code as a generic quality goal.

The ENGINEERING RATIONALE block and the construction-plan stage labels are explicitly
exempt: they are required content governed by their own capabilities, not narration.

#### Scenario: Generic comment instruction is gone

- **WHEN** `prompts/part.md` is rendered for any part
- **THEN** it contains no instruction to "generate clear, commented code" or equivalent
  generic comment-density directive

#### Scenario: Required blocks are unaffected

- **WHEN** a part script is authored under the comment rule
- **THEN** the ENGINEERING RATIONALE section is still present in the form its own
  capability requires, and `verify_stage` labels are still written where the
  construction-plan rule applies

### Requirement: The builder holds the specified scope

`prompts/part.md` SHALL instruct the builder to produce the part at the scope the
specification states: no features, interfaces, guards, or parameters beyond what the part
specification and the required `cq_verify` points call for, and no substitution of a
different structure for the one specified.

#### Scenario: No unrequested features

- **WHEN** a part specification lists two interfaces and declares no fillet or chamfer
- **THEN** the generated script builds those two interfaces and adds no third feature,
  decorative edge treatment, or extra mounting provision on its own initiative

#### Scenario: Guards stay at the documented points

- **WHEN** the builder considers adding a `cq_verify` call
- **THEN** it adds one only where the documented risk points call for it, rather than
  wrapping every boolean in the script

### Requirement: A retry edits what the error names

`prompts/part.md` and `skill/phase3_build.md` SHALL instruct that a retry attempt applies
a targeted fix for the reported error types and hints, and SHALL instruct that a retry
does not restructure, refactor, or rewrite parts of the script the reported error does not
implicate. Where a fix changes a parameter that the ENGINEERING RATIONALE's computed check
references, re-evaluating that check remains required (governed by `engineering-rationale`).

#### Scenario: Targeted fix on a reported error

- **WHEN** attempt 1 reports a single `dimension_mismatch` on the part's height
- **THEN** attempt 2 changes the height parameter and whatever depends on it, and leaves
  the rest of the script's structure intact

#### Scenario: No blind restart

- **WHEN** a retry prompt is rendered for any attempt after the first
- **THEN** it directs a targeted fix and states that the script is not to be rewritten
  from scratch

### Requirement: Modal language is reserved for checkable contracts

Uppercase modal language (MUST, SHALL, NEVER, ALWAYS, CRITICAL) in `prompts/part.md` and
the Phase 3 skill files SHALL be used only for a rule whose violation is detectable -- by
`src/script_lint.py`, by `run_cadquery_model.py`'s typed errors, by a check stage, or by
reading the produced script against a stated contract. Style and craft guidance SHALL be
written as plain statements.

#### Scenario: Contract keeps its modal

- **WHEN** the rule states that the ENGINEERING RATIONALE's computed check must reference
  the script's own parameter names
- **THEN** it keeps its modal form, because a check written with free-standing constants
  is detectable by reading the script

#### Scenario: Guidance drops its modal

- **WHEN** a statement in `prompts/part.md` expresses a preference with no detectable
  violation
- **THEN** it is written as a plain declarative sentence with no uppercase modal
