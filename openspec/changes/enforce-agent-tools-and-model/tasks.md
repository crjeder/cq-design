## 1. Measure project-level agents (gates group 3)

- [ ] 1.1 In a scratch directory, copy `agents/builder.md` to `.claude/agents/cq-design-builder.md`, open a fresh desktop Code session there, and spawn `cq-design-builder` with no `model` param and the prompt "Reply with the single word OK. Use no tools."
- [ ] 1.2 Read the sub-agent's `.prefix.json` `toolNames`, its `.meta.json` and the first-call usage; record tools, model and input tokens in this change's design.md Context table
- [ ] 1.3 If `tools:` is not honoured (more than the 6 listed tools), skip group 3, comment the result on anthropics/claude-code#108748, and remove the agent-definitions delta from this change

## 2. Explicit model on every spawn

- [x] 2.1 `src/render_prompt.py`: add `agent_model` (first of `fable`/`opus`/`sonnet`/`haiku` in the resolved id, else the id) next to `model` for every kind
- [x] 2.2 `tests/test_render_prompt.py`: sonnet id -> `sonnet`, opus id -> `opus`, unknown id passes through, and the part kind carries both fields
- [x] 2.3 Spawn prose in `skill/phase0_sourcing.md`, `skill/phase1_requirements.md`, `skill/phase2_planning.md` and `skill/phase3_build.md` (builder and auditor): pass the render output's `agent_model` as the Agent tool's `model`
- [x] 2.4 `src/skill_config.default.json` `_comment`: an absent key falls back to this file, not to the agent file
- [x] 2.5 `reference/scripts.md`: document `agent_model` in the `render_prompt.py` output contract

## 3. Project-level agent copies (only if 1.3 passed)

- [ ] 3.1 `src/init_permissions.py`: copy `agents/<role>.md` to `.claude/agents/cq-design-<role>.md` when absent or different, print each copied file, and touch nothing else in `.claude/agents/`
- [ ] 3.2 Rename each `agents/*.md` frontmatter `name` if needed so it equals `cq-design-<role>` (it already does; assert it in `tests/test_agents.py`)
- [ ] 3.3 `tests/test_init_permissions.py`: fresh dir gets five identical copies, a stale copy is refreshed, an unrelated agent file is untouched, and a second run reports no changes
- [ ] 3.4 Spawn prose: name `cq-design-<role>`, with `cq-design:<role>` as the fallback when the project agent is not offered
- [ ] 3.5 `commands/init.md`: mention the agent copies in the report step
- [ ] 3.6 `ARCHITECTURE.md` agent roster and `FILES.md`: note the project copies

## 4. Verify

- [ ] 4.1 `uv run pytest tests/test_render_prompt.py tests/test_init_permissions.py tests/test_agents.py`
- [ ] 4.2 Prose test: each role's spawn instruction names `agent_model`, and `cq-design-<role>` if group 3 landed (extend `tests/test_agents.py`)
- [ ] 4.3 After init in a fresh desktop session, spawn the builder from the skill flow and confirm Sonnet with the 6 tools in its `.prefix.json`
