## ADDED Requirements

### Requirement: Generated part scripts self-declare flat block imports
A generated part script SHALL bind every block in the part's `blocks_needed` by writing a flat package import of the form `from blocks import <function>` at the top of the script, where `<function>` is the block name. Scripts SHALL NOT import from block submodules (`from blocks.<module> import ...`). The runner SHALL NOT inject, prepend, or otherwise modify import statements; the script is complete as written and runs unchanged.

The `blocks` package re-exports every block from its submodules, so the flat import resolves without knowledge of which submodule defines the block. The runner sets `PYTHONPATH` to the `src` directory so the `blocks` package is importable.

#### Scenario: Part with one block
- **WHEN** a part's `blocks_needed` contains `["hollow_box"]`
- **THEN** the generated script contains `from blocks import hollow_box` and no `from blocks.<module> import` line

#### Scenario: Part with multiple blocks
- **WHEN** a part's `blocks_needed` contains `["hollow_box", "screw_boss", "port_cutout"]`
- **THEN** the generated script imports all three via `from blocks import ...` (one combined or three separate flat imports), with no submodule paths

#### Scenario: Part with no blocks
- **WHEN** a part's `blocks_needed` is empty
- **THEN** the script imports no blocks and uses raw CadQuery primitives

#### Scenario: Runner does not inject imports
- **WHEN** the runner executes a generated part script
- **THEN** it runs the script as written (via the shim's `runpy` execution) and adds no import statements; a script that calls a block function without a matching `from blocks import` line fails with `NameError`

#### Scenario: Every inventory block is flat-importable
- **WHEN** any block name registered in `blocks/inventory.json` is imported as `from blocks import <name>`
- **THEN** the import succeeds because `blocks/__init__.py` re-exports it

## REMOVED Requirements

### Requirement: Orchestrator prepends block imports to generated part scripts
**Reason**: The orchestrator (`src/orchestrate.py`) and its `_prepend_block_imports` helper were deleted in the 2026-05-27 inline-orchestration change. There is no longer any process that derives imports from `inventory.json` and prepends them; Claude writes the imports directly into each part script.
**Migration**: Generated part scripts now self-declare flat `from blocks import <function>` imports (see the ADDED requirement above). No orchestrator step is involved.
