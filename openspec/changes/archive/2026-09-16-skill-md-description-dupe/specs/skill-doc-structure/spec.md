## ADDED Requirements

### Requirement: SKILL.md body does not restate frontmatter-owned trigger content
SKILL.md's body SHALL NOT restate, summarize, or gesture at the natural-language
trigger phrases carried by the frontmatter `description` field. The frontmatter
`description` is the sole source of truth the dispatcher matches against to decide
whether the skill triggers; the body is only loaded into context after that decision
has already been made, so any body text referring to "natural-language triggers" or
similar cannot influence triggering and only duplicates content that lives in the
frontmatter.

#### Scenario: Command table row referencing natural-language triggering
- **WHEN** SKILL.md's command-reference table lists the `/cq-design` entry point
- **THEN** the row names only the slash command itself, with no phrase pointing back
  to natural-language trigger phrases already enumerated in the frontmatter
  `description`
