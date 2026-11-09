#!/usr/bin/env python3
"""Render a Phase 1 concept sketch (SVG) from a small JSON description. Stdlib only.

    python concept_sketch.py sketches/concept.json [--out sketches/concept.svg]

JSON: {"title": str,
       "shapes": [{"view", "type": "rect"|"circle"|"line"|"polyline", ...}],
       "labels": [{"view", "x", "y", "text"}],
       "dims":   [{"view", "from": [x, y], "to": [x, y], "text"}]}
`view` is front|top|side. Coordinates are mm, y up, one origin per view. rect: x, y, w, h
(lower-left corner); circle: cx, cy, r; line: x1, y1, x2, y2; polyline: points.
The sketch only communicates the understood concept; nothing is derived from it.
Exit 0 and prints {"out": path} on success; exit 1 and prints {"error": ...} on bad input.
"""

import argparse
import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape

VIEWS = ("front", "top", "side")
SHAPES = ("rect", "circle", "line", "polyline")
PANEL = 320  # px per view panel
MARGIN = 36


class SketchError(ValueError):
    """Unknown shape or view, or a missing field."""


def _points(item: dict) -> list[tuple[float, float]]:
    t = item["type"]
    if t == "rect":
        x, y, w, h = (item[k] for k in ("x", "y", "w", "h"))
        return [(x, y), (x + w, y + h)]
    if t == "circle":
        cx, cy, r = (item[k] for k in ("cx", "cy", "r"))
        return [(cx - r, cy - r), (cx + r, cy + r)]
    if t == "line":
        return [(item["x1"], item["y1"]), (item["x2"], item["y2"])]
    return [tuple(p) for p in item["points"]]


def _check(spec: dict) -> None:
    for item in spec.get("shapes", []):
        if item.get("type") not in SHAPES:
            raise SketchError(f"unknown shape type {item.get('type')!r}; use {SHAPES}")
    for key in ("shapes", "labels", "dims"):
        for item in spec.get(key, []):
            if item.get("view") not in VIEWS:
                raise SketchError(f"unknown view {item.get('view')!r} in {key}; use {VIEWS}")


def render(spec: dict) -> str:
    """Return the SVG text for `spec`; raises SketchError on bad input."""
    _check(spec)
    try:
        pts: dict[str, list] = {v: [] for v in VIEWS}
        for item in spec.get("shapes", []):
            pts[item["view"]] += _points(item)
        for d in spec.get("dims", []):
            pts[d["view"]] += [tuple(d["from"]), tuple(d["to"])]
        for lab in spec.get("labels", []):
            pts[lab["view"]].append((lab["x"], lab["y"]))
    except (KeyError, TypeError) as exc:
        raise SketchError(f"missing or malformed field: {exc}") from None
    used = [v for v in VIEWS if pts[v]]
    if not used:
        raise SketchError("nothing to draw")
    box = {}
    for v in used:
        xs, ys = zip(*pts[v], strict=True)
        box[v] = (min(xs), min(ys), max(xs), max(ys))
    span = max(max(b[2] - b[0], b[3] - b[1]) for b in box.values()) or 1.0
    k = (PANEL - 2 * MARGIN) / span
    width, height = PANEL * len(used), PANEL + 40
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        'font-family="sans-serif" font-size="12">',
        f"<title>{escape(str(spec.get('title', 'Concept sketch')))}</title>",
        f'<rect width="{width}" height="{height}" fill="#fff"/>',
    ]

    def at(v, x, y):
        i = used.index(v)
        x0, y0, _, y1 = box[v]
        return (i * PANEL + MARGIN + (x - x0) * k, 24 + MARGIN + (y1 - y) * k)

    for i, v in enumerate(used):
        out.append(
            f'<text x="{i * PANEL + PANEL / 2}" y="{height - 8}" text-anchor="middle" '
            f'fill="#666">{v}</text>'
        )
    style = 'fill="#eef2f6" stroke="#333" stroke-width="1.5"'
    for item in spec.get("shapes", []):
        v, t = item["view"], item["type"]
        if t == "rect":
            (ax, ay), (bx, by) = (
                at(v, item["x"], item["y"] + item["h"]),
                at(v, item["x"] + item["w"], item["y"]),
            )
            out.append(
                f'<rect x="{ax:.1f}" y="{ay:.1f}" width="{bx - ax:.1f}" '
                f'height="{by - ay:.1f}" {style}/>'
            )
        elif t == "circle":
            cx, cy = at(v, item["cx"], item["cy"])
            out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{item["r"] * k:.1f}" {style}/>')
        else:
            p = [at(v, *q) for q in _points(item)]
            out.append(
                f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in p)}" '
                'fill="none" stroke="#333" stroke-width="1.5"/>'
            )
    for d in spec.get("dims", []):
        (ax, ay), (bx, by) = at(d["view"], *d["from"]), at(d["view"], *d["to"])
        out.append(
            f'<line x1="{ax:.1f}" y1="{ay:.1f}" x2="{bx:.1f}" y2="{by:.1f}" '
            'stroke="#c0392b" stroke-width="1"/>'
        )
        out.append(
            f'<text x="{(ax + bx) / 2:.1f}" y="{(ay + by) / 2 - 4:.1f}" text-anchor="middle" '
            f'fill="#c0392b">{escape(str(d.get("text", "")))}</text>'
        )
    for lab in spec.get("labels", []):
        x, y = at(lab["view"], lab["x"], lab["y"])
        out.append(
            f'<text x="{x:.1f}" y="{y:.1f}" fill="#222">{escape(str(lab.get("text", "")))}</text>'
        )
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("spec", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    out = args.out or args.spec.with_suffix(".svg")
    try:
        svg = render(json.loads(args.spec.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, SketchError) as exc:
        print(json.dumps({"error": str(exc)}))
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    print(json.dumps({"out": out.as_posix()}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
