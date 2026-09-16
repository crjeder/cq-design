## Context

`/plan` is a documented entry-point name in `SKILL.md`'s command table (not a
registered slash-command file) and appears once more as an example in the
`skill-doc-structure` spec's trigger-load-cost scenario. No script, prompt,
or test references the literal string `/plan`.

## Goals / Non-Goals

**Goals:**
- Rename `/plan` to `/cq-plan` everywhere it is documented as a user-facing
  entry point.

**Non-Goals:**
- No behavior change to phases 1-2 or how planning-only invocation is
  detected; this is a naming change only.

## Decisions

- Use `/cq-plan` (matches the `/cq-design` prefix already used for the
  full-pipeline entry point) rather than a bare `/plan2` or similar, for
  consistency with the existing naming convention.

## Risks / Trade-offs

- [Stale doc/example elsewhere still says `/plan`] -> grep confirmed only
  `SKILL.md` and `openspec/specs/skill-doc-structure/spec.md` reference it;
  no further mitigation needed.
