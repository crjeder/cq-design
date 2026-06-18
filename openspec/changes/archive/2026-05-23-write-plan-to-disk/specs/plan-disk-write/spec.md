# Plan Disk Write

## Purpose

Defines requirements for persisting the validated `BUILD_PLAN.json` to the filesystem during Phase 2 of the `cq-design` skill.

## ADDED Requirements

### Requirement: Validated plan is written to disk before user review

After `plan_validate.py` passes, the skill SHALL write the plan JSON to `BUILD_PLAN.json` in the current working directory. The write SHALL occur before displaying the plan to the user and before asking for approval.

The skill SHALL report the absolute or relative path of the file written alongside the JSON display, so the user can confirm the file's location.

#### Scenario: Successful write on first run

- **WHEN** the planning phase produces a valid plan and no `BUILD_PLAN.json` exists in the working directory
- **THEN** the skill writes `BUILD_PLAN.json` to the working directory and confirms the path to the user

#### Scenario: Overwrite on repeat run

- **WHEN** a `BUILD_PLAN.json` already exists in the working directory and the skill produces a new valid plan
- **THEN** the skill overwrites the existing file without prompting, and confirms the path to the user

#### Scenario: Write failure due to permissions

- **WHEN** the working directory is not writable
- **THEN** the skill reports the write error and asks the user to confirm or change the working directory before continuing
