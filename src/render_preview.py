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
import os
import runpy
import shutil
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description="Render a CadQuery model script as a preview PNG")
    parser.add_argument("--script", required=True, help="Path to the CadQuery .py model script")
    parser.add_argument("--output", required=True, help="Output PNG path")
    parser.add_argument("--views", choices=["iso", "multi"], default="multi")
    parser.add_argument("--title", default=None)
    parser.add_argument("--subtitle", default=None)
    parser.add_argument(
        "--cross-sections",
        action="store_true",
        help="Append cross-section views to the multi-view tile (ignored for --views iso)",
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
    args = parser.parse_args()

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

    script_path = os.path.abspath(args.script)
    if not os.path.exists(script_path):
        print(f"ERROR: script not found: {script_path}", file=sys.stderr)
        sys.exit(1)

    # Ensure src/ is on the path so block imports resolve
    skill_root = os.path.dirname(os.path.abspath(__file__))
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

    # Extract result
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
        union_wps = list(result.values())
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

    # Render
    try:
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
                cross_sections=args.cross_sections,
                extra_sections=extra_sections or None,
            )
        else:
            preview.render_single(result, args.output, title=title)
    except Exception as exc:
        print(f"ERROR: preview render failed: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Preview saved: {args.output} ({os.path.getsize(args.output)} bytes)")
    sys.exit(0)


if __name__ == "__main__":
    main()
