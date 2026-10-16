## Context

`SKILL.md`, `commands/*.md`, `skill/*.md` and `prompts/*.md` are the instructions Claude follows. They name scripts and files in several forms:

- `$SKILL_DIR/src/log.py` (most common), `${CLAUDE_PLUGIN_ROOT}`-style prefixes, and `.claude/skills/cq-design/src/...` install-path forms
- bare repo-relative paths such as `skill/phase3_build.md` or `prompts/part.md`
- placeholders such as `$SKILL_DIR/src/<script>.py` and `templates/<file>`
- paths with spaces, e.g. `reference/Engineering Design Rules.md`

Nothing checks them today. Only `tests/test_render_prompt.py` touches the prose layer.

## Goals / Non-Goals

**Goals:**
- One fast test file, no CadQuery, that fails when a referenced `src/`, `skill/`, `prompts/`, `reference/` or `templates/` path does not exist.
- A second check that fenced bash lines invoking `src/<script>.py` only use flags that script's argparse defines.

**Non-Goals:**
- Validating prose semantics, flag values, or positional arguments.
- Checking paths outside those five roots (e.g. `build/`, `out/`, which are runtime outputs).
- Executing any script.

## Decisions

- **Regex over the raw text of each file, not a markdown parser.** Match `(src|skill|prompts|reference|templates)/[^\s`"')\]]+`, strip trailing punctuation, ignore any match containing `<`, `>`, `{`, `*` (placeholders/globs). Cheap and robust to every prefix form above, since the prefix before the root dir is ignored. Alternative: parse markdown links only; rejected, most references are bare backticked paths.
- **Paths with spaces.** Handle by also scanning for the known filenames in `reference/` literally: for each file actually present under the roots, nothing to do; instead the regex stops at whitespace, so `reference/Engineering` is resolved by prefix check: a match passes if it exists, or if any file in the repo starts with it followed by a space. Simple and avoids a per-file whitelist.
- **Flag check via AST, not import.** For each `src/<script>.py` found on a bash-fenced command line, parse the script with `ast`, collect string literals starting with `--` passed to any `add_argument` call, and assert each `--flag` on the prose line is among them. Importing would pull in CadQuery/trimesh and run argparse setup; AST keeps the test fast and dependency-free. Subcommand scripts (`log.py attempt|journal|request`, `plan.py validate|summary|import-params`) are covered because all subparsers' `add_argument` calls are collected into one flag set per script (union), a deliberate looseness.
- **Fenced bash only for flags.** Only lines inside ```` ```bash ```` / ```` ```sh ```` blocks, joined across `\` continuations, are checked, to avoid false positives from prose that mentions flags in passing.
- **Parametrized per file** so a failure names the prose file and the dangling reference.
- **Location:** `tests/test_prose_layer.py`, next to `test_plan.py`; add one line to the `tests/` list in `CLAUDE.md`.

## Risks / Trade-offs

- [False positives from illustrative paths in prose] -> skip placeholder characters; for any residual cases, an explicit small `IGNORE` set in the test with a comment.
- [Flags unioned across subparsers can mask a flag used with the wrong subcommand] -> accepted; catches renames and removals, which is the stated failure mode.
- [Scripts that build parsers dynamically or via helper functions may yield no literal flags] -> if a script has no `add_argument` literals, skip it for the flag check rather than fail.
