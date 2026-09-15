## 1. Renderer

- [x] 1.1 Restructure `render_prompt.py` `main()`: `--plan`/`--part` and part lookup only for `builder`/`audit`
- [x] 1.2 Add `render_planning(request, plan, profile_path)` returning `(text, profile_status, profile_errors)`: inventory lines, archetype lines, FDM via `tagged_sections` over prior-plan blocks, profile via `validate_profile`
- [x] 1.3 Add `planning` subcommand (`--request-file`, `--plan`, `--profile`, `--out`), default `build/planning_prompt.txt`, print `{"out", "chars", "profile"[, "profile_errors"]}`
- [x] 1.4 Add `render_research(targets, known)` and `research` subcommand (`--targets-file`, `--known-file`, `--out`), default `build/research_prompt.txt`
- [x] 1.5 Update the module docstring usage block

## 2. Tests

- [x] 2.1 `planning` fresh render: request text, every inventory/archetype name, `always` sections only, profile loaded from a valid tmp profile
- [x] 2.2 `planning --plan` with an eval-case plan includes that plan's block-tagged FDM section
- [x] 2.3 Absent and invalid profile produce the note and `absent`/`invalid` status
- [x] 2.4 `research` render with and without `--known-file`; no `{{` left in output
- [x] 2.5 Unfilled placeholder exits 1 and writes no file (monkeypatch template read)
- [x] 2.6 Run `uv run pytest tests/test_render_prompt.py` and `ruff check --fix` / `ruff format` on changed files

## 3. Docs

- [x] 3.1 `skill/phase2_planning.md`: replace the placeholder table with write-request-file + `render_prompt.py planning` command, `profile` status handling, and the `Read <out> in full and follow it.` spawn line
- [x] 3.2 `skill/phase1_requirements.md`: replace the hand substitution with write-targets/known files + `render_prompt.py research` and the same spawn line
- [x] 3.3 `SKILL.md` prompt table, `ARCHITECTURE.md` agent-roster rows, `CLAUDE.md` `render_prompt.py` and test descriptions: note planner/research prompts are rendered by the script
- [x] 3.4 Check `init_permissions.py` patterns already cover the new `render_prompt.py` invocations; add if not
