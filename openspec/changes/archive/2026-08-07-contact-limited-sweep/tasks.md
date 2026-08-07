## 1. Dependency

- [x] 1.1 Add `manifold3d` to `pyproject.toml` runtime dependencies with a comment naming
      why (boolean intersection volume for the interference measure) and refresh `uv.lock`.
- [x] 1.2 Extend `interference.load_backend()` to probe the boolean engine alongside trimesh
      and fcl, so a missing engine raises `ImportError` and reaches each caller's existing
      `check_skipped` path.

## 2. Interference primitive: volume measurement

- [x] 2.1 Replace depth thresholding in `interference.colliding_names`: keep
      `manager.in_collision_single` as the broadphase, and on a hit with a tolerance
      supplied, measure `trimesh.boolean.intersection([moving, other], engine="manifold")`
      volume per contacted body. Rename the parameter to `penetration_tol_mm3`.
- [x] 2.2 Keep the `None` tolerance path short-circuiting on broadphase contact with no
      boolean computed (keep-out any-contact semantics unchanged).
- [x] 2.3 Return the measured volume per colliding name (not just the name set) so callers
      can report it; update `check_interference` and the module docstring accordingly.
- [x] 2.4 Update `keep_out_check.py`'s call site for the new signature; verify its findings
      are unchanged (it passes no tolerance).
- [x] 2.5 Add tests to `tests/test_interference.py`: two boxes in exact face contact are not
      interfering under a volume tolerance; overlapping boxes are, with the reported volume
      matching the analytic overlap; `None` tolerance still flags bare contact.

## 3. Sweep: achieved range and bisection

- [x] 3.1 Change `_sweep_collision` in `kinematic_check.py` to track the last clear swept
      value and the minimum clearance observed, and to return the achieved range, the
      colliding union names, and the intersection volume at the stopping pose.
- [x] 3.2 Add a fixed 8-iteration bisection between the last clear value and the first
      binding value to refine the reported stop; reuse `iter_poses`' transform construction
      so revolute/prismatic/spherical all bisect through one code path.
- [x] 3.3 Extend the `motion_collision` finding with `achieved_range`, `min_clearance_mm`,
      and the measured `overlap_mm3`; leave its `severity: "error"` and message intent
      unchanged.
- [x] 3.4 Rename the CLI flag to `--penetration-tol-mm3` (default `0.1`) and correct its
      help text from "penetration depth (mm)"; thread the rename through
      `run_kinematic_check`'s signature and `quality_gate.py`'s invocation if it passes one.
- [x] 3.5 Confirm a clear sweep still emits no finding, and that a `stale_artifact` entry
      still returns before any sweep so it produces no achieved-range finding.

## 4. Contact-limited joints

- [x] 4.1 Add `stop_on_contact` (boolean, default `false`) to `kinematics_entry` in
      `src/build_plan_schema.json` with a description naming the contact-stop semantics.
- [x] 4.2 Branch in `run_kinematic_check`: for a `stop_on_contact` entry, treat first real
      interference as the mechanical stop -- emit no `motion_collision`, and when the
      achieved range falls short of `required_range`, emit a `warning` carrying
      `achieved_range`, the stopped-against union, `min_clearance_mm`, and the shortfall.
- [x] 4.3 Emit nothing extra when a `stop_on_contact` joint clears its full required range.
- [x] 4.4 Add tests to `tests/test_kinematic_check.py`: a contact-limited joint stopping
      short yields exactly one warning and no error; the same geometry without
      `stop_on_contact` still yields a `motion_collision` error; a contact-limited joint
      that clears its range yields neither.
- [x] 4.5 Add a `plan_validate` test that `stop_on_contact` is accepted and that the field
      is optional.

## 5. Documentation

- [x] 5.1 Update `CLAUDE.md`'s `interference.py` row (fcl broadphase + boolean volume, no
      fallback) and `kinematic_check.py` row (achieved range, bisection, `stop_on_contact`).
- [x] 5.2 Update `skill/phase3_build.md`'s Kinematic validation section: when to declare
      `stop_on_contact`, and how to read an achieved-range warning.
- [x] 5.3 Add the `stop_on_contact` field to the `kinematics` guidance in
      `prompts/planning.md` so the planner can emit it.
- [x] 5.4 Mark part (b) of `TODO.md`'s "kinematics for custom (block-free) hinges" sub-item
      done, keeping the minimum-cutout search noted as still open.

## 6. Verification

- [x] 6.1 Run `uv run pytest tests/test_interference.py tests/test_kinematic_check.py
      tests/test_keep_out_check.py tests/test_plan_validate.py` and confirm green.
- [x] 6.2 Regression-check the motivating case: sweep the C5 Phone-Holder plate/cradle STLs
      about the shipped pivot (car frame `[0, 5, 6]`, X axis) and confirm the tool reports a
      stop near -53.5 deg against `plate` rather than a range-wide collision.
