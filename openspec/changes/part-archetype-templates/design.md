# Design: Part Archetype Templates

## Context

Every from-scratch part today is authored as raw fluent CadQuery from a blank file. The 34 blocks cover attachable features (bosses, cutouts, hooks) but not whole-part topology; anything block-shaped is safe, everything else re-derives OCC-fragile idioms per attempt. IMPROVEMENT_PLAN.md item 2 names this the highest-leverage fix for from-scratch parts: a library of proven whole-part scripts, matched before authoring.

Existing machinery this builds on:

- `blocks/inventory.json` + `blocks/validate.py` establish the pattern for a machine-readable, schema-validated catalog.
- `src/script_lint.py` and `src/run_cadquery_model.py` define the pre-verification bar a template must pass.
- `src/cq_verify.py` provides the guards templates ship with pre-placed.
- The Phase 3 part loop in `skill/phase3_build.md` already has numbered steps (Step 2.5 lint precedent) to hang "Step 1.5 - match archetype" on.

## Goals / Non-Goals

**Goals:**

- Ship a first set of ~10 archetype templates covering the recurring request shapes.
- Machine-readable index so both the planner and the part loop can match without reading every script.
- Make template-copy-and-edit the default authoring path; blank-file raw authoring the explicit fallback.
- Every template verifiably passes lint + geometry validation in CI (tests), so "pre-verified" is enforced, not asserted.

**Non-Goals:**

- No new runtime code path: templates are inputs to the LLM authoring step, not imported modules. A part script that started from a template is a normal standalone script; the wrapper, exporters, and gate see no difference.
- No template composition/inheritance system. One archetype = one flat script. Combining archetypes is the LLM's editing job.
- No measured-baseline gating in this change: the eval-harness comparison (item 8) consumes this change's output but is not implemented here.
- Blocks are untouched; templates import and use blocks like any generated script.

## Decisions

**1. Templates are copy sources, not a Python package.**
A template is a complete, runnable part script (`result` variable, top-level PARAMETERS block, `from blocks import ...`, `cq_verify` guards). The part loop copies its text into the part's script and edits it. Alternative - a `templates` package of parametric functions called at runtime - was rejected: it would make every archetype a second block API to design, version, and inject, and would hide topology from the LLM instead of handing it over for delta edits. Copy-and-edit keeps the existing one-script-per-part contract byte-identical.

**2. `templates/archetypes.json` mirrors the inventory pattern.**
Index entries: `name` (kebab-case, unique), `file` (relative path in `templates/`), `use` (plain-English matching description), `params` (name -> unit/description), `aliases` (matching synonyms, e.g. "box" -> enclosure-body). Validated by `templates/archetypes_schema.json` (JSON Schema draft-7, same as the inventory) and a loader test that also asserts every listed `file` exists and every template file is listed. Alternative - deriving the index from docstrings - rejected as a parsing liability for no benefit at ~10 entries.

**3. Planner records the match; part loop confirms it.**
`src/build_plan_schema.json` gains an optional per-part `archetype` (string). `prompts/planning.md` instructs the planner to set it when a part matches an archetype's `use` description, else omit it. `src/plan_validate.py` cross-checks a present value against `templates/archetypes.json` exactly as `blocks_needed` is checked against the inventory. In the part loop, Step 1.5 uses the planned value when present, otherwise does its own match against the index; a non-match falls back to raw authoring with a one-line stated reason. Rationale: the planner has whole-model context (which lid style, which bracket), but making the field optional keeps old plans valid and keeps matching working when the planner abstains.

**4. Pre-verification is enforced by a test, not by convention.**
New `tests/test_templates.py` parametrizes over every index entry: (a) `script_lint.py` reports zero findings, (b) `run_cadquery_model.py` (or direct in-process execution mirroring the wrapper, matching existing integration-test style) yields valid watertight geometry with default parameters. This is the "known-good" guarantee; a broken template fails CI, not a user session. Templates follow the same constraints generated scripts must satisfy (named parameters, no magic numbers in chains, guarded booleans), so lint cleanliness is achievable by construction.

**5. Initial archetype set (from the plan, one script each).**
`enclosure_body`, `lid_sliding`, `lid_snap`, `lid_screwed`, `adapter_ring_flanged`, `l_bracket_gusset`, `plate_boss_pattern`, `hook`, `clip`, `stand`. Lids are separate archetypes rather than one parameterized lid: their topologies differ (rails vs. cantilever hooks vs. bosses), and flat separate scripts beat a mode-switching script for copy-and-edit clarity.

**6. Skill-doc changes stay minimal.**
`skill/phase3_build.md` gets Step 1.5 (match -> copy -> edit params -> apply deltas; fallback rule); `prompts/planning.md` gets one rule plus the index substituted alongside the block inventory. SKILL.md itself only gains the pointer, consistent with the split-doc structure.

## Risks / Trade-offs

- [Wrong-archetype match produces a worse starting point than a blank file] -> The match is advisory: Step 1.5 requires the part loop to confirm the template's `use` description against the part spec before copying, and the fallback is always available. A mismatch surfaces at the same visual review that catches raw-authoring topology errors.
- [Templates rot as lint rules / wrapper checks evolve] -> `tests/test_templates.py` runs the real lint and validation, so any tightened rule that breaks a template fails the suite immediately.
- [Heavy template edits ("enclosure but cylindrical") negate the inherited-topology benefit] -> Accepted: the archetype covers the common case; the fallback covers the rest. The eval harness (item 8) is the instrument that shows where the boundary lies.
- [Ten CadQuery-executing tests slow the suite] -> Same cost profile as existing integration tests (a few seconds each); the lint half of the test is milliseconds and runs without CadQuery.

## Open Questions

- Whether the part prompt (`prompts/part.md`) should embed the copied template text or reference it by path for the authoring LLM - resolved at implementation time by following the item-13 convention (cite in-context material, substitute only cold-context prompts).
