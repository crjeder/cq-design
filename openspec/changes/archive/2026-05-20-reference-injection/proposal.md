## Why

The part and planning prompts currently contain only a small hand-written subset of CadQuery patterns and no FDM design rules, so the code-generation LLM lacks the syntax reference it needs for less common operations and the design guidelines that govern printable geometry. The FDM guidelines will grow as new part types are supported, so the injection mechanism must allow new content to be added without touching Python.

## What Changes

- Add `{{CQ_REFERENCE}}` placeholder to `prompts/part.md` and `prompts/assembly.md`; inject the full `reference/CadQuery Pattern Reference.md` at render time
- Add `{{FDM_GUIDELINES}}` placeholder to `prompts/planning.md` and `prompts/part.md`; inject filtered sections from `reference/FDM 3D Print Design Guidelines.md` based on `blocks_needed`
- Add `<!-- applies_to: block1, block2 -->` tag convention to each section of the FDM guidelines file; sections tagged `always` are always injected
- Add a `_load_reference_sections(path, block_names)` helper in `orchestrate.py` that parses tags and returns only matching sections
- Remove the redundant "Common Modeling Patterns" section from `part.md` (superseded by the full CQ reference)
- Remove the redundant "Rules" section from `part.md` (superseded by FDM guidelines injection)

## Capabilities

### New Capabilities

- `reference-injection`: Loading and injecting reference file content into prompt templates, including full-file and tag-filtered injection modes

### Modified Capabilities

- `planning-phase`: Planning prompt now receives filtered FDM guidelines, changing what design constraints the planner sees
- `orchestration-loop`: Part and assembly render functions now load and inject reference content alongside existing template substitution

## Impact

- `orchestrate.py`: `_render_part_prompt`, `_render_assembly_prompt`, and `build()` modified; new `_load_reference_sections()` and `_load_full_reference()` helpers added
- `prompts/part.md`: `{{CQ_REFERENCE}}` and `{{FDM_GUIDELINES}}` placeholders added; redundant sections removed
- `prompts/planning.md`: `{{FDM_GUIDELINES}}` placeholder added
- `prompts/assembly.md`: `{{CQ_REFERENCE}}` placeholder added
- `reference/FDM 3D Print Design Guidelines.md`: `<!-- applies_to: ... -->` tags added to each section
- No schema changes, no new dependencies
