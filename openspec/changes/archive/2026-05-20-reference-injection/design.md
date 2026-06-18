## Context

`orchestrate.py` renders three prompt templates by string-substituting `{{PLACEHOLDER}}` tokens before calling `claude -p`. Currently the templates contain only a hand-written subset of CadQuery patterns and no FDM design rules.

Two reference files exist in `reference/`:
- `CadQuery Pattern Reference.md` — complete, stable, ~440 lines covering the full CQ API
- `FDM 3D Print Design Guidelines.md` — growing, ~150 lines, will expand as new part types are supported

The planning prompt is rendered by the skill (interactive Claude session) and substitutes `{{USER_REQUEST}}` and `{{BLOCK_INVENTORY}}`. The part and assembly prompts are rendered by `orchestrate.py` and substituted immediately before the `claude -p` subprocess call.

## Goals / Non-Goals

**Goals:**
- CQ reference available to the code-generation LLM (part and assembly prompts)
- FDM guidelines available to the planning LLM and the part-generation LLM
- Adding a new FDM guideline section requires only editing the guidelines file, not Python
- No new runtime dependencies

**Non-Goals:**
- Semantic or embedding-based retrieval of reference content
- MCP-based tool-use reference lookup during `claude -p` batch calls
- Splitting CQ reference into per-section files (it is stable and complete)

## Decisions

### Decision 1: Include CQ reference in full, not selectively

The CQ reference is complete and stable. At ~440 lines / ~3K tokens it is well within context limits for all models used. Selective injection would require a maintained mapping table with no meaningful quality benefit.

*Alternative considered*: section extraction keyed on `blocks_needed`. Rejected — adds maintenance burden for zero measurable gain while the file is stable.

### Decision 2: Tag-based section filtering for FDM guidelines

Each section in `FDM 3D Print Design Guidelines.md` gets an HTML comment tag:

```markdown
## Wall Thickness
<!-- applies_to: always -->
...

## Snap-fit Design
<!-- applies_to: snap_hook_clip, snap_socket_receiver -->
...
```

`_load_reference_sections(path, block_names)` in `orchestrate.py` parses these tags and returns sections whose `applies_to` list intersects with `block_names`, plus all sections tagged `always`.

*Alternative considered*: per-topic files with YAML frontmatter. Rejected — single-file authoring is simpler; a folder of files adds navigation overhead for a maintainer editing one document. Revisit if the file exceeds ~600 lines.

*Alternative considered*: always inject full guidelines. Rejected — the file will grow; always-full injection couples prompt size to file growth. Tag filtering keeps prompt size proportionate to part complexity.

### Decision 3: Reference assignment per prompt

| Prompt | CQ Reference | FDM Guidelines |
|--------|-------------|----------------|
| `part.md` | Full (code generation needs syntax) | Filtered by `blocks_needed` |
| `assembly.md` | Full (union/cut/transform operations) | No (parts already validated) |
| `planning.md` | No (planning doesn't write code) | Filtered by all block names across all parts |

### Decision 4: Load references once in `build()`, thread through render functions

Reference file content is loaded once at the start of `build()` and passed into `_render_part_prompt` and `_render_assembly_prompt` alongside the existing template strings. This avoids repeated file I/O per part and keeps the render functions pure (input → output, no side effects).

### Decision 5: Remove redundant sections from `part.md`

The existing "Common Modeling Patterns" section is a small subset of the CQ reference. The "Rules" section duplicates content that will come from FDM guidelines. Both are removed to avoid contradictory or stale duplicates.

## Risks / Trade-offs

- **Tag parsing brittleness** → The `<!-- applies_to: ... -->` format is simple enough that a regex handles it reliably. If a tag is malformed, the section is treated as untagged and excluded (safe default). A missing `always` tag means the section is never injected — mitigated by running tests with known block combinations.
- **Planning prompt rendered by skill, not orchestrate.py** → `{{FDM_GUIDELINES}}` in `planning.md` must be substituted by the skill itself. SKILL.md must document this expectation. If forgotten, the literal placeholder shows in the prompt — visible and fixable, not a silent failure.
- **FDM guidelines grow past single-file manageability** → The per-topic-file split remains available. The tag convention is forward-compatible: tags in frontmatter (YAML) would use the same `applies_to` key.

## Migration Plan

1. Add tags to `reference/FDM 3D Print Design Guidelines.md`
2. Add helpers and update render functions in `orchestrate.py`
3. Update all three prompt templates (add placeholders, remove superseded sections)
4. Update `SKILL.md` to document `{{FDM_GUIDELINES}}` substitution for planning phase
5. Run existing test suite — `test_orchestrate.py` mocks `claude -p` so prompts are exercised; update mock assertions to check placeholder expansion
