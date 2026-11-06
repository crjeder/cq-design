#!/usr/bin/env python3
"""
Subprocess entry point for CadQuery-based preview rendering.

Loads and runs a CadQuery model script in an isolated namespace,
captures the `result` workplane, then renders a preview PNG using
preview.render_multi_view or preview.render_single.

Usage:
    python3 render_preview.py --script model.py --output preview.png
    python3 render_preview.py --script model.py --output preview.png --views iso
    python3 render_preview.py --script model.py --output preview.png --title "My Part"

Exit codes:
    0  success
    1  script error, missing result, or render failure
"""

import argparse
import json
import os
import runpy
import shutil
import sys
import tempfile

MAX_SECTIONS = 3
MAX_SLICE_CUTS = 2
MAX_FEATURES = 4  # one 2 x 2 sheet


def _parse_detail_spec(spec: str) -> dict:
    """Parse one `--detail` spec into `{name, center, size, section}`.

    Format: `name=<feature>;center=x,y,z;size=<mm>[;section=<axis>=<pos>]`.
    `section` is optional; `axis` is x/y/z. Raises ValueError with a message
    naming the problem on any malformed spec.
    """
    parts = dict(item.split("=", 1) for item in spec.split(";") if item)
    for required in ("name", "center", "size"):
        if required not in parts:
            raise ValueError(f"missing '{required}=' in --detail spec '{spec}'")

    name = parts["name"].strip()
    if not name:
        raise ValueError(f"empty name= in --detail spec '{spec}'")

    center_parts = parts["center"].split(",")
    if len(center_parts) != 3:
        raise ValueError(f"center= must be 3 comma-separated values in --detail spec '{spec}'")
    try:
        center = tuple(float(v) for v in center_parts)
        size = float(parts["size"])
    except ValueError as exc:
        raise ValueError(f"non-numeric center/size in --detail spec '{spec}'") from exc

    section = None
    if "section" in parts:
        axis, _, pos = parts["section"].partition("=")
        axis = axis.strip().lower()
        if axis not in ("x", "y", "z") or not pos:
            raise ValueError(
                f"section= must be AXIS=VALUE with AXIS one of x/y/z in --detail spec '{spec}'"
            )
        try:
            section = (axis, float(pos))
        except ValueError as exc:
            raise ValueError(f"non-numeric section position in --detail spec '{spec}'") from exc

    return {"name": name, "center": center, "size": size, "section": section}


def _parse_callout_spec(spec: str) -> dict:
    """Parse one `--callout` spec into `{name, center}`.

    Format: `name=<feature>;center=x,y,z` (build-pose center). Raises
    ValueError with a message naming the problem on any malformed spec.
    """
    parts = dict(item.split("=", 1) for item in spec.split(";") if item)
    for required in ("name", "center"):
        if required not in parts:
            raise ValueError(f"missing '{required}=' in --callout spec '{spec}'")

    name = parts["name"].strip()
    if not name:
        raise ValueError(f"empty name= in --callout spec '{spec}'")

    center_parts = parts["center"].split(",")
    if len(center_parts) != 3:
        raise ValueError(f"center= must be 3 comma-separated values in --callout spec '{spec}'")
    try:
        center = tuple(float(v) for v in center_parts)
    except ValueError as exc:
        raise ValueError(f"non-numeric center in --callout spec '{spec}'") from exc

    return {"name": name, "center": center}


def _parse_callouts(args) -> list[dict]:
    """Parse and validate every `--callout` spec, exiting on error."""
    callouts = []
    for spec in args.callout:
        try:
            callouts.append(_parse_callout_spec(spec))
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            sys.exit(1)
    return callouts


def _whole_shape(result):
    """One Shape for a result; a Workplane's every val (.val() would drop .add()ed unions)."""
    import cadquery as cq

    if isinstance(result, cq.Workplane):
        return cq.Compound.makeCompound([v for v in result.vals() if isinstance(v, cq.Shape)])
    return result


def _auto_cuts(result, reserved, slots):
    """Geometry-driven (axis, pos) cuts: bore/boss cuts, else slice-scored cuts; [] on error."""
    if slots <= 0:
        return []
    try:
        from section_select import score_slices, select_sections

        shape = _whole_shape(result)
        cuts = select_sections(shape, slots, reserved)
        if not cuts:  # ponytail: slice scoring only when no bore/boss cut exists; bores win
            cuts = score_slices(shape, min(slots, MAX_SLICE_CUTS), reserved)
        return [(s["axis"], s["position_mm"]) for s in cuts]
    except Exception as exc:
        print(f"WARNING: --auto-sections failed: {exc}", file=sys.stderr)
        return []


