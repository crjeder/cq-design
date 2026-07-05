## Why

`TODO.md:51` notes "add https://github.com/lwidm/cq_gears" with no disposition. `cq_gears` (lwidm/cq_gears) generates parametric involute spur and helical gears for CadQuery via exact analytical curve equations -- a gap in `blocks/`, which has no gear geometry today. It cannot be pinned as a dependency or vendored the way `cq_warehouse` is: the upstream repo declares no license (`license: null` via the GitHub API), and this project is PolyForm Noncommercial, so bundling or redistributing it without an explicit grant is not safe. The only available integration is "optional external" (per the strategy taxonomy already recorded in `TODO.md`'s Prior-art section): point the user at it as a downloadable resource when their design needs gears, rather than shipping it.

## What Changes

- Planning phase: when the user's request or resulting plan involves gears, the planning prompt surfaces a note that `blocks/` has no gear geometry yet and points to `https://github.com/lwidm/cq_gears` as an external resource the user can download and install themselves; this is recorded in `planning_notes`, not silently skipped.
- `README.md`: add `lwidm/cq_gears` to the Prior art table (relevance `medium`, no-license caveat noted).
- `TODO.md`: remove the bare line-51 TODO now that it has a disposition; record the "optional external, no license" reasoning under Prior-art ideas alongside the existing strategy taxonomy.
- No new dependency, no new block, no change to `pyproject.toml` or `blocks/inventory.json`.

## Capabilities

### New Capabilities
- none

### Modified Capabilities
- `planning-phase`: add a requirement that the planning prompt/skill surfaces the `cq_gears` external-resource pointer in `planning_notes` when the design involves gears, since no gear block exists in the inventory.

## Impact

- `prompts/planning.md` -- one new rule (gear pointer), analogous to the existing `shadow_gap` proactive-proposal rule (item 12).
- `README.md` -- one new Prior art table row.
- `TODO.md` -- line 51 removed; a short disposition note added under Prior-art ideas.
- `openspec/specs/planning-phase/spec.md` -- one new requirement + scenarios.
- No `src/` code change, no new/changed dependency.
