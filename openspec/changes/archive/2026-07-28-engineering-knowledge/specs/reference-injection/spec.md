# Reference Injection (delta)

## ADDED Requirements

### Requirement: Engineering design rules are tag-filtered and mode-rendered like the FDM guide

There SHALL be a `reference/Engineering Design Rules.md` containing only numeric
engineering content - material constants (allowable strain, flexural modulus per
material), snap-fit formula coefficients, rib/boss/gusset ratio limits, insert and
clearance deltas not already in `hardware_dims.md` - with no prose tutorials, using
`<!-- applies_to: block1, block2 -->` section tags with the same vocabulary as the
FDM guide (including `always` for material constants). Section selection for a part
SHALL intersect `applies_to` with the part's `blocks_needed` plus `always`-tagged
sections, and SHALL additionally select all load-relevant sections when the part
declares a plan `load`. Rendering SHALL follow the existing mode split: an inline
part render cites the selected section names as already-in-context material; a
cold-context render (subagent or `claude -p`) receives the selected sections' full
bodies. An untagged section SHALL be excluded from all selections.

#### Scenario: Snap-fit part in a cold context

- **WHEN** a part with `blocks_needed: ["snap_hook_clip"]` is rendered for a cold
  context
- **THEN** the rendered prompt contains the snap-fit coefficient section body and
  all `always`-tagged constant sections, and excludes sections tagged only for
  unrelated blocks

#### Scenario: Same part rendered inline

- **WHEN** the same part is rendered inline
- **THEN** the prompt cites the selected section names of
  `reference/Engineering Design Rules.md` without their bodies

#### Scenario: Part with a declared load but no tagged blocks

- **WHEN** a part declares `load` in its plan entry and uses no load-bearing blocks
- **THEN** the load-relevant sections are still selected for it, plus `always`
  sections

#### Scenario: Non-load-bearing part

- **WHEN** a part with no `load` and no matching block tags is rendered
- **THEN** only `always`-tagged sections are selected (cited inline, injected cold)
