## Why

A `cq-design` run can be cut off mid-pipeline (usage limit reached, session compaction,
crash). Everything the run established that lives only in the conversation is lost:
the Phase 0 sourcing verdict, the researched-and-approved dimension table, which parts
the user already approved, the hints given during escalation. On resume the user is
asked the same questions again and pays for the same web lookups and part attempts
twice. The durable artifacts that do exist (`BUILD_PLAN.json`, `build/*.py`,
`build/attempts.jsonl`) record *what was built*, never *what was decided or approved*,
so nothing on disk tells a new session where to pick up.

## What Changes

- Add an append-only milestone journal at `build/journal.md` in the working directory.
  One line is appended **at the moment a durable fact is established** -- a user
  approval, a research verdict, a part acceptance -- not at the end of the phase that
  produced it.
- Add a resume procedure (`skill/resume.md`): when a session starts in a directory that
  already has `build/journal.md`, read the journal plus the on-disk artifacts, present a
  short "resuming at X" summary, and continue at the recorded point instead of
  restarting the pipeline.
- Write `parameters.py` at the Dimension validation checkpoint (when the user approves
  the table) instead of during Phase 2. This is the single most expensive Phase 1 output
  (web research); the file that records it already exists, it is just written too late.
- Create `build/` at pipeline start (currently created in Phase 3 Setup) so Phase 0/1
  milestones have somewhere to land.
- No new Python module and no new file format: the journal is markdown appended by the
  orchestrator, read back by the orchestrator.

## Capabilities

### New Capabilities
- `build-journal`: an append-only, human-readable milestone log written as each durable
  fact is established, and the resume procedure that reads it to restart an interrupted
  run at the last recorded point.

### Modified Capabilities
- `dimension-validation-checkpoint`: approving the table SHALL write `parameters.py`
  immediately, rather than deferring provenance to Phase 2.

## Impact

- `SKILL.md` -- resume pointer in Prerequisites; `build/journal.md` in the key-files table.
- `skill/resume.md` -- new file.
- `skill/setup.md`, `skill/phase0_sourcing.md`, `skill/phase1_requirements.md`,
  `skill/phase2_planning.md`, `skill/phase3_build.md`, `skill/phase4_deliver.md` --
  per-phase journal milestone lists; `build/` creation moves to setup; `parameters.py`
  write moves from Phase 2 to the Phase 1 checkpoint.
- `CLAUDE.md` -- file layout gains `skill/resume.md`.
- No `src/` change, no schema change, no dependency change. `build/attempts.jsonl` and
  `BUILD_PLAN.json`'s `request_log` are unaffected and keep their current roles.
