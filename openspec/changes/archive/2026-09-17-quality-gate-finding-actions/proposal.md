## Why

`quality_gate.py` emits findings (`source`, `severity`, `type`, `message`, `hint`) but
leaves it to the reader to know what to do with each one. That knowledge currently
lives as a hand-maintained type-by-type list in `skill/phase3_build.md`'s Quality gate
section (`stale_artifact` -> re-export, `motion_collision` -> relieve geometry or fix
`kinematics`, `contact_limited_stop` -> ask the user, warnings -> never fix, etc.). Every
new check module (`gridfinity_check.py`, `edge_treatment_check.py`, ...) that adds a
finding type has to get a matching entry added to that prose list by hand, and the
orchestrator has to re-derive the right response from prose instead of reading it off
the finding itself.

## What Changes

- Add an `action` field (`fix` | `re_export` | `ask_user` | `warn_only`) to every
  quality-gate finding, computed once in `quality_gate.py::run_gate` from each finding's
  `(type, severity)` — not authored per call site in the eight check modules.
- Default `action` from `severity` (`error` -> `fix`, `warning`/`info` -> `warn_only`),
  with a small explicit override table for the findings that don't follow the default:
  `stale_artifact` -> `re_export`; `motion_collision`, `range_exceeds_limit`,
  `contact_limited_stop` -> `ask_user`.
- Remove the per-type bullet list from `skill/phase3_build.md`'s Quality gate section;
  replace it with one generic rule keyed off `action`.
- **BREAKING**: `build/quality_gate.json` findings gain a required `action` key; any
  external reader of that file that validates against an exact key set needs updating.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `quality-gate-fix-policy`: findings now carry an `action` field the caller routes on,
  replacing the implicit severity-only routing ("error fixes, warning doesn't") with
  four explicit actions, two of which (`re_export`, `ask_user`) cover cases the current
  spec doesn't name at all.

## Impact

- `src/quality_gate.py`: `run_gate` gains an action-classification step over
  `all_issues` before returning the report.
- `src/units.py`: no signature change to `make_issue` — action is derived centrally, not
  passed in by callers.
- `skill/phase3_build.md`: Quality gate section's per-type bullet list is replaced by a
  generic action-routing rule.
- `build/quality_gate.json` (the report file Phase 3 reads): new `action` key on every
  finding.
- Tests: `tests/test_run_wrapper.py`-adjacent gate tests (wherever `quality_gate.py`'s
  report shape is asserted) need the new key.
