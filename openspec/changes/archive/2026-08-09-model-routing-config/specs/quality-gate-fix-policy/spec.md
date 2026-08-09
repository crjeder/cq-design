## MODIFIED Requirements

### Requirement: The cold-context fixer remains available

The `--fix` path SHALL keep the existing fix-prompt renderer and `claude -p`
invocation, so the gate remains usable standalone outside the skill pipeline.
Removing the default SHALL NOT remove the capability. The `claude -p` invocation SHALL
select its model from `skill_config.json`'s `models.fix_loop`, appending
`--model <value>`; a value of `"inline"`, a missing key, or a missing config file
SHALL invoke `claude -p` with no `--model` flag.

#### Scenario: Standalone scripted use

- **WHEN** the gate is invoked outside the skill with `--fix` on a script with a
  fixable error
- **THEN** it renders the targeted fix prompt, invokes the model, writes the
  corrected script, and re-runs the checks

#### Scenario: Configured fix-loop model

- **WHEN** `skill_config.json` sets `models.fix_loop` to a model id and the gate runs
  with `--fix`
- **THEN** the `claude -p` invocation carries `--model <that id>`

#### Scenario: Unconfigured fix loop is unchanged

- **WHEN** the gate runs with `--fix` and no `skill_config.json` exists in the working
  directory
- **THEN** `claude -p` is invoked with no `--model` flag and the fix path behaves
  exactly as before this change
