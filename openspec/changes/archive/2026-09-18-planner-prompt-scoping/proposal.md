## Why

Two prompts carry content that is scoped wider than the phase that reads it, inflating
main-session context for no benefit:

1. **Planning prompt**: `render_planning` calls `tagged_sections(...)` against the FDM
   guidelines using the `always` tag. 14 of the file's 20 sections are tagged `always`,
   so nearly every builder-facing modeling-mechanics section (chamfer/fillet mechanics,
   cosmetic slopes, warping, vase mode, print-in-place clearances, text/surface finish)
   rides into the ~43K planner prompt even though the planner makes structural decisions
   (part count, splits, materials, interfaces), not modeling-mechanics ones. Only a
   handful of `always` sections are actually planning-relevant (baseline tolerances,
   print-orientation splitting, load-orientation declaration, the tolerance-compensation/
   shadow-gap proposal rule).
2. **Phase 0 sourcing**: `skill/phase0_sourcing.md` (8.5K, read into the main session
   every request) spends ~20 lines/most of its length on license-reusability rules
   (no-license = all-rights-reserved, ND blocks rungs 1/2/4, rung-3 ND exception) that
   the main session applies by hand to a per-candidate license string the sourcing agent
   already read off the source page. The agent has the page in front of it; it can apply
   the same rules and return a verdict instead of a raw string.

## What Changes

- Add a `planning` tag value to `<!-- applies_to: ... -->` sections in
  `reference/FDM 3D Print Design Guidelines.md`, applied to the subset of currently
  `always`-tagged sections that inform planning-level (structural/BUILD_PLAN) decisions:
  Baseline & Tolerances, Print Orientation, Strength & Load Orientation, and Make It
  Adjustable (Tolerance Compensation). Sections keep their existing `always` tag for the
  builder/part path unchanged.
- Change `render_planning` (`src/render_prompt.py`) to select FDM sections by the
  `planning` tag (plus any block-matched sections, unchanged) instead of `always`, for
  both the fresh-plan and prior-plan cases.
- Move license-reusability determination from `skill/phase0_sourcing.md`'s prose rules
  into the Sourcing agent: the agent's return table gains a `Reusable` column stating the
  rung-scoped verdict (e.g. `yes`, `no (ND, no-derivatives)`, `rung-3-only (ND,
  redistribution permitted)`, `no (none stated)`), computed from the same rules, which
  move into `prompts/sourcing.md`. `skill/phase0_sourcing.md`'s License check section
  shrinks to trusting the agent's verdict column plus the unchanged provenance-recording
  instructions (what to record, not how to derive it).
- **BREAKING** (internal contract only): the Sourcing agent's return table gains a
  required `Reusable` column; any code or docs assuming the prior 5-column table shape
  must be updated in the same change.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `reference-injection`: the "FDM guidelines placeholder substituted across all part
  blocks for planning" requirement changes from selecting `always`-tagged sections to
  selecting `planning`-tagged sections (plus block-matched sections, unchanged).
- `sourcing-triage`: the "License check is mandatory at reuse rungs" requirement changes
  from being applied by the main session against a raw license string to being applied by
  the Sourcing agent, which returns a per-candidate reusability verdict the main session
  trusts. `prompts/sourcing.md`'s return contract (implementation of this requirement)
  gains the `Reusable` column and the license-rule prose that produces it;
  `render_prompt.py`'s `sourcing` subcommand itself is unaffected (no new placeholder, so
  `sourcing-prompt-rendering` has no requirement change).

## Impact

- `reference/FDM 3D Print Design Guidelines.md`: add `planning` to 4 sections' tags.
- `src/render_prompt.py`: `render_planning`'s `tagged_sections(...)` call for FDM
  guidelines switches scope from `always` to `planning`.
- `prompts/sourcing.md`: return contract gains a `Reusable` column; license rules
  (no-license, ND blocking, rung-3 exception) move in from `skill/phase0_sourcing.md`.
- `skill/phase0_sourcing.md`: License check section shortens to trusting the agent's
  verdict; ladder/provenance instructions unchanged.
- Tests: `tests/test_render_prompt.py` (planning FDM section selection) and any sourcing
  return-contract fixtures need updating for the new column/tag.
