## MODIFIED Requirements

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
the assembled-frame transform that carries the authored geometry into the part's stated
`pose_intent` (see `assembled-pose-handback`).

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

#### Scenario: Pin-hinge routing is stated as a contract rule

- **WHEN** `prompts/part.md` states the rule for building a print-in-place revolute
  knuckle hinge
- **THEN** it directs the author to `blocks.joints.pin_hinge` as an explicit directive,
  not softened into goal prose, and states the `verify_seated` fallback for the
  geometry-incompatible case
