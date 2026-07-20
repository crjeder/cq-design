#!/usr/bin/env python3
"""Feature-presence validation stage: assert plan-declared features were actually built.

A plan `interfaces[]` entry may declare a structured `position_mm` (the feature's intended
center, in the part's authored frame) and a size (`diameter_mm` or `size_mm`). This stage
confirms, deterministically, that such a feature really exists at that position -- the hard
backstop beneath the visual per-feature review, mirroring how the `disconnected_body`
wrapper error backs the visual connectedness question.

Interface blocks (`port_cutout`, `screw_boss`, ...) return *unpositioned* solids; the part
script positions them and applies them via a boolean. So the placement is captured where it
lands: this wraps `cq.Workplane.cut` / `.union`, re-runs the part script (the
`edge_treatment_check` pattern, via `exporters._load_result`), and records the
authored-frame bbox center + extents of every positioned tool. That set of built features
is matched against the part's declared interfaces:

- no built feature within `_POS_TOL_MM` of a declared position -> `feature_absent` (error).
- a nearest match beyond `_DRIFT_TOL_MM` in center, or a declared size not present among the
  feature's extents -> `feature_drift` (warning).
- otherwise the feature is confirmed present.

Only interface types emitted through a hooked boolean are asserted (the allowlist below);
any other type, or a script that cannot be re-run, is `check_skipped` -- never a false
`feature_absent`. The in-place hole family (`.hole`/`.cboreHole`) is out of first scope
(its position lives in workplane points, not a positioned tool); block-emitted bores are
covered because a block is applied via `.union` of its positioned solid.

Findings use the shared quality-gate issue contract `{source, severity, type, message,
hint, ...}`.

Usage:
    python3 feature_presence_check.py --plan BUILD_PLAN.json --script build/body.py
"""

import argparse
import math
import os
from typing import Any

from units import add_plan_argument, emit_issues, load_plan, make_issue

# Interface types whose feature is emitted through a hooked `.cut`/`.union` boolean.
_ASSERTABLE_TYPES = frozenset(
    {"port_cutout", "cable_slot", "vent_grid", "screw_boss", "pcb_standoff"}
)

# A built feature this close to a declared position counts as "the feature exists".
_POS_TOL_MM = 5.0
# A matched feature whose center drifts past this from the declared position is advisory.
_DRIFT_TOL_MM = 1.0
# A declared size dimension must appear among the feature's extents within this.
_SIZE_TOL_MM = 1.0


def _tool_bbox(tool: Any) -> tuple[tuple[float, float, float], tuple[float, float, float]] | None:
    """Authored-frame (center, extents) of a boolean tool argument, or None if unusable.

    The tool may be a Workplane (several solids) or a bare Shape; the enveloping bbox of all
    its solids is used.
    """
    shapes = tool.vals() if hasattr(tool, "vals") else [tool]
    lo = [math.inf, math.inf, math.inf]
    hi = [-math.inf, -math.inf, -math.inf]
    for shape in shapes:
        try:
            bb = shape.BoundingBox()
        except Exception:
            continue
        lo = [min(lo[0], bb.xmin), min(lo[1], bb.ymin), min(lo[2], bb.zmin)]
        hi = [max(hi[0], bb.xmax), max(hi[1], bb.ymax), max(hi[2], bb.zmax)]
    if lo[0] == math.inf:
        return None
    center = ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2)
    extents = (hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2])
    return center, extents


def _run_with_hook(script_path: str) -> list[dict]:
    """Re-run the part script with `.cut`/`.union` wrapped; return the recorded features.

    Each wrapper records its positioned tool's bbox *before* delegating to the original op,
    so recording never changes the produced geometry.
    """
    import cadquery as cq

    from exporters import _load_result

    records: list[dict] = []
    orig_cut = cq.Workplane.cut
    orig_union = cq.Workplane.union

    def _record(tool: Any) -> None:
        if tool is None:
            return
        bb = _tool_bbox(tool)
        if bb is not None:
            records.append({"center": bb[0], "extents": bb[1]})

    def cut(self: Any, toCut: Any = None, *a: Any, **k: Any) -> Any:  # noqa: N803  (CadQuery kwarg name)
        _record(toCut)
        return orig_cut(self, toCut, *a, **k)

    def union(self: Any, toUnion: Any = None, *a: Any, **k: Any) -> Any:  # noqa: N803  (CadQuery kwarg name)
        _record(toUnion)
        return orig_union(self, toUnion, *a, **k)

    cq.Workplane.cut = cut  # type: ignore[method-assign]
    cq.Workplane.union = union  # type: ignore[method-assign]
    try:
        _load_result(script_path)
    finally:
        cq.Workplane.cut = orig_cut  # type: ignore[method-assign]
        cq.Workplane.union = orig_union  # type: ignore[method-assign]
    return records


