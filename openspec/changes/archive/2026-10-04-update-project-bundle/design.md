## Context

`bundle_project.bundle(root)` copies unconditionally. `skill_version.py` already has
`describe_installed()` and `compare(installed, repo)` over git commits. `init_permissions.py`
merges additively and is safe to re-run. The goal is the minimal fix plus one update path.

## Goals / Non-Goals

**Goals:** know a project's bundle age; refresh it with one command; do not lose user edits to `pyproject.toml`; do not leave dead modules.
**Non-Goals:** re-running or linting existing part scripts after a refresh; three-way merging `pyproject.toml`; auto-installing a newer skill.

## Decisions

- **Stamp = `.bundle_version.json` at project root**, `{commit, dirty, bundled_at}`, taken from `skill_version.describe_installed()` of the skill that ran the bundle. Alternative (stamp inside `lib/`) rejected: `lib/` is pruned/overwritten, root is stable.
- **`--check` compares the stamp commit to the skill's current commit**: equal -> `current`; stamp is an ancestor -> `behind`; no stamp or no commit -> `unknown`. Exit 0 only for `current`.
- **Prune scope is the bundled set only**: delete files under `lib/blocks` and `lib/exporters` that `src/` no longer has, and bundled top-level modules no longer in `BUNDLE_MODULES`. Nothing else in `lib/` is touched (user may add files). Alternative (wipe `lib/`) rejected: loses user additions.
- **`pyproject.toml` / `.python-version`: skip if present**, print a note when content differs. Cheapest; new bundle deps require a manual merge, which the note flags.
- **Permissions merge folded into `main()`**, not `bundle()`: `bundle()` stays a pure file copy because tests import it.
- **Update flow is documentation**, not a new script: a short section in `skill/resume.md` and README. A wrapper for four commands is a single-use abstraction.

## Risks / Trade-offs

- Existing part scripts may break against changed `blocks` signatures -> out of scope; the doc section tells the user to re-run `build/build.py` and read failures.
- A stale `pyproject.toml` can miss new deps -> mitigated only by the differs-note.
- The stamp is not verified against file contents (a hand-edited `lib/` still reads `current`) -> accepted.