def _section_cuts(result, extra_sections, cross_sections, auto_sections=False):
    """Resolve which cross-sections to render, as (axis, position_mm, is_center) tuples.

    Caller-supplied declared positions (`--extra-section`, threaded from the plan's
    feature/union positions) come first. `--auto-sections` then fills the remaining
    slots (up to MAX_SECTIONS total) with section_select cuts through bore/boss axes.
    Only when that leaves no cut does `--cross-sections` fall back to the three
    bounding-box-center cuts. Returns [] when nothing is requested.
    """
    cuts = list(extra_sections)
    if auto_sections:
        cuts += _auto_cuts(result, extra_sections, MAX_SECTIONS - len(cuts))
    if cuts:
        return [(axis, pos, False) for axis, pos in cuts]
    if not (cross_sections or auto_sections):
        return []
    import preview

    shape = preview._get_shape(result)
    bb = shape.BoundingBox()
    return [
        ("x", (bb.xmax + bb.xmin) / 2, True),
        ("y", (bb.ymax + bb.ymin) / 2, True),
        ("z", (bb.zmax + bb.zmin) / 2, True),
    ]


def _parse_extra_sections(args) -> list[tuple[str, float]]:
    """Parse and validate every `--extra-section` spec, exiting on error."""
    extra_sections = []
    for spec in args.extra_section:
        axis, _, value = spec.partition("=")
        axis = axis.strip().lower()
        if axis not in ("x", "y", "z") or not value:
            print(
                f"ERROR: invalid --extra-section '{spec}', expected AXIS=VALUE_MM "
                "with AXIS one of x/y/z",
                file=sys.stderr,
            )
            sys.exit(1)
        try:
            extra_sections.append((axis, float(value)))
        except ValueError:
            print(
                f"ERROR: invalid --extra-section '{spec}', VALUE_MM must be numeric",
                file=sys.stderr,
            )
            sys.exit(1)
    return extra_sections


def _parse_details(args) -> list[dict]:
    """Parse and validate every `--detail` spec, exiting on error."""
    details = []
    for spec in args.detail:
        try:
            details.append(_parse_detail_spec(spec))
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            sys.exit(1)
    return details


def _parse_features(args) -> list[dict]:
    """Parse and validate every `--feature` spec, exiting on error."""
    from feature_frame import parse_feature_spec

    features = []
    for spec in args.feature:
        try:
            features.append(parse_feature_spec(spec))
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            sys.exit(1)
    return features


def _render_features(result, features, out_dir, stem):
    """Render the first MAX_FEATURES located features (in the order given).

    Returns `(tiles, notes, paths, frames)`: one `(path, caption)` sheet tile per feature
    (its axis section when that renders and shows something, else its view), footer notes
    for features not shown or not located, every written file, and `{name: frame}`.
    """
    import preview
    from feature_frame import derive_frame

    shape = _whole_shape(result)
    tiles: list[tuple[str, str]] = []
    notes: list[str] = []
    paths: list[str] = []
    frames: dict[str, dict] = {}
    for number, feat in enumerate(features, start=1):
        name = feat["name"]
        try:
            frame = derive_frame(shape, feat["center"], feat["extent"])
            if frame is None:
                notes.append(f"{name} (not located)")
                continue
            if len(tiles) >= MAX_FEATURES:
                notes.append(f"{name} (not shown)")
                continue
            frames[name] = frame
            view_path = os.path.join(out_dir, f"{stem}_feature_{name}.png")
            _, view = preview.render_feature_view(result, view_path, frame, number)
            paths.append(view_path)
            tile = (view_path, f"{number} {name} - view {view}")
            sec_path = os.path.join(out_dir, f"{stem}_feature_{name}_section.png")
            sec = preview.render_feature_section(result, sec_path, frame, number)
            if sec is not None:
                paths.append(sec)
                if sec.informative and sec.cut is not None:
                    tile = (sec_path, f"{number} {name} - section {sec.cut[0]}={sec.cut[1]:g}")
            tiles.append(tile)
        except Exception as exc:
            print(f"WARNING: feature '{name}' preview failed: {exc}", file=sys.stderr)
            notes.append(f"{name} (not shown)")
    return tiles, notes, paths, frames


