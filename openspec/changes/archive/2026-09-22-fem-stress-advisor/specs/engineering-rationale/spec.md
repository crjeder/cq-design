## MODIFIED Requirements

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
