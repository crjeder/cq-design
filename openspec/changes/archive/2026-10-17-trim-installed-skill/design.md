## Context

`install.sh` copies the repo minus a 13-entry exclusion list; `install.ps1` copies it minus a 25-entry list that also drops `openspec`, `tests`, `evals` and the installers. The lists have drifted, and neither drops `TODO.md`, `documentation/`, `src/*.egg-info/` or `src/.fossil/` (the latter only at the top level in `install.ps1`). Shipped prose (`SKILL.md`, `skill/`, `reference/`) still points at things only a checkout has. Two runtime reads live in dev-only directories:

- `src/session_cost.py` (`Stop` hook) reads `evals/model_prices.json`. Under `install.ps1` that file is absent, and the hook's always-exit-0 contract makes the failure silent.
- `src/render_prompt.py sourcing` reads `documentation/Block_Sources.md` (Phase 0).

`.claude-plugin/plugin.json` is required in a copy install: Claude Code loads the copy as a `skills-dir` plugin, which is how `/cq-design:*` commands appear (plugin-packaging spec).

## Goals / Non-Goals

**Goals:**
- A copy install holds only what runtime needs, defined once per installer as an allowlist, and both installers agree.
- Every path or name the shipped prose cites resolves inside the install.
- One repo layout tree (`FILES.md`) instead of two.
- A test keeps it that way.

**Non-Goals:**
- Plugin (marketplace) installs: `skills: ["."]` still ships the whole repo. Trimming that needs a separate packaging step.
- Code comments in `src/` that cite `TODO.md` anchors (`plan.py`, `quality_gate.py`, `edge_treatment_check.py`). They are history for developers, not instructions an agent follows; left alone.
- Shipping `tests/` or `evals/` in the install.

## Decisions

**Allowlist, not a better exclusion list.** New dev files at the repo root then stay out by default instead of leaking until someone notices. Entries: `SKILL.md`, `.claude-plugin/`, `commands/`, `skill/`, `prompts/`, `reference/`, `src/`, `templates/`, `pyproject.toml`, `uv.lock`, `.python-version`, `LICENSE`. Two additions beyond the requested list: `.claude-plugin/` (commands vanish without it) and `.python-version` (pins 3.12 for `uv sync` in the destination, matching the repo; 6 bytes). After copying, prune `__pycache__`, `*.egg-info` and `.fossil` directories anywhere under the destination. In `install.sh`, copy each allowlisted entry with `cp -R` (drop the rsync/tar branch: no exclusion logic left to share), then `find "$dest" -type d \( -name __pycache__ -o -name '*.egg-info' -o -name .fossil \) -prune -exec rm -rf {} +`. In `install.ps1`, `Copy-Item` each allowlisted entry that exists, then the existing recursive prune extended to the two extra names.

**Installer parity test** parses the two arrays (`ALLOWLIST=(...)` in bash, `$Allowlist = @(...)` in PowerShell) with a regex in `tests/test_prose_layer.py` and asserts equal sets. No CadQuery, no execution, so it stays in the fast tier.

**Move runtime data out of dev directories, don't ship the directories.** `evals/model_prices.json` -> `src/model_prices.json` (`session_cost._PRICES_PATH` becomes `Path(__file__).resolve().parent / "model_prices.json"`; `evals/run_evals.py` points at the new path). `documentation/Block_Sources.md` -> `reference/Block_Sources.md` (`render_prompt.py` path; README link). Nothing globs `reference/*.md` for injection, so the move adds no prompt weight. `git mv` keeps history.

**Capability-name citations.** Replace, per site:
- `skill/phase3_build.md` `planning-phase`'s rule 10 -> "`prompts/planning.md` rule 10" (rule 10 there declares `load` incl. `applied_at` / `grounded_at`).
- `fem-wall-shell-solve`, `fem-stress-advisor` -> `reference/scripts.md`'s `src/fem_check.py` row (shell solve and mesh-size note); if that row lacks the mesh-size point, drop the parenthetical rather than invent content.
- `quality-gate-fix-policy` (`phase3_build.md:238`) -> "`skill/phase4_deliver.md` step 1", where the stall/print-time numbers are reported and acted on.
- `phase4_deliver.md:28` and `reference/FDM 3D Print Design Guidelines.md:53` `toolpath-speed-advisor` -> `reference/scripts.md`'s `src/toolpath_speed.py` row.

**Installer-script mentions.** `SKILL.md:14`: "an installer copy". `skill/resume.md:85` comment: "skill stale? reinstall from the repo". `src/skill_version.py` docstring may keep naming the scripts (code, not prose an agent follows) but should say "the repo's installer" for consistency; low priority.

**`reference/scripts.md`.** Header drops the `evals/` and `CLAUDE.md` mentions; the `evals/run_evals.py` row moves verbatim to a new `evals/README.md`; the `bundle_project.py` row loses "(`tests/test_build_script.py` uses it)"; the `session_cost.py` row cites `src/model_prices.json`. Sweep the `src/log.py` row for its `tests/` hit.

**Layout tree.** CLAUDE.md's `File Layout` tree (current, larger) replaces FILES.md's stale content wholesale; CLAUDE.md keeps the section heading with a one-line pointer to `FILES.md` and the existing pointer to `reference/scripts.md`. README's "see FILES.md" stays valid.

**Prose guard.** Extend `tests/test_prose_layer.py` with one parametrized test over `SKILL.md`, `commands/`, `skill/`, `prompts/`, `reference/` that fails on a forbidden-path regex (`install\.(sh|ps1)`, `openspec/`, `tests/`, `evals/`, `documentation/`, `TODO.md`, `FILES.md`, `CLAUDE.md`) or a backticked token in `{d.name for d in (ROOT/"openspec/specs").iterdir()}`. Match on a word boundary so `src/tests_helper` style names would not trip it; there are none today.

## Risks / Trade-offs

- [A future runtime read of a non-allowlisted file breaks only copy installs] -> the prose guard catches prose citations; code reads are caught by the existing "Skill works after a copy install" scenario when someone runs it. Accepted; adding a code scanner is not worth it for two known reads.
- [Capability-name regex false positive on a common backticked word that is also a spec name, e.g. `model-export`] -> fix by rewording the prose; the set of spec names is kebab-case and rarely backticked otherwise.
- [Stale files linger in existing copy installs] -> both installers already `rm -rf` the destination first, so the next reinstall cleans them.
- [Dropping rsync in `install.sh` loses its incremental copy] -> irrelevant: the destination is wiped before every copy anyway.
