## Context

LLMs write three kinds of script, all under `build/`: step-form part scripts (builders,
`/cq-design:design`), legacy raw-CadQuery part scripts (older projects, on resume) and
edit scripts (`/cq-design:edit`). All are changed with the Edit/Write tools. Nothing
between the LLM's edit and the file checks that the edit stayed where it was aimed;
`script_lint.py` and the run tools catch some damage only after it is on disk.

Step scripts are already grouped by plan instance in practice. Across all 12 templates
the only code between `select`/`resize`/`place` calls is position arithmetic
(`x, y, z = part.positions(...)[0]`, list comprehensions over `positions`, `top =
part.param(...)`) and one `if part.has("boss"):` guard around an optional instance. A
handle may be placed more than once (`lid_snap`: two `place` calls for `clip`).

Change `script-history-restore` adds `src/script_history.py` (per-script blob store and
event log, `restore` targets). This change builds on it.

The model is a parametric CAD tool (solidcraft): UI, CLI scripts and the MCP agent all
run the same typed commands, each addressing a feature by stable id, with a preflight
check before a command applies.

## Goals / Non-Goals

**Goals:**
- An LLM edit can change only the group it addresses; everything else in the file is
  byte-identical afterwards, by construction.
- A command that would leave the script unparsable, lint-failing or with a dangling
  local is refused before anything is written.
- Every applied command is undoable through script history.
- A text edit that bypassed the commands is visible in the next run report.

**Non-Goals:**
- A declarative step format (`steps.json`) or an expression language for `at`: group
  code stays Python, so scripts keep running unchanged outside the worker.
- Preventing text edits. Hooks do not see builder sub-agent tool calls; detection is the
  enforceable part.
- Semantic checks beyond def-before-use (geometry checks stay with the step worker and
  probes).
- Changing `build.py`, the plan, or `lib/`.

## Decisions

### 1. Groups, not steps, are the unit of edit

A step script is parsed with `ast` into:

```
header   from blocks import ...; part = Part("<id>")
group    every top-level statement from a select(id=X) up to the next select or tail;
  ...    an `if part.has("X"):` whose body is one instance's statements is group X
tail     result = part.result()
```

Group id = the instance id `X`. Any other script groups by `# step: <name>` comment
lines (a group runs from its marker to the next marker or the tail); a script with no
markers and no `Part` is one group named `whole`. The tail is the last top-level
`result = ...` assignment.

Why groups rather than individual `select`/`resize`/`place` calls: the arithmetic
between them belongs to the instance, and editing a placement means editing that
arithmetic. Why instance ids: stable when steps are added, already the plan's key, and
the same key `--suppress` uses (solidcraft's `F12`).

Alternative considered: steps as JSON data with a restricted expression language for
`at`. Rejected: it needs a parser and evaluator for what is currently three lines of
Python per group, and it breaks the step-script requirement that scripts run unchanged
outside the worker.

### 2. The command set

```
script_ops.py list    <script>                         groups: id, kind, line span, hash
script_ops.py show    <script> <group>                 the group's source
script_ops.py new     <script> --template <file> | --code <file>
script_ops.py replace <script> <group> --code <file>
script_ops.py insert  <script> (--after <group> | --first) --code <file>
script_ops.py remove  <script> <group>
script_ops.py move    <script> <group> (--after <group> | --first)
```

- Code always comes from a file (convention `build/<stem>.op.py`, overwritten per
  command), never inline: no shell quoting, and no Windows command-line length limit.
- `new` refuses an existing script unless `--force`; it is the only command that writes
  the header and tail. A template copy (`--template`) also sets the `Part("...")` id.
- `replace`/`insert` code must form exactly one group: for a step script, every
  `select`/`resize`/`place` in it names one instance id (the addressed one for
  `replace`, a new one not yet in the script for `insert`); for a marked script, exactly
  one `# step:` marker as its first line, with the addressed name for `replace`.
- Output is one JSON object: `success`, `command`, `group`, `changed_groups`, `errors`
  (typed, with `hint`, as the run tools emit), `src` (new hash).

### 3. Preflight before every write

On the candidate file text, in order; the first failure refuses the command and the
file is untouched:

1. `parse_error`: the candidate does not parse.
2. `group_identity`: the code's group id or marker does not match the command (see 2).
3. `scope_violation`: anything outside the addressed group (header, tail, other groups,
   compared by source text) differs from the current file. This is the core guarantee;
   it is checked, not assumed from the splicing code.
4. `undefined_local`: a group reads a name that neither the header, an earlier group, nor
   the group itself assigns (simple def-before-use over top-level `Name` loads/stores).
   This is what makes `remove` and `move` safe across locals.
5. `unknown_instance` (step scripts): an inserted group's id is not a `blocks_needed`
   instance of the part in `BUILD_PLAN.json`.
6. Lint: `script_lint.py` on the candidate (`--step` for step scripts); its findings are
   returned as the command's errors.

Then the file is written atomically (temp file + replace) and a `command` event is
appended through `script_history` with the command, group and new `src`.

Running the model is not part of preflight: a command is milliseconds, and the builder
runs the step worker next anyway.

### 4. Unmanaged-edit detection

`step_worker.py run` and `run_cadquery_model.py` compare the script's hash with the
latest `src` of a `command`, `new` or `restore` event in its history log. When the log
has any such event and none matches, the run report carries `"unmanaged_edit": true`
(otherwise `false`), and the `run` event records it. A script with no command events at
all (a legacy project not yet touched by commands) reports `false`. It never fails the
run: it is a signal for the orchestrator, which reports it, and for the eval scorecard.

Alternative: a `PreToolUse` hook refusing Edit/Write on `build/*.py`. Rejected as the
mechanism because hooks do not see sub-agent tool calls; it can be added later for the
main session.

### 5. Where each LLM uses it

```
builder (step scripts)
  first stage: script_ops new --template | --code, then insert per instance
  fixes:       replace <instance_id>; undo: script_history restore @prev
edit command
  step 1/2:    script_ops new build/edit_input.py / build/<stem>_edited.py --code,
               with `# step: import` and one `# step: <feature>` per change
  revisions:   replace / insert / remove on sections
legacy part script (resume)
  replace whole --code: still preflighted (parse, lint) and recorded
orchestrator
  writes no scripts; surfaces unmanaged_edit from the builder's step report
```

## Risks / Trade-offs

- [Group detection mis-parses an unusual script (statements before the first `select`
  that are not header)] -> they belong to the header, which no command but `new` edits;
  `list` shows the grouping, so a builder sees it before editing.
- [Legacy scripts get only whole-file replace] -> no worse than today and recorded;
  new builds never produce legacy scripts.
- [Builder ignores the rule and uses Edit] -> `unmanaged_edit` in the report and run log;
  not prevented.
- [Def-before-use is shallow (no attribute or comprehension scoping subtleties)] ->
  comprehension targets are treated as local to the comprehension; anything the check
  cannot classify passes, and the run catches real `NameError`s.
- [More tool calls per edit (write code file, run command)] -> one extra file write per
  edit; the command replaces the Edit call rather than adding to it.

## Migration Plan

Additive. Existing scripts work unchanged; the first command on a script starts its
managed state. Lands after `script-history-restore`.

## Open Questions

- Should `unmanaged_edit` become blocking for the builder's `passed` contract once the
  prompts have been run through the evals?
- Whether `insert` should also accept an `if part.has(...)` wrapper automatically for
  optional instances, or leave it to the code file.
