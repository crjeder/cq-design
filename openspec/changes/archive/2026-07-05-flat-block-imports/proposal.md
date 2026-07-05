## Why

Five sources in the repo describe how a generated part script binds block names, and they disagree: `prompts/part.md` contradicts itself (line 11 "import the blocks" vs line 51 "do not write import statements -- the runner pre-imports them"), SKILL.md says per-submodule `from blocks.<module> import <fn>`, CLAUDE.md says flat `from blocks import <fn>` and explicitly forbids per-submodule, and the `block-import-injection` spec still documents an orchestrator (`_prepend_block_imports`) that was deleted in the 2026-05-27 inline-orchestration change. Only CLAUDE.md matches reality: the runner (`run_model_shim.py`) injects nothing, and `blocks/__init__.py` re-exports every block flat. `part.md:51` actively instructs the model to omit imports, which would produce a `NameError` on every part if a model obeyed it literally -- the build survives only because the model overrides that instruction.

## What Changes

- Converge every instruction onto CLAUDE.md's existing convention: a generated part script self-declares flat `from blocks import <function>` for each block in `blocks_needed`; nothing injects imports at runtime.
- `prompts/part.md`: delete line 51 ("pre-imported by the runner -- do not write import statements"); keep line 11 but make it concrete ("import cadquery as cq, and `from blocks import <fn>` for each block listed").
- SKILL.md: change the three per-submodule instructions (Step 2 write block ~L422, ~L827, generated-script rules ~L962) from `from blocks.<module> import <function>` to flat `from blocks import <function>`; drop the now-unnecessary "look up module and function from the inventory" step.
- **Remove** the `block-import-injection` capability: its single requirement describes deleted orchestrator code. The surviving behavior (script self-declares flat imports) is captured as a requirement so the contract is not lost.
- No production code change: `blocks/__init__.py` already re-exports flat and the runner already performs no injection. Optionally add a guard test.

## Capabilities

### New Capabilities
- none

### Modified Capabilities
- `block-import-injection`: Remove the "Orchestrator prepends block imports" requirement (the orchestrator and its `_prepend_block_imports` were deleted). Replace it with a requirement that generated part scripts self-declare flat `from blocks import <function>` imports for each block in `blocks_needed`, and that the runner performs no import injection.

## Impact

- `prompts/part.md` -- lines 11 and 51 reconciled to flat imports.
- `SKILL.md` -- three instructions switched to flat imports; inventory module-lookup ceremony dropped.
- `openspec/specs/block-import-injection/spec.md` -- rewritten to the flat-import script contract.
- `CLAUDE.md` -- already correct (lines 93-97); no change.
- No change to `blocks/__init__.py`, `run_model_shim.py`, or `run_cadquery_model.py` -- behavior already ships.
- Optional new guard test asserting every inventory block resolves via `from blocks import <name>` and that the runner injects nothing.
