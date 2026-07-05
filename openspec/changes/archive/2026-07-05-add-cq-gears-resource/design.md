## Context

`blocks/` has no gear geometry. `TODO.md:51` flagged `lwidm/cq_gears` (parametric involute spur/helical gears for CadQuery) as worth adding, but the project already has a documented four-way strategy taxonomy for adopting external prior art (`TODO.md` Prior-art ideas: reimplement / pinned dep / vendored snapshot / optional external). `cq_gears` fails the license test for the first three: the GitHub API reports `license: null` (no LICENSE file, no SPDX header found), and this project is PolyForm Noncommercial -- redistributing or bundling code with no stated license is not safe. `cq_warehouse`, by contrast, is a pinned git dependency because it carries a permissive license.

## Goals / Non-Goals

**Goals:**
- Give the planning phase a way to tell the user "gears aren't in the block library; here's an external tool you can install yourself" when a design calls for gears.
- Record the disposition of the `TODO.md:51` item and the license reasoning so it isn't re-litigated.
- Add the project to the README prior-art survey for discoverability.

**Non-Goals:**
- No gear block implementation (`blocks/gears.py` or similar) -- blocked on cq_gears having no license to build against, and cq_gears itself only covers spur/external-helical gears today (internal/bevel/worm are "planned" upstream, not shipped).
- No new `pyproject.toml` dependency, no `uv add`, no vendoring.
- No schema change to `BUILD_PLAN.json` -- gears are not a block name, so nothing is added to `blocks_needed` or `blocks/inventory.json`.

## Decisions

- **Optional-external via `planning_notes`, not a gate check.** The existing "optional external" pattern in this codebase (e.g. `kinematic_check.py` degrading to a `check_skipped` warning without `python-fcl`) applies when a tool is *used if present*. `cq_gears` isn't installed or called at all here -- there's no code path to degrade. So the right surface is the planning prompt: when the design needs gears, the LLM writes the pointer into `planning_notes` for the user to see in the plan review, the same way `shadow_gap` (rule 12) proactively surfaces an unrequested-but-relevant design consideration. Alternative considered: a post-hoc gate warning (like `check_skipped`) -- rejected because the gate operates on already-generated geometry; by the time it would run, the user has already had to hand-write gear geometry from scratch without knowing an external tool existed.
- **Detection is prompt-level, not schema-level.** No `is_gear` flag is added to the plan schema. The planning LLM already reads the full user request and produces `planning_notes`; asking it to recognize "this part is a gear" from the request text (word "gear", "pinion", "cog", tooth-count/module language) is consistent with how dimension-research and `shadow_gap` triggers already work (rule 1, rule 12) -- both are LLM judgment calls recorded in prose, not schema-validated booleans.
- **README row uses `medium` relevance**, matching the existing `rawwerks/VibeCAD` row's treatment of `gggears` (a comparable parametric-gear project already listed as an idea "parallel to `blocks/hardware`", also not adopted directly) -- consistent scoring for two projects in the same no-blocks-yet category.

## Risks / Trade-offs

- [Upstream `cq_gears` license could change or a LICENSE file could be added later, changing the calculus for pinning/vendoring] -> Not tracked automatically; re-check at the point someone proposes an actual gear block.
- [LLM may under- or over-trigger the gear pointer from free-text request parsing] -> Low stakes: the note is additive prose in `planning_notes`, not a gate failure or schema constraint, so a missed trigger just means the user doesn't see the pointer for that one plan, and a false trigger is a harmless extra note.
- [`cq_gears` only covers spur + external-helical gears upstream; internal/bevel/worm are unimplemented] -> Out of scope to track here; the pointer is a resource note, not a claim of completeness. If this becomes a recurring need, a future change can revisit vendoring once/if upstream licenses the project.
