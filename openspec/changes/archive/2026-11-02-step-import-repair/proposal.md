## Why

CADGenBench edit fixtures 202, 217, 240 and 250 ship an `input.step` that already fails the grader's validity gate, and `/cq-design:edit` carries the fault into the delivered file, so they score 0. Nothing in `src/` runs `BRepCheck`. `run_cadquery_model.py` reports `success: true` for all four invalid outputs, so neither an imported fault nor one the script introduces is ever caught.

A spike on the four inputs (2026-11-02) showed that generic `ShapeFix_Shape` / sewing / `UnifySameDomain` fix none of them. Targeted topological repairs do fix some: defeaturing the bad face (217) and dropping zero-area faces plus sewing at 1e-2 (250) both pass the full grader gate. Tolerance-only fixes look valid in memory but are lost on STEP export.

## What Changes

- New `blocks.import_solid(path, max_volume_deviation=0.01)`: imports a `.step`/`.stp`/`.brep` file and runs a cheap validity check on it: `BRepCheck_Analyzer.IsValid()` plus no face with area below 1e-3 mm². If that fails, it tries topological repairs, cheapest first, and accepts the first one that passes the same check with a volume change of at most `max_volume_deviation` (a fraction, default 1 %). A file that cannot be repaired within that limit raises a typed `step_unrepairable` error. Every repair is reported on stdout (strategy, faces removed, volume delta).
- Every STEP/BREP import in generated scripts goes through `blocks.import_solid` instead of `cq.importers.importStep` / `importBrep`. This covers the edit command's scripts and phase 0 rung-2 imports.
- `BRepCheck` runs on every `run_cadquery_model.py` run: the model shim checks each result body. An invalid body adds a blocking `invalid_brep` error naming the failing sub-shape statuses. **BREAKING** for any existing script whose result is BRep-invalid: it now fails instead of passing silently.
- Out of scope: the grader's topology-stitched mesh check (the cheap check stands in for it), and the faults the spike could not repair (202, 240).

## Capabilities

### New Capabilities
- `step-import-repair`: checked STEP/BREP import with a validity check, a repair ladder, a configurable volume-deviation limit, and a typed failure.
- `brep-validity-check`: `BRepCheck` on every wrapper run, reported as a blocking `invalid_brep` structured error.

### Modified Capabilities
- `step-edit-command`: edit scripts import the input through `blocks.import_solid` rather than `cq.importers` directly.
- `sourcing-triage`: rung-2 STEP/BREP imports use `blocks.import_solid`.

## Impact

- Code: `src/blocks/` (new importer module and export), `src/run_model_shim.py` (BRepCheck per body, sidecar JSON), `src/run_cadquery_model.py` (reads the sidecar, adds `invalid_brep`; new `step_unrepairable` hint in `_VERIFY_HINTS`).
- Prompts: `commands/edit.md`, `skill/phase0_sourcing.md`, `reference/scripts.md` (new error types), `FILES.md`.
- Runtime: BRepCheck costs about 1 s per 2,000 faces on each run. A repair costs seconds, paid on every run of a script that imports a broken file, because the repaired result is not cached.
- Benchmark: should flip 217 and 250. 202 and 240 still fail, now with an explicit `step_unrepairable` error instead of a silent invalid delivery.
- No new dependencies (OCP only).
