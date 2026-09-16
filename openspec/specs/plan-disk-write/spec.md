# Plan Disk Write

## Purpose

Defines requirements for persisting the validated `BUILD_PLAN.json` to the filesystem during Phase 2 of the `cq-design` skill.

## Requirements

### Requirement: Validated plan is written to disk before user review

The planner agent SHALL write the plan JSON to `BUILD_PLAN.json` in the caller's working
directory (the directory from which the skill was invoked) itself, via Bash, as part of
its own write-validate-retry loop -- not the main session parsing and writing text from
the agent's reply. The write SHALL occur before the main session displays the plan to the
user and before asking for approval.

The main session SHALL report the absolute path of the file the planner agent wrote
alongside the plan summary, so the user can confirm the file's location. Using a relative
path is insufficient -- the absolute path MUST be shown so the user can verify artefacts
landed in their project directory, not the skill root.

#### Scenario: Successful write on first run

- **WHEN** the planning phase produces a valid plan and no `BUILD_PLAN.json` exists in the
  caller's working directory
- **THEN** the planner agent writes `BUILD_PLAN.json` to the caller's working directory
  and the main session confirms the absolute path to the user

#### Scenario: Overwrite on repeat run

- **WHEN** a `BUILD_PLAN.json` already exists in the caller's working directory and the
  planner agent produces a new valid plan
- **THEN** the planner agent overwrites the existing file without prompting, and the main
  session confirms the absolute path to the user

#### Scenario: Write failure due to permissions

- **WHEN** the caller's working directory is not writable
- **THEN** the planner agent reports the write error in its status summary, and the main
  session asks the user to confirm or change the working directory before continuing

#### Scenario: Plan not written to skill root

- **WHEN** the skill is invoked from `/home/user/myproject` and the skill root is
  `/opt/skills/cq-design`
- **THEN** `BUILD_PLAN.json` is created at `/home/user/myproject/BUILD_PLAN.json`, not at
  `/opt/skills/cq-design/BUILD_PLAN.json`
