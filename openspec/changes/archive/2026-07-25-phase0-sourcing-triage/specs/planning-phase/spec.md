# Planning Phase (delta)

## ADDED Requirements

### Requirement: Plans derived from found sources record provenance
When a `BUILD_PLAN.json` derives from a source found during Phase 0 sourcing triage (a reused/converted parametric source, an imported BREP, or a rung-4 partial rebuild), `prompts/planning.md` SHALL instruct that `planning_notes` records the source URL, the license, and the sourcing rung under which it was reused. Plans for from-scratch designs (rung 5 or Phase 0 skipped) are unaffected.

#### Scenario: Rung 4 partial rebuild plan
- **WHEN** planning runs for a part rebuilt from a close-fit found mesh
- **THEN** the resulting `BUILD_PLAN.json`'s `planning_notes` contains the found model's URL, its license, and the rung

#### Scenario: From-scratch plan
- **WHEN** planning runs for a request where Phase 0 found nothing usable
- **THEN** no provenance entry is required in `planning_notes`
