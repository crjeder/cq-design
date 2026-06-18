## ADDED Requirements

### Requirement: Part prompt instructs LLM not to write block imports
The `prompts/part.md` template SHALL explicitly instruct the LLM that block functions are pre-imported by the runner and that the LLM SHALL NOT write import statements for them.

The script structure section of `prompts/part.md` SHALL NOT contain a placeholder comment suggesting the LLM write `from blocks import ...` lines.

#### Scenario: Block functions called without imports in generated code
- **WHEN** the LLM generates a part script for a part with `blocks_needed: ["hollow_box"]`
- **THEN** the generated code calls `hollow_box(...)` directly without a preceding import statement for it

#### Scenario: Prompt template contains no import placeholder
- **WHEN** `prompts/part.md` is rendered for any part
- **THEN** the rendered prompt contains no comment or instruction suggesting the LLM write `from blocks import` lines
