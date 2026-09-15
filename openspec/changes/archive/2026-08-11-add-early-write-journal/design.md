## Context

The pipeline already persists what it *builds*: `BUILD_PLAN.json` (+ `request_log`),
`parameters.py`, `build/<part>.py`, `build/attempts.jsonl`, `preview/*.png`, `stl/`.
It persists nothing about what was *decided*. Approvals, the sourcing verdict, the
stub checkpoint, which parts cleared their audit, and escalation hints exist only in
the conversation, so an interrupted session cannot tell where it stopped and re-asks
the user or re-pays for research and part attempts.

The orchestrator is Claude following `SKILL.md` and `skill/phase*.md`; every write in
this pipeline is already an instruction, not a code path. The single writer and the
single reader of the journal are the same agent.

## Goals / Non-Goals

**Goals:**
- Any interrupt after a durable fact is established leaves that fact on disk.
- A fresh session in the same directory can state what is done and resume at the next
  unfinished step without re-asking the user.
- Zero new Python, zero new schema, zero new dependency.

**Non-Goals:**
- Automatic resumption. The user confirms the resume point; the skill never silently
  continues a run it did not start.
- Crash-safe transactional state. A line lost to a mid-write kill costs one repeated
  step, not correctness.
- Replacing `request_log` (verbatim user requests, inside the plan) or
  `attempts.jsonl` (per-attempt telemetry for the eval harness). The journal records
  decisions and phase position; those two keep their existing, narrower roles.

## Decisions

**Markdown, one line per milestone, appended directly -- no helper script.**
`src/telemetry.py` is the closest existing writer, but its schema is attempt-specific
and generalising it would mean adding a schema switch to a file that currently has one
job. A helper would not improve compliance either: telemetry uses one and is still an
instruction the orchestrator can skip. Markdown wins because the reader is an LLM
reading it back into context, and a human debugging a stuck run can read it too.
Alternative considered: `build/journal.jsonl` with a `journal.py` append CLI --
rejected as a module, a test file, and a schema in exchange for validation nobody
consumes.

**`build/journal.md`, next to `attempts.jsonl`.** Same directory, same lifecycle,
already gitignore-shaped in user projects. `build/` creation moves from Phase 3 Setup
to pipeline start so Phase 0/1 can write.

**Line format `- <phase>/<milestone>: <fact>`.** Grep-able by phase, sorts naturally
by append order, needs no parser. Timestamps are optional -- ordering is what resume
needs, and `request_log` already carries timestamps for user wording.

**Point at artifacts, do not copy them.** A milestone whose content is on disk
(`BUILD_PLAN.json`, `parameters.py`, a part script) names the artifact. Only facts with
no artifact -- approvals, verdicts, hints -- are written out in full. This keeps the
journal short enough to read back whole in one go.

**`parameters.py` moves to the Phase 1 checkpoint.** The most expensive Phase 1 output
is the web research behind the dimension table, and the file that records it already
exists in the pipeline -- it was simply written one phase too late. Moving the write is
the early-write principle applied to an artifact that already exists, rather than a new
one. Phase 2 keeps a narrower job: update the file if planning added a measurement.

**Resume detail lives in `skill/resume.md`, pointed at from `SKILL.md`'s
Prerequisites.** Matches the existing per-phase split (`skill/setup.md`,
`skill/phase*.md`) and keeps `SKILL.md` to a pointer, so the resume procedure costs
nothing to read on a normal fresh run.

## Risks / Trade-offs

- **The orchestrator forgets to append a line** → the journal is written at the same
  points that already stop for a user decision, so the append rides along with a turn
  that is happening anyway; resume also cross-checks the on-disk artifacts, so a
  missing line degrades to a slightly earlier resume point rather than a wrong one.
- **Journal and artifacts disagree** (e.g. a part script hand-edited after acceptance)
  → the resume procedure treats on-disk artifacts as authoritative for content and the
  journal as authoritative only for decisions, matching the existing Design approval
  checkpoint rule about hand-edited `PARAMETERS`.
- **Stale journal from an unrelated older run in the same directory** → resume always
  presents its summary and waits for confirmation; the user can decline and start over,
  and the journal is appended to, never truncated.
- **Unbounded growth over many re-runs** → one line per milestone is tens of lines per
  run; nothing to do until that is measurably a problem.
