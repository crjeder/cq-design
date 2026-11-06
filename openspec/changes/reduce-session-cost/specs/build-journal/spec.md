## ADDED Requirements

### Requirement: Milestone-completing scripts append their own journal line

`plan.py validate` (`plan_written`) and `write_assembly.py` (`assembly_written`) SHALL append their milestone to `build/journal.md` on success when that file exists, using the existing journal format and skipping an identical existing line. The skill prose SHALL NOT instruct a separate Bash call for these two milestones. Other milestones (user decisions, orientation, gate result, delivery) keep an explicit append.

#### Scenario: Validate writes the milestone
- **WHEN** `plan.py validate` succeeds with a journal path available
- **THEN** a `plan_written` line is appended exactly once

#### Scenario: Failure writes nothing
- **WHEN** the script fails
- **THEN** no milestone line is appended

#### Scenario: Repeated run
- **WHEN** the same script succeeds twice with the same outcome, or no journal file exists
- **THEN** the journal does not gain a duplicate line
