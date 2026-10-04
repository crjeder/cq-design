## Context

`model_export.export_model` places each union (`placed[uid]`) and writes `model.3mf` (print pose), per-union STLs (assembled pose) and fused plate STLs. `build_template.py` is a thin CLI over it. The modular exporters in `src/exporters/` (`_REGISTRY`) already write step/obj/iges/scad from a `cq.Workplane`, but only `run_cadquery_model.py --deliver` uses them, on the authored pose.

## Goals / Non-Goals

**Goals:**
- One command (`build.py`) yields extra CAD formats, in the same pose as the per-union STLs.
- Default output byte-for-byte unchanged.

**Non-Goals:**
- Making 3MF or STL optional (the gate's kinematic/plate-clearance/keep-out checks consume the STLs).
- STEP for fused plates, or STEP in the print-oriented pose.
- Assembly-structured STEP (one file with named products); one file per union only.

## Decisions

- **`formats` lists extras only.** Alternative: a full list defaulting to `stl,3mf`. Rejected: it implies STL/3MF can be dropped, which would break the gate checks.
- **Assembled pose, one file per union.** Matches the per-union STLs and what a CAD user wants to import to reassemble. Alternative, print pose: useful for slicers but those use the 3MF.
- **Reuse `exporters._REGISTRY`.** Call each module's `export(wp, path)` on `placed[uid]`; no new writer. The registry's `stl`/`3mf` entries are excluded because those are written by existing code paths. Validate keys against the registry minus those two, before writing anything.
- **Written to `stl_dir`** next to the union STLs; reported under a new `format_files` result key. Existing keys unchanged.
- **Freshness manifest untouched**: it tracks STLs, which are still the checked artifacts.

## Risks / Trade-offs

- [STEP export of a placed `Workplane` after `_pose_union` may lose nothing, but is untested] -> test that the STEP re-imports with the same volume and bounding box as the union STL.
- [`exporters` imports cadquery at import time; `model_export` already does] -> no new import cost.
- [Docs claim `--formats` on build.py] -> update README and `reference/scripts.md` in the same change.

## Open Questions

- Should the print-oriented pose be selectable (`--pose assembled|print`) later? Deferred until asked.
