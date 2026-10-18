## Context

Prompts under `prompts/` are rendered into sub-agent instructions (builder, auditor, planner). Each has drifted from the tool it describes. The fixes are text-only; the question is which side to move -- the prompt or the tool.

## Goals / Non-Goals

**Goals:**
- Every statement in the three prompts about section cuts, preview camera direction, and the `load` field matches current code.
- No change to `src/` behaviour or schemas.

**Non-Goals:**
- Implementing `render_preview.py --auto-sections` and forwarding it from `run_cadquery_model.py` (separate change).
- Changing `_section_cuts` precedence.

## Decisions

- **Fix the prompt, not the tool, for sections.** Wiring `--auto-sections` touches renderer, wrapper, and tests; documenting the hand-run `section_select.py` path is the minimal correct fix now. Alternative (implement the flag first) is deferred so the prompt stops misdescribing the tool immediately.
- **Use the renderer's labels verbatim in `audit.md`.** Copying `preview.py`'s "Viewed from South/West/above" strings means the auditor's vocabulary matches the PNG titles it sees. Alternative (fix to "looking +Y") still leaves two vocabularies.
- **Emit `dir: [0, 0, -1]` for compression rather than relaxing the schema.** `print_orientation.py:201` already ignores `load_dir` for compression, so a fixed downward vector is harmless and keeps the schema's single `required: ["dir"]`. Alternative (conditional `if/then` making `dir` optional for compression) adds schema complexity and touches every `load.dir` reader that assumes it is present.

## Risks / Trade-offs

- [Builder must run `section_select.py` itself to get bore cuts, costing a tool call] -> acceptable until `--auto-sections` lands; the prompt already gives the exact command.
- [A planner might copy `[0, 0, -1]` onto a non-compression part] -> rule text scopes it to the compression bullet only; the structural bullet still demands a real `dir`.
