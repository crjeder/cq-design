## Why

A probe on 2026-11-10 showed that in the Claude desktop app a plugin-loaded agent ignores its `tools:` and `model:` frontmatter. `cq-design:builder` was given all 44 desktop tools and ran on Opus, with a first call of 65.6k input tokens. The same definition run headless got its 6 tools, ran on Sonnet and started at 11.2k. Every builder, auditor, research, sourcing and planner call pays for that gap, and any spawn that omits `model` silently runs on the parent's model (anthropics/claude-code#108748, #89723).

## What Changes

- `/cq-design:init` (`src/init_permissions.py`) copies the shipped `agents/*.md` into the project's `.claude/agents/` as `cq-design-<role>.md`. Re-running init refreshes them. Project-level agents are expected to honour `model:`, as #89723 reports. Whether they also honour `tools:` in the desktop app gets measured first, and that result gates this part.
- Spawn prose names the project agent (`cq-design-<role>`) and falls back to the plugin agent (`cq-design:<role>`) only when the project copy is missing.
- Every spawn passes `model` explicitly. `render_prompt.py` adds an `agent_model` field with the Agent tool alias (`sonnet`, `opus`, `haiku`, `fable`), derived from the configured model id, so the main session never translates ids itself.
- A role with no key in `skill_config.json` falls back to the shipped `skill_config.default.json`, not to the agent file's `model:`. This matches what `log.role_model()` already does. The spec claim that the agent file is the fallback is corrected.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-definitions`: adds a requirement that setup installs project-level copies of the agents and that spawns prefer them, and drops reliance on frontmatter `model:` as the source of truth.
- `model-routing-config`: an absent key falls back to the shipped default config, not the agent file. The render output carries an Agent-tool model alias, and every spawn passes it.

## Impact

- `src/init_permissions.py`: new copy step, with a test.
- `src/render_prompt.py`: adds `agent_model` to its output, with a test.
- `skill/phase0_sourcing.md`, `skill/phase1_requirements.md`, `skill/phase2_planning.md`, `skill/phase3_build.md`, `commands/init.md`: spawn wording.
- `src/skill_config.default.json`: comment wording.
- `reference/scripts.md`, `ARCHITECTURE.md`: contract and roster lines.
- User projects gain `.claude/agents/cq-design-*.md`. These are plugin-owned files that init overwrites.
