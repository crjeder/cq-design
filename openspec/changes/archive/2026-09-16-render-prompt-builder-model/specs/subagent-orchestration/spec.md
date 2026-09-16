## MODIFIED Requirements

### Requirement: Builder agents use the configured authoring model
A builder agent spawned for an autonomous part SHALL use the `model` field of
`render_prompt.py builder`'s JSON output (resolved from `skill_config.json`'s
`models.part_author`; absent that file or key, the documented mid-tier default) as its
per-call model override. The main session SHALL NOT re-read `skill_config.json`
itself to make this decision. When the value is `"inline"`, the part loop SHALL run in
the calling session instead of spawning a builder agent. The model actually used SHALL
be what Step 5's telemetry record names.

#### Scenario: Configured authoring model
- **WHEN** `models.part_author` names a model and a part routes autonomous
- **THEN** `render_prompt.py builder`'s JSON output carries that model in its `model`
  field, the builder agent is spawned with it, and its `attempts.jsonl` records name
  that model

#### Scenario: Inline authoring
- **WHEN** `models.part_author` is `"inline"`
- **THEN** `render_prompt.py builder`'s JSON output carries `"inline"` in its `model`
  field, no builder agent is spawned, and the part loop runs in the main session with
  telemetry naming the main session's model
