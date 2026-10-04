## ADDED Requirements

### Requirement: Bundling stamps the project with its source commit

`bundle_project.py` SHALL write `.bundle_version.json` at the project root recording the skill commit (when known), whether the skill tree was dirty, and a timestamp.

#### Scenario: Stamp written
- **WHEN** `bundle_project.py DIR` completes
- **THEN** `DIR/.bundle_version.json` exists and contains `commit` and `bundled_at`

### Requirement: Staleness check

`bundle_project.py --check [DIR]` SHALL report whether the project's bundle is `current`, `behind`, or `unknown` relative to the running skill, change no files, and exit 0 only when `current`.

#### Scenario: Behind
- **WHEN** the stamp commit is an ancestor of the skill's HEAD but not equal to it
- **THEN** the output status is `behind` and the exit code is non-zero

#### Scenario: No stamp
- **WHEN** the project has no `.bundle_version.json`
- **THEN** the status is `unknown` and the exit code is non-zero

### Requirement: Refresh prunes retired bundled files

Re-bundling SHALL delete files inside the bundled package directories (`lib/blocks`, `lib/exporters`) and bundled top-level modules that the skill no longer ships, and SHALL NOT delete other files in `lib/`.

#### Scenario: Removed block module
- **WHEN** `lib/blocks/old.py` exists but `src/blocks/old.py` does not, and the bundle runs
- **THEN** `lib/blocks/old.py` is deleted

#### Scenario: User file untouched
- **WHEN** `lib/my_helper.py` exists and the bundle runs
- **THEN** it is left in place

### Requirement: One command refreshes bundle and permissions

Running `bundle_project.py DIR` SHALL also merge the skill's permission patterns and hooks into `DIR/.claude/settings.local.json` additively, without removing existing entries.

#### Scenario: Permissions merged
- **WHEN** `bundle_project.py DIR` runs on a project whose settings lack a current pattern
- **THEN** the pattern is added and existing entries are preserved
