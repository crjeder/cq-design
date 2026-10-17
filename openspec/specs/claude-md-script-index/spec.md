## Purpose

Keeps `CLAUDE.md` a short, current index of `src/` and `evals/` scripts
instead of duplicating their full contracts, so per-script detail has one
authoritative home (`reference/scripts.md`) and doesn't drift out of sync
with `CLAUDE.md`.
## Requirements
### Requirement: CLAUDE.md lists each script's one-line description exactly once
The repository SHALL contain exactly one one-line-per-script index of `src/` and
`evals/` scripts, in the directory tree in `FILES.md`. `CLAUDE.md` SHALL point to
`FILES.md` for the repository layout and SHALL NOT carry its own layout tree.
Full per-script contract detail (JSON shapes, CLI flags, typed error names, edge
cases) SHALL live in `reference/scripts.md` for `src/` scripts and in
`evals/README.md` for `evals/` scripts, and neither `CLAUDE.md` nor `FILES.md`
SHALL restate that detail.

#### Scenario: Single index in File Layout
- **WHEN** a reader looks for what a script does
- **THEN** they find its one-line description in `FILES.md`'s directory tree, and
  `CLAUDE.md`'s `File Layout` section links to `FILES.md` instead of repeating it

#### Scenario: Full detail lives in reference/scripts.md
- **WHEN** a reader needs a `src/` script's JSON contract, CLI flags, or typed
  error names before modifying or calling it
- **THEN** `CLAUDE.md` and `FILES.md` point them to `reference/scripts.md`

#### Scenario: Eval detail stays out of the shipped reference
- **WHEN** a reader needs `evals/run_evals.py`'s scoring contract
- **THEN** it is in `evals/README.md`, and `reference/scripts.md` does not mention
  `evals/`

#### Scenario: Adding a new script
- **WHEN** a new script is added under `src/` or `evals/`
- **THEN** it is documented in exactly two places: a one-line entry in
  `FILES.md`'s tree, and a full contract entry in `reference/scripts.md` (for
  `src/`) or `evals/README.md` (for `evals/`)

