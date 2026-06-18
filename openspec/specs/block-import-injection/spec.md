# Block Import Injection

## Purpose

TBD - Defines requirements for how the orchestrator injects block import statements into generated part scripts.

## Requirements

### Requirement: Orchestrator prepends block imports to generated part scripts
The orchestrator SHALL derive import statements from `module` and `function` fields in `inventory.json` and prepend them to every generated part script before writing it to disk, for each block name listed in the part's `blocks_needed`.

The import format SHALL be: `from <module> import <function>`

If a block name in `blocks_needed` is not found in the inventory, the orchestrator SHALL skip it silently (plan validation is responsible for catching unknown block names before the loop runs).

The injected imports SHALL appear before any LLM-generated code in the written script file.

#### Scenario: Part with one block
- **WHEN** a part's `blocks_needed` contains `["hollow_box"]`
- **THEN** the written script begins with `from blocks.primitives import hollow_box` before any generated code

#### Scenario: Part with multiple blocks
- **WHEN** a part's `blocks_needed` contains `["hollow_box", "screw_boss", "port_cutout"]`
- **THEN** the written script begins with three import lines, one per block, in `blocks_needed` order

#### Scenario: Part with no blocks
- **WHEN** a part's `blocks_needed` is empty
- **THEN** no import lines are prepended and the script begins with the LLM-generated code unchanged

#### Scenario: Unknown block name
- **WHEN** `blocks_needed` contains a name not present in `inventory.json`
- **THEN** plan validation SHALL have already rejected the plan before the part loop runs; if somehow reached, `_prepend_block_imports` skips that name and writes no import line for it
