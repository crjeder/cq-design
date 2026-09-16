## Why

SKILL.md:10 reads `` `/cq-design` or a natural-language trigger `` in a slash-command
table that is otherwise a plain command reference. That phrase is the only place in
the body that gestures at the natural-language trigger phrases already enumerated in
the frontmatter `description` field. The body is only read after the skill has already
triggered (the description is what the dispatcher matches against beforehand), so this
line cannot help triggering and only adds a redundant, unlinked pointer to content that
lives elsewhere.

## What Changes

- Remove the `` or a natural-language trigger `` phrase from the `/cq-design` row in
  SKILL.md's command table (SKILL.md:10), keeping the row as a plain `/cq-design`
  command entry consistent with the other rows.
- No other command-table rows or frontmatter change.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `skill-doc-structure`: adds a requirement that SKILL.md's body SHALL NOT restate or
  gesture at frontmatter-owned trigger content, since the frontmatter `description` is
  the sole source of truth for trigger matching and the body is not in context until
  after triggering has already happened.

## Impact

- `SKILL.md` (single-line edit to the command table).
