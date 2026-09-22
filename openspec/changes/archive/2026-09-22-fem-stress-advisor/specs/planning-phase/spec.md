## MODIFIED Requirements

### Requirement: Build plan carries a per-part load determined by the planner

The build plan SHALL allow a part to declare a `load`: the principal load direction (and
optional `type`) in the part's own authored frame, used to drive print-orientation strength
scoring. The planning phase SHALL determine and declare the principal load for every part
whose print orientation depends on strength -- naming the real load path rather than leaving
it to be guessed downstream -- and SHALL ask the user when the load path is genuinely unclear
rather than omitting the field. A flat cover, lid, or panel that carries no structural
tension/bending/shear load SHALL be declared with `load.type: "compression"` (orientation-
neutral) so it is not tipped onto its edge. Plan validation SHALL accept the field when
present (a direction in the authored frame) and SHALL still accept parts that omit it. When a
part declares `load`, the planning summary SHALL surface it. When a part omits `load`, the
downstream strength scoring SHALL be orientation-neutral (no load axis is inferred from
geometry); an omitted load is a neutral default, never a fabricated bending direction.

The `load` MAY additionally carry a solvable load case: `magnitude_n` (the force in
newtons), `applied_at` (one `interfaces[].name` where the load enters the part),
`applied_dir` (an optional direction override for that interface), and `grounded_at` (a
list of `interfaces[].name` that hold the part). All are optional and their absence SHALL
NOT affect any existing behaviour. Plan validation SHALL accept a part that declares none,
all, or any subset of them, and SHALL check only that a declared `applied_at` or
`grounded_at` names an interface that exists on that part.

`applied_dir` SHALL override `load.dir` for the applied traction only, for a load that
enters its interface at an angle to the part's principal load direction. When omitted the
traction direction SHALL be `load.dir`. `applied_dir` SHALL NOT affect print-orientation
strength scoring, the rationale trigger, or anything else that reads `load.dir` -- the
principal direction remains the part-level one.

The planner SHALL NOT state a `magnitude_n` it invented. The value SHALL be derived from a
mass the research phase actually looked up, as
`magnitude_n = mass_g * 9.81 / 1000 * safety_factor`, with the safety factor taken from
`reference/Engineering Design Rules.md`. A part whose load has no researched mass behind it
SHALL declare no `magnitude_n`, and the planner SHALL add the mass to the research lookup
targets rather than estimating it.

#### Scenario: Plan with a declared load validates
- **WHEN** a build plan declares a `load` direction on a part
- **THEN** plan validation accepts it and the value is available to the orientation
  optimizer

#### Scenario: Plan without a load is still valid and scores neutral
- **WHEN** a part omits the `load` field
- **THEN** plan validation accepts the part and downstream strength scoring is
  orientation-neutral for it (no geometry-inferred load axis is fabricated)

#### Scenario: Load case declared alongside the direction
- **WHEN** a part's `load` declares `magnitude_n`, `applied_at`, and `grounded_at` naming
  interfaces that exist on that part
- **THEN** plan validation accepts it and the load case is available to the FEM advisor

#### Scenario: Load enters at an angle to the principal direction
- **WHEN** a part declares `load.dir` of `[0, 0, -1]` and `applied_dir` of `[0, -0.5, -1]`
  on its `applied_at` interface
- **THEN** the FEM advisor applies the traction along `applied_dir`, while the orientation
  optimizer and the rationale trigger still read `load.dir`

#### Scenario: Direction without a load case is unchanged
- **WHEN** a part declares `load.dir` and `load.type` but none of `magnitude_n`,
  `applied_at`, or `grounded_at`
- **THEN** plan validation accepts it and every existing behaviour -- orientation scoring,
  rationale triggering, summary rendering -- is identical to before this capability

#### Scenario: Anchor names a non-existent interface
- **WHEN** `applied_at` names a string that matches no `interfaces[].name` on that part
- **THEN** plan validation reports it as a finding

