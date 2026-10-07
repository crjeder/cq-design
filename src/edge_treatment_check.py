#!/usr/bin/env python3
"""Edge-treatment validation stage: enforce the Chamfer / Fillet rule.

The FDM guideline "Chamfer / Fillet" says: treat an edge by its bed-relative
orientation -- **chamfer** a horizontal edge (parallel to the bed: constant overhang
angle, clean layer stepping) and **fillet** a vertical edge (perpendicular to the bed,
`edges("|Z")`: smooth head motion, fewer acceleration artifacts). Unlike `wall_min_mm`
or `overhang_max_deg`, nothing downstream measured this: it was pure prose the generating
model could ignore.

Rather than reverse-engineer edge treatment from a triangulated mesh (a filleted edge and
a legitimately-round bore share the same triangle signature -- see the classifier notes in
`TODO.md`), this stage inspects the treatment at the moment it is applied. It wraps
`cq.Workplane.fillet` / `.chamfer`, re-runs the part script so every call is recorded with
the *exact* BRep direction of each edge it operates on (bores, pins, and posts never pass
through a fillet/chamfer call, so they cannot produce a false positive), then classifies
each edge in the **build frame**: the recorded tangents are in the part's authored frame,
so each is rotated through the union's print orientation (`print_orientation.py`'s
`rotate`, the same convention `placement` uses) before the horizontal/vertical test.

A fillet on a horizontal edge (rule: chamfer) and a chamfer on a vertical edge (rule:
fillet) are the two violations; every other combination -- including diagonal edges and
tilted round rims, where the rule does not cleanly apply -- is passed silently. Findings
are **advisory** (`severity: "warning"`): the rule is a print-quality/strength preference,
not a hard printability failure (the harmful half, a fillet curling a bottom edge past the
overhang limit, is already caught by the overhang check). Emits the shared quality-gate
issue contract `{source, severity, type, message, hint, ...}`.

Usage:
    python3 edge_treatment_check.py --plan BUILD_PLAN.json --script build/body.py
    python3 edge_treatment_check.py --plan BUILD_PLAN.json --script build/body.py \\
        --orientations build/orientations.json
"""

import argparse
import json
import math
import os
from collections.abc import Callable
from typing import Any

from placement import transform_direction
from units import (
    add_plan_argument,
    bbox_envelope,
    emit_issues,
    load_plan,
    make_issue,
    resolve_unions,
)

# An edge whose (build-frame) tangent is within this of horizontal counts as a horizontal
# edge; within this of vertical counts as a vertical edge. ~5 deg, matching the tolerance
# print_orientation uses to call a face flat.
_ANGLE_EPS_DEG = 5.0
_HORIZ_MAX_TZ = math.sin(math.radians(_ANGLE_EPS_DEG))  # |tangent.z| <= this  -> horizontal
_VERT_MIN_TZ = math.cos(math.radians(_ANGLE_EPS_DEG))  # |tangent.z| >= this  -> vertical
# Bounding-box slack for attributing an edge midpoint to a union (mm).
_BBOX_TOL_MM = 0.5
# Edge-curve parameters sampled for the tangent test (0..1). A straight edge is constant;
# a circular rim needs several to confirm the whole loop lies in one plane.
_SAMPLES = (0.0, 0.25, 0.5, 0.75, 1.0)


def _edges_of(obj: Any) -> list[Any]:
    """Edges a single fillet/chamfer stack object operates on.

    A fillet/chamfer selects either edges directly (`edges(...).fillet()`) or a face
    (`faces(...).chamfer()` chamfers every edge of the selected face). Anything else on the
    stack is ignored.
    """
    name = type(obj).__name__
    if name == "Edge":
        return [obj]
    if name == "Face":
        return list(obj.Edges())
    return []


def _record_edge(records: list[dict], treatment: str, edge: Any) -> None:
    """Append one edge's treatment, authored-frame tangents, and midpoint to ``records``.

    Silently skips an edge whose geometry cannot be sampled (e.g. a degenerate curve),
    so a single odd edge never aborts the whole check.
    """
    try:
        tangents = [tuple(edge.tangentAt(t).toTuple()) for t in _SAMPLES]
        midpoint = tuple(edge.positionAt(0.5).toTuple())
    except Exception:
        return
    records.append({"treatment": treatment, "tangents": tangents, "midpoint": midpoint})


