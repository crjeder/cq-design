## MODIFIED Requirements

### Requirement: Canonical eval corpus
The repository SHALL contain an `evals/cases/` corpus of approximately 10-15
canonical requests. Each case directory SHALL contain the verbatim user
request (`request.md`), a golden `BUILD_PLAN.json` that passes
`plan_validate.py`, one or more golden meshes under `golden/` in the authored
frame, and a `case.json` with at minimum `tolerance_mm` and the expected part
count.

The corpus SHALL include at least one case whose golden `BUILD_PLAN.json`
declares a `joints` entry (a matched-pair block such as `pin_hinge`) linking
two parts, a `kinematics` entry sweeping that joint's declared range, and a
shared-pivot interface referenced by both parts -- exercising multi-part
mate-chain-derived placement, not independently authored literals.

The corpus SHALL include at least one round-2 correction case: a case
directory containing a `seed/` subdirectory holding a prior round's accepted
`BUILD_PLAN.json` and part script(s), whose `request.md` is phrased as a
correction to that seeded state (not a from-scratch specification), and whose
golden reflects the corrected result.

The corpus SHALL include at least one case whose `request.md` names the same
feature using both a viewing-station phrase (e.g. "visible in the South
view") and a face-normal phrase (e.g. "on the East-facing wall"), such that
conflating the two would place the feature on the opposite side under the
`prompts/planning.md` fixed compass convention (North=+Y, East=+X).

#### Scenario: Case plans are valid
- **WHEN** `plan_validate.py` is run against any case's `BUILD_PLAN.json`
- **THEN** validation passes with no errors

#### Scenario: Case is self-contained
- **WHEN** a case directory is inspected
- **THEN** it contains `request.md`, `BUILD_PLAN.json`, at least one golden
  mesh, and `case.json`

#### Scenario: Joints-and-kinematics case is present
- **WHEN** the corpus is inspected
- **THEN** at least one case's `BUILD_PLAN.json` has a non-empty `joints`
  array, a non-empty `kinematics` array, and two parts that reference a
  common interface fused by that joint

#### Scenario: Round-2 correction case is present
- **WHEN** the corpus is inspected
- **THEN** at least one case directory contains `seed/` with a prior-round
  `BUILD_PLAN.json` and part script, and that case's `request.md` reads as a
  correction to the seeded state

#### Scenario: Compass-wording case is present
- **WHEN** the corpus is inspected
- **THEN** at least one case's `request.md` refers to one feature by both a
  viewing-station phrase and a face-normal phrase for opposite compass
  directions, and its golden mesh places the feature per the fixed convention

### Requirement: Generation captures the result envelope
When `run_evals.py` generates a case (`--generate`), it SHALL invoke `claude -p`
with `--output-format json`, capture the result envelope, and write the case's
`session_id`, `num_turns`, `duration_ms`, `total_cost_usd`, and token `usage`
block to `<case>/cost.json`. A generation that times out or whose output cannot
be parsed SHALL leave `<case>/cost.json` unwritten rather than write a partial or
guessed record.

Before invoking `claude -p`, generation SHALL check the case directory for a
`seed/` subdirectory. When present, its contents SHALL be copied into the
case's working directory first, and the request prompt SHALL be framed as a
correction to that seeded state rather than a from-scratch request. When
`seed/` is absent, generation SHALL behave exactly as before: an empty working
directory and a from-scratch request.

#### Scenario: Envelope written on a successful generation
- **WHEN** a case is generated and `claude -p` returns a JSON result envelope
- **THEN** `<case>/cost.json` exists and contains `total_cost_usd` and the
  `usage` token counts from that envelope

#### Scenario: Timed-out generation writes no cost file
- **WHEN** a case generation times out
- **THEN** `<case>/cost.json` is not created, and scoring falls back to
  `build/cost.json` or the estimate

#### Scenario: Seeded case starts from a prior accepted state
- **WHEN** a case directory contains `seed/` with a `BUILD_PLAN.json` and part
  script, and generation runs with `--generate`
- **THEN** those files exist in the case's working directory before
  `claude -p` is invoked, and the prompt frames `request.md` as a correction

#### Scenario: Unseeded case is unaffected
- **WHEN** a case directory has no `seed/` subdirectory
- **THEN** generation starts in an empty working directory exactly as before
  this change
