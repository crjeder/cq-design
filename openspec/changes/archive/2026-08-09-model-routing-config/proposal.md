## Why

Model choice is currently hardcoded in prose: `skill/phase3_build.md` says builder
agents use a "mid-tier (Sonnet-class)" model, `ARCHITECTURE.md` says the planner uses
"strong (Fable/Opus)", and `quality_gate.py`'s `_call_claude` invokes bare `claude -p`
with no `--model` at all. Changing the routing means editing skill files. C6 of
`CLAUDE5_CONVERSION_PLAN.md` closes this out with the 5-series names, which also
unblocks the C6/C7 A/B runs (telemetry already records the executing model per attempt).

## What Changes

- New `skill_config.json` in the working directory, seeded from a shipped default like
  `printer_profile.json` is, with a `models` section: `planner`, `part_author`,
  `fix_loop`. Never overwritten if it already exists.
- `skill/phase3_build.md` and `skill/phase2_planning.md` read the model for an agent
  spawn from `skill_config.json` instead of naming a model tier in prose.
- `src/quality_gate.py` `_call_claude` passes `--model` from `skill_config.json`'s
  `models.fix_loop` when the fix loop is explicitly enabled (`--fix`); `inline` means
  no `--model` flag, i.e. whatever model the caller is already running.
- 5-series subagent caution: state in `skill/phase3_build.md` that one part gets at
  most one builder agent and no verification subagents, so an Opus-5 orchestrator's
  readier delegation cannot multiply spawns. The existing routing gate stays the only
  dispatch decision.
- A/B the two authoring configurations (Opus-5 inline vs Sonnet-5 subagent) on the eval
  corpus and record the result in `CLAUDE5_CONVERSION_PLAN.md`.

Not in scope, deliberately: a JSON Schema + validator module for a three-string config
(the printer profile has one because it carries physical constraints consumed by
checks; this is a name lookup), and `.claude/agents/*.md` files — `ARCHITECTURE.md`
already records that the part prompt is self-contained and passed as an Agent-tool
prompt with a per-call model override, so agent files would be a second source of truth
for the same names.

## Capabilities

### New Capabilities
- `model-routing-config`: a working-directory config file that names which model runs
  each LLM role in the pipeline, seeded with defaults, read by the skill phases and by
  the quality gate's opt-in fix loop.

### Modified Capabilities
- `subagent-orchestration`: agent model selection is read from `skill_config.json`
  rather than a prose tier; a per-part cap on builder-agent spawns and a prohibition on
  verification subagents.
- `quality-gate-fix-policy`: the opt-in `--fix` path selects its `claude -p` model from
  the config.

## Impact

- New: `src/skill_config.default.json`, seeding step in `skill/setup.md`.
- Modified: `src/quality_gate.py` (`_call_claude`), `skill/phase2_planning.md`,
  `skill/phase3_build.md`, `ARCHITECTURE.md` (agent roster Model column),
  `CLAUDE.md` (file layout + script table), `CLAUDE5_CONVERSION_PLAN.md` (C6 result),
  `IMPROVEMENT_PLAN.md` (item 15 status).
- No dependency changes. No change to any deterministic check's behavior.
