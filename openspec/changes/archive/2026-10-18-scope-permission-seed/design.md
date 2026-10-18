## Context

`init_permissions.py` merges `skill_permissions.json`'s `allow` list into
`.claude/settings.local.json` without prompting; `bundle_project.py` calls the same
`merge_permissions`. The list contains shapes broader than its comment claims (see
proposal). A grep of `SKILL.md`, `skill/`, `commands/` and `reference/` finds no
skill-issued `cp`, `mkdir`, `Copy-Item` or `New-Item`: copies happen in Python
(`bundle_project.py`, `seed_default_files`) and `scaffold_directories` creates the tree.
Every skill script call is documented as `uv run --project "$SKILL_DIR" python
"$SKILL_DIR/src/<script>.py" ...` or `python "${CLAUDE_PLUGIN_ROOT}/src/<script>.py" ...`,
with the literal path substituted (SKILL.md Prerequisites).

## Goals / Non-Goals

**Goals:**
- Seed contains only shapes the skill issues, anchored to the skill directory.
- Existing working directories lose the old broad grants on the next init/update.

**Non-Goals:**
- Scoping `uv sync*` or `uv run python build/build.py*` (already working-dir-relative and
  harmless).
- Changing how the skill composes commands.
- Touching user-authored allow entries.

## Decisions

1. **Drop copy/mkdir entirely instead of scoping to `cp * build/*`.** Nothing issues them,
   so a scoped pattern is still an unused grant, and `cp * build/*` would still let any
   file overwrite anything under `build/`. Alternative (scope it) rejected: no caller.
2. **Drop bare `WebSearch`.** It is read-only but unrestricted, and searches are occasional
   (Phase 0 sourcing, Phase 1 dimension research), so one prompt per use is acceptable.
   If Claude Code supports a scoped `WebSearch(...)` rule form, prefer leaving it out
   anyway: the docs don't name a fixed query shape to scope to.
3. **`{skill_dir}` placeholder resolved at seed time.** Canonical entries become e.g.
   `Bash(uv run --project "{skill_dir}" python "{skill_dir}/src/log.py" *)` and
   `Bash(python "{skill_dir}/src/log.py" *)`. `init_permissions.py` substitutes the
   absolute skill root (parent of `src/`), reusing the existing `_resolve_command`
   placeholder approach. The template keeps `/src/` with a forward slash because that is
   how the docs write it after the substituted root. Alternative (`*/cq-design/src/log.py`)
   rejected: the install directory name is not guaranteed, and a leading wildcard
   re-opens the "same name elsewhere" hole.
4. **Sentinel is the resolved run_cadquery_model pattern.** `is_initialized` resolves it
   before lookup, so old seeds and moved installs read as uninitialized and trigger a
   re-merge.
5. **Pruning.** `skill_permissions.json` gains a `retired` list (the exact old broad
   strings, Bash and PowerShell). The merge removes those, plus any entry that matches a
   canonical template with `{skill_dir}` replaced by a wildcard but is not the current
   resolution (old plugin cache path). Mirrors `_drop_stale` for hooks. Removed entries
   are returned/printed alongside added ones.

## Risks / Trade-offs

- [Path spelling mismatch on Windows (backslash root vs. forward-slash `/src/`, or a
  different drive-letter case) makes calls prompt] -> Resolve the root the same way the
  "Base directory for this skill" line prints it (`os.path.abspath`); a mismatch only
  costs a prompt, never widens access. Verify once on Windows during apply.
- [Pruning removes a `WebSearch` the user added themselves] -> Accepted; it is reported
  in the merge output so the user can re-add it.
- [More prompts for WebSearch and any ad-hoc copy] -> Intended.

## Migration Plan

Ship with the next release; `/cq-design:init` or `/cq-design:update` (via
`bundle_project.py`) re-merges and prunes. Rollback: revert the JSON and script; the
pruned entries are not restored automatically.

## Open Questions

- Does Claude Code's permission matcher see the double quotes in
  `python "<path>/src/log.py"`? Check against the permission-rule docs during apply; if
  quotes are stripped, drop them from the templates.
