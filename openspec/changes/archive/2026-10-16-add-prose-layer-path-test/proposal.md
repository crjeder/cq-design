## Why

The skill's behavior is defined by prose (`SKILL.md`, `commands/`, `skill/`, `prompts/`) that tells Claude which scripts and files to use. Only `test_render_prompt.py` touches that layer. A renamed script, a deleted phase file, or a changed CLI flag silently breaks the instructions with no failing test; Phase 3 alone references about 15 scripts.

## What Changes

- Add one fast, CadQuery-free test that extracts every `src/...`, `skill/...`, `prompts/...`, `reference/...` and `templates/...` path from `SKILL.md`, `commands/*.md`, `skill/*.md` and `prompts/*.md`, and asserts each exists in the repo.
- Add a second check in the same file: for each `python .../src/<script>.py <flags>` line in fenced bash blocks, assert every `--flag` is accepted by that script's argparse parser.
- No change to the prose or scripts themselves beyond fixing any dangling references the new test surfaces.

## Capabilities

### New Capabilities
- `prose-layer-validation`: tests that keep paths and CLI flags referenced from the instruction prose in sync with the repository.

### Modified Capabilities

## Impact

- New `tests/test_prose_layer.py`; runs in well under a second per check, no CadQuery.
- Possible small prose fixes where the test finds stale references.
- No runtime, schema, or dependency changes.
