## Why

Block functions from `blocks/*.py` are referenced by name in generated part scripts but the LLM has no reliable way to produce correct import statements - `module` and `function` fields exist in the inventory but are never rendered into the prompt. The orchestrator already knows which blocks each part needs (from `blocks_needed` in BUILD_PLAN); it should inject the imports itself rather than hoping the LLM guesses correctly.

## What Changes

- Add `_prepend_block_imports()` helper to `orchestrate.py` that reads `module` + `function` from inventory and prepends `from <module> import <function>` lines to generated scripts before writing them to disk.
- Call this helper after `_extract_python()` in the part build loop.
- Remove the `# from blocks import ...` placeholder comment from `prompts/part.md` and replace it with an explicit instruction: block functions are pre-imported by the runner, do not write import statements for them.
- `module` and `function` fields in `inventory.json` / `inventory_schema.json` are unchanged but now have a real runtime consumer.

## Capabilities

### New Capabilities

- `block-import-injection`: The orchestrator injects correct block import statements into generated part scripts, derived from inventory metadata, before script execution.

### Modified Capabilities

- `planning-phase`: The part prompt no longer instructs the LLM to write block imports; it tells the LLM the functions are pre-imported.

## Impact

- `orchestrate.py`: new helper function, called in part build loop
- `prompts/part.md`: one comment removed, one instruction added
- No changes to `inventory.json`, `inventory_schema.json`, or any block `.py` files
- Generated part scripts will have import lines prepended by the orchestrator; scripts are not intended to be run standalone
