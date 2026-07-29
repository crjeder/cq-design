## 1. Produced-solid enumeration

- [x] 1.1 Replace `find_produced_stl` in `evals/run_evals.py` with an enumeration helper that
      returns every `<case_run_dir>/stl/*.stl`, excluding `plate_*.stl` and `keep_out__*.stl`,
      sorted by name for deterministic ordering.
- [x] 1.2 Delete the `rglob` fallback and confirm no remaining call site depends on it.
- [x] 1.3 Return an empty list (not an error) when `stl/` is absent, so the no-artifacts state
      in task 3.3 has a clean input.

## 2. Geometric assignment

- [x] 2.1 Add a shape-descriptor helper: for a loaded mesh, the three bounding-box extents
      sorted descending plus the mesh volume.
- [x] 2.2 Add a pairwise cost function combining descriptor terms as relative differences
      (`|a-b| / max(a,b)` per term) so large and small parts contribute comparably.
- [x] 2.3 Solve the assignment with `scipy.optimize.linear_sum_assignment` over the
      produced x golden cost matrix; handle rectangular matrices (returns `min(n, m)` pairs).
      Add no new dependency -- `scipy` is already declared in `pyproject.toml`.
- [x] 2.4 Compute `chamfer_mm` only for assigned pairs, leaving the existing Chamfer function
      (symmetric, point-to-surface, bbox-centered, 2000 samples) unchanged.

## 3. Scorecard semantics

- [x] 3.1 Keep `chamfer_mm` keyed by golden part id (`null` for an unmatched golden part) and
      add a sibling `matched_to` map recording the assigned produced STL name per golden part.
- [x] 3.2 Change `within_tolerance` so an unmatched golden part makes it `false`, replacing the
      current `all(c <= tol for c in measured) if measured else None`, which excludes
      unmatched parts and can report `true` on a partially-built model.
- [x] 3.3 Report a no-artifacts state, distinct from unavailable metrics, when a case's run
      directory contains no produced solids; `within_tolerance` is `false` there.
- [x] 3.4 Report surplus produced solids against `case.json`'s `expected_parts` (reported only,
      not failing -- see design Open Questions).
- [x] 3.5 Add a contributing-case count for the mean Chamfer to `aggregate()` and surface it in
      `render_markdown`'s aggregate line.
- [x] 3.6 Surface the no-artifacts state distinctly in the markdown table so it does not read
      as `unavailable`.

## 4. Tests

- [x] 4.1 Update `tests/test_run_evals.py` fixtures that write `stl/<part_id>.stl` -- the id no
      longer drives lookup, so at least one fixture should deliberately use a different name.
- [x] 4.2 Test: golden `sliding_lid` vs produced `lid.stl` with matching geometry assigns and
      scores near-zero Chamfer, with `matched_to` recording `lid`.
- [x] 4.3 Test: a two-golden-part case with one produced solid reports the unmatched part as a
      miss and `within_tolerance` false, even when the matched part is within tolerance.
- [x] 4.4 Test: `plate_*.stl` and `keep_out__*.stl` in `stl/` are not treated as produced
      solids.
- [x] 4.5 Test: a run directory with no `stl/` directory reports the no-artifacts state, not a
      crash and not `unavailable`.
- [x] 4.6 Test: two produced solids and two golden meshes assign one-to-one rather than both
      collapsing onto the nearest single golden mesh.
- [x] 4.7 Test: the aggregate reports its contributing-case count.
- [x] 4.8 Confirm the existing translation-normalization and missing-telemetry tests still
      pass unchanged.
- [x] 4.9 Run `uv run pytest tests/test_run_evals.py` and `ruff check --fix` / `ruff format` on
      the changed files.

## 5. Documentation

- [x] 5.1 Update `evals/run_evals.py`'s module docstring, which currently describes Chamfer as
      being computed against "the golden meshes" with correspondence unstated.
- [x] 5.2 Update the `evals/run_evals.py` row in `CLAUDE.md`'s Core Scripts table to mention
      geometric assignment.

## 6. Re-score existing runs

- [x] 6.1 Re-score `evals/runs/baseline-pre-claude5`, `evals/runs/before-citation`, and
      `evals/runs/after-citation` in score mode (no `--generate`, no token cost) to regenerate
      their scorecards on the new basis.
- [x] 6.2 Record in the change that pre-change scorecards are not comparable to the new ones.
- [x] 6.3 Report whether the re-scored A/B actually moves, and feed the result into the open
      `engineering-knowledge` section-4 item in `TODO.md`.

> Time-sensitive: `evals/runs/` is untracked and exists only on the current machine. Group 6 is
> possible only while those directories survive; once cleaned, re-scoring costs a full
> `--generate` run.
