## MODIFIED Requirements

### Requirement: Phase 0 runs before requirements analysis
The skill SHALL provide a Phase 0 sourcing triage, documented in `skill/phase0_sourcing.md` and entered before Phase 1, that searches for existing models answering the user's request before any from-scratch design begins. The search SHALL be dispatched to the Sourcing agent (rendered `prompts/sourcing.md`, see the `sourcing-prompt-rendering` and `subagent-orchestration` capabilities) rather than run inline or reuse Phase 1's search workflow by reference. The user SHALL be able to skip Phase 0 by requesting a from-scratch design explicitly.

#### Scenario: Standard request enters Phase 0 first
- **WHEN** the user requests a model without saying "design from scratch"
- **THEN** the skill reads `skill/phase0_sourcing.md`, dispatches the Sourcing agent, and receives a candidate list before Phase 1 requirements analysis

#### Scenario: Explicit from-scratch request skips Phase 0
- **WHEN** the user asks to design the model from scratch
- **THEN** Phase 0 is skipped, no Sourcing agent is spawned, and the pipeline starts at Phase 1

#### Scenario: Custom-dimension request gets the quick pass
- **WHEN** the request is dominated by user-specific dimensions or interfaces
- **THEN** the Sourcing agent is asked to run a single quick search pass rather than the full ladder before falling through to Phase 1
