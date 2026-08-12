## Why

The C5 Phone-Holder retrospective (`TODO.md` line 139) found that "how tall must this
notch be to clear this swing?" was answered by hand: edit a height parameter, rerun
the part, eyeball the collision, repeat, then binary-search toward the minimum.
`contact-limited-sweep` and `blockless-kinematics` already made the *measurement*
(does this pose collide, how far did the joint get) precise and automated; nothing
automates the *search* over geometry edits that measurement feeds into. That search
loop is common to any clearance-limited feature (a notch, a slot, a standoff) sized
against a kinematic sweep, not specific to one project.

## What Changes

- New script `src/minimal_cutout_search.py`: bisects a single numeric
  `PARAMETERS`-block constant in a part script to find the minimal (or maximal)
  value at which a named `kinematics` entry's `required_range` sweeps clear, per
  `run_kinematic_check` (from `kinematic_check.py`, unchanged).
- Each candidate value is applied by rewriting the script's parameter line
  (AST-located the same way `import_params.py` locates it), regenerating only the
  affected part's assembled-frame STL (loading `result` and posing it the same way
  `model_export.py` does), and re-running the sweep for just the named joint.
- CLI reports the converged boundary value and a recommended value with a safety
  margin; it does not write geometry changes back unless `--apply` is passed.
- Explicitly out of scope: multi-parameter search, non-monotonic parameter/clearance
  relationships (the tool assumes and checks monotonicity at its bounds, and fails
  fast if that assumption doesn't hold), and any new collision/measurement primitive.

## Capabilities

### New Capabilities
- `minimal-cutout-search`: bisection search over a single part-script parameter to
  find the minimal clearance-satisfying value against a kinematics entry's required
  range of motion, reusing the existing kinematic sweep as its oracle.

### Modified Capabilities
(none -- `kinematic-range-validation` and `interference-primitive` are consumed
unchanged)

## Impact

- New: `src/minimal_cutout_search.py`, `tests/test_minimal_cutout_search.py`.
- Reuses without modification: `src/run_cadquery_model.py` (`--deliver` STL export),
  `src/kinematic_check.py` (`run_kinematic_check`), `src/import_params.py`'s
  parameter-location approach (AST, module-level numeric assignment).
- No schema, prompt, or gate-pipeline changes -- this is an author-invoked tool, not
  a pipeline stage.
