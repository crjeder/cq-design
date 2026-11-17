#!/usr/bin/env python3
"""Write the model files (3MF, STL, STEP, ...) with each object in its print orientation.

This script is a deliverable: the cq-design skill copies it into the `build/`
directory of your working directory, alongside the per-part scripts. The bundled
build tooling (`exporters/`, `blocks/`, `write_assembly.py`, `deliverables.py`,
`print_orientation.py`, `mesh_io.py`, `placement.py`, `mate_chain.py`) lives in a
sibling `lib/` directory, not build/ itself -- build/ holds only the part scripts you
actually edit. The working directory is a self-contained uv project, so everything needed to rebuild
the model lives here -- the skill does not have to be installed.

How to generate the model files
-------------------------------
The working directory is a uv project (it has its own `pyproject.toml`,
`.python-version`, and committed `uv.lock`). Sync the environment once, then run the
build with uv from the working-directory root:

    uv sync
    uv run python build/build.py

`uv sync` downloads a compatible Python (3.10-3.12) and installs the pinned
dependencies (CadQuery, trimesh, ...). Subsequent runs reuse the synced `.venv`.
With no arguments only the format your slicer prefers (profile.json's
`slicer.preferred_format`) is written. Ask for others with `--formats`:

    uv run python build/build.py --formats 3mf,step

Arguments (all optional):
    --plan          BUILD_PLAN.json (default: the parent of build/, i.e. the project root)
    --parts-dir     directory of <part-id>.py scripts (default: this script's dir)
    --out           where the model files are written (default: <project root>/out)
    --orientations  accepted orientations JSON (default: orientations.json in --parts-dir)
    --profile       profile.json (default: the project root); slicer.preferred_format is required
    --formats       formats to write, comma-separated: 3mf, stl, step, obj, iges, scad, estampo
                    (default: the profile's preferred_format only)

Outputs (all in --out, only for the formats requested):
    3mf:  model.3mf        one named object per union, with plate metadata
    stl:  <union-id>.stl   one print-pose STL per union
          plate_<n>.stl    one fused print-pose STL per multi-union plate
    step/obj/iges/scad:  <union-id>.<ext>  print pose, one per union
    estampo:  estampo.toml  slicer config for the STLs (also written)

When `orientations.json` (the skill's accepted per-union orientations) sits next to
the part scripts, build.py reuses it so the plates match what the skill delivered;
otherwise it computes each orientation fresh with the same `print_orientation` tooling,
honoring the plan's `optimize_for` mode (per-part override, else plan-level, else
`strength`). The files are written via `deliverables`, exactly as the skill writes them.

The bundled tooling sits in a `lib/` directory next to this script's own directory
(i.e. `../lib` relative to build.py), so it is added to `sys.path` explicitly below
before the imports that depend on it.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "lib"))

import cadquery as cq

from deliverables import FORMATS, write_deliverables
from freshness import is_stale, script_hash
from print_finishing import orientation_for
from units import is_copy, load_plan
from write_assembly import load_part_unions


def resolve_orientations(
    plan: dict, parts_dir: str, orientations_path: str
) -> tuple[dict[str, dict], dict[str, dict], list[str]]:
    """Return ({part_id: {"rotate": [...]}}, {part_id: full orientation result}, recomputed).

    Reuses the skill's accepted `orientations.json` when it exists (so the plates
    match the delivered ones); otherwise computes each union's orientation fresh. An
    accepted entry is checked against its union's current source script via its
    `source_script_hash` stamp: a mismatch means the part script changed since the
    entry was accepted, so it is recomputed instead of reused (and the fresh result is
    stamped); an entry with no stamp is reused unconditionally, matching the behavior
    before provenance stamping existed. `recomputed` lists the union ids that were
    recomputed specifically because their accepted entry was stale.
    Raises RuntimeError naming the union when a part script cannot be loaded or
    oriented, so the caller can fail fast with an actionable message.
    """
    accepted: dict[str, dict] = {}
    if os.path.isfile(orientations_path):
        with open(orientations_path, encoding="utf-8") as f:
            accepted = json.load(f)

    overhang_deg = plan["constraints"]["overhang_max_deg"]
    bridge_max_mm = plan["constraints"].get("bridge_max_mm", 10.0)
    plan_mode = plan.get("optimize_for", "strength")
    orientations: dict[str, dict] = {}
    summary: dict[str, dict] = {}
    recomputed: list[str] = []
    parts_by_id = {p["id"]: p for p in plan.get("parts", [])}

    def _script(part: dict) -> str:
        return os.path.join(
            parts_dir, f"{part['copy_of']['part'] if is_copy(part) else part['id']}.py"
        )

    def _union_ids(part: dict) -> list[str]:
        return [u["id"] for u in part.get("unions", [])] or [part["id"]]

    # Unions that must be computed (no accepted entry, or a stale one) -> was it stale.
    # Only these are reported as progress, so N is known up front.
    todo: dict[str, bool] = {}
    for part in plan.get("parts", []):
        for uid in _union_ids(part):
            entry = accepted.get(uid)
            stale = entry is not None and is_stale(entry.get("source_script_hash"), _script(part))
            if entry is None or stale:
                todo[uid] = stale
    done = 0
    for part in plan.get("parts", []):
        script = _script(part)
        optimize_for = part.get("optimize_for", plan_mode)
        wp_by_uid: dict[str, cq.Workplane] | None = None  # loaded lazily, once per part
        for uid in _union_ids(part):
            stale = todo.get(uid, False)
            if uid not in todo:
                chosen = accepted[uid]
            else:
                done += 1
                print(f"[{done}/{len(todo)}] orientation {uid}", flush=True)
                try:
                    if wp_by_uid is None:
                        wp_by_uid = dict(load_part_unions(part, parts_by_id, parts_dir)[2])
                    chosen = orientation_for(
                        wp_by_uid[uid],
                        part,
                        overhang_deg,
                        optimize_for,
                        bridge_max_mm,
                        progress=lambda line: print(line, flush=True),
                    )
                except Exception as exc:
                    raise RuntimeError(f"union {uid!r}: {exc}") from exc
                chosen = {**chosen, "source_script_hash": script_hash(script)}
                if stale:
                    recomputed.append(uid)
            orientations[uid] = {"rotate": chosen["rotate"]}
            summary[uid] = chosen
    return orientations, summary, recomputed


def load_preferred_format(profile_path: str) -> tuple[str, str | None, dict]:
    """Return (preferred_format, slicer_name, profile) from profile.json; ValueError if unset."""
    if not os.path.isfile(profile_path):
        hint = ""
        legacy = os.path.join(os.path.dirname(profile_path), "printer_profile.json")
        if os.path.isfile(legacy):
            hint = " (rename printer_profile.json to profile.json)"
        raise ValueError(f"{profile_path} not found{hint}")
    with open(profile_path, encoding="utf-8") as f:
        profile = json.load(f)
    slicer = profile.get("slicer") or {}
    fmt = slicer.get("preferred_format")
    if fmt not in FORMATS:
        raise ValueError(
            f"{profile_path}: slicer.preferred_format must be one of "
            f"{', '.join(FORMATS)}; got {fmt!r}"
        )
    return fmt, slicer.get("slicer_name"), profile


def write_labeled_previews(
    plan: dict, plan_path: str, parts_dir: str, preview_dir: str
) -> list[str]:
    """Write `<id>_design.stl` + `<id>_preview_labeled.png` per part script; return the PNGs.

    A part whose recorded script hash still matches is not re-exported. A failing part is
    reported on stderr and skipped: the preview never fails the build.
    """
    import export_design_stl
    import render_labeled

    pngs = []
    for part in plan.get("parts", []):
        script = os.path.join(parts_dir, f"{part['id']}.py")
        if is_copy(part) or not os.path.isfile(script):
            continue
        stl = os.path.join(preview_dir, f"{part['id']}_design.stl")
        feats = os.path.join(preview_dir, f"{part['id']}_design.features.json")
        png = os.path.join(preview_dir, f"{part['id']}_preview_labeled.png")
        try:
            with open(feats, encoding="utf-8") as f:
                recorded = json.load(f).get("source_script_hash")
        except (OSError, ValueError):
            recorded = None
        if not (os.path.isfile(png) and os.path.isfile(stl)) or recorded != script_hash(script):
            report = export_design_stl.export_design_stl(script, stl)
            if not report["success"]:
                msg = report["errors"][0]["message"]
                sys.stderr.write(f"labeled preview skipped for {part['id']}: {msg}\n")
                continue
            render_labeled.render_labeled(stl, feats, png, part["id"], plan_path)
        pngs.append(png)
    return pngs


def _print_summary(summary: dict[str, dict], result: dict, recomputed: list[str]) -> None:
    """Print the chosen orientation per union, then the files written per format."""
    for pid, chosen in summary.items():
        rot = ", ".join(f"{s['axis']}{s['angle_deg']:+g}" for s in chosen["rotate"])
        print(f"{pid}: orientation [{rot}]")
    for fmt, files in result["files"].items():
        for name, path in files.items():
            print(f"{fmt} {name}: {path}")
    if recomputed:
        print(f"recomputed (source script changed since accepted): {', '.join(recomputed)}")


def main() -> None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.join(script_dir, os.pardir)
    parser = argparse.ArgumentParser(
        description="Write the model files (3mf, stl, step, ...) in print orientation"
    )
    parser.add_argument(
        "--plan",
        default=os.path.join(project_root, "BUILD_PLAN.json"),
        help="Path to BUILD_PLAN.json (default: the project root)",
    )
    parser.add_argument(
        "--parts-dir",
        default=script_dir,
        help="Directory of <id>.py part scripts (default: this script's dir)",
    )
    parser.add_argument(
        "--out",
        default=os.path.join(project_root, "out"),
        help="Output directory for the model files (default: <project root>/out)",
    )
    parser.add_argument(
        "--orientations",
        default=None,
        help="Accepted orientations JSON (default: orientations.json in --parts-dir)",
    )
    parser.add_argument(
        "--profile",
        default=os.path.join(project_root, "profile.json"),
        help="Path to profile.json (default: the project root)",
    )
    parser.add_argument(
        "--formats",
        default="",
        help=f"Formats to write, comma-separated ({', '.join(FORMATS)}); "
        "default: the profile's preferred_format",
    )
    parser.add_argument(
        "--preview-dir",
        default=os.path.join(project_root, "preview"),
        help="Directory for the labeled preview files (default: <project root>/preview)",
    )
    parser.add_argument(
        "--no-labeled-preview",
        action="store_true",
        help="Skip the design STL export and the labeled preview PNG",
    )
    args = parser.parse_args()
    formats = [f for f in args.formats.split(",") if f]
    bad = [f for f in formats if f not in FORMATS]
    if bad:
        parser.error(f"unsupported format(s) {bad}; supported: {', '.join(FORMATS)}")

    try:
        preferred, slicer_name, profile = load_preferred_format(args.profile)
    except ValueError as exc:
        sys.stderr.write(f"build failed: {exc}\n")
        sys.exit(1)
    formats = formats or [preferred]
    print(f"preferred format: {preferred}" + (f" ({slicer_name})" if slicer_name else ""))

    orientations_path = args.orientations or os.path.join(args.parts_dir, "orientations.json")

    plan = load_plan(args.plan)

    try:
        orientations, summary, recomputed = resolve_orientations(
            plan, args.parts_dir, orientations_path
        )
        result = write_deliverables(
            plan,
            args.parts_dir,
            args.out,
            orientations,
            formats,
            progress=lambda line: print(line, flush=True),
            profile=profile,
        )
    except Exception as exc:
        sys.stderr.write(f"build failed: {exc}\n")
        sys.exit(1)

    _print_summary(summary, result, recomputed)
    if not (args.no_labeled_preview or os.environ.get("CQ_NO_LABELED_PREVIEW")):
        for png in write_labeled_previews(plan, args.plan, args.parts_dir, args.preview_dir):
            print(f"labeled preview: {png}")
    sys.exit(0)


if __name__ == "__main__":
    main()
