## Context

`README.md` and `skill/resume.md` carry the same "Updating an existing project" block. `/cq-design:update` already runs the `bundle_project.py` step, and `resume.md` already says so.

## Goals / Non-Goals

**Goals:** one canonical copy (README); `resume.md` stops paying context for a stale, path-hardcoded block.
**Non-Goals:** fixing the README block's hardcoded paths, or changing `/cq-design:update`.

## Decisions

- Delete the block and the `bundle_project.py` behavior paragraph from `resume.md`; keep the heading and a one-sentence pointer to `/cq-design:update`. Alternative (rewrite with `SKILL_DIR`) rejected: still a duplicate that drifts.
- Keep the "If no `build/journal.md` exists" closing paragraph; it is resume logic, not update logic.

## Risks / Trade-offs

- Resumed runs lose the inline "part scripts untouched / blocks signature may have changed" note. Mitigation: it remains in README; confirm `commands/update.md` covers it, else move one sentence there.
