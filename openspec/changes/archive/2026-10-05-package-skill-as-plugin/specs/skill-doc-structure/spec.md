## MODIFIED Requirements

### Requirement: Core SKILL.md stays under 10 KB
SKILL.md SHALL contain only always-needed content - trigger, overview, phase
overview with per-phase summaries and read pointers, prerequisites pointer,
a pointer to the plugin `commands/` directory, JSON contract, typed-error reference, DFM constraint
values, coordinate system, generated script rules, and the key-files quick
reference - and SHALL be under 10 KB.

#### Scenario: Trigger load cost
- **WHEN** the skill triggers for any invocation (`/cq-design:render`, `/cq-design:deliver`,
  `/cq-design:plan`, or a full design request)
- **THEN** the initially loaded SKILL.md is under 10 KB and contains no phase-local
  step-by-step procedures
