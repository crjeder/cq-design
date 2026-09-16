## Context

`render_prompt.py`'s `part_author_model()` (`src/render_prompt.py:128`) already resolves
`models.part_author` from `./skill_config.json`, falling back to
`src/skill_config.default.json`, then `"unknown"`. It's called once, inside
`validate_args()`, to bake a `--model` flag into the builder prompt's rendered
`run_cadquery_model.py` invocation (telemetry only). The main session's spawn decision
(`skill/phase3_build.md` Routing) needs the same value but has no defined way to get it
-- the doc just names the config file and key in prose.

## Goals / Non-Goals

**Goals:**
- One resolution of `models.part_author` feeds both the telemetry `--model` flag and
  the main session's spawn choice.
- The main session gets that value from the same `render_prompt.py builder` call it
  already runs to produce the prompt file, not a second file read.

**Non-Goals:**
- Not changing how `models.planner` or `models.fix_loop` are resolved or consumed.
- Not changing `part_author_model()`'s fallback order or the `"inline"` sentinel.

## Decisions

- Add `"model": part_author_model()` to the builder branch's `extra` dict in `main()`
  (`src/render_prompt.py:472`, alongside the existing `extra["stages"]`), so it's in the
  JSON already printed to stdout. Rejected alternative: a separate `render_prompt.py
  model` subcommand -- adds a second process spawn and a second config read for a value
  already computed by the call the orchestrator makes anyway.
- `phase3_build.md`'s Routing section changes from "`models.part_author` in
  `skill_config.json`" to reading the `model` field of Step 1's render output. The
  `"inline"` behavior (don't spawn, follow the prompt yourself) is unchanged; it now
  triggers off the field's literal value instead of a separate config read.

## Risks / Trade-offs

- [`render_prompt.py builder` is also invoked for a part whose stage checkpoints run
  inline (progressive build), where the `model` field is unused] -> harmless; the field
  is always emitted, callers that don't need it ignore it, same as `stages` today for a
  render used only for its `--model` flag.
