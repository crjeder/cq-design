## MODIFIED Requirements

### Requirement: An interrupted run resumes from the journal

When the skill is invoked in a working directory where `build/journal.md` already
exists, the skill SHALL run `pipeline.py status` (which reads the journal and the on-disk artifacts) before doing any
other pipeline work, present a short summary of what is already done, what is void or stale, and where it will
resume (`allowed_next`), and ask the user to confirm resuming or start over. The skill SHALL NOT re-run
a phase whose milestone `status` reports as done, and SHALL NOT count a milestone line `status` reports as void.

#### Scenario: Resume after interruption during the part loop

- **WHEN** a session starts in a directory whose journal records an approved plan and
  two of four parts accepted
- **THEN** the skill reports the two accepted parts, does not re-run Phase 1 or Phase 2,
  and resumes the part loop at the third part after the user confirms

#### Scenario: User chooses to start over

- **WHEN** the user declines to resume
- **THEN** the skill appends a `- phase0/restart:` line, starts the pipeline from the
  top and continues appending to the existing journal rather than truncating it, and a
  later resume considers only milestones after the last `phase0/restart` line

#### Scenario: Journal absent

- **WHEN** no `build/journal.md` exists in the working directory
- **THEN** the skill starts at Phase 0 as usual and creates the journal on its first
  milestone

#### Scenario: Void or stale milestone on resume

- **WHEN** `status` reports a recorded milestone as void or a part as stale
- **THEN** the summary names it, and the run resumes at the earliest step `allowed_next` lists rather than trusting the line
