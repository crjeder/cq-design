## 1. Parameter location and rewrite

- [x] 1.1 In `src/minimal_cutout_search.py`, add a parameter-locating function that
      AST-parses a script and returns the line number + literal span of a named
      module-level numeric assignment, following `import_params.py`'s
      `parse_parameters` convention (reject non-module-level, non-numeric-literal
      targets).
- [x] 1.2 Add a rewrite function that replaces only the literal value on that line,
      preserving surrounding text (comments, whitespace).
- [x] 1.3 Unit test: locate + rewrite round-trip on a small fixture script with a
      `PARAMETERS` block, including a case with a trailing comment on the parameter
      line.

## 2. Candidate evaluation

- [x] 2.1 Add a function that, given a candidate value: rewrites the part script,
      loads its `result` and unions (`units.resolve_unions`), poses each union into
      the assembled frame by reusing `model_export.py`'s `_pose_union` directly
      (honors a `mate_chain.compute_mate_poses` pose when present, else
      `placement`), and writes each union's STL into `--stl-dir` (reusing existing
      STLs for every other union). Loads the script via a local `compile()`+`exec()`
      loader (`_exec_script`), not `exporters._load_result`'s import machinery --
      found during implementation that the ordinary import path re-reads stale
      `__pycache__` bytecode when the same script path is rewritten and reloaded
      many times per second, which this search loop does.
- [x] 2.2 Add a function that runs `run_kinematic_check` (imported from
      `kinematic_check.py`) against the plan and `--stl-dir`, and returns pass/fail
      for the named `joint_id` (pass = no issue in the result naming that
      `joint_id`, matching the spec's "no finding for that joint_id" wording).
- [x] 2.3 Unit test candidate evaluation against a fixture plan + script pair with a
      known-colliding and known-clearing parameter value (a small real CadQuery
      box-and-arm fixture in `tests/test_minimal_cutout_search.py`, not adapted from
      `kinematic_check`'s trimesh-only fixtures since this tool needs a real
      `PARAMETERS` script to search over).

## 3. Bounds precondition and bisection loop

- [x] 3.1 Implement the bounds precondition check (`--lo` fails, `--hi` passes) with
      a clear error message naming the offending bound.
- [x] 3.2 Implement the bisection loop: converge when `hi - lo <= --tolerance-mm`,
      maintaining the fail/pass invariant at each step.
- [x] 3.3 Compute and report the recommended value (`hi + --margin-mm`).
- [x] 3.4 Unit test: bisection converges to the expected boundary within tolerance
      on the fixture from 2.3; unit test the bounds-precondition error paths.

## 4. CLI and write-back

- [x] 4.1 Add the `argparse` CLI: script path, `--param`, `--plan`, `--joint-id`,
      `--stl-dir`, `--lo`, `--hi`, `--tolerance-mm` (default 0.1),
      `--margin-mm` (default 0.2), `--apply`.
- [x] 4.2 Implement `--apply`: write the recommended (margined) value back via the
      rewrite function from 1.2; default (no `--apply`) leaves the script
      untouched and only reports the result.
- [x] 4.3 CLI smoke test (`tests/test_minimal_cutout_search.py`): run the tool
      end-to-end via subprocess on the fixture, asserting the reported value and
      that the script is unchanged without `--apply` / changed with `--apply`.

## 5. Wrap-up

- [x] 5.1 Add `src/minimal_cutout_search.py` to the CLAUDE.md Core Scripts table and
      File Layout section.
- [x] 5.2 Run `ruff check --fix` and `ruff format` on the new file.
- [x] 5.3 Run the full test suite (`uv run pytest tests/`) and confirm no
      regressions. (699 passed, 0 failed.)
