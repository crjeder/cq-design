## Context

Load sites per gate run (`quality_gate.py` process unless noted): shim subprocess (`run_cadquery_model.py`), `--deliver` (`run_exporters` -> `_load_result`, wrapper process), edge-treatment (`_run_with_hook`, with the orientation's rotate), feature-presence (`_run_with_hook`, authored frame), toolpath-speed (the gate stage resolves unions, then `run_toolpath_speed_check` loads again), Gridfinity (`run_gridfinity_check`). `_load_result` always re-executes the script. The hooks monkey-patch `Workplane.fillet/chamfer` and `.cut/.union`, so they need a live execution and cannot be served from a cache.

## Goals / Non-Goals

**Goals:** each distinct (script content, print pose) executes once per process; `--deliver` adds no second execution when the shim already ran the same pose; findings unchanged.

**Non-Goals:** removing the shim subprocess (it isolates the run for timeout and typed stderr errors); cross-process caching; caching STL tessellation (TODO item 7); the whole-model stage reload (TODO item 3).

## Decisions

- **Memoize inside `_load_result`.** Key `(abspath, sha256(file bytes), json.dumps(print_rotate))`. Content hash, not mtime, so an in-session edit invalidates. A module-level dict with no eviction (a gate process handles one script). New kwarg `fresh=False`; hooked loads pass `fresh=True` (skip lookup, still store, since hooks do not change geometry). Rejected: per-call-site caching, which leaves every caller to remember it.
- **Cached `result` is shared.** Callers get the same `Workplane`. Known callers only read it (bbox, tessellate, `resolve_unions`) and CadQuery ops return new objects. Task 1.1 audits for in-place mutation before relying on this.
- **Merge the two hooks into one load, keyed by rotate.** The two checks take an optional `load` callable and the gate nests the feature check inside the edge check's load (`quality_gate._run_hooked_stages`), since the two hook disjoint methods (fillet/chamfer vs cut/union). Feature-presence compares in the authored frame, so it may share the load only when the part's rotate is None or identity; for a rotated part it keeps its own authored-frame load. Net: one hooked load for unrotated parts, two for rotated, down from two always. Standalone CLI and test use is unchanged (`load` defaults to a plain fresh load).
- **`--deliver` via the shim.** The wrapper passes the formats and output dir to the shim (env vars `CQ_DELIVER_FORMATS`, `CQ_DELIVER_DIR`) only when `--print-rotate` is absent, because `--deliver` exports the authored frame while a rotated shim run holds the posed frame. The shim calls a new `export_loaded(result, stem, formats, out_dir)` split out of `run_exporters` (which also calls it). With `--print-rotate`, behavior is unchanged (in-process reload). Exporter failures surface as today: stderr text and `success=False`.

## Risks / Trade-offs

- A script with import-time side effects (writes a file, prints) runs them once instead of several times. Strictly less surprising.
- `fresh=True` hooked loads still execute fully; the saving there is the merge, and the stored result feeds the toolpath-speed and Gridfinity stages.
- Shim-side delivery moves export time inside the shim's `--timeout`. Slow 3MF or STEP exports could trip it where the in-process path did not. Mitigation: measure on the largest eval case (task 5.1); fall back to in-process delivery if it regresses.
- Stale-cache risk is limited to a script that reads external files whose content changes between loads in one process. Not a pattern the gate uses.
