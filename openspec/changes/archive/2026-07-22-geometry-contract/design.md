## Context

`src/cq_verify.py` already provides three construction-time assertions
(`verify_boolean`, `verify_feature_bounds`, `check_workplane`) that a generated part
script imports under the wrapper's `PYTHONPATH`. Each wraps a post-operation
Workplane/solid, raises a marked `RuntimeError` (`[cq-verify:<kind>:<label>] ...`) on
failure, and returns its argument unchanged on success so it chains inline.
`run_cadquery_model.py` catches these marked errors and maps them to typed
`silent_boolean`/`feature_overflow`/`workplane_drift` entries in its JSON `errors`
list. This change adds a fourth helper, `verify_stage`, following the same shape, for
scratch (non-block, non-archetype) parts that currently have no construction-time
checkpoint at all until the whole script finishes.

## Goals / Non-Goals

**Goals:**
- Let a scratch part script assert an expected bbox and/or minimum volume at a named
  construction stage, failing immediately with that stage's name on mismatch.
- Reuse the existing marked-`RuntimeError` / typed-error convention so
  `run_cadquery_model.py`'s error handling and the part loop's retry-prompt logic
  need only one additional case, not a new mechanism.
- Make the construction-plan requirement apply only where it earns its keep: scratch
  geometry with no block or archetype template already supplying verified topology.

**Non-Goals:**
- Not a general-purpose CAD assertion DSL. `verify_stage` checks bbox and/or volume
  only, matching what `measure_stl.py`/the wrapper's geometry block already compute
  elsewhere.
- Not applied retroactively to block- or archetype-based parts, which already inherit
  correct topology and don't need staged assertions.

## Decisions

- **Shape mirrors `verify_feature_bounds`**: `verify_stage(wp, label, bbox=None,
  vol_min=None)` takes the workplane/solid post-stage, an expected bbox tuple and/or
  a minimum volume (both optional, at least one required), and returns `wp`
  unchanged on success. Chains inline exactly like the other three helpers.
  Alternative considered: a stage-tracking context manager (`with
  stage("base_shell"): ...`) -- rejected as a bigger surface change for no benefit
  over an inline call, and inconsistent with the other three helpers' style.
- **Error type**: `stage_mismatch`, mapped in `run_cadquery_model.py` next to the
  existing three. Reuses the same `[cq-verify:<kind>:<label>]` marker convention so
  the wrapper's existing marked-error regex/parsing extends by one kind rather than
  needing new parsing logic.
- **Scope of the construction-plan requirement**: lives in `prompts/part.md`'s
  guidance for the scratch-authoring fallback path only (Step 1.5's "no archetype
  match" branch), not as a new schema field or lint rule -- keeping this a prompting
  change, consistent with how the existing `verify_boolean`/`check_workplane`
  guidance is already prose-level in `prompts/part.md` rather than mechanically
  enforced.

## Risks / Trade-offs

- [A stage assertion with a loose bbox/volume tolerance could pass even when
  topology is wrong in a way that doesn't move the bbox or volume much] → Mitigation:
  this is advisory-strength like the existing helpers; it catches the common case
  (wrong stage entirely) and is not claimed as a complete correctness proof.
- [Prompt-level requirement, not mechanically enforced by `script_lint.py`] →
  Mitigation: out of scope for this change; `script_lint.py`'s AST checks could gain
  a `missing_stage_plan` finding later if telemetry (item 8) shows scratch parts
  skipping it.

