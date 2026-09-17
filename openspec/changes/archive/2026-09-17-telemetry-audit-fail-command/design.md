## Context

`record_attempt` (the `--hook` path) already derives `prompt_chars` and `model` for the
base attempt record from files on disk: it globs
`{part_id}_prompt_attempt{attempt}.txt` / `{part_id}_prompt.txt` under `build/` for
`prompt_chars`, and the hook derives `model` from the session transcript. The audit-fail
follow-up (skill/phase3_build.md's Implementation audit, step 3) needs the same two
values but isn't triggered by a Bash/PowerShell tool call, so it can't reuse the
transcript-scanning path — it has no hook payload, only `--part` and the auditor's
verdict JSON path. `part_author_model()` in `render_prompt.py` already resolves the
builder's configured model (`skill_config.json`'s `models.part_author`, falling back to
the seeded default) without needing a transcript, and is the correct source here since
the audit-fail record is always about the part-author role, not an arbitrary tool call.

## Goals / Non-Goals

**Goals:**
- One command, `telemetry.py audit-fail --part <id> --audit <path>`, replaces the
  hand-assembled `--field` list in skill/phase3_build.md's audit-fail step.
- `prompt_chars` and `model` are derived from disk, not typed by the caller.

**Non-Goals:**
- Not changing how the base (hook) record is produced, or `fold_attempts` semantics.
- Not changing the auditor's own JSON contract (`verdict`/`failed_questions`/`findings`/
  `missing_views`) — `audit-fail` only reads it.

## Decisions

- **Attempt number**: use the highest `attempt` already present for `part_id` in
  `attempts.jsonl` (via `fold_attempts`), not `len(...) + 1`. The follow-up record must
  land on the *same* attempt as the base record the hook already appended for this
  contract, so `fold_attempts` treats them as one attempt with the follow-up's fields
  authoritative (per the existing `attempt-telemetry` spec's fold semantics). Error if no
  prior attempt exists for the part — a follow-up with nothing to follow up is a caller
  bug, not a fail-open case (unlike the hook, which fails open because it runs
  unattended).
- **`prompt_chars` lookup**: reuse the exact glob `record_attempt` uses
  (`{part_id}_prompt_attempt{attempt}.txt` then `{part_id}_prompt.txt`) against the
  resolved attempt number, so the two paths can't disagree on which prompt file counts.
  Refactor that lookup into a small shared helper rather than duplicating the two-line
  loop.
- **`model` lookup**: `render_prompt.py` already imports `_read_records` and
  `fold_attempts` from `telemetry.py`, so the reverse import would be circular. Move
  `part_author_model()` into `telemetry.py` (its only real dependency, `_read`, is a
  one-line `Path.read_text` inline) and have `render_prompt.py` import it from there,
  keeping the existing one-way dependency direction instead of introducing a cycle.
- **Failed question**: `failed_questions[0]` from the audit JSON becomes
  `visual_review.failed_question`, matching the existing single-question field already
  in the spec's scenario ("Visual review failure records the question"). If
  `failed_questions` is empty (verdict wasn't actually `fail`), treat it as a caller
  error and exit non-zero rather than writing a record with a missing field.

## Risks / Trade-offs

- [Importing `render_prompt` from `telemetry.py` couples two previously independent
  scripts] → both already live in `src/` and are invoked from the same working
  directory convention (`skill_config.json` resolved relative to cwd); no circular
  import since `render_prompt.py` does not import `telemetry.py`.
