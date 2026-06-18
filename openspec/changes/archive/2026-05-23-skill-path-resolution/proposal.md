## Why

When the skill is invoked from a directory other than the skill root, script references like `src/orchestrate.py` and `src/plan_validate.py` resolve against the caller's working directory and fail. Simultaneously, output files (`BUILD_PLAN.json`, `build/`) land in the skill directory instead of where the user expects them -- the directory they called the skill from.

## What Changes

- All internal script paths in SKILL.md (`src/orchestrate.py`, `src/plan_validate.py`, etc.) must be computed relative to SKILL.md's own location, not the caller's cwd.
- All skill-generated output artefacts (`BUILD_PLAN.json`, `build/`, STL/3MF exports) must be written to the directory from which the user invoked the skill (the caller's cwd), not the skill directory.
- The `src/orchestrate.py` invocation must accept and forward the caller's output directory.
- `src/plan_validate.py` and all other scripts that receive file paths as arguments must not assume any particular cwd.

## Capabilities

### New Capabilities

- `skill-invocation-path-resolution`: Ensure skill scripts are referenced via an absolute path derived from SKILL.md's location, and that all generated artefacts are directed to the caller's working directory.

### Modified Capabilities

- `orchestration-loop`: The orchestrator's `--output-dir` default and `BUILD_PLAN.json` path must reflect the caller's cwd, not the skill root.
- `plan-disk-write`: The plan file write path must be anchored to the caller's cwd.

## Impact

- SKILL.md (phase 1, phase 2, and reference table sections)
- `src/orchestrate.py` (default paths, BUILD_PLAN.json resolution)
- `src/plan_validate.py` (path argument handling)
- Any downstream script that derives output paths from its own `__file__` or cwd assumptions
