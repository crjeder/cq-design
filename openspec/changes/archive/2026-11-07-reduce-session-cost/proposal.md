## Why

A real session (Siebtragerhalter, 2026-11-04) cost about $46 for a one-part model. The input side is 97% cache reads, so cost is roughly calls x context size. Three things inflate it: sub-agents start at 61k tokens because every spawn is `general-purpose` with the full tool list; sourcing, research and both audits run on the inherited Opus; and the main session is a 96-call relay at 84k-198k context. About 30% more was a re-plan caused by a concept mismatch that only surfaced at the profile stub. Details: `TODO.md` "Siebtragerhalter session".

## What Changes

- **Dedicated agent definitions** (`agents/*.md`) for sourcing, research, planner, builder and auditor, each with a minimal `tools:` list and a `model:` (Sonnet for sourcing, research, builder and audit; the planner stays on the strong model). Spawns reference them by name.
- **BREAKING**: drop the "no `.claude/agents/` files, portable with the skill" rule. `install.sh` and `install.ps1` install the agent files too. The installer stays local (copy or `--link`); no external marketplace is required.
- **Model config**: `skill_config.json` `models` gains `sourcing`, `research`, `auditor`; the agent definitions' `model:` is the default and the config overrides it.
- **`parameters.py` becomes the single source of every dimension.** The planner records each dimension (user-given, researched, assumed, and each design allowance such as clearance or gap) there as a commented constant tagged by origin. `BUILD_PLAN.json` params hold expressions over those names, evaluated by `plan.py`; part scripts keep reading `part.param(...)`, which returns the evaluated value. Changing a measurement is then one edit to `parameters.py`.
- **Cheaper parameter changes**: after such an edit, `plan.py validate` reports which parts' resolved params changed; only those parts are rebuilt and re-gated, and the visual audit re-runs only for parts whose resolved params changed.
- **Fewer relay calls**: `plan.py validate` and `write_assembly.py` append their journal line themselves, replacing the separate `log.py journal append` Bash calls.
- **Phase 1 concept sketch**: Phase 1 ends with a simple SVG drawing of the understood concept, approved by the user before planning starts.
- **ASCII art to SVG**: every ASCII-art illustration in shipped prose (`SKILL.md`, `skill/`, `prompts/`, `reference/`, `README.md`) is replaced by an SVG file referenced from the text (`TODO.md` line 70).
- **Prose**: recommend a fresh session after `/cq-design:init`.

## Capabilities

### New Capabilities

- `agent-definitions`: plugin/skill agent files with per-agent `tools:` and `model:`, and the rule that spawns use them.
- `concept-sketch`: the end-of-Phase-1 SVG concept drawing and its approval checkpoint.
- `svg-illustrations`: shipped prose uses SVG files, not ASCII art, for diagrams and layouts.
- `parameters-single-source`: `parameters.py` holds every dimension; plan params are expressions over it; resolved-diff drives partial rebuild.

### Modified Capabilities

- `model-routing-config`: new roles `sourcing`, `research`, `auditor`; agent-file `model:` is the default.
- `plugin-packaging`: installer path now also installs agent files; agents ship with the plugin; no marketplace dependency.
- `skill-install`: allowlist gains `agents/`; installers place agent files where Claude Code loads them and remove them on uninstall.
- `subagent-orchestration`: spawns use the named agent definitions instead of `general-purpose`.
- `build-journal`: milestone lines are written by the completing script, not by a separate Bash call.
- `dimension-validation-checkpoint`: Phase 1 exit also yields the concept sketch.
- `parameters-provenance-check`: gate also flags plan literals that duplicate a `parameters.py` constant.

## Impact

- New: `agents/*.md`, `src/` additions for the expression evaluator and sketch rendering, `skill/` sketch step.
- Changed: `install.sh`, `install.ps1`, `.claude-plugin/plugin.json`, `src/plan.py`, `src/blocks/part.py`, `src/log.py` callers, `src/render_prompt.py`, `src/skill_config.default.json`, `src/build_plan_schema.json` (param value may be a string expression), `skill/phase1_requirements.md`, `skill/phase2_planning.md`, `skill/phase3_build.md`, `prompts/planning.md`, `ARCHITECTURE.md`, `README.md`, `FILES.md`, `reference/scripts.md`.
- Plans written before this change keep literal params; they stay valid (literal or expression).
- Items not in scope: Phase 0/1 research-agent call counts (40 calls for 7 dimensions), the preview defects in `TODO.md` lines 28-29.
