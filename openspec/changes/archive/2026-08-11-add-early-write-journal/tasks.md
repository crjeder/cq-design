## 1. Journal + resume procedure

- [x] 1.1 Write `skill/resume.md`: detect `build/journal.md`, read it plus the on-disk
  artifacts (`BUILD_PLAN.json`, `parameters.py`, `build/*.py`, `build/attempts.jsonl`,
  `stl/`), present the "done so far / resuming at X" summary, wait for confirm-or-restart,
  and state the rule that artifacts are authoritative for content while the journal is
  authoritative for decisions.
- [x] 1.2 In `skill/resume.md`, document the journal contract in one place: path,
  append-only, line format `- <phase>/<milestone>: <fact>`, point-at-artifacts rule, and
  the full milestone table from the spec — so the per-phase files can point here instead
  of restating it.
- [x] 1.3 `SKILL.md` Prerequisites: add the resume pointer ("if `build/journal.md`
  exists in the working directory, read `skill/resume.md` in full before Phase 0").
- [x] 1.4 `SKILL.md` key-files table: add `build/journal.md` and `skill/resume.md`.

## 2. Per-phase milestone writes

- [x] 2.1 `skill/setup.md`: create `build/` at pipeline start; remove the `build/`
  creation line from `skill/phase3_build.md`'s Setup section.
- [x] 2.2 `skill/phase0_sourcing.md`: append the rung decision, chosen source, and
  license verdict at the moment the ladder resolves.
- [x] 2.3 `skill/phase1_requirements.md`: append the confirmed topology reading at the
  Topology clarification step; append the dimension-table approval at the checkpoint.
- [x] 2.4 `skill/phase1_requirements.md`: move the `parameters.py` write here — write it
  in the same turn the user approves or corrects the dimension table, using the
  docstring/format currently specified in `skill/phase2_planning.md`.
- [x] 2.5 `skill/phase2_planning.md`: narrow its `parameters.py` section to "update the
  existing file only if planning introduced or changed a measurement"; append journal
  lines for plan written+validated and plan approved.
- [x] 2.6 `skill/phase3_build.md`: append journal lines at stub checkpoint approval,
  part acceptance (progressive Step 4 pass and Implementation audit pass), escalation
  outcome including the user's hint verbatim, design approval checkpoint, print
  orientation chosen, model exported, and quality gate result.
- [x] 2.7 `skill/phase4_deliver.md`: append the delivered milestone.

## 3. Docs

- [x] 3.1 `CLAUDE.md` File Layout: add `skill/resume.md` to the `skill/` entry and note
  `build/journal.md` alongside `build/attempts.jsonl`.
- [x] 3.2 `TODO.md`: tick the `"write early"` item.

## 4. Verify

- [x] 4.1 Walk one recorded milestone per phase against `skill/resume.md`'s contract and
  confirm each phase file names its milestones with the same `<phase>/<milestone>` keys.
- [x] 4.2 Dry-run the resume procedure against a hand-written `build/journal.md`
  (plan approved, 2 of 4 parts accepted) and confirm it resumes at part 3 without
  re-entering Phase 1 or 2.
- [x] 4.3 `uv run pytest tests/` — no `src/` change is expected, so this only confirms
  nothing was disturbed.
