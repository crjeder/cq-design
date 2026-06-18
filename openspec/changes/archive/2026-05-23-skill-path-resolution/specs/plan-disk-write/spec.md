## MODIFIED Requirements

### Requirement: Validated plan is written to disk before user review
After `plan_validate.py` passes, the skill SHALL write the plan JSON to `BUILD_PLAN.json` in the caller's working directory (the directory from which the skill was invoked). The write SHALL occur before displaying the plan to the user and before asking for approval.

The skill SHALL report the absolute path of the file written alongside the JSON display, so the user can confirm the file's location. Using a relative path is insufficient -- the absolute path MUST be shown so the user can verify artefacts landed in their project directory, not the skill root.

#### Scenario: Successful write on first run
- **WHEN** the planning phase produces a valid plan and no `BUILD_PLAN.json` exists in the caller's working directory
- **THEN** the skill writes `BUILD_PLAN.json` to the caller's working directory and confirms the absolute path to the user

#### Scenario: Overwrite on repeat run
- **WHEN** a `BUILD_PLAN.json` already exists in the caller's working directory and the skill produces a new valid plan
- **THEN** the skill overwrites the existing file without prompting, and confirms the absolute path to the user

#### Scenario: Write failure due to permissions
- **WHEN** the caller's working directory is not writable
- **THEN** the skill reports the write error and asks the user to confirm or change the working directory before continuing

#### Scenario: Plan not written to skill root
- **WHEN** the skill is invoked from `/home/user/myproject` and the skill root is `/opt/skills/cq-design`
- **THEN** `BUILD_PLAN.json` is created at `/home/user/myproject/BUILD_PLAN.json`, not at `/opt/skills/cq-design/BUILD_PLAN.json`
