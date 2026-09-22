# Engineering Rationale

## Purpose

Defines requirements for the engineering-rationale record a load-bearing part must
carry: a load path, worst-case stress location, and a computed strain/stress-vs-allowable
check, or a one-line "no load-bearing features" statement otherwise. The record lives in
the part's `BUILD_PLAN.json` entry, not in the generated script. Applicability is derived
from the plan via a single trigger set defined in `src/plan_validate.py`, the obligation
persists across retries, plan validation checks the record against the trigger, and the
regeneration prompt carries it forward.

## Requirements

### Requirement: Load-bearing parts carry an engineering-rationale record

The engineering rationale SHALL be recorded in `BUILD_PLAN.json` as the part entry's
`engineering_rationale` field, not as a comment section in the generated part script.

For a load-bearing part the field SHALL be an object stating (a) `load_path`, (b)
`worst_case_stress`, and (c) `check`: at least one computed check, a formula evaluated
with the part script's own parameter values, compared against a stated material allowable
(e.g. "strain = 1.5*t*d/L^2 = 1.0% <= 2.0% allowable (PETG)"). The `check` SHALL reference
the script's parameter names, not free-standing constants. A part with no load-bearing
features SHALL instead carry the string form `no load-bearing features (<short reason>)`.

Where `src/fem_check.py` produced an `ok` result for the part, the `check` SHALL cite that
result -- its failure index and the peak location -- instead of a closed-form derivation,
and `worst_case_stress` SHALL name the location the solve reported rather than the location
the author assumed. Where no FEM result exists (no declared load case, a skipped run, or a
part whose geometry the closed forms in `reference/Engineering Design Rules.md` genuinely
fit, such as a cantilever snap arm), the closed-form derivation remains the required form.
The field stays a string in both cases; no schema form is added.

`prompts/part.md` SHALL instruct the author to write this field into the part's plan entry
after authoring the script, and SHALL NOT ask for an `ENGINEERING RATIONALE` comment block
in the script.

#### Scenario: Snap-fit lid part

- **WHEN** a part whose plan entry uses `snap_hook_clip` is authored
- **THEN** its `BUILD_PLAN.json` entry carries an `engineering_rationale` object stating
  the load path, the worst-case stress location, and a computed strain-vs-allowable check
  using the script's arm-thickness/deflection/length parameter names

#### Scenario: Cosmetic part

- **WHEN** a part with no declared `load` and no load-bearing blocks is authored
- **THEN** its plan entry's `engineering_rationale` is the string form stating no
  load-bearing features, with no invented load calculation

#### Scenario: No rationale block in the script

- **WHEN** any part script is authored, by either the from-scratch or the
  archetype-template path
- **THEN** the script contains no `ENGINEERING RATIONALE` comment section, and the
  rationale for that part is found in exactly one place: its plan entry

#### Scenario: Rationale survives both render modes

- **WHEN** the part prompt is rendered inline or for a cold context (subagent or
  `claude -p`)
- **THEN** the write-back requirement appears in the rendered prompt in both modes, and
  the plan edit is separate from the script the prompt returns (the "output only the
  Python script" contract is unchanged)

#### Scenario: Part with a FEM result cites the solve

- **WHEN** a bracket with a declared load case was analysed and `fem_check.py` returned an
  `ok` result
- **THEN** its `check` cites the reported failure index and peak location rather than a
  closed-form beam formula, and `worst_case_stress` names the solved peak location

#### Scenario: Part without a FEM result keeps the closed form

- **WHEN** a load-bearing part declares no solvable load case, or its FEM run was skipped
- **THEN** its `check` is the closed-form derivation against a stated allowable, exactly as
  required without this capability

### Requirement: Applicability is determined from the plan

Whether a part takes the object form or the string form SHALL be determined from its
`BUILD_PLAN.json` entry: the object form applies when the entry declares a `load`, or when
its `blocks_needed` or `archetype` is in the load-bearing set (snap hooks, clips, hooks,
brackets, screw bosses, pcb standoffs, living hinge, dovetail joints). The trigger set
SHALL be defined once, machine-readably, in `src/plan_validate.py`; `prompts/part.md` and
`skill/phase3_build.md` SHALL point at it rather than restating it.

#### Scenario: Plan declares a load

- **WHEN** a part's plan entry declares `load` (any type)
- **THEN** the object form is required regardless of which blocks it uses

#### Scenario: No trigger matches

- **WHEN** a part declares no `load` and none of its blocks or archetype are in the
  load-bearing set
- **THEN** the string form is required and suffices

#### Scenario: Trigger set has one definition

- **WHEN** the load-bearing set is consulted by the part prompt, the Phase 3 skill file,
  or the plan validator
- **THEN** all three resolve to the single list in `src/plan_validate.py`, and no second
  enumeration of the set exists in the prompt or skill files

### Requirement: Retry prompts preserve the rationale obligation

A correction prompt for a failed attempt SHALL NOT waive the rationale requirement. Where
a retry changes a parameter that the part's `engineering_rationale.check` references, the
retry SHALL re-evaluate that check with the new value and write the updated field back to
`BUILD_PLAN.json` in the same round as the script fix.

#### Scenario: Parameter changed on retry

- **WHEN** a retry changes a parameter that appears in the rationale's computed check
- **THEN** the part's `engineering_rationale.check` in `BUILD_PLAN.json` is re-evaluated
  with the new value, so no stale number outlives the script it claims to check

### Requirement: Plan validation checks rationale form against the trigger

`src/plan_validate.py` SHALL check every part's `engineering_rationale` against the
load-bearing trigger: a triggered part carrying the string form, an untriggered part
carrying neither form, and a missing field SHALL each be a finding. Following the existing
deferred-advisory pattern, the findings SHALL be advisory on a run without
`--require-rationale` -- the Phase 2 run, where no part is authored yet -- and errors that
exit non-zero under `--require-rationale`, which the Phase 3 pre-export run passes.

#### Scenario: Phase 2 plan has no rationales yet

- **WHEN** `plan_validate.py` runs on a freshly planned `BUILD_PLAN.json` with no
  `engineering_rationale` on any part
- **THEN** it reports the missing rationales as advisory findings and exits 0

#### Scenario: Pre-export run blocks a missing rationale

- **WHEN** the Phase 3 pre-export run passes `--require-rationale` and a part authored in
  this session carries no `engineering_rationale`
- **THEN** validation fails, exits non-zero, and the export is blocked

#### Scenario: Load-bearing part fobbed off with the string form

- **WHEN** a part declares `load` and its `engineering_rationale` is
  `"no load-bearing features (flat plate)"`
- **THEN** validation reports that the part's declared load requires the object form

### Requirement: The regeneration prompt carries the rationale

`src/regen_prompt.py` SHALL render each part's `engineering_rationale` into
`REGENERATE.md`, so a fresh session receives the load reasoning behind the dimensions
rather than the dimensions alone.

#### Scenario: Load-bearing part in the regeneration prompt

- **WHEN** `REGENERATE.md` is generated for a model with a load-bearing bracket
- **THEN** the bracket's load path, worst-case stress location, and computed check appear
  in the rendered prompt
