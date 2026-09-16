## Context

SKILL.md:10's command-table row for `/cq-design` reads `` `/cq-design` or a
natural-language trigger ``. The frontmatter `description` field already enumerates
the natural-language trigger phrases and is the only field the dispatcher reads before
the skill body is loaded. This is a single-line documentation fix; no architectural
decision is needed beyond what's already captured in the proposal and spec delta.

## Goals / Non-Goals

**Goals:**
- Remove the dead trigger-phrase pointer from SKILL.md's command table.

**Non-Goals:**
- Changing the frontmatter `description` itself.
- Restructuring the command table or any other SKILL.md section.

## Decisions

- Edit SKILL.md:10 directly to drop `` or a natural-language trigger ``, leaving
  `` `/cq-design` `` as the row's command cell. No alternative considered; the table's
  other rows already use this plain single-command format.

## Risks / Trade-offs

None — the removed phrase carried no functional behavior.
