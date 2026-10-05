## Why

`build.py` prints nothing until it finishes. Orientation resolution and `export_model` load and tessellate every part, so a project with many parts can run for minutes with no output, and a person at the terminal cannot tell progress from a hang.

## What Changes

- `build.py` prints a `[k/N] <step> <id>` line to stdout as each unit of work starts, flushed immediately so lines appear live when stdout is piped or captured.
- Each phase has its own counter, with no cross-phase percentage:
  - orientation: one line per union whose accepted orientation is missing or stale (reused entries print nothing; `N` is the count of unions that need computing)
  - loading: one line per part
  - 3MF: a single `writing model.3mf` line, no counter
  - STL: one line per union
  - plates: one line per fused multi-union plate
- `export_model(..., progress=None)` gains an optional keyword-only callback taking the line text. `build.py` passes `print(..., flush=True)`; `quality_gate.py` and the `model_export` CLI pass nothing.
- The existing final summary and the `build failed:` message on stderr are unchanged.
- No bar, no TTY detection, no `\r` redraw, no new dependency.

## Capabilities

### New Capabilities

### Modified Capabilities
- `build-script`: `build.py` reports `[k/N]` progress lines on stdout while building.
- `model-export`: `export_model` accepts an optional progress callback and calls it per part, union, and plate.

## Impact

- Code: `src/build_template.py`, `src/model_export.py`.
- Docs: README command-line reference (mention the progress lines), `reference/scripts.md` if it documents `export_model`'s signature.
- Tests: `tests/test_build_script.py`, `tests/test_model_export.py`.
- Sequencing: `build-format-option` also edits the `export_model` signature and adds a per-union extra-formats loop. Land that first so this change can label that loop; if not, `progress` is added alongside `formats` with no conflict.
- Default behaviour of `quality_gate.py` and `model_export` CLI output (JSON on stdout) is unchanged.
