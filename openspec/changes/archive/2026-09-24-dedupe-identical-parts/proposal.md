## Why

When a plan says two parts are pairwise mirrored (e.g. `wall_a` / `wall_b`), the planner
still emits two `parts[]` entries, so Phase 3 authors, audits, gates, and exports two
near-identical scripts. `TODO.md` ("Mirrored parts dedup") records the model itself
conceding it "over-built" and asking to delete `wall_b.py`. The plan schema has no way
to say "this part is another part, reflected", so the duplication is forced.

## What Changes

- Add an optional `copy_of` object on a part: `{"part": "<source id>", "mirror": "X"|"Y"|"Z"}`
  (`mirror` omitted = identical copy, not reflected).
- A part with `copy_of` has no script, is skipped by the Phase 3 part loop, and is exported
  by reflecting/reusing the source part's geometry, then applying its own `placement`.
- `plan.py validate` checks `copy_of` references (exists, not self, source is not itself a
  copy, source declares no `unions`).
- Planner prompt gains a rule: pairwise-mirrored or identical parts use `copy_of` instead of
  a second full part.

## Capabilities

### New Capabilities
- `part-copies`: `copy_of` schema field, validation, and export behaviour.

### Modified Capabilities

## Impact

- `src/build_plan_schema.json`, `src/plan.py` (validate), `src/model_export.py`,
  `src/units.py` (`iter_unions`), `prompts/planning.md`, `skill/phase3_build.md`,
  `TODO.md`.
- Existing plans without `copy_of` are unaffected.
