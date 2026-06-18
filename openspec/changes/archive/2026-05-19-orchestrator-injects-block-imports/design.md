## Context

The part build pipeline in `orchestrate.py` calls `claude -p` with a rendered prompt, extracts the Python code, writes it to disk, then executes it via `run_cadquery_model.py`. The runner sets `PYTHONPATH` to include the skill root, so `from blocks.fasteners import snap_hook_clip` resolves correctly at runtime.

Currently the LLM is expected to write these import lines, but the prompt never gives it the module paths. The `module` and `function` fields in `inventory.json` are the canonical source of this information and are already loaded by the orchestrator - they just aren't used.

## Goals / Non-Goals

**Goals:**
- Eliminate LLM import guessing by injecting correct imports from inventory metadata
- Give `module` and `function` inventory fields a runtime consumer
- Simplify the part prompt by removing the ambiguous import placeholder

**Non-Goals:**
- Making generated scripts runnable standalone (they remain orchestrator-dependent)
- Changing the inventory schema or block implementations
- Modifying how `blocks_needed` is specified in BUILD_PLAN

## Decisions

**Inject imports after extraction, before writing to disk**

After `_extract_python(raw_code)` returns cleaned code, call `_prepend_block_imports(code, part["blocks_needed"], inventory)` before writing to `script_path`. This means the file on disk is always self-consistent: imports are present before the validator runs.

Alternative considered: inject imports at execution time by passing them as `PYTHONSTARTUP` or via a wrapper script. Rejected - the on-disk script would be broken/incomplete, complicating debugging.

**Derive import string from `module` + `function`, no new schema field**

`f"from {b['module']} import {b['function']}"` is unambiguous for all current blocks (1:1 function-to-module). Adding an explicit `import` field would be redundant and create a sync risk.

Alternative considered: explicit `"import"` field in inventory. Rejected - the data to derive it already exists; redundancy introduces drift risk with no current benefit.

**Part prompt instructs LLM not to write imports**

Replace the vague `# from blocks import ...  (only if blocks are listed above)` comment in the script template with an explicit sentence: "Block functions are pre-imported by the runner - do not write import statements for them." This is a direct, unambiguous instruction the LLM can follow.

## Risks / Trade-offs

[LLM writes imports anyway] → The `_extract_python` step won't remove them, and duplicate imports are harmless in Python. Low risk.

[Block not in inventory but listed in `blocks_needed`] → Primary mitigation is `plan_validate.py`, which cross-checks every `blocks_needed` name against the inventory and fails hard before the loop starts. The planning prompt (rule 3) also restricts the LLM to inventory names at generation time. `_prepend_block_imports` silently skips any name not found as a last-resort fallback; in a healthy pipeline this branch is unreachable.

[Retry prompt includes corrected code with orchestrator-injected imports] → `_build_correction_prompt` embeds `prev_code` (the on-disk script, which has imports prepended). When the LLM sees the previous attempt, it sees the import lines and may write them again in the next attempt. Duplicate imports are still harmless, but it's noise. Acceptable for now.

## Migration Plan

No stored state to migrate. The change affects only the orchestrator and the prompt template. Old generated scripts (in `build/`) are unaffected. New builds will produce scripts with injected imports from first run.
