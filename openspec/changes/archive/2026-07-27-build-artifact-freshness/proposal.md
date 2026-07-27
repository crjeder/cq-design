## Why

Several pipeline stages consume artifacts derived from a part script, and none of them can
tell whether the script has changed since the artifact was produced. The artifacts are
cached deliberately -- that part is right, they are expensive and they encode accepted user
decisions -- but the cache has no invalidation at all.

Two consumers, both silent on staleness:

- **`build/orientations.json`.** `build_template.resolve_orientations`
  (`src/build_template.py:99-136`) reuses the accepted orientations whenever the file exists,
  specifically so a rebuild does not silently re-decide a pose the user approved. It compares
  nothing. Edit a part script, re-run `build/build.py`, and the deliverable 3MF/STL are
  written in the pose computed for the *old* geometry.
- **`stl/<union>.stl`.** The whole-model stages -- `kinematic_check.py`,
  `plate_clearance_check.py`, `keep_out_check.py` -- resolve assembled-pose STLs by path and
  check only `os.path.exists` (`src/kinematic_check.py:236`). If the export has not been re-run
  since the last script edit, every one of those checks validates geometry the project no
  longer builds, and reports a clean pass for it.

The C5 Phone-Holder retrospective caught the orientation case live and recorded it in
`TODO.md` ("orientation cache staleness"): `build/orientations.json` was carrying
`build_height_mm: 8.599` and a rationale explicitly dated "Recomputed round 4" while the
then-current round-6 cradle stood 16.1 mm tall. Nothing warned; `build.py` would have
regenerated deliverables against that stale pose and score.

Worth stating precisely, because it is the sharpest argument for the guard rather than
against it: **that project's files agree again today**, by luck. A later round moved the
cradle's pivot back down (`PIVOT_Z` 13.5 -> 6.0), which returned the part to 8.6 mm and
re-matched the cached height by coincidence. The stale rationale prose ("Recomputed round 4")
is still there, but the numbers are accidentally correct. A staleness bug that repairs itself
through an unrelated edit is precisely the kind that is never noticed and never fixed -- and
in the window where it was wrong, nothing in the pipeline could have said so.

## What Changes

- Add `src/freshness.py`: a small stdlib-only helper that computes a provenance stamp for a
  generated artifact and compares it against the source that produced it. The stamp is a hash
  of the **part script's contents** -- the honest provenance key, since the script is what
  `model_export` and `print_orientation` actually consume. File mtime is deliberately not the
  key: it is noisy across checkouts, copies, and editors.
- Record the stamp at write time:
  - `print_orientation.py` gains an optional `--source-script` argument and records that
    script's hash in the orientation result, so `build/orientations.json` entries become
    self-describing. It needs the argument because its CLI input is the authored-frame STL,
    not the script -- only the caller knows which script produced that STL. Omitting the
    argument leaves the result unstamped, which the consumer treats as "no stamp" (see the
    degradation rule below) rather than as a mismatch.
  - `model_export.py` writes a sidecar manifest next to the exported STLs mapping each union
    id to the hash of the script it was built from, plus the export timestamp.
- Verify the stamp at read time:
  - `build_template.resolve_orientations` recomputes each part script's hash and, on mismatch,
    **recomputes that entry's orientation** rather than reusing it -- with a clear note in the
    build summary saying which entries were recomputed and why. Reuse remains the behaviour for
    entries that still match, so approved poses are not silently discarded.
  - The whole-model stages (`kinematic_check`, `plate_clearance_check`, `keep_out_check`)
    consult the manifest and emit a `stale_artifact` finding -- shared
    `{source, severity, type, message, hint}` contract, `severity: "error"` -- naming the union
    and telling the user to re-run the export, instead of validating superseded geometry and
    passing.
- Handle the absent-manifest case as `check_skipped` (a `warning`), not a hard failure: a
  project exported before this change, or an STL dropped in by hand, must not become
  unvalidatable. This mirrors how the collision backend already degrades.

Deliberately **not** in scope: hashing the block library or the `lib/` bundle (a block edit
can change geometry without touching the part script -- real, but a much wider blast radius
and a separate decision); auto-re-running the export from inside a check stage (the stages
stay read-only; they report and let the pipeline act); and geometry-bbox comparison as an
alternative key (cheap and tempting, but it misses any edit that preserves the bounding box --
the phone-holder pivot move being exactly such an edit).

## Capabilities

### New Capabilities

- `build-artifact-freshness`: a shared provenance-stamp mechanism -- how a generated artifact
  records the source script it came from, and how a consumer detects that the source has
  changed since. Covers the stamp definition, the absent-stamp degradation rule, and the
  `stale_artifact` finding contract.

### Modified Capabilities

- `print-orientation-optimization`: an orientation result carries the provenance stamp of the
  script it was computed from.
- `model-export`: the export writes a provenance manifest alongside the per-union STLs.
- `build-script`: `build.py` validates each cached orientation's stamp before reusing it, and
  recomputes (reporting which and why) on mismatch, instead of reusing unconditionally.

## Impact

- `src/freshness.py` (new), `tests/test_freshness.py` (new) -- stdlib only, fast, no CadQuery.
- `src/print_orientation.py` -- stamp on the result object.
- `src/model_export.py` -- write the manifest.
- `src/build_template.py` -- `resolve_orientations` gains per-entry validation; **note** this
  file is copied verbatim to `build/build.py`, so the change ships to every generated project
  and must stay dependency-free relative to the bundled `lib/`.
- `src/kinematic_check.py`, `src/plate_clearance_check.py`, `src/keep_out_check.py` -- manifest
  consultation and the `stale_artifact` finding.
- `src/quality_gate.py` -- surface `stale_artifact` in the aggregated report.
- `skill/phase3_build.md` -- what a `stale_artifact` finding means and the re-export step that
  clears it.
- `CLAUDE.md` -- new Core Scripts row; amend the `model_export.py` / `build_template.py` rows.
- `TODO.md` -- mark the "orientation cache staleness" sub-item.
- Backward compatible: projects without a manifest degrade to today's behaviour with a
  `check_skipped` warning rather than failing.