def _run_with_hook(
    script_path: str, print_rotate: list | None = None, load: Callable[[], Any] | None = None
) -> tuple[Any, list[dict]]:
    """Re-run the part script with fillet/chamfer wrapped; return ``(result, records)``.

    The wrappers capture each call's edges *before* delegating to the original op (which
    consumes the stack), so recording never changes the produced geometry. `load` replaces
    the script execution so another hooked check can share it (see `quality_gate`).
    """
    import cadquery as cq

    from exporters import _load_result

    records: list[dict] = []
    orig_fillet = cq.Workplane.fillet
    orig_chamfer = cq.Workplane.chamfer

    def fillet(self: Any, *a: Any, **k: Any) -> Any:
        for obj in self.objects:
            for edge in _edges_of(obj):
                _record_edge(records, "fillet", edge)
        return orig_fillet(self, *a, **k)

    def chamfer(self: Any, *a: Any, **k: Any) -> Any:
        for obj in self.objects:
            for edge in _edges_of(obj):
                _record_edge(records, "chamfer", edge)
        return orig_chamfer(self, *a, **k)

    cq.Workplane.fillet = fillet  # type: ignore[method-assign]
    cq.Workplane.chamfer = chamfer  # type: ignore[method-assign]
    try:
        result = (load or (lambda: _load_result(script_path, print_rotate, fresh=True)))()
    finally:
        cq.Workplane.fillet = orig_fillet  # type: ignore[method-assign]
        cq.Workplane.chamfer = orig_chamfer  # type: ignore[method-assign]
    return result, records


def _union_bbox(workplane: Any) -> tuple[float, float, float, float, float, float] | None:
    """Authored-frame bounding box (xmin..zmax) enveloping every solid in a union, or None."""
    envelope = bbox_envelope(workplane.vals())
    if envelope is None:
        return None
    lo, hi = envelope
    return (lo[0], lo[1], lo[2], hi[0], hi[1], hi[2])


def _attribute(midpoint: tuple, bboxes: list[tuple[str, tuple]]) -> str | None:
    """Union id whose (authored-frame) bbox an edge midpoint belongs to.

    Prefers bbox containment (with `_BBOX_TOL_MM` slack); on none or a tie, falls back to
    the nearest bbox center. Single-union parts always resolve to that one union.
    """
    if not bboxes:
        return None
    inside = [
        uid
        for uid, bb in bboxes
        if bb[0] - _BBOX_TOL_MM <= midpoint[0] <= bb[3] + _BBOX_TOL_MM
        and bb[1] - _BBOX_TOL_MM <= midpoint[1] <= bb[4] + _BBOX_TOL_MM
        and bb[2] - _BBOX_TOL_MM <= midpoint[2] <= bb[5] + _BBOX_TOL_MM
    ]
    pool = [b for b in bboxes if b[0] in inside] if len(inside) > 1 else bboxes
    if len(inside) == 1:
        return inside[0]

    def _center_dist(bb: tuple) -> float:
        cx, cy, cz = (bb[0] + bb[3]) / 2, (bb[1] + bb[4]) / 2, (bb[2] + bb[5]) / 2
        return (midpoint[0] - cx) ** 2 + (midpoint[1] - cy) ** 2 + (midpoint[2] - cz) ** 2

    return min(pool, key=lambda ub: _center_dist(ub[1]))[0]


def _classify(tangents: list[tuple], rotate: list[dict]) -> str:
    """Classify an edge as ``horizontal``, ``vertical``, or ``other`` in the build frame.

    Each authored-frame tangent is rotated through the union's print orientation (`rotate`
    steps) before its Z-component is tested. An edge is horizontal only if *every* sample
    lies in the bed plane (a flat straight edge or a flat round rim), and vertical only if
    *every* sample is along build Z (a straight column edge); mixed samples are ``other``.
    """
    placement = {"rotate": rotate} if rotate else None
    tzs = [abs(transform_direction(t, placement)[2]) for t in tangents]
    if max(tzs) <= _HORIZ_MAX_TZ:
        return "horizontal"
    if min(tzs) >= _VERT_MIN_TZ:
        return "vertical"
    return "other"


# (treatment, edge orientation) -> what the rule wants instead (the violations).
_VIOLATIONS = {
    ("fillet", "horizontal"): "chamfer",
    ("chamfer", "vertical"): "fillet",
}

# Why the recommended treatment is preferred, keyed by that treatment (for the fix hint).
_REASON = {
    "chamfer": "horizontal edges keep a constant overhang angle and clean layer stepping",
    "fillet": "a rounded vertical edge gives smoother head motion and fewer acceleration artifacts",
}


