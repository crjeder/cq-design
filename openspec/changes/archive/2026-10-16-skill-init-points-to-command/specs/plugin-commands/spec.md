## ADDED Requirements

### Requirement: Init command lines have one copy

The init command lines (`uv sync`, `init_permissions.py`, `printer_profile_validate.py`) SHALL appear only in `commands/init.md`. `SKILL.md` SHALL refer to that file for the once-per-directory setup instead of repeating the commands.

#### Scenario: SKILL.md references init
- **WHEN** `SKILL.md` Prerequisites describes directory setup
- **THEN** it says to run the `/cq-design:init` logic and points to `commands/init.md`
- **AND** it contains no `init_permissions.py` or `printer_profile_validate.py` command line
