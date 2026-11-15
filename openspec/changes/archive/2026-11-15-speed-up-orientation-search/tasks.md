## 1. Progress (done in the working tree)

- [x] 1.1 Add `progress` callback to `optimize_orientation`, `orientation_for`, `build_template.py`, and the CLI (stderr)
- [x] 1.2 Add a unit test: callback receives "candidate i/N" lines; no callback prints nothing

## 2. Vectorized pre-pass

- [x] 2.1 Add a helper computing per-candidate `nz`, centroid z, bed mask, raw support cost, build height (hull vertices), gentle-incline fraction, strength, cosmetic-down from rotations without copying the mesh
- [x] 2.2 Make the bed-contact and overhang-angle definitions shared with `mesh_io` so the pre-pass and exact path cannot drift
- [x] 2.3 Test: pre-pass values equal the per-candidate posed-mesh values on fixtures (within float tolerance)

## 3. Bounded exact evaluation

- [x] 3.1 Evaluate exact support in ascending lower-bound order and stop when the next lower bound strictly exceeds the incumbent, per `optimize_for` mode and respecting bands and the stable-only filter
- [x] 3.2 Add `prune` switch (default on) so the exhaustive path remains available
- [x] 3.3 Equivalence test: pruned vs exhaustive give the same `rotate`, `support_score`, `strength_score`, `bed_contact_mm2`, `stable` for every `optimize_for` mode across existing fixtures
- [x] 3.4 Tie test: a candidate whose lower bound equals the incumbent is still evaluated

## 4. Scoring tessellation

- [x] 4.1 Add `tolerance` / `angular_tolerance` to `orientation_for`, default unchanged
- [x] 4.2 Sweep a few curved fixtures at coarser tolerances; record whether selections match and the face-count reduction
- [x] 4.3 Decide on a new default only if every selection matches; otherwise leave opt-in

## 5. Validation

- [x] 5.1 Time the Silica-tray tray before and after (baseline 53.5 s, 1,292,626 faces); record in the change notes
- [x] 5.2 Run `uv run pytest tests/test_print_orientation.py tests/test_build_script.py` and `uv run --group dev mypy` on touched files
- [x] 5.3 Update `reference/scripts.md` for the `progress`, `prune` and tolerance parameters
