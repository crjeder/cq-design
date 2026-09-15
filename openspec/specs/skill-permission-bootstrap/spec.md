# skill-permission-bootstrap

## Purpose

Seed the working directory's project-local Claude settings with the permission patterns the
cq-design pipeline needs, so the user is not prompted for each skill-issued tool call. Also
scaffolds the documented top-level working-directory tree so it exists from the start of a
run instead of appearing piecemeal as different pipeline scripts run.

## Requirements

### Requirement: Bootstrap permissions on first use or explicit init

The skill SHALL write the curated set of permission patterns its pipeline commands require
into the working directory's `.claude/settings.local.json` on the first invocation of the
skill in that directory, and whenever the user explicitly requests init. First use SHALL be
detected by the absence of the skill's sentinel permission pattern in that file; the presence
of the sentinel SHALL cause an ordinary (non-explicit) invocation to skip the bootstrap.

#### Scenario: Fresh working directory

- **WHEN** the skill is invoked in a directory whose `.claude/settings.local.json` does not
  contain the skill's sentinel pattern (and is absent or lacks the skill block)
- **THEN** the skill writes the canonical permission patterns into
  `.claude/settings.local.json` under `permissions.allow`
- **AND** reports the patterns it added

#### Scenario: Already initialized

- **WHEN** the skill is invoked normally (not explicit init) in a directory whose
  `.claude/settings.local.json` already contains the sentinel pattern
- **THEN** the skill skips the bootstrap and makes no write

#### Scenario: Explicit init re-runs the merge

- **WHEN** the user explicitly asks the skill to init in a directory that was initialized by
  an older skill version missing some patterns
- **THEN** the skill re-runs the merge and adds the missing patterns

### Requirement: Idempotent, non-destructive merge

The bootstrap SHALL create `.claude/settings.local.json` (and its parent `.claude/`
directory) when absent, and otherwise merge the canonical patterns into the existing
`permissions.allow` array. The merge SHALL add only patterns not already present, SHALL NOT
remove, reorder, or duplicate existing entries, and SHALL leave all other settings keys
untouched. The same additive, non-destructive discipline SHALL apply to the session-cost
hook entry: it is added under `hooks` only when an equivalent entry is absent, and existing
hook entries (the skill's own or the user's) are never removed or reordered.

#### Scenario: File absent

- **WHEN** the working directory has no `.claude/settings.local.json`
- **THEN** the skill creates `.claude/` and `.claude/settings.local.json` with a
  `permissions.allow` array containing the canonical patterns

#### Scenario: File present with unrelated entries

- **WHEN** `.claude/settings.local.json` already has a `permissions.allow` array with the
  user's own entries
- **THEN** the canonical patterns are appended without removing or reordering the user's
  existing entries
- **AND** other top-level keys in the file are preserved unchanged

#### Scenario: All patterns already present

- **WHEN** every canonical pattern is already in `permissions.allow` and the session-cost
  hook entry is already present
- **THEN** the merge makes no change to the file (no duplicates added)

#### Scenario: User hook entries are preserved

- **WHEN** `.claude/settings.local.json` already defines an unrelated `Stop` hook
- **THEN** the session-cost hook is appended alongside it and the user's entry is left
  unchanged

### Requirement: Session-cost hook seeded on bootstrap

Whenever the permission merge runs (fresh directory, or explicit re-init), the skill SHALL
also seed a `Stop` hook into the working directory's project-local
`.claude/settings.local.json` that runs `src/session_cost.py` in hook mode. The seeded
command SHALL reference `session_cost.py` by an absolute path resolved at seed time, SHALL
run without a network dependency, and SHALL be the only hook the bootstrap adds. The hook
SHALL NOT be written to global settings or the skill's own directory.

#### Scenario: Fresh working directory gets the hook

- **WHEN** the skill bootstraps a directory with no `.claude/settings.local.json`
- **THEN** the resulting file has a `Stop` hook whose command invokes `session_cost.py` in
  hook mode by absolute path

#### Scenario: Re-init does not duplicate the hook

- **WHEN** the bootstrap runs again in a directory whose settings already carry the
  session-cost `Stop` hook
- **THEN** no second copy of the hook is added

#### Scenario: Bootstrap output names the hook

- **WHEN** the bootstrap seeds the hook
- **THEN** its reported summary names the session-cost hook alongside the count of
  permission patterns added

### Requirement: Canonical permission set scoped to skill commands

The canonical pattern set SHALL be a single documented list covering the command shapes the
pipeline issues — the `uv run`/`python`/`uv sync` tool invocations, the self-contained-build
file copies and directory creation, and dimension-lookup `WebSearch`/`WebFetch` for the maker
sources the skill names — expressed as wildcard patterns that match regardless of the
interpolated skill directory path and per-part arguments, and including both Bash and
PowerShell variants. The set SHALL NOT include destructive command shapes, and SHALL be
written only to the working directory's project-local settings (never global settings or the
skill's own directory).

#### Scenario: Patterns absorb path and argument variation

- **WHEN** the skill later runs `uv run --project "<skill_dir>" python "<skill_dir>/src/run_cadquery_model.py" build/part.py --preview`
- **THEN** that call matches a seeded allow pattern and does not prompt

#### Scenario: Both shells covered

- **WHEN** the skill issues a command via PowerShell on Windows or via Bash on POSIX
- **THEN** a seeded pattern for the corresponding shell matches the command shape

#### Scenario: Destructive shapes excluded

- **WHEN** the canonical set is inspected
- **THEN** it contains only read, scaffold, and build command shapes — no delete/overwrite
  verbs beyond the skill's own build-bundle copies into the working directory

### Requirement: Working-directory tree is scaffolded on bootstrap

Whenever the permission merge runs (fresh directory, or explicit re-init), the skill SHALL
also create the working directory's top-level `build/`, `stl/`, and `preview/` directories if
absent, so the layout documented for the pipeline exists from the first invocation rather than
being created one at a time by whichever script needs it first. The scaffold SHALL be
idempotent and SHALL NOT touch a directory's existing contents.

#### Scenario: Fresh working directory

- **WHEN** the permission merge runs in a directory with none of `build/`, `stl/`, `preview/`
- **THEN** all three are created

#### Scenario: Directories already exist

- **WHEN** the permission merge runs in a directory where `build/` already contains part
  scripts
- **THEN** `build/`'s existing contents are left untouched and no error occurs

#### Scenario: Re-running the scaffold is a no-op

- **WHEN** the permission merge runs again in an already-scaffolded directory
- **THEN** no directories are reported as newly created
