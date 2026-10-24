## ADDED Requirements

### Requirement: Warm worker executes step scripts
`src/step_worker.py run <script>` SHALL execute the part script's step list in a
persistent per-project worker process that keeps CadQuery imported between runs, and
SHALL print one JSON report. The client SHALL start the worker on demand and the worker
SHALL exit after an idle timeout.

#### Scenario: First run starts the worker
- **WHEN** `step_worker.py run build/plate.py` is called and no worker is running
- **THEN** the client starts a worker bound to 127.0.0.1 with an authkey, records its
  address in `build/.step_worker.json`, and prints the step report

#### Scenario: Second run reuses the worker
- **WHEN** a second run follows within the idle timeout
- **THEN** the same worker process serves it without re-importing CadQuery

### Requirement: Prefix cache re-runs from the first changed step
The worker SHALL key each step's resulting body and probe registry by a hash chained
over all previous steps' kind, resolved arguments and the selected entry's source, and
SHALL re-execute only from the first step whose key has no cached result.

#### Scenario: Editing step 5 reuses steps 1-4
- **WHEN** only the arguments of step 5 change between two runs
- **THEN** steps 1-4 are reported `cached: true` and steps 5 onward are executed

#### Scenario: Plan edit invalidates dependent steps
- **WHEN** a plan value read first in step 3 changes and the script is unchanged
- **THEN** steps 1-2 are cached and steps 3 onward are executed

### Requirement: Every step is checked and the run stops at the first failure
After each step the worker SHALL check body validity, solid count and every probe in the
registry. The run SHALL stop at the first failing step and the report SHALL name that
step, list each failing probe with its owner, kind and location, and give a diff against
the last passing step (volume, bbox, solid count, face count).

#### Scenario: Cut that misses the body
- **WHEN** a `place` step with `op="cut"` leaves the volume unchanged
- **THEN** that step fails on its `delta` probe, later steps are not executed, and
  `failed_step` is its index

#### Scenario: Later step breaks an earlier feature
- **WHEN** step 7 unions a rib that fills a plan-declared bore placed at step 3
- **THEN** step 7 fails on the bore's `empty_at` probe, owned by the plan

### Requirement: Full tier runs only after all steps pass
When every step passes, the client SHALL run the existing `run_cadquery_model.py`
validate-and-preview command for the part and include its JSON result in the report
unchanged. When any step fails, no STL, mesh check or preview SHALL be produced.

#### Scenario: All steps pass
- **WHEN** a run's steps all pass
- **THEN** the report carries the `run_cadquery_model.py` result with its standard keys
  and preview paths

### Requirement: Crash and timeout fall back to a cold run
If the worker dies or exceeds the timeout, the client SHALL terminate it, run the script
cold in a subprocess producing the same report format, and leave the next call to start
a fresh worker.

#### Scenario: OCC crash in the worker
- **WHEN** the worker process exits abnormally during a run
- **THEN** the client reports the run from a cold subprocess and the report notes
  `worker: "fallback"`

### Requirement: Builder-only snapshots
The worker SHALL keep the last passing step's body and registry as `last_good`, and
SHALL provide `snapshot save <name>`, `snapshot restore <name>` and
`snapshot compare <a> <b>`. Save SHALL write the body as BRep plus the script's step
source and registry to `build/snapshots/<part>/`. Restore SHALL rewrite the part script
from the stored source. Compare SHALL report volume, bbox, solid count, face count and
probes whose state differs. Snapshots SHALL NOT be presented at user checkpoints.

#### Scenario: Restore rewrites the script
- **WHEN** the builder restores snapshot `base_v1`
- **THEN** `build/<part>.py` equals the source stored with `base_v1` and the next run is
  served from cache up to that point

### Requirement: Repeated probe failure is reported as stuck
The worker SHALL record each probe failure in `build/<part>.steps.jsonl` with the probe
identity (owner, kind, rounded location). When a probe that already failed fails again
after a snapshot restore or after the failing step's content changed, the report SHALL
set `probe_stuck: true` and include both occurrences.

#### Scenario: Same probe fails after a different approach
- **WHEN** a bore's `ray` probe fails at step 4, the builder rewrites step 4 differently,
  and the same probe fails again
- **THEN** the report has `probe_stuck: true`

#### Scenario: A different probe failing is not stuck
- **WHEN** the rewritten step 4 passes the bore probe but fails a wall probe
- **THEN** `probe_stuck` is false
