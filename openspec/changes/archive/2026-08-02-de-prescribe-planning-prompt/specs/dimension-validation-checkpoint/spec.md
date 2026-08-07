## REMOVED Requirements

### Requirement: Dimension lookups are announced before they start

**Reason**: Forced-narration scaffolding. Two grounds: 5-series models do not need a
rule telling them to narrate what they are about to do, and the requirement is no longer
satisfiable as written - Phase 1's dimension lookups run inside a research agent that has
no user channel, so "the skill outputs a message" cannot happen per lookup.

**Migration**: None for users. The user-visible artifact is unchanged: after the research
agent returns, main presents the Dimension validation checkpoint table (Item / Value /
Source / Status) and waits for approval or correction. The **Lookup narration** paragraph
in `skill/phase1_requirements.md` is deleted with this requirement.
