## ADDED Requirements

### Requirement: SKILL_DIR is established before any script invocation
The skill SHALL establish a `SKILL_DIR` variable that resolves to the absolute path of the directory containing SKILL.md before any `src/` script is invoked. All subsequent script invocations SHALL reference scripts via `$SKILL_DIR/src/<script>.py`.

#### Scenario: Skill invoked from a different directory
- **WHEN** the user's shell cwd is `/home/user/myproject` and the skill root is `/opt/skills/cq-design`
- **THEN** `SKILL_DIR` resolves to `/opt/skills/cq-design` and all `src/` script paths are absolute

#### Scenario: SKILL_DIR does not contain the expected scripts
- **WHEN** `$SKILL_DIR/src/orchestrate.py` does not exist at invocation time
- **THEN** the skill surfaces a clear error identifying the missing script and the resolved SKILL_DIR value

### Requirement: Generated artefacts are written to the caller's working directory
All files produced by the skill (BUILD_PLAN.json, build/ directory, exported STL/3MF files) SHALL be written relative to the caller's cwd at invocation time. The skill SHALL NOT change the working directory at any point during execution.

#### Scenario: Skill generates BUILD_PLAN.json
- **WHEN** the skill completes the planning phase from `/home/user/myproject`
- **THEN** `BUILD_PLAN.json` is written to `/home/user/myproject/BUILD_PLAN.json`, not to the skill root

#### Scenario: Skill generates build outputs
- **WHEN** the orchestrator runs with default `--output-dir build/`
- **THEN** the `build/` directory is created under the caller's cwd, not under the skill root

### Requirement: Script invocations do not assume cwd equals skill root
No SKILL.md shell command SHALL rely on the shell's cwd being the skill root directory. Internal references to `src/`, `prompts/`, and `reference/` MUST be prefixed with `$SKILL_DIR/`.

#### Scenario: Plan validation command
- **WHEN** the skill runs plan validation
- **THEN** the command is `python "$SKILL_DIR/src/plan_validate.py" BUILD_PLAN.json`, not `python src/plan_validate.py BUILD_PLAN.json`

#### Scenario: Orchestrator invocation
- **WHEN** the skill starts the orchestrator
- **THEN** the command is `python "$SKILL_DIR/src/orchestrate.py" --plan BUILD_PLAN.json --output-dir build/ --max-retries 3`
