## ADDED Requirements

### Requirement: Generation fixtures are prompted through the design command

`evals/cadgenbench_run.py` SHALL start the `claude -p` prompt of every generation fixture
(one without `edit_description.txt`) with `/cq-design:design`, followed by the unattended,
fidelity, STEP-delivery and drawing instructions as the command's argument.

#### Scenario: Generation prompt
- **WHEN** the runner builds the prompt for a fixture holding only `input.png` and
  `description.yaml`
- **THEN** the prompt starts with `/cq-design:design ` and contains `input.png`

#### Scenario: Edit prompt unchanged
- **WHEN** the fixture has `edit_description.txt`
- **THEN** the prompt starts with `/cq-design:edit input.step`

### Requirement: Runner audits each fixture's pipeline artifacts

After generation, the runner SHALL write a `pipeline` object for every generation fixture
that has a work directory into that fixture's `sanity.json` entry, creating the entry if no
candidate exists. It SHALL hold `plan` (bool: `BUILD_PLAN.json` exists), `gate_result`
(bool: `pipeline.py status` lists `phase3/gate_result` as done), `gate_passed` (bool: at
least one `build/*.quality_gate.json` exists and every one has `passed: true`), and
`b1_checked` (bool: `approved_b1` from `pipeline.py status` is non-empty). Round copies
(`*.quality_gate.round<n>.json`) SHALL NOT count. The runner SHALL print the number of
generation fixtures with any of these false. The audit SHALL NOT change packaging.

#### Scenario: Plan-less run
- **WHEN** a fixture's work directory has `build/plate.py` but no `BUILD_PLAN.json`
- **THEN** its `pipeline` is `{"plan": false, "gate_result": false, "gate_passed": false,
  "b1_checked": false}` and the summary counts it as bypassed

#### Scenario: Full pipeline
- **WHEN** a work directory has a plan, a valid `gate_result`, a passed gate report and a
  `plan_approved` line with `b1=`
- **THEN** all four fields are `true`

#### Scenario: Round copy ignored
- **WHEN** `block.quality_gate.round1.json` has `passed: false` and `block.quality_gate.json`
  has `passed: true`
- **THEN** `gate_passed` is `true`