def _load_script_result(script_path: str, skill_root: str):
    """Run the model script in an isolated temp dir and return its validated `result`."""
    if not os.path.exists(script_path):
        print(f"ERROR: script not found: {script_path}", file=sys.stderr)
        sys.exit(1)

    # Ensure src/ is on the path so block imports resolve
    if skill_root not in sys.path:
        sys.path.insert(0, skill_root)

    # Run the model script in a temp directory so any STL exports land there
    # instead of polluting the caller's working directory.
    run_dir = tempfile.mkdtemp(prefix="cq_preview_")
    orig_dir = os.getcwd()
    try:
        os.chdir(run_dir)
        try:
            namespace = runpy.run_path(script_path, init_globals={"__file__": script_path})
        except Exception as exc:
            print(f"ERROR: model script failed: {exc}", file=sys.stderr)
            sys.exit(1)
    finally:
        os.chdir(orig_dir)
        shutil.rmtree(run_dir, ignore_errors=True)

    import cadquery as cq

    result = namespace.get("result")
    if result is None:
        print(
            "ERROR: model script did not assign a `result` variable.\n"
            "Every generated script must assign the final geometry to `result`.",
            file=sys.stderr,
        )
        sys.exit(1)
    if isinstance(result, dict):
        # Multi-union part: preview all unions together (added as separate solids, not fused).
        # The reserved keep-out key holds declared zones, not real geometry -- skip it (as
        # run_model_shim does) so zones don't render as phantom solids.
        from units import KEEP_OUT_KEY

        union_wps = [wp for uid, wp in result.items() if uid != KEEP_OUT_KEY]
        if not union_wps:
            print(
                "ERROR: `result` dict has no union geometry (only the reserved "
                f"'{KEEP_OUT_KEY}' key).",
                file=sys.stderr,
            )
            sys.exit(1)
        combined = union_wps[0]
        for wp in union_wps[1:]:
            combined = combined.add(wp)
        result = combined
    if not isinstance(result, (cq.Workplane, cq.Shape)):
        print(
            f"ERROR: `result` is {type(result).__name__}, expected a CadQuery Workplane or Shape.",
            file=sys.stderr,
        )
        sys.exit(1)
    return result


def _render_all(
    result,
    args,
    extra_sections: list[tuple[str, float]],
    details: list[dict],
    callouts: list[dict],
    features: list[dict] | None = None,
) -> list[str]:
    """Render the main preview plus any cross-section/detail files. Return extra preview paths."""
    import preview

    title = args.title or (
        os.path.splitext(os.path.basename(args.script))[0].replace("_", " ").title()
    )
    if args.views == "multi":
        preview.render_multi_view(
            result,
            args.output,
            title=title,
            subtitle=args.subtitle,
            callouts=callouts,
            unlocated_names=args.unlocated_name,
            density_g_cm3=args.density,
            material=args.material,
        )
    else:
        preview.render_single(
            result, args.output, title=title, density_g_cm3=args.density, material=args.material
        )

    out_dir = os.path.dirname(args.output) or "."
    stem = os.path.splitext(os.path.basename(args.output))[0]
    extra_previews = []
    section_tiles = []

    # Cross-sections as SEPARATE files (multi view only): through the
    # caller-supplied declared positions (--extra-section) when provided, else the
    # bounding-box-center X/Y/Z cuts. Each is its own file so the review can open
    # and scrutinize it against a specific verification question, one at a time.
    if args.views == "multi" and (args.cross_sections or args.auto_sections or extra_sections):
        cuts = _section_cuts(result, extra_sections, args.cross_sections, args.auto_sections)
        for axis, pos, is_center in cuts:
            name = (
                f"{stem}_section_{axis}.png"
                if is_center
                else f"{stem}_section_{axis}_{pos:g}mm.png"
            )
            section_path = os.path.join(out_dir, name)
            written = preview.render_section(result, section_path, axis, pos)
            if written is None:
                print(
                    f"WARNING: cross-section {axis}={pos:g} failed (degenerate cut), skipping",
                    file=sys.stderr,
                )
            else:
                extra_previews.append(written)
                section_tiles.append((written, f"section {axis}={pos:g}"))

    for number, spec in enumerate(details, start=1):
        detail_path = os.path.join(out_dir, f"{stem}_detail_{spec['name']}.png")
        preview.render_detail_view(
            result, detail_path, spec["center"], spec["size"], marker=(number, spec["center"])
        )
        extra_previews.append(detail_path)

        if spec["section"] is not None:
            axis, pos = spec["section"]
            section_path = os.path.join(out_dir, f"{stem}_section_{axis}_{spec['name']}.png")
            written = preview.render_detail_section(
                result,
                section_path,
                axis,
                pos,
                spec["center"],
                spec["size"],
                marker=(number, spec["center"]),
            )
            if written is None:
                print(
                    f"WARNING: detail section for '{spec['name']}' failed "
                    "(degenerate cut), skipping",
                    file=sys.stderr,
                )
            else:
                extra_previews.append(written)

    if features or args.sheet:
        tiles, notes, paths, frames = _render_features(result, features or [], out_dir, stem)
        if frames:
            with open(os.path.join(out_dir, f"{stem}_frames.json"), "w", encoding="utf-8") as f:
                json.dump(frames, f)
        sheet_tiles = (tiles + section_tiles)[:MAX_FEATURES]
        if args.sheet and sheet_tiles:
            sheet_path = os.path.join(out_dir, f"{stem}_sheet.png")
            preview.render_sheet(sheet_tiles, sheet_path, notes, title=title)
            extra_previews.insert(0, sheet_path)
        extra_previews += paths

    return extra_previews


