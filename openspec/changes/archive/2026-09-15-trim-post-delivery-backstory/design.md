## Context

`skill/phase3_build.md`'s "Post-delivery corrections" section (lines 267-283) mixes an
enforceable rule with the incident narrative that motivated it. The narrative already
has a permanent home at `TODO.md#silica-tray-re-export-coincidence`, so the inline copy
in the skill file is pure duplication paid for on every Phase 3 load.

This is a documentation-only edit: no code, schema, or behavior changes. Design detail
below is intentionally thin.

## Goals / Non-Goals

**Goals:**
- Keep the rule text Phase 3 must follow ("a post-delivery geometry correction re-opens
  print-orientation, model export, and quality gate for the affected union(s) before
  Phase 4 re-reports delivery") fully intact and unambiguous.
- Remove the inline incident narrative, replacing it with a link to
  `TODO.md#silica-tray-re-export-coincidence`.

**Non-Goals:**
- Changing what Phase 3 actually does (the rule's substance is unchanged).
- Editing `TODO.md` itself -- it already contains the full story.
- Trimming other sections of `phase3_build.md` not covered by this rule.

## Decisions

- **Keep the rule as an imperative, self-contained instruction.** It must stand on its
  own without the reader needing to open `TODO.md` to know what to do -- only the *why*
  moves out.
- **Link rather than delete the backstory reference.** A bare link
  (`see TODO.md#silica-tray-re-export-coincidence for why`) preserves discoverability for
  anyone auditing the rule's origin, at near-zero token cost, versus removing the
  reference entirely.

## Risks / Trade-offs

- [Risk: trimming drops a nuance the rule depends on] -> Mitigation: diff the before/after
  rule text line-by-line against the current wording to confirm the actionable
  instruction (re-run orientation/export/gate for affected unions before re-reporting)
  survives verbatim in substance.
