## Why

`skill/phase3_build.md:369` tells the reader to re-run "Model export", but no heading has that name; the step is "Write assembly" plus `build/build.py`. Separately, `commands/render.md:7` expands `$ARGUMENTS` unquoted, so a script path containing spaces splits into several arguments.

## What Changes

- Replace the "Model export" reference in `skill/phase3_build.md` with "Write assembly, then `build/build.py`".
- Quote the script argument in the `commands/render.md` bash block.
- `commands/build.md:9` is left unquoted: its argument is a comma-separated format list that never contains spaces, and quoting would break the empty-argument case.

## Capabilities

### New Capabilities

### Modified Capabilities
- `cq-preview-rendering`: the `/cq-design:render` command must pass a script path containing spaces as one argument.

## Impact

- `skill/phase3_build.md`, `commands/render.md`. Docs/command text only; no script or JSON-contract change.
