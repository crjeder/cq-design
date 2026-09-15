## ADDED Requirements

### Requirement: CLAUDE.md lists each script's one-line description exactly once
`CLAUDE.md` SHALL contain exactly one one-line-per-script index of `src/` and
`evals/` scripts. Full per-script contract detail (JSON shapes, CLI flags,
typed error names, edge cases) SHALL live only in `reference/scripts.md`, and
`CLAUDE.md` SHALL point to it rather than restating that detail.

#### Scenario: Single index in File Layout
- **WHEN** a reader looks in `CLAUDE.md` for what a script does
- **THEN** they find its one-line description in the `File Layout` section's
  directory tree, and nowhere else in `CLAUDE.md`

#### Scenario: Full detail lives in reference/scripts.md
- **WHEN** a reader needs a script's JSON contract, CLI flags, or typed
  error names before modifying or calling it
- **THEN** `CLAUDE.md`'s `File Layout` section points them to
  `reference/scripts.md` for that detail

#### Scenario: Adding a new script
- **WHEN** a new script is added under `src/` or `evals/`
- **THEN** it is documented in exactly two places: a one-line entry in
  `CLAUDE.md`'s `File Layout` tree, and a full contract entry in
  `reference/scripts.md` — not in a third, separate summary table