def run_edge_treatment_check(
    plan: dict, script_path: str, orientations: dict, load: Callable[[], Any] | None = None
) -> list[dict]:
    """Check one part script's fillet/chamfer calls against the Chamfer / Fillet rule.

    `orientations` maps union id -> an orientation result (uses its `rotate` to reach the
    print frame; a `rotate` of `[]` states the print pose equals the authored frame).
    Classification always happens in the print frame, since the rule is bed-relative: a
    treated union absent from the map cannot be classified and is reported as a
    `check_skipped` warning instead of being judged in the authored frame. Returns a list
    of advisory `edge_treatment` warnings (empty when the part applies no misoriented edge
    treatment, or applies none at all).
    """
    stem = os.path.splitext(os.path.basename(script_path))[0]
    part = next((p for p in plan.get("parts", []) if p.get("id") == stem), None)
    if part is None:
        return []

    try:
        result, records = _run_with_hook(
            script_path, (orientations.get(stem) or {}).get("rotate"), load
        )
        if not records:
            return []
        unions = resolve_unions(part, result)
    except ImportError as exc:
        return [
            make_issue(
                "edge_treatment",
                "warning",
                "check_skipped",
                f"CadQuery unavailable for the edge-treatment check: {exc}",
                "Install CadQuery to enable the chamfer/fillet check.",
            )
        ]
    except ValueError as exc:
        # resolve_unions: the script's `result` keys don't match its declared `unions`
        # (e.g. mid-edit). Not this stage's job to report -- plan_validate/the wrapper
        # already surface that mismatch as a blocking error.
        return [
            make_issue(
                "edge_treatment",
                "warning",
                "check_skipped",
                f"Could not resolve this part's unions for the edge-treatment check: {exc}",
                "Fix the script's declared unions/result mismatch; see the other reported errors.",
            )
        ]
    bboxes = [(uid, bb) for uid, wp in unions if (bb := _union_bbox(wp)) is not None]

    # tally[(uid, wanted)] -> [count, sample_authored_midpoint]
    tally: dict[tuple[str, str], list] = {}
    # Unions that apply an edge treatment but have no print orientation: the rule is
    # bed-relative, so an edge cannot be classified without the print frame. Skip them
    # (reported once each) rather than silently classifying in the authored frame.
    unoriented: set[str] = set()
    for rec in records:
        uid = _attribute(rec["midpoint"], bboxes)
        if uid is None:
            continue
        entry = orientations.get(uid)
        if not entry or "rotate" not in entry:
            unoriented.add(uid)
            continue
        orientation = _classify(rec["tangents"], entry["rotate"])
        wanted = _VIOLATIONS.get((rec["treatment"], orientation))
        if wanted is None:
            continue
        key = (uid, wanted)
        if key in tally:
            tally[key][0] += 1
        else:
            tally[key] = [1, rec["midpoint"]]

    issues: list[dict] = [
        make_issue(
            "edge_treatment",
            "warning",
            "check_skipped",
            f"Union '{uid}' applies edge treatments but has no print orientation; its edges "
            "cannot be classified in the bed-relative print frame.",
            "Provide the union's print orientation (build/orientations.json or --orientation) "
            "so the chamfer/fillet check runs in the print frame.",
            union=uid,
        )
        for uid in sorted(unoriented)
    ]
    for (uid, wanted), (count, loc) in sorted(tally.items()):
        applied = "fillet" if wanted == "chamfer" else "chamfer"
        edge_kind = "horizontal" if wanted == "chamfer" else "vertical"
        loc_mm = [round(float(c), 2) for c in loc]
        issues.append(
            make_issue(
                "edge_treatment",
                "warning",
                "edge_treatment",
                f"Union '{uid}': {count} {edge_kind} edge(s) got a {applied}; the "
                f"Chamfer / Fillet rule wants a {wanted} on {edge_kind} edges "
                f"(e.g. near {loc_mm} in the authored frame).",
                f"Use {wanted} instead of {applied} on {edge_kind} edges ({_REASON[wanted]}). "
                "Advisory: disregard if this edge is internal or intentionally treated.",
                union=uid,
                applied=applied,
                recommended=wanted,
                edge_orientation=edge_kind,
                count=count,
                location_xyz_mm=loc_mm,
            )
        )
    return issues


def main() -> None:
    parser = argparse.ArgumentParser(description="Chamfer / Fillet edge-treatment validation")
    add_plan_argument(parser)
    parser.add_argument("--script", required=True, help="Path to the part's <id>.py script")
    parser.add_argument(
        "--orientations",
        default=None,
        help="Per-union orientations JSON (build/orientations.json); omit to classify in "
        "the authored frame",
    )
    args = parser.parse_args()

    plan = load_plan(args.plan)
    orientations = {}
    if args.orientations and os.path.isfile(args.orientations):
        with open(args.orientations, encoding="utf-8") as f:
            orientations = json.load(f)

    issues = run_edge_treatment_check(plan, args.script, orientations)
    emit_issues(issues, fail_on_error=False)


if __name__ == "__main__":
    main()
