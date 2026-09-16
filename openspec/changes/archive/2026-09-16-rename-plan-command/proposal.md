## Why

`/plan` collides with the generic `/plan` mode/command that other tooling
(and users) associate with planning-only workflows unrelated to cq-design.
Renaming it to `/cq-plan` matches the `/cq-design` prefix already used for
the full-pipeline entry point and disambiguates it from unrelated `/plan`
invocations.

## What Changes

- Rename the planning-only entry point from `/plan` to `/cq-plan` in
  `SKILL.md`'s command table.
- Update the `skill-doc-structure` spec scenario that names `/plan` as a
  trigger example to say `/cq-plan`.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `skill-doc-structure`: the "Trigger load cost" scenario's list of example
  invocations changes `/plan` to `/cq-plan`.

## Impact

- `SKILL.md` (command table entry)
- `openspec/specs/skill-doc-structure/spec.md` (scenario wording, via delta
  spec in this change)
- No script, schema, or test references `/plan` as a literal string outside
  these two docs.