#### Scenario: No researched mass means no magnitude
- **WHEN** a part carries a load whose mass was never researched
- **THEN** the planner declares `dir` and `type` without `magnitude_n`, and adds the mass to
  the research lookup targets rather than estimating a force

### Requirement: Plan is shown to user for review before loop starts
The system SHALL display the generated `BUILD_PLAN.json` to the user and pause for confirmation or edits before the orchestration loop begins.

A dimension-validation checkpoint SHALL occur before `BUILD_PLAN.json` is generated (see `dimension-validation-checkpoint` spec). Confirmation of that checkpoint does not substitute for review of the final plan -- both pauses are required.

The system SHALL write `BUILD_PLAN.json` to disk after validation passes, then display a human-readable Markdown summary of the plan to the user and pause for confirmation or edits before the orchestration loop begins. The path written to disk SHALL be shown alongside the summary. The raw JSON SHALL NOT be displayed in the chat; only the summary is shown.

The summary SHALL include the following sections:
- Printer, material, and nozzle diameter
- Parts table: ID, description, W x D x H dimensions, print orientation, and blocks_needed
- Interfaces table: one row per interface entry across all parts, showing part ID, type, connector (if any), wall, and position
- Constraints: wall_min_mm, overhang_max_deg, dimension_tolerance_mm
- Load cases table, rendered only when at least one part declares `magnitude_n`: one row
  per such part showing part ID, the source mass and its unit, the safety factor applied,
  the resulting `magnitude_n`, the `applied_at` interface (with `applied_dir` when it
  overrides `load.dir`), and the `grounded_at` interfaces

The load-cases table exists because every downstream stress number scales linearly with
`magnitude_n`, and that value is a derivation from a researched mass rather than something
the user stated. The summary SHALL therefore show the mass and the factor, not the force
alone, so the derivation is checkable at the same checkpoint that approves the plan. A part
declaring `load` without `magnitude_n` SHALL NOT appear in this table.

The summary SHALL NOT include an assembly-strategy section.

#### Scenario: User approves plan
- **WHEN** user confirms the plan without changes
- **THEN** orchestrator proceeds to Phase 3 using the file already written to disk

#### Scenario: User edits plan
- **WHEN** user modifies a dimension in the plan file on disk
- **THEN** orchestrator re-validates the edited file from disk and then proceeds

#### Scenario: Dimension checkpoint precedes plan generation
- **WHEN** the model involves any real-world product requiring dimension research
- **THEN** the dimension-validation table is presented and approved BEFORE `BUILD_PLAN.json` is generated, and the final plan review occurs AFTER generation

#### Scenario: Plan written before display
- **WHEN** the planning phase produces a valid plan
- **THEN** `BUILD_PLAN.json` exists on disk before the user is shown the summary

#### Scenario: Summary shows all parts
- **WHEN** the plan contains three parts
- **THEN** the summary table contains exactly three rows, one per part, with correct IDs and dimensions

#### Scenario: No raw JSON in chat
- **WHEN** the plan is displayed for approval
- **THEN** the chat message contains no fenced JSON code block -- only the Markdown summary and the file path

#### Scenario: Summary shows no assembly strategy
- **WHEN** the plan has more than one part
- **THEN** the summary contains no assembly-strategy section; multi-part relationships are conveyed by the parts table and their placements

#### Scenario: Derived load magnitude is shown with its derivation
- **WHEN** a part declares `magnitude_n` derived from a researched mass
- **THEN** the summary's load-cases table shows that part's source mass, the safety factor,
  the resulting force in newtons, and the applied/grounded interfaces, so the user can
  check the derivation before approving

#### Scenario: User corrects the mass at the checkpoint
- **WHEN** the user states a different mass at the plan-review pause
- **THEN** `magnitude_n` is re-derived from the corrected mass, the plan is re-validated
  from disk, and the corrected mass is recorded in `request_log` as a user correction

#### Scenario: No load cases omits the table
- **WHEN** no part declares `magnitude_n`
- **THEN** the summary contains no load-cases table and is otherwise unchanged
