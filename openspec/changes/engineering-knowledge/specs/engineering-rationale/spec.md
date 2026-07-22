# Engineering Rationale

## ADDED Requirements

### Requirement: Load-bearing parts carry an engineering-rationale block

The part prompt (`prompts/part.md`) SHALL require every generated part script to
contain an `ENGINEERING RATIONALE` comment section between the PARAMETERS and MODEL
sections. For a load-bearing part, the block SHALL state (a) the load path, (b) the
worst-case stress location, and (c) at least one computed check: a formula evaluated
with the script's own parameter values, compared against a stated material allowable
(e.g. "strain = 1.5*t*d/L^2 = 1.0% <= 2.0% allowable (PETG)"). The computed check
SHALL reference the script's parameter names, not free-standing constants. A part
with no load-bearing features SHALL instead carry the one-line form
`# ENGINEERING RATIONALE: no load-bearing features (<short reason>)`.

#### Scenario: Snap-fit lid part

- **WHEN** a part whose plan entry uses `snap_hook_clip` is authored
- **THEN** the script contains an ENGINEERING RATIONALE section stating the load
  path, the worst-case stress location, and a computed strain-vs-allowable check
  using the script's arm-thickness/deflection/length parameters

#### Scenario: Cosmetic part

- **WHEN** a part with no declared `load` and no load-bearing blocks is authored
- **THEN** the script contains the one-line rationale stating no load-bearing
  features, with no invented load calculation

#### Scenario: Rationale survives both render modes

- **WHEN** the part prompt is rendered inline or for a cold context (subagent or
  `claude -p`)
- **THEN** the rationale requirement appears in the rendered prompt in both modes,
  and the block is part of the script output (the "output only the Python script"
  contract is unchanged)

### Requirement: Applicability is determined from the plan

Whether a part takes the full rationale block or the one-line form SHALL be
determined from its `BUILD_PLAN.json` entry: the full form applies when the entry
declares a `load`, or when its `blocks_needed` or `archetype` is in the documented
load-bearing set (snap hooks, clips, hooks, brackets, screw bosses, pcb standoffs,
living hinge, dovetail joints). The trigger list SHALL be documented in one place in
the part prompt.

#### Scenario: Plan declares a load

- **WHEN** a part's plan entry declares `load` (any type)
- **THEN** the full rationale block is required regardless of which blocks it uses

#### Scenario: No trigger matches

- **WHEN** a part declares no `load` and none of its blocks or archetype are in the
  load-bearing set
- **THEN** the one-line form is required and suffices

### Requirement: Retry prompts preserve the rationale obligation

A correction prompt for a failed attempt SHALL NOT waive the rationale requirement:
the corrected script SHALL carry an ENGINEERING RATIONALE section consistent with its
(possibly changed) parameter values.

#### Scenario: Parameter changed on retry

- **WHEN** a retry changes a parameter that appears in the rationale's computed check
- **THEN** the corrected script's rationale re-evaluates the check with the new value
