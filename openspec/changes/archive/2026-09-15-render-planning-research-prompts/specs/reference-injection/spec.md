## MODIFIED Requirements

### Requirement: FDM guidelines placeholder substituted across all part blocks for planning
The system SHALL substitute `{{FDM_GUIDELINES}}` in `prompts/planning.md` with all
`always`-tagged sections plus, when a prior `BUILD_PLAN.json` is passed to
`render_prompt.py planning --plan`, the sections matching the union of all
`blocks_needed` across all parts in that plan. A fresh plan (no prior plan) SHALL receive
the `always` sections only.

#### Scenario: Multi-part plan with different blocks per part
- **WHEN** the prior plan has `body` needing `["hollow_box"]` and `lid` needing `["snap_hook_clip"]` and is passed via `--plan`
- **THEN** the planning prompt includes guideline sections for both `hollow_box` and `snap_hook_clip`, plus all `always` sections

#### Scenario: Fresh plan
- **WHEN** `render_prompt.py planning` runs without `--plan`
- **THEN** the planning prompt includes only the `always` FDM sections
