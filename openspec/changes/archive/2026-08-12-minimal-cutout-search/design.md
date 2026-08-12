## Context

`run_kinematic_check` (`src/kinematic_check.py`) already answers "does this pose
collide" and, since `contact-limited-sweep`, "how far did this joint get before it
stopped." What it does not answer is the inverse question a designer actually asks
mid-session: "how big does this clearance feature need to be for the joint to reach
its full required range?" On the C5 Phone-Holder, that inverse question was answered
by hand across two correction rounds: change `NOTCH_HEIGHT`, rerun, read the
collision finding, adjust, repeat -- a manual bisection.

The sweep is already precise (bisected stop values, `penetration_tol_mm3`
tolerance). The missing piece is purely the outer loop that drives a geometry
parameter toward the value where the sweep stops failing. This change adds only
that loop.

## Goals / Non-Goals

**Goals:**
- Automate the bisection loop a designer currently runs by hand: given a part
  script, a numeric parameter in its `PARAMETERS` block, and a `kinematics` entry's
  `joint_id`, find the minimal (or maximal) parameter value at which the sweep
  reports no `motion_collision`/uncapped `contact_limited_stop` for that joint.
- Reuse `run_kinematic_check` as the sole pass/fail oracle -- no new collision or
  volume measurement.
- Keep the tool a manual, author-invoked utility (like `import_params.py`), not a
  pipeline stage the gate calls automatically.

**Non-Goals:**
- Multi-parameter / multi-dimensional search. One scalar parameter per invocation.
- Handling non-monotonic parameter-to-clearance relationships. The tool checks its
  two bounds first (one must collide, one must clear) and fails fast if that
  precondition doesn't hold; it does not attempt to characterize the function shape.
- A new geometry/interference primitive. Every candidate is evaluated by literally
  regenerating the STL and calling the existing sweep.
- Automatic detection of *which* parameter to search over, or *which* joint is
  under-cleared. The author already knows this from a `motion_collision` finding;
  the tool takes both as required arguments.

## Decisions

**Bisection over the raw script text, located the same way `import_params.py`
locates parameters (AST, module-level `NAME = <numeric literal>` assignment).**
Rejected alternative: an environment-variable or CLI-flag override hook threaded
through `run_cadquery_model.py`. That would require every part script to opt in to
an override contract, touching the part-authoring convention for a search tool used
occasionally. AST-locate-and-rewrite touches no convention: it works on any script
already following the existing `PARAMETERS` block convention, unchanged.

**Per-candidate STL regeneration is scoped to the one part whose script was
edited; the rest of the model's STLs are reused from the existing `build/`
export.** `run_kinematic_check` needs every union's mesh, but only the searched
union's geometry changes between candidates. Regenerating the whole model per
bisection step (a script that already took a few seconds each on cq-design's own
integration tests) would make a ~10-15 step bisection the slow part of the
session; regenerating one part's STL does not.
Precondition: the plan's other unions must already have fresh exported STLs
(`freshness.py`'s existing staleness check surfaces this if not -- the tool does
not duplicate that check, it just requires a `--stl-dir` that's already current).

**The searched part's STL is written in the assembled frame via `model_export.py`'s
placement logic, not `run_cadquery_model.py --deliver`.** `--deliver` (via
`exporters.run_exporters`) writes the script's *authored*-frame geometry --
correct for iterating on a part in isolation, but `kinematic_check.py` reads
`stl_dir` expecting each `<union_id>.stl` already posed into the shared assembled
frame (placement, or a `joints` mate-chain pose when the part is reached through
one -- see `model_export.export_model`'s `_pose_union`). The candidate-evaluation
step therefore loads the part's `result` the same way `model_export.py` does
(`exporters._load_result` + `resolve_unions`), applies the same pose
(`placement.apply_cq`/`apply_matrix`, choosing the mate-chain pose when
`mate_chain.compute_mate_poses` has one for this part, exactly as
`_pose_union` does), and writes each resulting union's STL directly -- it does not
shell out to `run_cadquery_model.py` at all for this step, since there is nothing
in the JSON contract this loop needs (no DFM/geometry checks per candidate, only a
posed mesh for the sweep).

**Convergence and output.** Bisect between `--lo` (must fail the sweep) and `--hi`
(must pass) until `hi - lo <= --tolerance-mm` (default 0.1mm, matching
`penetration_tol_mm3`'s existing calibration note in `kinematic_check.py`). Report
both the converged boundary (`hi`, the tightest value observed to pass) and a
`--margin-mm` (default 0.2mm) recommended value (`hi + margin`). The tool never
writes the script by default; `--apply` writes the recommended value back using the
same line-rewrite path used for candidates, so the author can review before
accepting.

**Precondition check, not silent failure, on bad bounds.** Before bisecting, the
tool evaluates `--lo` and `--hi` once each. If `--lo` already passes or `--hi`
still fails, it exits with an error naming which bound broke the monotonicity
assumption, rather than bisecting toward a meaningless midpoint.

## Risks / Trade-offs

[A parameter is not actually monotonic with clearance -- e.g. a height parameter
also shifts a hole that briefly re-collides at a different pose] → mitigated by the
bounds precondition check (catches the common case: one bound already fails the
assumption) but not a full guarantee across the interior of the range; documented
as a known limitation, not solved.

[Bisection re-runs the CadQuery script + sweep every step; slow parts make this
slow] → scoped to single-part regeneration (see Decisions) keeps each step close to
one `run_cadquery_model.py` invocation; no further optimization (e.g. caching) is
in scope for a first version.

[`--apply` overwrites a script line a designer may have hand-formatted (comments,
alignment)] → line-level text substitution preserves the rest of the line's
formatting the same way `import_params.py`'s write-back does for the plan; the
value literal is the only thing replaced.

[Reusing `exporters._load_result` (ordinary Python import machinery) to load each
candidate's `result` reads back stale `__pycache__` bytecode, because the loop
rewrites the same script path many times per second -- faster than the pyc
mtime/size cache reliably invalidates -- so a candidate can silently execute the
*previous* candidate's compiled geometry] → the tool uses its own loader
(`_exec_script`) that `compile()`s and `exec()`s the source directly on every call,
bypassing the bytecode cache entirely. Found during implementation by observing
identical exported STL bounds across different parameter values.

## Open Questions

None blocking -- if usage surfaces a need for multi-parameter search or
non-monotonic handling, that is a follow-up change, not a gap in this one.
