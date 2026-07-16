## Why

Every mechanically-detectable mistake in a generated part script currently costs a full
CadQuery subprocess run (several seconds) plus a retry round through the part loop.
Anti-patterns like booleans in a loop, a missing `result`, or submodule block imports
are visible in the AST before any geometry is built; catching them pre-run is the
cheapest possible retry killer (improvement plan item 7).

## What Changes

- New `src/script_lint.py`: AST-based static lint for generated part scripts. Pure
  stdlib (`ast`), no CadQuery import, runs in milliseconds.
- Detects the mechanically checkable anti-patterns:
  - boolean operations (`cut`/`union`/`intersect`) inside a loop
  - missing top-level `result` assignment
  - imports from block submodules (`from blocks.primitives import ...`) instead of
    the `blocks` package
  - direct `cq.exporters.export` calls (the shim owns export)
  - magic numbers outside the PARAMETERS block
  - `.center()`/`.hole()` followed by feature placement without re-anchoring
  - computed-offset boolean without a `verify_boolean` guard
  - `.shell()` after `.fillet()`
- Emits findings in the shared `{type, message, hint}` error contract so the part
  loop can build correction prompts the same way it does for wrapper errors.
- CLI entry point (`python src/script_lint.py <script.py>`) returning JSON; exit 0
  when clean, 1 when findings exist.
- SKILL.md part loop gains "Step 2.5 - lint before validate; fix findings before the
  first run".
- New `tests/test_script_lint.py` (fast, no CadQuery).

## Capabilities

### New Capabilities
- `script-lint`: static AST-based pre-flight lint of generated part scripts, with the
  finding catalog, JSON output contract, and part-loop integration point.

### Modified Capabilities

(none - no existing spec's requirements change; the part loop gains an additional
pre-run step but existing behavior of the wrapper and gate is untouched)

## Impact

- New file `src/script_lint.py`, new test `tests/test_script_lint.py`.
- SKILL.md part-loop section (one new step).
- No changes to `run_cadquery_model.py`, `quality_gate.py`, or the JSON contract;
  lint runs before, not inside, the wrapper.
- No new dependencies (stdlib `ast` + `json` only).
