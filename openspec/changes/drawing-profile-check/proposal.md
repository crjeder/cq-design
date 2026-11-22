## Why

In the CADGenBench submission `cq-design v0.1.0 (merged best-of)`, several generation
fixtures have the wrong overall shape (136: IoU 0.03, 135: IoU 0.19, 139: IoU 0.42) even
where the bounding box and hole count are right (#396). On thin-walled and sheet-metal parts
a wall offset to the wrong side of its dimension, or a flange folded the wrong way, removes
most of the overlap. Nothing checks the built profile against the drawing's section views:
the plan can already hold `solid_at`/`empty_at` probes (rule 17), but the gate never
evaluates them on a plain part script, and the planner is not told to write them for walls
and flanges. Failures like 136 also cannot be diagnosed, because the run's `_work/<id>`
scripts and logs were deleted after `cgb-v1`.

## What Changes

- New quality-gate stage `plan_probes`: evaluates every authored `probes[]` entry of a part
  on its finished build-pose body and emits a blocking `probe_unmet` error per failing
  probe (label, kind, expected, observed). Runs for step scripts and plain part scripts
  alike; parts without `probes[]` see no change.
- Planning prompt rule for thin-walled and sheet-metal drawings: before decomposing, derive
  the 3D form from the section views (which side of each thickness dimension the wall lies,
  inside or outside bend radius, flange direction) and record it in `planning_notes`, naming
  the face each thickness dimension references. Then author a `solid_at`/`empty_at` bracket
  for every dimensioned wall face and a `solid_at` probe at each flange tip, labelled with
  the view (`"SECTION A-A: 2 mm wall, outer face y=57"`).
- `evals/cadgenbench_run.py` keeps `<run>/_work/<id>/` after each fixture and deletes only
  its `.venv/`, so build scripts, plan, journal and logs stay for diagnosis without the disk
  cost that led to the manual cleanup.

## Capabilities

### New Capabilities
- `drawing-profile-check`: gate evaluation of authored plan probes on the finished part, and
  the planning rule that turns section-view wall sides and flange directions into probes.
- `cadgenbench-work-retention`: the CADGenBench runner keeps each fixture's work directory
  except its virtual environment.

### Modified Capabilities
<!-- none: probe kinds and the step-script registry are unchanged; the gate gains a stage -->

## Impact

- `src/quality_gate.py`: new `_run_plan_probes_stage`, called next to the oracle stage.
- `prompts/planning.md`: thin-wall / sheet-metal section-view rule beside rule 17.
- `evals/cadgenbench_run.py`: drop `_work/<id>/.venv` after each fixture.
- Docs: `reference/scripts.md` (`quality_gate.py` issue type), `evals/README.md` (runner).
- Tests: `tests/test_quality_gate.py`, a runner test for the prune.
