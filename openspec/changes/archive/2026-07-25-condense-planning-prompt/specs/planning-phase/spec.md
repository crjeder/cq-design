## ADDED Requirements

### Requirement: Planning prompt rules are uniquely numbered

`prompts/planning.md`'s Rules section SHALL assign each rule a unique identifier
(a bare number, or a number with a lettered suffix such as `3a`), with no two rules
sharing the same identifier. Other documents in the repository (e.g.
`skill/phase2_planning.md`, `skill/phase3_build.md`) cite specific rules by this
identifier; a duplicate identifier makes such a citation ambiguous.

#### Scenario: No duplicate rule identifiers

- **WHEN** `prompts/planning.md`'s Rules section is scanned for its rule identifiers
- **THEN** every identifier appears exactly once

#### Scenario: Cross-referenced rule identifiers stay resolvable

- **WHEN** another document in the repository cites a `prompts/planning.md` rule by
  number (e.g. "rule 14")
- **THEN** exactly one rule in the current `prompts/planning.md` carries that
  identifier, and its subject matter matches what the citing document describes
