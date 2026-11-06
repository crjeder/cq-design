## 1. Verify platform behavior (before wiring anything)

- [x] 1.1 Check Claude Code docs: plugin agent frontmatter (`name`, `description`, `tools`, `model`), plugin-namespaced spawn name, and that `tools:` is enforced. Record the findings in design.md Open Questions.
- [x] 1.2 Test whether a copy install in `~/.claude/skills/cq-design/` loads `agents/`; decide whether the installers also copy to the personal agents directory.

## 2. Agent definitions and model routing

- [x] 2.1 Write `agents/{sourcing,research,planner,builder,auditor}.md` with minimal `tools:` and `model:`
- [x] 2.2 Add `sourcing`, `research`, `auditor` to `src/skill_config.default.json` and the config reader; fall back to the agent file's model
- [x] 2.3 Make `part_author_model()` / attempts log record the real model id; test in `tests/test_log.py`
- [x] 2.4 Replace `general-purpose` spawn instructions in `SKILL.md`, `skill/phase*.md`, `commands/*.md`; update `src/render_prompt.py` output text; add a test that no shipped prose names `general-purpose` for these roles
- [ ] 2.5 Run the audit eval case with the auditor on Sonnet vs the previous model; record the result in the change
- [x] 2.6 Rewrite `ARCHITECTURE.md` agent roster and the "No `.claude/agents/` files" rule

## 3. Installers

- [x] 3.1 Add `agents` to `ALLOWLIST` in `install.sh` and `install.ps1`; extend the allowlist-agreement test
- [x] 3.2 Add the personal-agents-directory copy and uninstall removal if task 1.2 requires it
- [x] 3.3 Update `.claude-plugin/plugin.json`; confirm `claude plugin validate .` passes; update README Setup for local-only installs; note the change in `FILES.md`

## 4. parameters.py as single source

- [x] 4.1 `src/plan_params.py`: load constants from `parameters.py` via `ast`, evaluate whitelisted expressions, typed errors; `tests/test_plan_params.py` (resolves, unknown name, unsafe syntax, `min`/`max`/`round`)
- [x] 4.2 `build_plan_schema.json`: allow string param values; `plan.py validate` evaluates them
- [x] 4.3 `blocks/part.py` `Part.param` returns resolved values; test with an expression plan and an unchanged part script
- [x] 4.4 `plan.py validate` writes `build/params_resolved.json` and prints changed parts; test unchanged / one-changed cases
- [x] 4.5 N/A in v1: `import-params` reconciles `parts[].dimensions`, which stay literal; expressions live in instance `params` only. Dropped the `parameter-round-trip` delta.
- [x] 4.6 `quality_gate` provenance check: duplicate-literal and missing-origin advisories; tests
- [x] 4.7 Update `skill/phase1_requirements.md` (origin tags, drop "not imported by the build"), `skill/phase2_planning.md`, `prompts/planning.md` (every dimension traces to a constant, params are expressions), `skill/phase3_build.md` (partial rebuild and re-audit rule)
- [x] 4.8 Check `export_standalone.py` produces a working bundle for an expression plan; test

## 5. Journal side effects

- [x] 5.1 `log.append_once`; called from `plan.py validate` (`plan_written`) and `write_assembly.py` (`assembly_written`); idempotent, success only, journal must exist; tests. Orientation, gate and delivery milestones stay explicit (no script owns their text)
- [x] 5.2 Removed the matching standalone Bash steps for those two milestones from `skill/*.md`
- [x] 5.3 Added the "fresh session after `/cq-design:init`" note to `commands/init.md`

## 6. Concept sketch and SVG illustrations

- [x] 6.1 (result: none in shipped prose; two box diagrams in `documentation/Knowledge Domains.md`, converted to `documentation/img/*.svg`; the Gemini page dump `LLM Text-to-CAD Skill Domains.md` was left alone) Inventory real ASCII diagrams in `README.md`, `SKILL.md`, `skill/`, `prompts/`, `reference/`, `ARCHITECTURE.md` (by hand; the pattern search also matches tables); list them in the change
- [x] 6.2 `src/concept_sketch.py` and `tests/test_concept_sketch.py` (valid input, unknown shape, no CadQuery import)
- [x] 6.3 `skill/phase1_requirements.md`: sketch step in the exit checkpoint, approval rule, request-log correction; `regen_prompt.py` lists the sketch files; test
- [x] 6.4 Convert the diagrams from 6.1 to `reference/img/*.svg`, link them from the markdown, give prompt diagrams a prose description
- [x] 6.5 Test that every referenced SVG exists and parses; add the entries to `FILES.md` and the contracts to `reference/scripts.md`

## 7. Wrap up

- [ ] 7.1 Run `uv run pytest tests/` and `ruff check` on changed Python
- [x] 7.2 Tick the `TODO.md` items (lines 26, 27, 70) and trim the Siebtragerhalter details that this change resolves
