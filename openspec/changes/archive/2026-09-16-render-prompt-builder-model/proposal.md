## Why

`render_prompt.py`'s `part_author_model()` already resolves `models.part_author` from
`skill_config.json` (falling back to the shipped default) and bakes it into the
builder prompt's `--model` flag for telemetry. But `subagent-orchestration`'s "Builder
agents use the configured authoring model" requirement puts the *same* resolution on
the main session, for spawn routing, with no defined interface: `phase3_build.md`'s
Routing section just says "`models.part_author` in `skill_config.json`" in prose. The
main session has no instructed command to read that file, so the value used to spawn
the builder can drift from the value `render_prompt.py` already computed and recorded
in `attempts.jsonl` -- two independent reads of the same config, one of them undocumented.

## What Changes

- `render_prompt.py`'s builder JSON output gains a `"model"` field carrying
  `part_author_model()`'s resolved value (a model id, or `"inline"`).
- `phase3_build.md`'s Routing section reads the spawn model from that field instead of
  re-reading `skill_config.json` itself.

## Capabilities

### Modified Capabilities
- `subagent-orchestration`: "Builder agents use the configured authoring model" now
  sources the per-call model override from `render_prompt.py`'s builder JSON output
  instead of a second, undocumented read of `skill_config.json`.

## Impact

- `src/render_prompt.py` (`main()`'s builder branch, `extra` dict)
- `skill/phase3_build.md` (Routing section wording)
- `tests/test_render_prompt.py` (new assertion on the `model` key)
