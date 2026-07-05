## 1. Reserved-key plumbing

- [x] 1.1 In `src/units.py`, add `resolve_keep_out(part, result)` (mirroring `resolve_unions`) that
      extracts `result["keep_out"]` (if present) as `[(zone_name, workplane), ...]`; posing happens
      where `resolve_unions`'s output is already posed (`model_export.py`), not in `units.py`, which
      stays CadQuery-free. Added `keep_out_stl_name(part_id, zone_name)` as the shared writer/reader
      naming convention, and `KEEP_OUT_KEY` as the reserved-word constant.
- [x] 1.2 `resolve_unions` now strips the reserved `"keep_out"` key before the "script result keys
      must match declared `unions`" comparison, in both the declared and undeclared-dict-result paths.
- [x] 1.3 In `src/plan_validate.py`'s `_check_unions`, reject `keep_out` as a declared union `id`
      (reserved-word conflict), alongside the existing duplicate-union-id check.
- [x] 1.4 Cross-part zone-name collisions are disambiguated by construction: `keep_out_check` issues
      always carry `zone_part` and `zone_name` as separate structured fields (never smashed into one
      string), and zone STLs are filesystem-qualified by part id (`keep_out_stl_name`) -- no separate
      dedup step is needed the way `model_export`'s single 3MF object name requires one.

## 2. Export, plate, and sweep exclusion

- [x] 2.1 In `src/model_export.py`, the per-part loop now also calls `resolve_keep_out`, poses each
      zone the same way as the part's real unions, and writes it to its own STL
      (`units.keep_out_stl_name`) -- zones never enter `records`/`plates`/`placed`, so they are never
      written to the 3MF, never assigned a plate, and never included in a fused plate STL. Returned
      as a new `keep_out_stls` key (`"<part_id>::<zone_name>"` -> path).
- [x] 2.2 In `src/run_model_shim.py`, the per-part auto-export loop now skips `KEEP_OUT_KEY` (it isn't
      a Workplane, so exporting it directly would crash; the whole-model check is what actually
      validates zones, not the per-part wrapper).
- [x] 2.3 Confirmed: `src/kinematic_check.py` derives its union list purely from `iter_unions(plan)`
      (plan-declared unions only) and never touches a script's `result` dict, so it was already
      unaffected -- no code change needed. Verified by the new `test_keep_out_check.py` /
      `test_units.py` tests rather than a kinematic_check code path.

## 3. Keep-out validation check

- [x] 3.1 Created `src/keep_out_check.py`: discovers every zone's STL in `--stl-dir` via the
      `keep_out__<part_id>__<zone_name>.stl` naming convention (longest-part-id-prefix match), then
      intersects each zone against every union excluding the zone's own declaring part's unions
      (trimesh + python-fcl `CollisionManager`, same tooling as `kinematic_check.py`).
- [x] 3.2 Emits `keep_out_violation` issues matching the shared `{source, severity, type, message,
      hint}` contract (`source: "geometry"`, `severity: "error"`), naming the offending union and the
      `(zone_part, zone_name)` pair as both structured fields and in the message text, with a hint
      pointing at the offending union's geometry.
- [x] 3.3 Degrades to a single `check_skipped` warning when trimesh/python-fcl are unavailable and at
      least one zone STL was discovered; returns `[]` immediately (before any import attempt) when no
      zone STLs are found, regardless of backend availability.
- [x] 3.4 Wired into `src/quality_gate.py` as `_run_keep_out_stage`, running once outside the fix loop
      alongside the existing kinematic and plate-clearance stages (after plan validation passes).

## 4. Tests

- [x] 4.1 New `tests/test_units.py`: `resolve_unions` ignores the reserved `keep_out` key (declared
      and undeclared-dict-result paths) and still raises on a real mismatch; `resolve_keep_out`
      extracts zones (and returns `[]` when absent or for a non-dict result); `keep_out_stl_name`
      naming convention.
- [x] 4.2 `tests/test_plan_validate.py`: `keep_out` rejected as a declared union id and as a bare
      part id (reserved-word conflict). The cross-check exemption itself is covered at the
      `resolve_unions` level in `test_units.py`, since that check lives in `units.py`, not
      `plan_validate.py`.
- [x] 4.3 `tests/test_model_export.py`: a declared zone is absent from the 3MF, from `union_stls`,
      and from `plate_stls`, but present in the new `keep_out_stls`; a zone inherits its declaring
      part's `placement`; a zone inherits its declaring part's derived mate-chain pose.
- [x] 4.4 New `tests/test_keep_out_check.py`: violation reported for a foreign union overlapping a
      zone; no violation for the declaring part's own union overlapping its own zone (but a
      DIFFERENT part's zone still checks against the first part); pass when no overlaps; `[]`
      returned (no import attempt) when no zone STLs are discovered; `check_skipped` degrade when
      the backend is unavailable or a foreign union's STL is missing.
- [x] 4.5 Gate-integration test lives in `tests/test_keep_out_check.py`
      (`test_gate_surfaces_keep_out_violation`), mirroring where `test_gate_surfaces_plate_clearance`
      lives in `test_plate_clearance_check.py` rather than in `test_quality_gate.py`: a
      `keep_out_violation` blocks a clean pass and appears in the rendered fix prompt.

Full suite: `uv run pytest tests/` -- 379 passed. `uv run ruff check` / `ruff format --check` clean
on every touched file.

## 5. Docs

- [x] 5.1 Updated `CLAUDE.md`'s script table (`units.py`, `quality_gate.py`, `model_export.py`,
      new `keep_out_check.py` row) and File Layout tree (also added the previously-missing
      `plate_clearance_check.py` entry it had drifted from).
- [x] 5.2 Updated `README.md`'s Files listing (`units.py`, `model_export.py`, new
      `keep_out_check.py` and `test_keep_out_check.py`/`test_units.py` entries).
