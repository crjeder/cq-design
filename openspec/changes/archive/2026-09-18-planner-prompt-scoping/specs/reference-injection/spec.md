## MODIFIED Requirements

### Requirement: FDM guidelines placeholder substituted across all part blocks for planning
The system SHALL substitute `{{FDM_GUIDELINES}}` in `prompts/planning.md` with all
`planning`-tagged sections of `reference/FDM 3D Print Design Guidelines.md` plus, when a
prior `BUILD_PLAN.json` is passed to `render_prompt.py planning --plan`, the sections
matching the union of all `blocks_needed` across all parts in that plan. A fresh plan (no
prior plan) SHALL receive the `planning`-tagged sections only. The `planning` tag SHALL be
distinct from `always` (which continues to govern part/builder rendering unchanged): a
section MAY carry both tags when it is relevant to both phases.

#### Scenario: Multi-part plan with different blocks per part
- **WHEN** the prior plan has `body` needing `["hollow_box"]` and `lid` needing `["snap_hook_clip"]` and is passed via `--plan`
- **THEN** the planning prompt includes guideline sections for both `hollow_box` and `snap_hook_clip`, plus all `planning`-tagged sections

#### Scenario: Fresh plan
- **WHEN** `render_prompt.py planning` runs without `--plan`
- **THEN** the planning prompt includes only the `planning`-tagged FDM sections

#### Scenario: Section relevant to both phases
- **WHEN** a section is tagged `<!-- applies_to: always, planning -->`
- **THEN** it is selected for both the planner render and the builder/part render

#### Scenario: Builder rendering is unaffected
- **WHEN** a part prompt is rendered (inline or cold-context)
- **THEN** FDM section selection still uses the `always` tag plus block matches, unchanged from before this requirement's update
