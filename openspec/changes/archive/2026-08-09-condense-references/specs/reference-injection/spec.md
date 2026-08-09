## ADDED Requirements

### Requirement: Injected CadQuery references carry only non-recallable content

`reference/CadQuery Pattern Reference.md` and `reference/CadQuery Anti-Patterns.md`
SHALL contain only material a competent CadQuery author cannot reliably recall:
exact API signatures and argument semantics, selector-string vocabulary, OCC/BRep
failure signatures and their causes, numeric tables, and project-specific contracts
(block imports, `result` conventions, `cq_verify` usage). They SHALL NOT contain
prose tutorials, restatements of general Python or CAD fundamentals, or worked
examples whose idiom an archetype template in `templates/` already demonstrates.
Each document SHALL be at most 65% of its pre-change byte size.

#### Scenario: Tutorial prose is removed

- **WHEN** a section explains a general concept without naming an API signature, a
  failure signature, a numeric value, or a project contract
- **THEN** that section is absent from the condensed document

#### Scenario: Gotchas and tables are retained

- **WHEN** a section documents an exact API gotcha, an OCC error signature, or a
  numeric table
- **THEN** that section is retained in the condensed document

#### Scenario: Size target met

- **WHEN** the condensed documents are measured
- **THEN** each is at most 65% of its pre-change byte size

---

### Requirement: Reference cuts are backed by attempt-history evidence

A section removal SHALL be justified by evidence, not preference. Before removal,
the archived attempt telemetry (`build/attempts.jsonl` across `evals/runs/*`) SHALL
be surveyed for error types the section addresses. A section addressing an error
type observed in that history SHALL be retained (condensed, not deleted). The
evidence survey and the retain/cut decision per section SHALL be recorded in the
change's design document.

#### Scenario: Section maps to an observed error type

- **WHEN** a candidate section addresses an error type present in the archived
  attempt history
- **THEN** the section is retained in condensed form rather than removed

#### Scenario: Section maps to no observed error and no non-recallable content

- **WHEN** a candidate section addresses no observed error type and contains no
  signature, failure signature, table, or project contract
- **THEN** the section is removed

---

### Requirement: Condensation is validated by an eval sweep before acceptance

The condensed references SHALL be accepted only after a full eval sweep
(`evals/run_evals.py --generate` over the canonical corpus) whose first-shot rate
and attempts-to-pass are no worse than the preceding archived run, and whose mean
cold-render `prompt_chars` is measurably lower than the `c2-prompt-chars` run. A
sweep failing the first condition SHALL cause the condensation to be reverted or
narrowed, not accepted with a caveat.

#### Scenario: Sweep holds quality and reduces prompt size

- **WHEN** the post-condensation sweep holds first-shot rate and attempts-to-pass
  and shows lower mean cold-render `prompt_chars`
- **THEN** the condensation is accepted and the run dir plus scorecard are archived
  under `evals/runs/`

#### Scenario: Sweep regresses quality

- **WHEN** the post-condensation sweep shows a lower first-shot rate or higher
  attempts-to-pass than the preceding run
- **THEN** the condensation is reverted or narrowed and re-measured

---

### Requirement: Cited section names remain resolvable after condensation

Inline renders cite reference sections by name. Any section name referenced from
`prompts/*.md`, `skill/*.md`, or `SKILL.md` SHALL still exist in the condensed
documents, or the referencing text SHALL be updated in the same change.

#### Scenario: A renamed or removed section is still cited

- **WHEN** condensation removes or renames a section named elsewhere in the skill
- **THEN** the citing text is updated in the same change so no citation points at a
  missing section
