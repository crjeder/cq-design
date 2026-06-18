## MODIFIED Requirements

### Requirement: Orchestrator reads BUILD_PLAN and drives one focused LLM call per part
The system SHALL provide `orchestrate.py` that reads a validated `BUILD_PLAN.json`, iterates over `parts` in order, and for each part invokes `claude -p <rendered_prompt_file>` as a subprocess to generate the part's CadQuery code.

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

### Requirement: Orchestrator build log is written to the caller's cwd
The orchestrator SHALL write `build_log.json` to the caller's cwd (the directory from which the orchestrator was invoked), alongside `BUILD_PLAN.json`. The log SHALL be written incrementally (one entry per part as it completes), not only at the end.

#### Scenario: Partial build failure
- **WHEN** the build is aborted mid-way through part 2 of 3
- **THEN** `build_log.json` in the caller's cwd contains a complete entry for part 1 and a partial entry for part 2 with its error history

#### Scenario: Build log location when invoked remotely
- **WHEN** the orchestrator is invoked from `/home/user/myproject`
- **THEN** `build_log.json` is written to `/home/user/myproject/build_log.json`
