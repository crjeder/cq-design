## Why

The builder and auditor prompts are rendered by `src/render_prompt.py`, but the planner
prompt is still assembled by hand in the main session (`skill/phase2_planning.md:5-13`):
Claude reads `src/blocks/inventory.json`, `templates/archetypes.json`, the FDM guidelines
and `printer_profile.json` only to fill five placeholders. The research prompt
(`skill/phase1_requirements.md:94`) is filled the same way. Those files then sit in the
main session's context for the rest of the run, and each hand render can condense them
differently, so the planner's input drifts between runs.

## What Changes

- Add a `planning` subcommand to `render_prompt.py` that renders `prompts/planning.md`
  from a request text file, the block inventory, the archetype index, the `always`-tagged
  FDM sections (plus the sections for an existing plan's blocks on a re-plan), and the
  validated printer profile. It writes `build/planning_prompt.txt` and reports whether the
  profile was loaded.
- Add a `research` subcommand that renders `prompts/research.md` from a lookup-targets
  file and an optional known-context file, writing `build/research_prompt.txt`.
- Restructure `render_prompt.py`'s CLI so `--plan`/`--part` stay required for `builder`
  and `audit` only.
- Replace the hand-substitution instructions in `skill/phase2_planning.md` and
  `skill/phase1_requirements.md` with the render command and the
  "Read <out> in full and follow it" spawn line already used in Phase 3.
- Resolve the FDM guideline contradiction: the existing specs require the union of every
  part's `blocks_needed`, which does not exist before the first plan. Fresh plans get the
  `always` sections; re-plans also get the prior plan's blocks.

## Capabilities

### New Capabilities
- `planner-research-prompt-rendering`: `render_prompt.py planning` and `research` modes --
  inputs, placeholder sources, output path, JSON report, and unfilled-placeholder failure.

### Modified Capabilities
- `planning-phase`: the planning prompt is rendered by `render_prompt.py planning`, adds
  `{{ARCHETYPE_INDEX}}` to the listed placeholders, and the FDM union rule applies only on
  a re-plan.
- `reference-injection`: the planning FDM-guidelines requirement uses the prior plan's
  blocks when one exists and `always` sections alone otherwise.

## Impact

- `src/render_prompt.py` (two new render functions, CLI restructure)
- `tests/test_render_prompt.py`
- `skill/phase1_requirements.md`, `skill/phase2_planning.md`, `SKILL.md`,
  `ARCHITECTURE.md`, `CLAUDE.md` (doc pointers)
- No new dependencies; reuses `printer_profile_validate.validate_profile` and
  `tagged_sections`.
