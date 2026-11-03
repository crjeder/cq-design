## Why

CADGenBench has editing fixtures (`edit_description.txt` + `input.step`): the agent must
apply a described change to a given solid and leave everything else, including its
coordinates, untouched. cq-design only has the full design pipeline (phases 0-4), which
re-plans from scratch, delivers in print pose, and spends most of its budget on
printability work an edit does not need. `evals/cadgenbench_run.py` currently papers over
this with an ad-hoc prompt ("import it with importStep and apply this edit"), so edit runs
take an unspecified path through the skill. The TODO "edit mode (import step) and apply
changes" tracks the same gap for ordinary users.

## What Changes

- New command `/cq-design:edit <file> <change description>`: reads a STEP (or BREP)
  file, writes one part script `build/<stem>_edited.py` that imports the file as the base body and
  applies the described change, iterates on it with `run_cadquery_model.py`, and delivers
  the result as `out/<stem>_edited.step` in the **input's coordinate frame** (no print-pose
  rotation, no `BUILD_PLAN.json`, no phases 0-2).
- The edit loop verifies the change with the existing `diff_models.py`: input and result
  are meshed and diffed in the shared frame; a diff that is empty (nothing changed) or
  whose changed volume lies outside the region the edit names is reported back for
  another iteration.
- Previews of input and result (existing `run_cadquery_model.py --preview`) are compared
  by the main session before delivery.
- `evals/cadgenbench_run.py` builds the prompt for edit fixtures as a `/cq-design:edit`
  invocation instead of the free-form "import and apply" instruction.
- `plugin-commands` gains `edit` in its command set.

## Capabilities

### New Capabilities
- `step-edit-command`: the `/cq-design:edit` command: input formats, the single edit
  script, frame preservation, diff-based change verification, delivered file, and the
  CADGenBench edit-fixture prompt.

### Modified Capabilities
- `plugin-commands`: the namespaced command set gains `edit`.

## Impact

- New `commands/edit.md` (prompt only; no new `src/` script -- import, run, export and
  diff are all existing tools).
- `evals/cadgenbench_run.py` `build_prompt` (edit branch) and its test.
- `FILES.md`, `README.md` command list, `SKILL.md` command list line.
- No change to the design pipeline, `BUILD_PLAN.json` schema, or JSON contracts.
