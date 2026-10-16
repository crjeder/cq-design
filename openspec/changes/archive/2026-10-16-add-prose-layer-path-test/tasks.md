## 1. Path-reference test

- [x] 1.1 Create `tests/test_prose_layer.py` that collects `SKILL.md`, `commands/*.md`, `skill/*.md`, `prompts/*.md`
- [x] 1.2 Extract `src|skill|prompts|reference|templates` paths by regex, skip placeholders/globs, handle space-containing `reference/` names
- [x] 1.3 Parametrize per prose file; assert each path exists
- [x] 1.4 Run it, fix any genuinely dangling references in the prose (or add a commented `IGNORE` entry)

## 2. CLI-flag test

- [x] 2.1 Extract `src/<script>.py` command lines from bash/sh fenced blocks (join `\` continuations)
- [x] 2.2 Collect `--flag` literals from each script's `add_argument` calls via `ast` (union across subparsers)
- [x] 2.3 Assert each prose `--flag` is in the script's set; skip scripts with no literal flags
- [x] 2.4 Run it, fix stale flags in the prose

## 3. Wrap-up

- [x] 3.1 Add `test_prose_layer.py` to the `tests/` list in `CLAUDE.md`
- [x] 3.2 Run `uv run pytest tests/test_prose_layer.py` and `uv run ruff check tests/test_prose_layer.py`
