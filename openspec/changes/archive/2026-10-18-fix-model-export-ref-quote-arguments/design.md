## Context

Slash-command markdown is expanded by Claude Code before the bash block runs, so `$ARGUMENTS` is substituted as raw text. The phase3 "Post-delivery corrections" paragraph names a step ("Model export") that has no heading; the real steps are "Write assembly" (`skill/phase3_build.md:305`) and `build/build.py`.

## Goals / Non-Goals

**Goals:** make the cross-reference resolve to a real heading; make `/cq-design:render` safe for paths with spaces.

**Non-Goals:** `commands/build.md` (format list, no spaces); other "Model export" mentions in `openspec/specs/` (assembly-phase, quality-gate-fix-policy), which are spec wording outside this fix.

## Decisions

- Wrap `$ARGUMENTS` in double quotes in `render.md`. Trade-off: the command now takes exactly one script path; extra flags passed in the argument would be read as part of the path. The command's `argument-hint` is already `<script.py>`, so this matches intent.
- Reword the phase3 reference in place rather than add a "Model export" heading.

## Risks / Trade-offs

- [A user passes extra flags to `/cq-design:render`] -> not a documented use; the hint shows a single script path.
