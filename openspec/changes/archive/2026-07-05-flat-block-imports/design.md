## Context

`from blocks import <fn>` already works: `blocks/__init__.py` re-exports every block flat, `run_cadquery_model.py` sets `PYTHONPATH=src`, and `run_model_shim.py` executes the script via `runpy` with no import injection. CLAUDE.md (lines 93-97) already mandates flat imports and forbids submodule imports and injection. The defect is purely in the instruction surface: `prompts/part.md` is self-contradictory (L11 vs L51), SKILL.md tells a per-submodule story in three places, and the `block-import-injection` spec documents an orchestrator deleted in the 2026-05-27 inline-orchestration change. This change makes every instruction match the shipping behavior and CLAUDE.md.

## Goals / Non-Goals

**Goals:**
- One block-import story across part.md, SKILL.md, CLAUDE.md, and the spec: flat `from blocks import <fn>`, model-written, no runtime injection.
- Remove the affirmative wrong instruction at `part.md:51` that would break the build if obeyed literally.
- Rewrite the `block-import-injection` spec to the surviving contract.

**Non-Goals:**
- No change to `blocks/__init__.py`, the runner, or the shim -- behavior already ships.
- No renaming of the `block-import-injection` capability directory (out of scope; the requirement text carries the new meaning).
- No change to how blocks are selected during planning or to `{{BLOCK_SPECS}}` rendering.

## Decisions

- **Flat over per-submodule.** Choose `from blocks import <fn>` (CLAUDE.md's existing convention) over SKILL.md's `from blocks.<module> import <fn>`. Rationale: the flat re-export in `blocks/__init__.py` already dissolves the "which submodule?" problem that per-submodule imports (and the old injector) existed to solve; flat needs no inventory module-lookup step and never requires module info in `{{BLOCK_SPECS}}`. Alternative (converge on per-submodule) rejected: smaller doc edit but keeps the lookup ceremony and directly contradicts CLAUDE.md's explicit "not from individual submodules."
- **Remove, not repurpose-by-rename.** Keep the `block-import-injection` directory name; express the new behavior by removing the orchestrator requirement and adding the script-side contract. Renaming the capability is not supported cleanly by the delta workflow and adds churn for no behavioral gain.
- **Add a guard test.** A small test that (a) imports every `inventory.json` block via `from blocks import <name>` and (b) asserts the shim adds no imports, to keep the spec's new scenarios enforced. Optional but cheap and prevents future drift.

## Risks / Trade-offs

- [Capability name `block-import-injection` becomes a misnomer once it no longer describes injection] -> Acceptable; the requirement text is authoritative and a rename can be a separate cleanup.
- [Docs-only change could drift again] -> Mitigated by the guard test tying the flat-import contract to CI.
- [A future model still sees flat vs per-submodule examples elsewhere in reference/ files] -> Migration step greps reference/ and planning.md to confirm no competing import guidance remains.
