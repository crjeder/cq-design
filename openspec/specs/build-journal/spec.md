# Build Journal

## Purpose

TBD - Defines requirements for the append-only `build/journal.md` milestone log that
records durable pipeline facts as they are established, and lets an interrupted run
resume without re-doing completed work.

## Requirements

### Requirement: A milestone journal is appended as facts are established

The skill SHALL maintain an append-only markdown file `build/journal.md` in the
caller's working directory. One line SHALL be appended at the moment a durable fact is
established -- never batched to the end of a phase, and never rewritten or reordered
afterwards.

A durable fact is one that cannot be recomputed from the on-disk artifacts: a user
decision or approval, a research verdict, or the acceptance state of a part. Each line
has the form:

```
- <phase>/<milestone>: <one line stating the fact>
```

The skill SHALL create `build/` at pipeline start (before Phase 0), not at Phase 3.

#### Scenario: Dimension table approved

- **WHEN** the user approves the Dimension validation checkpoint table
- **THEN** a `- phase1/dimensions_approved:` line is appended to `build/journal.md`
  in the same turn, before Phase 2 begins

#### Scenario: Journal is append-only

- **WHEN** a later milestone supersedes an earlier one (e.g. a part is rebuilt after a
  correction)
- **THEN** a new line is appended recording the new state, and the earlier line is left
  untouched

#### Scenario: Facts already on disk are not journalled

- **WHEN** a milestone's content is fully recoverable from `BUILD_PLAN.json`,
  `parameters.py`, `build/*.py`, or `build/attempts.jsonl`
- **THEN** the journal line names the milestone and points at that artifact rather than
  duplicating its content

### Requirement: Every phase records its user-decision milestones

Each phase SHALL append a journal line for each of its milestones:

| Phase | Milestones |
|-------|-----------|
| 0 | rung decision with the chosen source and its license verdict |
| 1 | topology reading confirmed; dimension table approved (with `parameters.py` written) |
| 2 | plan written and validated; plan approved by the user |
| 3 | per part: stub checkpoint approved, part accepted (progressive review or audit pass), escalation outcome with the user's hint; design approval checkpoint approved; print orientation chosen; model exported; quality gate result |
| 4 | delivered |

#### Scenario: Part accepted mid-build

- **WHEN** a part passes its Implementation audit
- **THEN** a `- phase3/part_accepted:` line naming the part id is appended before the
  next part's loop starts

#### Scenario: User hint given at escalation

- **WHEN** the user supplies a hint for a blocked builder
- **THEN** the hint is recorded verbatim in the journal line, so a resumed session can
  re-apply it without re-asking

### Requirement: An interrupted run resumes from the journal

When the skill is invoked in a working directory where `build/journal.md` already
exists, the skill SHALL read the journal and the on-disk artifacts before doing any
other pipeline work, present a short summary of what is already done and where it will
resume, and ask the user to confirm resuming or start over. The skill SHALL NOT re-run
a phase whose milestone the journal already records.

#### Scenario: Resume after interruption during the part loop

- **WHEN** a session starts in a directory whose journal records an approved plan and
  two of four parts accepted
- **THEN** the skill reports the two accepted parts, does not re-run Phase 1 or Phase 2,
  and resumes the part loop at the third part after the user confirms

#### Scenario: User chooses to start over

- **WHEN** the user declines to resume
- **THEN** the skill starts the pipeline from the top and continues appending to the
  existing journal rather than truncating it

#### Scenario: Journal absent

- **WHEN** no `build/journal.md` exists in the working directory
- **THEN** the skill starts at Phase 0 as usual and creates the journal on its first
  milestone
