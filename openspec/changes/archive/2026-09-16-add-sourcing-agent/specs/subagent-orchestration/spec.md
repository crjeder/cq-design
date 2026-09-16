## ADDED Requirements

### Requirement: Phase 0 sourcing search runs as a sourcing agent
When Phase 0 sourcing triage runs (not skipped by an explicit from-scratch request), the
search workflow (web search, Thingiverse, Printables, MakerWorld, GitHub lookups; opening
result pages and reading descriptions, comments, and licenses) SHALL run in a sourcing
agent whose prompt is the rendered `prompts/sourcing.md`. The agent SHALL return only a
structured candidate list (source URL, platform, kind, license, notes) to the main
session. The five-rung classification, license enforcement, and rung-3 user confirmation
SHALL remain in the main session.

#### Scenario: Heavy pages stay in the sourcing agent
- **WHEN** the sourcing agent opens model listing pages across Thingiverse, Printables,
  and MakerWorld
- **THEN** the main session receives the candidate list and sources, not page snapshots

#### Scenario: Classification stays in the main session
- **WHEN** the sourcing agent returns two candidates, one a parametric source and one a
  mesh
- **THEN** the main session (not the agent) applies the five-rung ladder and picks rung 1

## MODIFIED Requirements

### Requirement: Dimension lookup runs as a research agent
When Phase 1 requires real-world dimension lookups, the lookup workflow (web
search, spec pages, community model pages, STL download + `measure_stl.py`)
SHALL run in a research agent that returns only the dimension validation table
(value, source, status per row) and source URLs. When no lookup is needed, no
research agent is spawned. This is distinct from Phase 0's sourcing agent (see "Phase 0
sourcing search runs as a sourcing agent"): the research agent looks up dimensions of a
named real-world object, not whole reusable models.

#### Scenario: Heavy pages stay in the agent
- **WHEN** the research agent browses spec pages and model listings
- **THEN** the main session receives the validation table and sources, not page
  snapshots