def _declared_size(iface: dict) -> list[float]:
    """The declared size dimensions of an interface entry (empty when none)."""
    if "diameter_mm" in iface:
        return [float(iface["diameter_mm"])]
    if "size_mm" in iface:
        return [float(v) for v in iface["size_mm"]]
    return []


def _size_matches(declared: list[float], extents: tuple[float, float, float]) -> bool:
    """True when every declared dimension is within `_SIZE_TOL_MM` of some feature extent.

    Lenient by design: a feature's depth extent (unmatched by a declared lateral size) is
    ignored, so only a genuinely wrong size -- a declared dimension that appears nowhere --
    trips the drift warning.
    """
    return all(any(abs(d - e) <= _SIZE_TOL_MM for e in extents) for d in declared)


def _dist(a: tuple[float, float, float], b: list[float]) -> float:
    """Euclidean distance between a feature center and a declared position."""
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def run_feature_presence_check(plan: dict, script_path: str) -> list[dict]:
    """Assert one part script's declared-position interfaces are realized. Returns issues.

    Returns `[]` without re-running when the part declares no positioned interface (nothing
    to assert). Degrades to a single `check_skipped` warning when the script cannot be
    re-run (e.g. CadQuery unavailable).
    """
    stem = os.path.splitext(os.path.basename(script_path))[0]
    part = next((p for p in plan.get("parts", []) if p.get("id") == stem), None)
    if part is None:
        return []

    positioned = [i for i in part.get("interfaces", []) if "position_mm" in i]
    if not positioned:
        return []

    try:
        records = _run_with_hook(script_path)
    except ImportError as exc:
        return [
            make_issue(
                "feature_presence",
                "warning",
                "check_skipped",
                f"CadQuery unavailable for the feature-presence check: {exc}",
                "Install CadQuery to enable the feature-presence check.",
            )
        ]

    issues: list[dict] = []
    for iface in positioned:
        itype = iface.get("type", "(unknown)")
        pos = [float(v) for v in iface["position_mm"]]
        pos_mm = [round(v, 2) for v in pos]

        if itype not in _ASSERTABLE_TYPES:
            issues.append(
                make_issue(
                    "feature_presence",
                    "warning",
                    "check_skipped",
                    f"Part '{stem}': interface '{itype}' at {pos_mm} is not an assertable "
                    "type (not emitted through a hooked cut/union boolean); presence not checked.",
                    "Only block-emitted interface features are asserted; verify this one visually.",
                    part=stem,
                    interface_type=itype,
                    position_mm=pos_mm,
                )
            )
            continue

        nearest = min(records, key=lambda r: _dist(r["center"], pos), default=None)
        dist = _dist(nearest["center"], pos) if nearest is not None else math.inf

        if nearest is None or dist > _POS_TOL_MM:
            issues.append(
                make_issue(
                    "feature_presence",
                    "error",
                    "feature_absent",
                    f"Part '{stem}': declared '{itype}' feature at {pos_mm} was not built "
                    "(no cut/union feature found near that position).",
                    f"Add the '{itype}' feature at {pos_mm}, or correct its declared position_mm.",
                    part=stem,
                    interface_type=itype,
                    position_mm=pos_mm,
                )
            )
            continue

        if dist > _DRIFT_TOL_MM:
            built = [round(c, 2) for c in nearest["center"]]
            issues.append(
                make_issue(
                    "feature_presence",
                    "warning",
                    "feature_drift",
                    f"Part '{stem}': '{itype}' feature declared at {pos_mm} was built at "
                    f"{built} ({dist:.2f} mm off).",
                    "Reconcile the built feature position with the declared position_mm.",
                    part=stem,
                    interface_type=itype,
                    position_mm=pos_mm,
                    built_position_mm=built,
                )
            )
            continue

        declared = _declared_size(iface)
        if declared and not _size_matches(declared, nearest["extents"]):
            built_extents = [round(e, 2) for e in nearest["extents"]]
            issues.append(
                make_issue(
                    "feature_presence",
                    "warning",
                    "feature_drift",
                    f"Part '{stem}': '{itype}' at {pos_mm} was built, but its size "
                    f"{built_extents} does not match the declared {declared}.",
                    "Reconcile the built feature size with the declared diameter_mm/size_mm.",
                    part=stem,
                    interface_type=itype,
                    position_mm=pos_mm,
                    declared_size_mm=declared,
                    built_extents_mm=built_extents,
                )
            )

    return issues


def main() -> None:
    parser = argparse.ArgumentParser(description="Feature-presence validation")
    add_plan_argument(parser)
    parser.add_argument("--script", required=True, help="Path to the part script to re-run")
    args = parser.parse_args()

    plan = load_plan(args.plan)
    issues = run_feature_presence_check(plan, args.script)
    emit_issues(issues)


if __name__ == "__main__":
    main()
