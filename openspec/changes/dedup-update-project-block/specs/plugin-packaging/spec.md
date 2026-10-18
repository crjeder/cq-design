## MODIFIED Requirements

### Requirement: Shipped prose does not name the installer scripts
Shipped prose SHALL NOT tell a copy-install reader to run a script the install lacks. `skill/resume.md` SHALL refer to refreshing a project only through `/cq-design:update`, without a duplicated command block.

#### Scenario: Shipped prose does not name the installer scripts
- **WHEN** a reader of a copy install follows `SKILL.md` to refresh a stale skill
- **THEN** they are told to reinstall from the repo, not to run a script the install lacks

#### Scenario: Resume refresh pointer
- **WHEN** a reader follows `skill/resume.md` to refresh a project's bundled tooling
- **THEN** they are pointed to `/cq-design:update` and no hardcoded `~/.claude/skills/cq-design/src/...` or `<path-to-this-repo>` command appears
