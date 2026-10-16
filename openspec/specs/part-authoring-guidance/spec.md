## Purpose

Governs how `prompts/part.md` (and, for retry behavior, `skill/phase3_build.md`)
expresses authoring guidance to the part-building model: behavioral/craft guidance
as compact goal and constraint prose, contract rules the pipeline mechanically
enforces as enumerated imperative directives, and uppercase modal language
reserved for rules whose violation is actually detectable.

## Requirements

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
changelog narrative in comments; placing `cq_verify` guards at the documented
risk points; building a print-in-place revolute knuckle hinge via `blocks.joints.pin_hinge`
rather than hand-rolling knuckle/riser primitives, unless the part's geometry is
incompatible with `pin_hinge`'s two-leaf shape, in which case a hand-rolled knuckle join
SHALL be declared via `verify_seated` (see `runtime-boolean-verification`); and reporting
the assembly-pose transform that carries the authored geometry into the part's stated
`pose_intent` (see `assembled-pose-handback`).

#### Scenario: Lint-enforced rules are stated as rules

- **WHEN** a rule in `prompts/part.md` corresponds to a finding type `src/script_lint.py`
  can detect (`submodule_import`, `missing_result`, `magic_number`, `direct_export`,
  `unguarded_boolean`, `unanchored_feature`)
- **THEN** that rule is stated as an explicit directive, not softened into goal prose

#### Scenario: The pose handback is stated as a contract rule

- **WHEN** `prompts/part.md` states the author's obligation to report its assembly pose
  transform
- **THEN** it appears in the enumerated contract-rule list, not as goal prose, because
  the pre-export `plan_validate` run and the model export both consume its result

#### Scenario: Pin-hinge routing is stated as a contract rule

- **WHEN** `prompts/part.md` states the rule for building a print-in-place revolute
  knuckle hinge
- **THEN** it directs the author to `blocks.joints.pin_hinge` as an explicit directive,
  not softened into goal prose, and states the `verify_seated` fallback for the
  geometry-incompatible case

### Requirement: The authoring frame is the author's choice

`prompts/part.md` SHALL state that the author chooses the frame in which it builds the
part, and SHALL NOT prescribe an authoring frame or require the author to match a frame
assumed elsewhere in the plan. Guidance that recommends an authoring frame for a class of
part (for example, authoring a printable foundation with its physical bottom at Z=0)
SHALL be stated as a recommendation the author may follow or depart from, and never as a
precondition of the part's placement being correct.

This recommendation SHALL name the case it is meant to resolve: a part whose stated pose
intent places its physical bottom away from Z=0 in the assembly pose (a "floating"
part). For that case, `prompts/part.md` SHALL pair the Z=0-bottom authoring
recommendation with the existing `translate_mm` write-back mechanism (contract rule 6):
author with the physical bottom at script Z=0, then report the offset as
`placement.translate_mm` to land in the stated pose intent. This remains a
recommendation, not a new contract rule -- an author who authors a floating part in a
different frame and reports the matching transform is still not incorrect.

#### Scenario: Author departs from a recommended frame
- **WHEN** the author builds a part in a frame other than one the guidance recommends
- **THEN** the part is not incorrect on that account; the author reports the transform
  matching the frame it actually used

#### Scenario: Guidance does not pin the frame to the plan
- **WHEN** `prompts/part.md` discusses authoring frames
- **THEN** it does not instruct the author to adopt a frame the plan assumed, because the
  plan no longer assumes one

#### Scenario: Floating assembly pose names the paired pattern
- **WHEN** a part's stated pose intent places its physical bottom away from Z=0 in the
  assembly pose
- **THEN** `prompts/part.md` names this case and recommends authoring with the physical
  bottom at script Z=0, reporting the offset as `placement.translate_mm` (contract rule
  6) to reach the stated pose intent, rather than leaving the pairing implicit

### Requirement: Comments carry constraints, not narration

`prompts/part.md` SHALL instruct that a comment in a generated part script exists to
record a constraint, intent, or derivation the code itself cannot show, and SHALL
instruct that comments do not restate what the following line does. The prompt SHALL NOT
instruct the model to produce "commented" code as a generic quality goal.

The construction-plan stage labels are explicitly exempt: they are required content
governed by their own capability, not narration. The engineering rationale is no longer an
exemption, because it is no longer a comment -- it is written to the part's
`engineering_rationale` plan entry (see `engineering-rationale`).

#### Scenario: Generic comment instruction is gone

- **WHEN** `prompts/part.md` is rendered for any part
- **THEN** it contains no instruction to "generate clear, commented code" or equivalent
  generic comment-density directive

#### Scenario: Required blocks are unaffected

- **WHEN** a part script is authored under the comment rule
- **THEN** `verify_stage` labels are still written where the construction-plan rule
  applies, and the part's rationale is present in its plan entry rather than in the script

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
implicate. Where a fix changes a parameter that the part's `engineering_rationale.check`
references, re-evaluating that check and writing it back to `BUILD_PLAN.json` remains
required (governed by `engineering-rationale`).

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
`src/script_lint.py`, by `run_cadquery_model.py`'s typed errors, by `plan.py validate`, by
a check stage, or by reading the produced script against a stated contract. Style and
craft guidance SHALL be written as plain statements.

#### Scenario: Contract keeps its modal

- **WHEN** the rule states that the `engineering_rationale.check` must reference the
  script's own parameter names
- **THEN** it keeps its modal form, because a check written with free-standing constants
  is detectable by reading the plan entry against the script

#### Scenario: Guidance drops its modal

- **WHEN** a statement in `prompts/part.md` expresses a preference with no detectable
  violation
- **THEN** it is written as a plain declarative sentence with no uppercase modal
