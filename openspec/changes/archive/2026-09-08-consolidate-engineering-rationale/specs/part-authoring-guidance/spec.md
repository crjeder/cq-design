## MODIFIED Requirements

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

---

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

---

### Requirement: Modal language is reserved for checkable contracts

Uppercase modal language (MUST, SHALL, NEVER, ALWAYS, CRITICAL) in `prompts/part.md` and
the Phase 3 skill files SHALL be used only for a rule whose violation is detectable -- by
`src/script_lint.py`, by `run_cadquery_model.py`'s typed errors, by `plan_validate.py`, by
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
