## MODIFIED Requirements

### Requirement: Sourcing prompt is rendered by render_prompt.py
`src/render_prompt.py` SHALL provide a `sourcing` subcommand taking `--request-file`
(required, the user's request/lookup targets text) and `--out` (default
`build/sourcing_prompt.txt`). It SHALL render `prompts/sourcing.md` with
`{{REQUEST_TEXT}}` = the request file's text and `{{SOURCING_CORPUS}}` = the full "Phase
0 sourcing corpus" section (both the "Hardware & component archives" and "Finished models
by domain" tables) of `reference/Block_Sources.md`, then write the prompt and print
`{"out", "chars"}`. Unlike the research prompt, the sourcing prompt has no shell command
that needs the skill root, so it takes no `{{SKILL_DIR}}` placeholder.

#### Scenario: Rendering the sourcing prompt
- **WHEN** `render_prompt.py sourcing --request-file build/request.md` runs
- **THEN** `build/sourcing_prompt.txt` contains the request text and the current
  Block_Sources.md rung-1/rung-2 tables, and the printed JSON reports the char count

### Requirement: Main session does not assemble the sourcing prompt by hand
`skill/phase0_sourcing.md` SHALL instruct the main session to write the request text to a
file, run `render_prompt.py sourcing`, and spawn the sourcing agent with
`Read <out> in full and follow it.` The doc SHALL NOT instruct the main session to open
`reference/Block_Sources.md` or `prompts/sourcing.md` itself to build this prompt.

#### Scenario: Phase 0 prompt construction
- **WHEN** the main session starts Phase 0 (not skipped)
- **THEN** it renders the sourcing prompt with `render_prompt.py sourcing` and spawns the
  sourcing agent, without opening `reference/Block_Sources.md` or
  `prompts/sourcing.md` itself
