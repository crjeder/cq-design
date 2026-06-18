# Orchestration Loop

## Purpose

Defines requirements for `orchestrate.py`: the build pipeline entry point that reads `BUILD_PLAN.json`, drives one focused LLM call per part, validates geometry, retries on failure, and produces a structured build log.

## Requirements

### Requirement: Orchestrator reads BUILD_PLAN and drives one focused LLM call per part
The system SHALL provide `orchestrate.py` that reads a validated `BUILD_PLAN.json`, iterates over `parts` in order, and for each part invokes `claude -p <prompt_text>` as a subprocess to generate the part's CadQuery code. The prompt text SHALL be passed directly as the `-p` argument string; no intermediate file is written.

Before the part loop begins, the orchestrator SHALL load reference file content once. The orchestrator SHALL locate reference files using paths relative to its own `__file__` location (i.e., `Path(__file__).parent.parent / "reference" / ...`), not relative to cwd:
- Full contents of `reference/CadQuery Pattern Reference.md`
- Tag-filtered contents of `reference/FDM 3D Print Design Guidelines.md`

These loaded contents SHALL be passed to `_render_part_prompt` and `_render_assembly_prompt` for `{{CQ_REFERENCE}}` and `{{FDM_GUIDELINES}}` substitution.

#### Scenario: Two-part build plan
- **WHEN** `BUILD_PLAN.json` contains parts `["body", "lid"]`
- **THEN** orchestrator generates `body.py` and `lid.py` in sequence, each from a separate `claude -p` invocation

#### Scenario: Claude CLI not available
- **WHEN** `claude --version` returns non-zero at startup
- **THEN** orchestrator exits immediately with a clear error before generating any prompts

#### Scenario: Part prompt includes CQ reference
- **WHEN** orchestrator renders the part prompt for any part
- **THEN** the rendered prompt file contains the full CQ reference at `{{CQ_REFERENCE}}` and relevant FDM guidelines at `{{FDM_GUIDELINES}}`

#### Scenario: Reference files loaded once per build
- **WHEN** a build contains multiple parts
- **THEN** reference file content is loaded from disk once before the part loop, not once per part

#### Scenario: Reference files found regardless of caller cwd
- **WHEN** the orchestrator is invoked from a directory other than the skill root
- **THEN** reference files are still located correctly using paths relative to orchestrate.py's own location

---

### Requirement: Orchestrator validates geometry against plan after each part
After the wrapper runs successfully for a part, the orchestrator SHALL compare the actual bounding box from the wrapper JSON against the plan's `dimensions` for that part. A mismatch exceeding `constraints.dimension_tolerance_mm` (default 1.0 mm) SHALL trigger a structured correction prompt, not a raw retry.

#### Scenario: Dimension within tolerance
- **WHEN** plan specifies `w_mm: 50` and wrapper reports `bbox.x: 50.3` with tolerance 1.0 mm
- **THEN** orchestrator accepts the part and moves to the next

#### Scenario: Dimension outside tolerance
- **WHEN** plan specifies `w_mm: 50` and wrapper reports `bbox.x: 43.1`
- **THEN** orchestrator generates a correction prompt containing the specific axis, actual value, expected value, and delta; does not retry blindly

---

### Requirement: Retry limit is enforced per part
The orchestrator SHALL retry a failing part at most 3 times (configurable via `--max-retries`). On exhausting retries, it SHALL pause and present the user with the last structured error summary and ask whether to skip, abort, or provide manual guidance.

#### Scenario: Part succeeds on second attempt
- **WHEN** the first attempt produces a non-manifold edge error and the second attempt produces a valid mesh
- **THEN** orchestrator records the part as done and continues

#### Scenario: Part fails all retries
- **WHEN** three consecutive attempts all fail with geometry errors
- **THEN** orchestrator prints the last structured error summary and prompts the user for action (skip / abort / provide hint)

---

### Requirement: Assembly phase receives verified actual dimensions, not plan estimates
After all parts complete, the orchestrator SHALL pass actual bounding-box dimensions from the wrapper JSON results (not from `BUILD_PLAN.json`) to the assembly prompt.

#### Scenario: Part came out slightly different than planned
- **WHEN** body was planned at 50 mm wide but actual wrapper output is 49.8 mm
- **THEN** assembly prompt receives 49.8 mm as the body width, not 50 mm

---

### Requirement: Orchestrator build log is written to the caller's cwd
The orchestrator SHALL write `build_log.json` to the caller's cwd (the directory from which the orchestrator was invoked), alongside `BUILD_PLAN.json`. The log SHALL record for each part: attempts, errors per attempt, final status, and actual dimensions. The log SHALL be written incrementally (one entry per part as it completes), not only at the end.

#### Scenario: Partial build failure
- **WHEN** the build is aborted mid-way through part 2 of 3
- **THEN** `build_log.json` in the caller's cwd contains a complete entry for part 1 and a partial entry for part 2 with its error history

#### Scenario: Build log location when invoked remotely
- **WHEN** the orchestrator is invoked from `/home/user/myproject`
- **THEN** `build_log.json` is written to `/home/user/myproject/build_log.json`
