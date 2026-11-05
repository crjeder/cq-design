## ADDED Requirements

### Requirement: Every script run is recorded
`src/script_history.py` SHALL keep, per script, `build/history/<stem>/<sha12>.py` (the
source, keyed by the first 12 hex characters of its SHA-256, written only when absent) and
`build/history/<stem>/log.jsonl`. `step_worker.py run` and `run_cadquery_model.py` SHALL
each append one `run` event per run with `src`, `ok`, `ts`, and, when known, `attempt`
(plan revision) and `suppressed`. A `run_cadquery_model.py` run with `CQ_HISTORY_SKIP=1`
in its environment SHALL NOT record. Recording SHALL apply to step-form part scripts,
legacy part scripts and edit-command scripts alike, SHALL need no LLM action, and a
recording failure SHALL only print a one-line stderr warning, never change the run's
result or exit code.

#### Scenario: Edit-command script is recorded
- **WHEN** `run_cadquery_model.py build/part_edited.py --preview` runs twice with an edit
  in between
- **THEN** `build/history/part_edited/` holds two blobs and `log.jsonl` two `run` events
  with their `src` hashes and `ok` values

#### Scenario: Unchanged source stores nothing new
- **WHEN** the same source is run twice
- **THEN** one blob exists and both `run` events carry the same `src`

#### Scenario: Step script full tier is recorded once
- **WHEN** `step_worker.py run` passes every step and runs the full tier
- **THEN** `log.jsonl` gains exactly one `run` event for that run

#### Scenario: Unwritable history does not fail the run
- **WHEN** `build/history/` cannot be written
- **THEN** the run's JSON result and exit code are what they would be without history

### Requirement: Restore and mark work for every script
`script_history.py restore <target> <script>` SHALL rewrite the script from the resolved
blob and append a `restore` event (target, resolved hash); when `build/<stem>.steps.jsonl`
exists it SHALL also append a step-worker `restore` event there. Targets SHALL be
`@last_ok` (the `src` of the latest `run` with `ok: true` and no `suppressed`), `@prev`
(the latest recorded `src` differing from the current script's hash), `@<prefix>` (a
unique blob prefix of at least 4 hex characters) and `<name>` (the latest `mark` with that
name). `script_history.py mark <name> <script>` SHALL store the current source if absent
and append a `mark` event; names starting with `@` SHALL be rejected. A missing,
ambiguous or unknown target SHALL return `success: false` with an error naming it and
leave the script unchanged. Both commands SHALL print one JSON object.

#### Scenario: Undo the last edit
- **WHEN** an edit makes a passing script fail and `restore @prev` runs
- **THEN** the script equals the source run before the edit

#### Scenario: Back to the latest green run
- **WHEN** several failing edits follow a successful run and `restore @last_ok` runs
- **THEN** the script equals the source of that successful run

#### Scenario: Named baseline
- **WHEN** `mark accepted` ran on a script, later edits followed, and `restore accepted`
  runs
- **THEN** the script equals the marked source

#### Scenario: Ambiguous prefix
- **WHEN** two blobs share the given prefix
- **THEN** restore returns `success: false`, lists the matching hashes, and leaves the
  script unchanged

#### Scenario: Restore keeps stuck detection
- **WHEN** a step script is restored and the same probe fails again afterwards
- **THEN** the step worker reports `probe_stuck: true`

### Requirement: Restore warns across plan revisions
When the restored source's latest `run` event has an `attempt` and the part's current plan
revision is known and differs, restore SHALL still rewrite the script and SHALL return
`"warning": "attempt_mismatch"` with both revisions. Scripts with no plan part SHALL never
warn.

#### Scenario: Restoring a source from before a plan change
- **WHEN** a `parameter` request-log entry advanced the part to revision 2 and a source
  last run at revision 1 is restored
- **THEN** the script is restored and the result carries `attempt_mismatch` with 1 and 2

### Requirement: Run-time suppression by instance id
`step_worker.py run --suppress <instance_id>` (repeatable) SHALL make `Part` record every
`select`, `resize` and `place` step of that instance with `"suppressed": true` and skip
its key-chain advance, construction, boolean, probe registration and arming, without
modifying the script. An id that is not a `blocks_needed` instance SHALL fail as
`step_plan` naming the planned ids. A run with any suppression SHALL report
`"suppressed": [ids]`, SHALL NOT run the full tier (`full: null`), and SHALL be recorded
with `suppressed` so `@last_ok` never resolves to it. Runs outside the step worker SHALL
ignore suppression.

#### Scenario: Bisect a failing cut
- **WHEN** step `cut hole_h` fails `cut removed no volume` and the builder runs with
  `--suppress boss`
- **THEN** the `boss` steps are reported suppressed, the script on disk is unchanged, and
  the `hole_h` cut's result shows whether it depended on `boss`

#### Scenario: Toggling stays cache-warm
- **WHEN** the builder runs with `--suppress rib`, then without it, then with it again
- **THEN** the third run executes no step from scratch

#### Scenario: Suppressed planned feature cannot pass
- **WHEN** an instance with a plan interface probe is suppressed
- **THEN** `result()` fails that plan probe and the run does not succeed

#### Scenario: Suppressed run never becomes last_ok
- **WHEN** a suppressed run passes every step and `restore @last_ok` runs later
- **THEN** the restored source is that of the latest unsuppressed successful run

### Requirement: LLM undo goes through restore
`prompts/builder.md`, `skill/phase3_build.md` and `commands/edit.md` SHALL tell the LLM to
undo a script edit with `script_history.py restore` and SHALL NOT tell it to revert an
edit by editing the text back.

#### Scenario: Builder prompt names restore
- **WHEN** `render_prompt.py builder` renders a builder prompt
- **THEN** the prompt contains the `script_history.py restore` command with the
  `@prev` and `@last_ok` targets