def main():
    parser = argparse.ArgumentParser(description="Render a CadQuery model script as a preview PNG")
    parser.add_argument("--script", required=True, help="Path to the CadQuery .py model script")
    parser.add_argument("--output", required=True, help="Output PNG path")
    parser.add_argument("--views", choices=["iso", "multi"], default="multi")
    parser.add_argument("--title", default=None)
    parser.add_argument("--subtitle", default=None)
    parser.add_argument(
        "--density", type=float, default=1.24, help="Filament density in g/cm3 (default: PLA)"
    )
    parser.add_argument("--material", default="PLA", help="Material name for the footer label")
    parser.add_argument(
        "--cross-sections",
        action="store_true",
        help=(
            "Render cross-sections as separate files (multi view only): through the "
            "--extra-section positions when given, else the bounding-box-center cuts. "
            "Ignored for --views iso."
        ),
    )
    parser.add_argument(
        "--auto-sections",
        action="store_true",
        help=(
            "Fill the remaining section slots (up to 3 total, after any --extra-section "
            "cuts) with geometry-driven cuts through bore/boss axes from section_select.py. "
            "Implies --cross-sections; bounding-box-center cuts remain the fallback when "
            "nothing is selected. A selector error only warns."
        ),
    )
    parser.add_argument(
        "--extra-section",
        action="append",
        default=[],
        metavar="AXIS=VALUE_MM",
        help=(
            "Additional targeted cross-section beyond the default center cuts, e.g. "
            "--extra-section x=50. AXIS is x/y/z, VALUE_MM is the cut position along "
            "that axis. Repeatable. Ignored for --views iso."
        ),
    )
    parser.add_argument(
        "--detail",
        action="append",
        default=[],
        metavar="SPEC",
        help=(
            "Standalone high-resolution detail view for a small feature: "
            "'name=<feature>;center=x,y,z;size=<mm>', optionally with a matching "
            "detail cross-section: '...;section=<axis>=<pos>'. Written as separate "
            "files named after <feature>, independent of --views. Repeatable."
        ),
    )
    parser.add_argument(
        "--callout",
        action="append",
        default=[],
        metavar="SPEC",
        help=(
            "Numbered badge + leader line at a feature's projected position on the "
            "tile's three orthographic panels (multi view only): "
            "'name=<feature>;center=x,y,z'. Repeatable; badge numbers follow "
            "supply order. Adds a legend row mapping badges to names."
        ),
    )
    parser.add_argument(
        "--unlocated-name",
        action="append",
        default=[],
        metavar="NAME",
        help=(
            "Named feature with no known position: listed in the legend as "
            "'NAME (not located)' without a badge. Repeatable."
        ),
    )
    parser.add_argument(
        "--feature",
        action="append",
        default=[],
        metavar="SPEC",
        help=(
            "Per-feature preview in relevance order: 'name=<feature>;center=x,y,z"
            "[;diameter=<d>|;size=<w>,<h>]'. The feature's bbox, normal and depth are "
            "derived from the solid; writes <stem>_feature_<name>.png (camera along the "
            "normal, marker on the feature) and, when it has depth, "
            "<stem>_feature_<name>_section.png. Only the first 4 located features are "
            "rendered; the rest are listed '(not shown)'. Repeatable."
        ),
    )
    parser.add_argument(
        "--sheet",
        action="store_true",
        help=(
            "Compose one 2 x 2 <stem>_sheet.png of at most 4 tiles: --feature tiles in "
            "order, then whole-part sections. Listed first among the extra previews."
        ),
    )
    args = parser.parse_args()

    extra_sections = _parse_extra_sections(args)
    features = _parse_features(args)
    details = _parse_details(args)
    callouts = _parse_callouts(args)

    script_path = os.path.abspath(args.script)
    skill_root = os.path.dirname(os.path.abspath(__file__))
    result = _load_script_result(script_path, skill_root)

    try:
        extra_previews = _render_all(result, args, extra_sections, details, callouts, features)
    except Exception as exc:
        print(f"ERROR: preview render failed: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Preview saved: {args.output} ({os.path.getsize(args.output)} bytes)")
    for path in extra_previews:
        flag = getattr(path, "informative", None)
        note = "" if flag is None else f" (informative: {str(flag).lower()})"
        print(f"Detail preview saved: {path}{note}")
    print(json.dumps({"extra_previews": extra_previews}))
    sys.exit(0)


if __name__ == "__main__":
    main()
