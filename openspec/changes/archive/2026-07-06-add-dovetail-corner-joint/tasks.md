## 1. Implement the block

- [x] 1.1 In `src/blocks/joints.py`, add an internal helper (e.g. `_dovetail_comb`) that tiles
      `pin_count` trapezoid teeth across X at pitch `pin_width + tail_width`, centered about
      X=0, reusing `_trapezoid_profile`/`_extrude_profile` for the per-tooth cross-section, with
      `half_base = pin_width / 2` and `half_top = half_base - tan(radians(flare_deg)) *
      board_thickness`.
- [x] 1.2 Add `dovetail_corner_joint(pin_count, pin_width, tail_width, board_thickness,
      tooth_length, flare_deg=15.0, corner_angle_deg=90.0, clearance=0.1) ->
      dict[str, cq.Workplane]`. `"pins"` = the comb from 1.1 at nominal dimensions. `"tails"` =
      the same comb with `half_top`/`half_base` each grown by `clearance`, rotated about the X
      axis (through the shared corner edge) by `-corner_angle_deg` relative to `"pins"`'s frame.
- [x] 1.3 Write the function docstring following this file's existing convention (see
      `pin_hinge`, `dovetail_groove`): explain the corner-joint use case, the `emits` dict-key
      contract (which board pulls which key, union vs. cut), the `flare_deg` vs.
      `dovetail_groove.angle` naming distinction, the `corner_angle_deg` generalization and its
      board-mitering non-goal, and the recommended print orientation (flat, tooth axis in the
      build plane).

## 2. Integrate into the inventory

- [x] 2.1 Add `dovetail_corner` to `src/blocks/inventory_schema.json`'s interface `type` enum.
- [x] 2.2 Add `dovetail_corner` to `_VALID_INTERFACE_TYPES` in `src/blocks/validate.py`.
- [x] 2.3 Add a `dovetail_corner_joint` entry to `src/blocks/inventory.json`: `module:
      blocks.joints`, `function: dovetail_corner_joint`, `motion: rigid`, `reversible: true`,
      `carries` including a shear direction, `emits: ["pins", "tails"]`, `params` documenting
      each parameter (including the `flare_deg` vs. `angle` and `corner_angle_deg` distinctions),
      one `dovetail_corner`-type interface, and a `use` string that documents the mating contract
      in prose (which member is unioned vs. cut, and that two different boards are wired via a
      `joints` entry) following the `pin_hinge` entry's self-documenting style.

## 3. Tests

- [x] 3.1 `tests/test_blocks.py`: comb X-span and centering (spec scenarios "Pins comb spans...",
      "Comb is centered in X").
- [x] 3.2 `tests/test_blocks.py`: `flare_deg=0` produces a rectangular tooth; default `flare_deg`
      matches the documented formula.
- [x] 3.3 `tests/test_blocks.py`: default `corner_angle_deg=90` vs. a non-default value (e.g. 60)
      rotates `"tails"` relative to `"pins"` by the expected amount.
- [x] 3.4 `tests/test_blocks.py`: `clearance` sign behavior -- positive grows the tail socket,
      negative shrinks it, zero reproduces the nominal (reference-equivalent) exact fit.
- [x] 3.5 `tests/test_blocks.py`: inventory validation passes with the new entry and interface
      type; a regression guard (mirroring `test_shipped_inventory_still_valid`) that the shipped
      inventory stays valid.
- [x] 3.6 `tests/test_plan_validate.py` (or `tests/test_mate_chain.py`): a `joints` entry naming
      `block: "dovetail_corner_joint"` with `members: [{member: "pins", part: ...}, {member:
      "tails", part: ...}]` validates successfully and `mate_chain.compute_mate_poses` derives a
      pose for the non-root part -- the first real exercise of the cross-part matched-pair path.

## 4. Verify

- [x] 4.1 Run `uv run ruff check` / `uv run ruff format --check` on changed files.
- [x] 4.2 Run `uv run mypy src/` to confirm no type errors.
- [x] 4.3 Run `uv run pytest tests/` to confirm the full suite stays green.
- [x] 4.4 Run `openspec validate add-dovetail-corner-joint`.
