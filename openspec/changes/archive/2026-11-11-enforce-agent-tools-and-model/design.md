## Context

`agents/*.md` declare a minimal `tools:` list and a `model:` per role (change `reduce-session-cost`). A desktop-app probe on 2026-11-10 showed that neither field takes effect for a plugin-loaded agent:

| Spawn | Tools | Model | First-call input |
|---|---|---|---|
| desktop, `cq-design:builder`, no `model` param | 44 (full desktop set) | Opus | 65.6k |
| desktop, `general-purpose`, `model: "sonnet"` | 44 | Sonnet | 65.9k |
| headless `claude -p --agents`, same definition | 6 | Sonnet | 11.2k |

anthropics/claude-code#89723 reports that `model:` is ignored for plugin agents but honoured for project-level agents. The tools half is filed as #108748. Whether project-level agents also honour `tools:` in the desktop app is **not yet measured**.

Already in place:
- `render_prompt.py` prints `model` (a full id such as `claude-sonnet-5-5`), resolved by `log.role_model()` from `./skill_config.json` and then `src/skill_config.default.json`.
- The spawn prose in phases 0-3 already says "on the render output's `model`". But the Agent tool's `model` parameter takes only the aliases `sonnet`/`opus`/`haiku`/`fable`, so the main session has to translate the id itself.

## Goals / Non-Goals

**Goals:**
- Sub-agents start with only their declared tools wherever the host honours a project-level definition.
- Every spawn runs on the configured model, whatever the host does with frontmatter.
- No LLM-side id-to-alias translation.

**Non-Goals:**
- Running sub-agents as headless `claude -p` subprocesses. That would give 11k starts but lose live progress, resume and in-app permissions. Revisit only if project agents also fail to honour `tools:`.
- Trimming the user's global plugins or CLAUDE.md. That is user configuration, not something the skill owns.
- Changing the `quality_gate.py --fix` `claude -p` path. It already passes `--model`.

## Decisions

**1. Measure before building the copy step.** Task 1 is a desktop probe: copy `agents/builder.md` into a scratch project's `.claude/agents/cq-design-builder.md`, open a fresh desktop session there, spawn it, and read the sub-agent's `.prefix.json` `toolNames` and its first-call usage.
- If `tools:` is honoured, build the copy step as described.
- If it is not, ship only the model half (decisions 4-5) and record the result on #108748.

Alternative rejected: build the copy first and measure afterwards. That risks shipping files that change nothing.

**2. Init copies the agents; it does not bundle them.** `init_permissions.py` already writes `.claude/settings.local.json` in the project and is idempotent, so it is the natural owner. The copy goes to `.claude/agents/cq-design-<role>.md`, with the role taken from the source filename.
- Files are always overwritten when their content differs. They are plugin-owned; users change models through `skill_config.json`, not by editing agent files.
- Only the five `cq-design-*.md` names are touched, never other files in `.claude/agents/`.
- Alternative rejected: adding this to `bundle_project.py` (`/cq-design:update`). That only runs for bundled projects, and an agent install is needed before Phase 0.

**3. Spawn prose prefers the project agent.** Phases name `cq-design-<role>`, which matches the project copy's `name:`. If that type is not offered, they fall back to the plugin's `cq-design:<role>`. A project that never ran init still works, just at the old cost.

**4. `render_prompt.py` emits `agent_model`.** This is the Agent tool alias derived from the resolved id: the first of `fable`, `opus`, `sonnet`, `haiku` that appears in it, otherwise the id itself.
- `model` stays the full id, so logs and `attempts.jsonl` keep recording it.
- `inline` produces no spawn, so `agent_model` is moot there and can stay unset.
- Prose changes from "on the render output's `model`" to "pass the render output's `agent_model` as the Agent tool's `model`".
- Alternative rejected: changing `skill_config.json` values to aliases. Aliases lose the version, and `claude -p --model` in the gate takes full ids.

**5. Fallback is the shipped default config, not the agent file.** This is already the code's behaviour. The spec scenario "Absent key falls back to the agent file" and the `skill_config.default.json` comment are corrected to match. The agent files' `model:` stays as documentation and for hosts that honour it.

## Risks / Trade-offs

- [Project agents also ignore `tools:` in desktop] → decision 1 gates the copy step. The model half still lands.
- [Stale project copies after a plugin upgrade] → init refreshes them on every run. `/cq-design:status` already flags bundle staleness, and an agent check can be added later if this shows up in practice.
- [Name collision with a user's own `cq-design-*` agent] → unlikely given the prefix. Init overwrites it, and the file names are documented in `commands/init.md`.
- [Host maps an unknown alias badly, e.g. a future model family] → `agent_model` falls back to the raw id, and the main session reports a spawn error instead of silently using Opus.

## Migration Plan

Existing projects pick the agents up the next time `/cq-design:init` runs. The phase prose falls back to plugin agents until then. Rollback is to delete `.claude/agents/cq-design-*.md`.

## Open Questions

- Do user-level agents (`~/.claude/agents/`, used by the copy installers) honour `tools:` in desktop? This is out of scope here; the measurement in task 1 can note it if it's cheap to check.
