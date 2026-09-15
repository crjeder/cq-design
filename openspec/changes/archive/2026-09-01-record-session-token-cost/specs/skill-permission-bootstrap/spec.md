## MODIFIED Requirements

### Requirement: Idempotent, non-destructive merge

The bootstrap SHALL create `.claude/settings.local.json` (and its parent
`.claude/` directory) when absent, and otherwise merge the canonical patterns
into the existing `permissions.allow` array. The merge SHALL add only patterns
not already present, SHALL NOT remove, reorder, or duplicate existing entries,
and SHALL leave all other settings keys untouched. The same additive,
non-destructive discipline SHALL apply to the session-cost hook entry: it is
added under `hooks` only when an equivalent entry is absent, and existing hook
entries (the skill's own or the user's) are never removed or reordered.

#### Scenario: File absent

- **WHEN** the working directory has no `.claude/settings.local.json`
- **THEN** the skill creates `.claude/` and `.claude/settings.local.json` with a
  `permissions.allow` array containing the canonical patterns

#### Scenario: File present with unrelated entries

- **WHEN** `.claude/settings.local.json` already has a `permissions.allow` array
  with the user's own entries
- **THEN** the canonical patterns are appended without removing or reordering the
  user's existing entries
- **AND** other top-level keys in the file are preserved unchanged

#### Scenario: All patterns already present

- **WHEN** every canonical pattern is already in `permissions.allow` and the
  session-cost hook entry is already present
- **THEN** the merge makes no change to the file (no duplicates added)

#### Scenario: User hook entries are preserved

- **WHEN** `.claude/settings.local.json` already defines an unrelated `Stop` hook
- **THEN** the session-cost hook is appended alongside it and the user's entry is
  left unchanged

## ADDED Requirements

### Requirement: Session-cost hook seeded on bootstrap

Whenever the permission merge runs (fresh directory, or explicit re-init), the
skill SHALL also seed a `Stop` hook into the working directory's project-local
`.claude/settings.local.json` that runs `src/session_cost.py` in hook mode. The
seeded command SHALL reference `session_cost.py` by an absolute path resolved at
seed time, SHALL run without a network dependency, and SHALL be the only hook the
bootstrap adds. The hook SHALL NOT be written to global settings or the skill's
own directory.

#### Scenario: Fresh working directory gets the hook

- **WHEN** the skill bootstraps a directory with no `.claude/settings.local.json`
- **THEN** the resulting file has a `Stop` hook whose command invokes
  `session_cost.py` in hook mode by absolute path

#### Scenario: Re-init does not duplicate the hook

- **WHEN** the bootstrap runs again in a directory whose settings already carry
  the session-cost `Stop` hook
- **THEN** no second copy of the hook is added

#### Scenario: Bootstrap output names the hook

- **WHEN** the bootstrap seeds the hook
- **THEN** its reported summary names the session-cost hook alongside the count
  of permission patterns added
