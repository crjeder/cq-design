## MODIFIED Requirements

### Requirement: Contract rules stay enumerated and machine-checkable

A rule in `prompts/part.md` SHALL remain in enumerated, imperative form when it is a
contract the pipeline consumes or enforces mechanically. The contract set is: the flat
`from blocks import <function>` import form; binding the final geometry to a top-level
`result` (a `Workplane`, or a dict keyed by declared union ids for a multi-union part);
defining dimensions in a PARAMETERS block rather than as magic numbers in the geometry;
not calling `cq.exporters.export()`; not emitting OpenSCAD; not writing round-by-round
changelog narrative in comments; placing `cq_verify` guards at the documented
risk points; and reporting the assembled-frame transform that carries the authored
geometry into the part's stated `pose_intent` (see `assembled-pose-handback`).

#### Scenario: Lint-enforced rules are stated as rules

- **WHEN** a rule in `prompts/part.md` corresponds to a finding type `src/script_lint.py`
  can detect (`submodule_import`, `missing_result`, `magic_number`, `direct_export`,
  `unguarded_boolean`, `unanchored_feature`)
- **THEN** that rule is stated as an explicit directive, not softened into goal prose

#### Scenario: The pose handback is stated as a contract rule

- **WHEN** `prompts/part.md` states the author's obligation to report its assembled-frame
  transform
- **THEN** it appears in the enumerated contract-rule list, not as goal prose, because
  the pre-export `plan_validate` run and the model export both consume its result

## ADDED Requirements

### Requirement: The authoring frame is the author's choice

`prompts/part.md` SHALL state that the author chooses the frame in which it builds the
part, and SHALL NOT prescribe an authoring frame or require the author to match a frame
assumed elsewhere in the plan. Guidance that recommends an authoring frame for a class of
part (for example, authoring a printable foundation with its physical bottom at Z=0)
SHALL be stated as a recommendation the author may follow or depart from, and never as a
precondition of the part's placement being correct.

#### Scenario: Author departs from a recommended frame
- **WHEN** the author builds a part in a frame other than one the guidance recommends
- **THEN** the part is not incorrect on that account; the author reports the transform
  matching the frame it actually used

#### Scenario: Guidance does not pin the frame to the plan
- **WHEN** `prompts/part.md` discusses authoring frames
- **THEN** it does not instruct the author to adopt a frame the plan assumed, because the
  plan no longer assumes one
