## Why

`reference/scripts.md` indexes ~30 scripts of which any one part uses a handful, and
the doc/permission surface duplicates itself across scripts that share one shape:
append-or-search one file under `build/` (`journal.py`, `telemetry.py`,
`request_log_search.py`), or read/validate/write `BUILD_PLAN.json`
(`plan_validate.py`, `plan_summary.py`, `import_params.py`). Each earns its own
`skill_permissions.json` entry (Bash + PowerShell), its own line in
`reference/scripts.md`, and its own mention wherever the pipeline calls it.
Consolidating each cluster behind one dispatcher with subcommands -- the pattern
`render_prompt.py` already uses for five prompt kinds -- cuts both without changing
what any script does.

## What Changes

- Add `src/log.py` with subcommands `journal append`, `attempt append`,
  `attempt audit-fail`, `request search`, `request add`, replacing
  `journal.py`, `telemetry.py`, and `request_log_search.py` as the invoked CLI.
  Their functions (`append_line`, `fold_attempts`, `append_attempt_record`, the
  `request_log` search/add helpers) move into `log.py` unchanged and stay
  importable for `render_prompt.py`'s in-process reuse of `telemetry.py`'s
  `audit-fail` derivation (per `attempt-telemetry`'s existing requirement that
  `render_prompt.py` import it rather than reimplement it).
- Add `src/plan.py` with subcommands `validate`, `summary`, `import-params`,
  replacing `plan_validate.py`, `plan_summary.py`, and `import_params.py` as the
  invoked CLI. `plan_validate.py`'s validator functions (used in-process by
  `quality_gate.py`'s plan-validation stage and by `subagent-orchestration`'s
  planner self-check) move into `plan.py` unchanged.
- **BREAKING**: the six replaced scripts are deleted. Every invocation --
  in `skill/*.md`, `prompts/*.md`, `SKILL.md`, `reference/scripts.md`,
  `src/skill_permissions.json`, `src/render_prompt.py`, `src/quality_gate.py`,
  `tests/*.py`, and the ~15 spec files below that name a literal invocation --
  is updated to the new subcommand form. No validation rule, telemetry field,
  or journal format changes; this is an entry-point rename, not a behavior change.
- `reference/scripts.md` gains two entries (`log.py`, `plan.py`) replacing six.
- `src/skill_permissions.json` gains two allow-pattern pairs (Bash + PowerShell)
  replacing six pairs.

## Capabilities

### New Capabilities
(none -- this reorganizes existing capabilities' entry points, it does not add
requirements)

### Modified Capabilities
- `build-journal`: the append command is `log.py journal append <journal> <milestone> <text>`
  instead of `journal.py append ...`.
- `attempt-telemetry`: the record/fold/audit-fail commands are `log.py attempt append ...`
  and `log.py attempt audit-fail ...` instead of `telemetry.py append` / `telemetry.py audit-fail`;
  `fold_attempts` is imported from `log.py`.
- `request-log-search`: the search/add commands are `log.py request search <plan> ...`
  and `log.py request add <plan> ...` instead of `request_log_search.py search` / `add`.
- `gate-plan-validation`: the quality gate imports the plan validator from `plan.py`
  instead of `plan_validate.py`.
- `plan-summary-checkpoint`: the module implementing both requirements is
  `plan.py` instead of `plan_summary.py`.

`parameter-round-trip` is **not** in this list: its requirements describe "the
tool" generically and never name `import_params.py`, so folding it into
`plan.py import-params` changes no requirement text.

## Impact

- **~15 other spec files mention a replaced script's filename inside an
  example invocation or cross-reference** (`skill-invocation-path-resolution`,
  `subagent-orchestration`, `visual-self-review`, `request-relative-acceptance`,
  `eval-harness`, `preview-cross-sections`, `coordinate-frame`,
  `engineering-rationale`, `joint-mate-entity`, `kinematic-range-validation`,
  `shared-literal-detection`, `dovetail-corner-joint`,
  `fastener-receiving-blocks`, `external-corpus-import`, `planning-phase`,
  `part-authoring-guidance`, `request-log`, `minimal-cutout-search`,
  `assembled-pose-handback`). None of these own the renamed script's
  requirements -- the mention is illustrative, not a definition of behavior --
  so they are **not** listed as Modified Capabilities and get no delta spec.
  They still need the literal string fixed so the spec corpus doesn't read as
  stale; `tasks.md` does this as a direct, non-delta edit to
  `openspec/specs/*/spec.md` (this repo's established pattern for updating a
  script name that spec text merely mentions -- see e.g. the
  `2026-09-16-add-log-commands` change, which updated `reference/scripts.md`
  the same way without treating it as a requirement change).
- Code: `src/journal.py`, `src/telemetry.py`, `src/request_log_search.py`,
  `src/plan_validate.py`, `src/plan_summary.py`, `src/import_params.py` deleted;
  `src/log.py`, `src/plan.py` added. `src/quality_gate.py` and `src/render_prompt.py`
  update their imports.
- Tests: `tests/test_journal.py`, `tests/test_telemetry.py`,
  `tests/test_request_log_search.py` merge into `tests/test_log.py`;
  `tests/test_plan_validate.py`, `tests/test_plan_summary.py`,
  `tests/test_import_params.py` merge into `tests/test_plan.py`.
- Docs: `reference/scripts.md`, `SKILL.md`, `skill/*.md`, `prompts/*.md`,
  `CLAUDE.md`'s script index.
- Permissions: `src/skill_permissions.json` (both Bash and PowerShell allow lists).
- No change to `BUILD_PLAN.json` schema, journal/attempts.jsonl file formats, or
  any validation rule's pass/fail behavior.
