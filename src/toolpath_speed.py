#!/usr/bin/env python3
"""Toolpath speed advisor: print-time cost of corner sharpness and feature crowding.

At a fixed slicer profile, print time has exactly one geometric driver: how often and
how hard the toolhead has to slow down. This is computable straight from the part's own
B-rep, with no slicer and no G-code:

- a **corner** (a real dihedral vertex, or a filleted round) caps sustainable speed to
  `v_corner = min(v_cruise, sqrt(a * R_eff))`, where `R_eff` is the fillet radius for a
  treated corner and a firmware-junction-deviation equivalent radius for a sharp one --
  one continuous formula, not a rule with exceptions (see `_r_eff_sharp`);
- a **short wall** between corners never reaches `v_cruise` at all, which is the
  dominant cost on a part built from small, closely spaced features.

Per-union geometry is read via an EXACT planar section of the CAD solid (not a
tessellated mesh) at a handful of representative heights: `cadquery.Workplane.section`
returns the true outer-wire edges at that height as LINE (wall) and CIRCLE (fillet)
segments with exact lengths and radii, and a bore or other interior hole is a separate
*inner* wire, so it is structurally excluded rather than needing to be told apart from a
fillet by triangle shape. See `design.md`'s "B-rep edges, not mesh sectioning" decision
(the sectioning here is of the exact CAD solid, not of its tessellated mesh, so the
concern that motivated avoiding a mesh classifier does not apply).

Print time is decomposed into three terms that sum exactly:
`T_actual = T_ideal + T_corners + T_crowding`, plus `speed_efficiency = T_ideal /
T_actual`. `T_corners` dominating produces a ranked, leave-one-out per-corner
attribution table (recompute `T_actual` with that corner's radius unbounded).
`T_crowding` dominating produces a single "features too small to reach cruise" finding.
See `design.md` for the worked numbers.

A posed union's STL additionally lets this module estimate per-layer path length
(`mesh_io.lateral_area`) and detect a minimum-layer-time stall, where total print time
is driven by height and the profile's floor alone and no fillet buys anything -- see the
`toolpath-speed-advisor` capability's stall requirements.

This is an ADVISOR, never a gate: it always exits 0 and adds no `quality_gate.py` stage
capable of failing. A missing `profile.json` `motion` block, or geometry the
section model cannot represent (low height-coverage across the sampled slices),
degrades to `{"status": "skipped", "reason": ...}`, also exit 0.

Usage:
    python3 toolpath_speed.py --plan BUILD_PLAN.json --script build/body.py
    python3 toolpath_speed.py --plan BUILD_PLAN.json --script build/body.py \\
        --stl stl/body.stl
"""

import argparse
import json
import math
import os
from typing import Any

from units import add_plan_argument, load_plan, make_issue, resolve_unions

# A candidate slice below this fraction of its solid's total height-coverage (fraction of
# sampled slices that actually intersected the solid) is not modeled as prismatic enough
# to trust the mean-layer-perimeter estimate.
HEIGHT_COVERAGE_FLOOR = 0.6
# Number of representative Z heights sampled per union for the section model.
_N_SLICES = 5
# A part at or above this speed_efficiency gets no corner/crowding finding: already
# printing efficiently, nothing to report.
SPEED_EFFICIENCY_REPORT_THRESHOLD = 0.85
# How many ranked corners to report in the attribution table.
_MAX_ATTRIBUTION_ROWS = 8


def _r_eff_sharp(phi_rad: float, junction_deviation_mm: float) -> float:
    """Effective corner radius for a sharp (non-filleted) corner of turn angle `phi_rad`.

    Derived from Marlin's junction-deviation cornering-speed limit
    `v_j = sqrt(JD * a * sin(phi/2) / (1 - sin(phi/2)))` rewritten as `v_j = sqrt(a *
    R_eff)`: `R_eff = JD * cos(phi/2) / (1 - cos(phi/2))`, using the *exterior* turn
    angle convention (`phi = 0` -> straight through, no limit; `phi = pi` -> full
    reversal). A straight-through vertex (`phi` at or near 0) returns `inf`.
    """
    half = phi_rad / 2.0
    denom = 1.0 - math.cos(half)
    if denom <= 1e-12:
        return math.inf
    return junction_deviation_mm * math.cos(half) / denom


def v_corner(r_eff_mm: float, accel_mm_s2: float, v_cruise_mm_s: float) -> float:
    """Sustainable speed through a corner of effective radius `r_eff_mm`."""
    if math.isinf(r_eff_mm):
        return v_cruise_mm_s
    return min(v_cruise_mm_s, math.sqrt(accel_mm_s2 * r_eff_mm))


def _segment_time(
    v_a: float, v_b: float, length_mm: float, accel_mm_s2: float, v_cruise_mm_s: float
) -> float:
    """Trapezoid-profile traverse time of a straight segment between two speed-limited
    nodes, entering at `v_a` and leaving at `v_b`, capped at `v_cruise_mm_s`.

    `v_peak = min(v_cruise, sqrt((v_a^2 + v_b^2) / 2 + a * L))` is the standard
    accelerate-then-decelerate solution that exactly covers `L` when it stays at or
    below cruise; when it saturates at `v_cruise` the remainder of `L` is covered at
    constant cruise speed.
    """
    if length_mm <= 0:
        return 0.0
    v_peak_sq = max(0.0, (v_a**2 + v_b**2) / 2.0 + accel_mm_s2 * length_mm)
    v_peak = min(v_cruise_mm_s, math.sqrt(v_peak_sq))
    d_acc = max(0.0, (v_peak**2 - v_a**2) / (2 * accel_mm_s2))
    d_dec = max(0.0, (v_peak**2 - v_b**2) / (2 * accel_mm_s2))
    d_cruise = max(0.0, length_mm - d_acc - d_dec)
    t = 0.0
    t += (v_peak - v_a) / accel_mm_s2 if v_peak > v_a else 0.0
    t += (v_peak - v_b) / accel_mm_s2 if v_peak > v_b else 0.0
    t += d_cruise / v_cruise_mm_s
    return t


class Corner:
    """One corner of a layer's closed path: either a sharp vertex (`arc_length_mm ==
    0`) between two straight walls, or a fillet's own arc (`arc_length_mm > 0`,
    traversed at the corner's own constant sustainable speed)."""

    __slots__ = ("r_eff_mm", "arc_length_mm", "location_xyz_mm", "kind")

    def __init__(self, r_eff_mm: float, arc_length_mm: float, location_xyz_mm: list, kind: str):
        self.r_eff_mm = r_eff_mm
        self.arc_length_mm = arc_length_mm
        self.location_xyz_mm = location_xyz_mm
        self.kind = kind  # "sharp" or "fillet"


def compute_path_times(
    corners: list[Corner],
    wall_lengths_mm: list[float],
    accel_mm_s2: float,
    v_cruise_mm_s: float,
    override_index: int | None = None,
) -> dict:
    """Time model for one closed layer path: `n` corners connected by `n` wall segments
    (`wall_lengths_mm[i]` is the wall between `corners[i]` and `corners[(i+1) % n]`).

    Returns `{T_ideal, T_corners, T_actual, T_crowding, speed_efficiency}`. When
    `override_index` is given, that corner's `r_eff_mm` is treated as unbounded (used
    for leave-one-out attribution) without mutating the input list.
    """
    n = len(corners)
    if n == 0 or sum(wall_lengths_mm) <= 0:
        return {
            "T_ideal": 0.0,
            "T_corners": 0.0,
            "T_actual": 0.0,
            "T_crowding": 0.0,
            "speed_efficiency": 1.0,
        }

    v_limits = [
        v_cruise_mm_s if i == override_index else v_corner(c.r_eff_mm, accel_mm_s2, v_cruise_mm_s)
        for i, c in enumerate(corners)
    ]

    l_total = sum(wall_lengths_mm) + sum(
        0.0 if i == override_index else c.arc_length_mm for i, c in enumerate(corners)
    )
    t_ideal = l_total / v_cruise_mm_s

    t_corners_isolated = sum(
        (v_cruise_mm_s - v) ** 2 / (accel_mm_s2 * v_cruise_mm_s) for v in v_limits
    )

    t_actual = 0.0
    for i in range(n):
        v_a = v_limits[i]
        v_b = v_limits[(i + 1) % n]
        t_actual += _segment_time(v_a, v_b, wall_lengths_mm[i], accel_mm_s2, v_cruise_mm_s)
        # The corner itself: a fillet's arc is traversed at its own constant speed; a
        # sharp vertex has zero arc length and contributes no time of its own (the
        # deceleration/reacceleration around it is already inside the segment times).
        arc_len = 0.0 if i == override_index else corners[i].arc_length_mm
        if arc_len > 0:
            t_actual += arc_len / v_limits[i]

    t_crowding = max(0.0, t_actual - t_ideal - t_corners_isolated)
    speed_efficiency = t_ideal / t_actual if t_actual > 0 else 1.0
    return {
        "T_ideal": t_ideal,
        "T_corners": t_corners_isolated,
        "T_actual": t_actual,
        "T_crowding": t_crowding,
        "speed_efficiency": speed_efficiency,
    }


def attribute_corners(
    corners: list[Corner],
    wall_lengths_mm: list[float],
    accel_mm_s2: float,
    v_cruise_mm_s: float,
) -> list[dict]:
    """Leave-one-out time recovered per corner, ranked highest first."""
    base = compute_path_times(corners, wall_lengths_mm, accel_mm_s2, v_cruise_mm_s)
    rows = []
    for i, c in enumerate(corners):
        without = compute_path_times(
            corners, wall_lengths_mm, accel_mm_s2, v_cruise_mm_s, override_index=i
        )
        recovered = max(0.0, base["T_actual"] - without["T_actual"])
        rows.append(
            {
                "location_xyz_mm": c.location_xyz_mm,
                "kind": c.kind,
                "r_eff_mm": None if math.isinf(c.r_eff_mm) else round(c.r_eff_mm, 3),
                "time_recovered_s": round(recovered, 4),
            }
        )
    rows.sort(key=lambda r: r["time_recovered_s"], reverse=True)
    return rows[:_MAX_ATTRIBUTION_ROWS]


# ---------------------------------------------------------------------------
# Geometry extraction: exact CAD-solid section, not a tessellated mesh.
# ---------------------------------------------------------------------------


def _outer_wires_at(workplane: Any, z: float) -> list[Any]:
    """Outer wires of the workplane's solids sectioned at world height `z`.

    Interior wires (bores, pockets) are dropped by construction -- each returned wire
    is the outer boundary of one connected cross-section face, never a hole.
    """
    try:
        sec = workplane.section(z)
    except Exception:
        return []
    wires = []
    for comp in sec.vals():
        faces = list(comp.Faces()) if hasattr(comp, "Faces") else [comp]
        for f in faces:
            try:
                wires.append(f.outerWire())
            except Exception:
                continue
    return wires


def _wire_corners_and_walls(
    wire: Any, junction_deviation_mm: float
) -> tuple[list[Corner], list[float]] | None:
    """Walk one outer wire's edges into a corner list and the wall length following
    each corner (`walls[k]` is the wall between `corners[k]` and `corners[(k+1) % n]`).

    A `LINE` edge is a wall token. A `CIRCLE` edge is itself a fillet-corner token: its
    radius is exact (`edge.radius()`) and its own arc length is its swept turn angle at
    that radius. A sharp corner is inserted at every vertex between two consecutive
    `LINE` (wall) tokens -- never between a wall and a fillet, since a fillet is
    tangent-continuous with its neighboring walls by construction, so there is no real
    direction change to record there. Returns None if the wire's edges cannot be read
    or contain a curve type this model does not represent (degenerate section).
    """
    try:
        edges = _ordered_edges(wire)
    except Exception:
        return None
    if len(edges) < 2:
        return None

    tokens: list[dict] = []
    for e in edges:
        try:
            gt = e.geomType()
        except Exception:
            return None
        if gt == "LINE":
            try:
                tokens.append({"type": "wall", "length": float(e.Length())})
            except Exception:
                return None
        elif gt == "CIRCLE":
            try:
                r = float(e.radius())
                arc_len = float(e.Length())
                mid = [round(c, 2) for c in e.positionAt(0.5).toTuple()]
            except Exception:
                return None
            tokens.append({"type": "corner", "corner": Corner(r, arc_len, mid, "fillet")})
        else:
            # A curve type other than a straight wall or a circular fillet (e.g. a
            # BSPLINE authored surface) -- not modeled; bail out on this wire rather
            # than silently mis-scoring it.
            return None

    n = len(tokens)
    final: list[dict] = []
    for i in range(n):
        final.append(tokens[i])
        nxt = tokens[(i + 1) % n]
        if tokens[i]["type"] == "wall" and nxt["type"] == "wall":
            try:
                d_prev = _direction(edges[i])
                d_cur = _direction(edges[(i + 1) % n])
                phi = _turn_angle(d_prev, d_cur)
                loc = [round(c, 2) for c in _ends(edges[(i + 1) % n])[0]]
            except Exception:
                return None
            r_eff = _r_eff_sharp(phi, junction_deviation_mm)
            final.append({"type": "corner", "corner": Corner(r_eff, 0.0, loc, "sharp")})

    corner_indices = [i for i, t in enumerate(final) if t["type"] == "corner"]
    if not corner_indices:
        return None
    m = len(final)
    out_corners = [final[i]["corner"] for i in corner_indices]
    out_walls: list[float] = []
    for k, idx in enumerate(corner_indices):
        nxt_idx = corner_indices[(k + 1) % len(corner_indices)]
        total = 0.0
        j = (idx + 1) % m
        while j != nxt_idx:
            if final[j]["type"] == "wall":
                total += final[j]["length"]
            j = (j + 1) % m
        out_walls.append(total)
    return out_corners, out_walls


def _ordered_edges(wire: Any) -> list[Any]:
    """The wire's edges in traversal order, each keeping its in-wire orientation."""
    import cadquery as cq
    from OCP.BRepTools import BRepTools_WireExplorer

    explorer = BRepTools_WireExplorer(wire.wrapped)
    edges = []
    while explorer.More():
        edges.append(cq.Edge(explorer.Current()))
        explorer.Next()
    return edges


def _ends(edge: Any) -> tuple[tuple, tuple]:
    """(start, end) in traversal order; startPoint()/endPoint() follow the curve's own
    parameter and ignore an edge reversed in its wire."""
    from OCP.TopAbs import TopAbs_REVERSED

    p0, p1 = edge.startPoint().toTuple(), edge.endPoint().toTuple()
    return (p1, p0) if edge.wrapped.Orientation() == TopAbs_REVERSED else (p0, p1)


def _direction(edge: Any):
    p0, p1 = _ends(edge)
    d = [p1[k] - p0[k] for k in range(3)]
    norm = math.sqrt(sum(v * v for v in d))
    return [v / norm for v in d] if norm > 1e-9 else [0.0, 0.0, 0.0]


def _turn_angle(d_prev, d_cur) -> float:
    dot = max(-1.0, min(1.0, sum(a * b for a, b in zip(d_prev, d_cur, strict=True))))
    return math.acos(dot)


def extract_corner_model(workplane: Any, junction_deviation_mm: float) -> dict | None:
    """Corner/wall model for a union's build-pose geometry, from `_N_SLICES`
    representative section heights.

    Returns `{"corners": [...], "wall_lengths_mm": [...], "height_mm": H,
    "height_coverage": fraction}` using the slice whose corner count matches the modal
    (most common) corner count across sampled slices -- the representative prismatic
    cross-section -- or `None` if no slice yielded a usable section.
    """
    from units import bbox_envelope

    envelope = bbox_envelope(workplane.vals())
    if envelope is None:
        return None
    (_, _, zmin), (_, _, zmax) = envelope
    height = zmax - zmin
    if height <= 0:
        return None

    zs = [zmin + height * (i + 0.5) / _N_SLICES for i in range(_N_SLICES)]
    slices = []
    for z in zs:
        wires = _outer_wires_at(workplane, z)
        if not wires:
            continue
        # Multiple disjoint cross-sections at one height (e.g. two separate towers):
        # combine their corners/walls into one representative layer path.
        combined_corners: list[Corner] = []
        combined_walls: list[float] = []
        ok = True
        for w in wires:
            parsed = _wire_corners_and_walls(w, junction_deviation_mm)
            if parsed is None:
                ok = False
                break
            c, wl = parsed
            combined_corners.extend(c)
            combined_walls.extend(wl)
        if ok and combined_corners:
            slices.append((len(combined_corners), combined_corners, combined_walls))

    coverage = len(slices) / _N_SLICES
    if not slices:
        return {"corners": [], "wall_lengths_mm": [], "height_mm": height, "height_coverage": 0.0}

    # Representative slice: the modal corner count (the prismatic case has all slices
    # agree; picking the mode is robust to one or two slices landing on a chamfer/step).
    counts = [s[0] for s in slices]
    modal_count = max(set(counts), key=counts.count)
    corners, walls = next((c, w) for n, c, w in slices if n == modal_count)
    return {
        "corners": corners,
        "wall_lengths_mm": walls,
        "height_mm": height,
        "height_coverage": coverage,
    }


# ---------------------------------------------------------------------------
# Layer-time / stall model, from a posed union mesh.
# ---------------------------------------------------------------------------


def layer_time_model(
    mesh: Any,
    motion: dict,
    speed_efficiency: float,
    perimeters: int,
) -> dict:
    """Estimate per-layer path length, layer time, stall state, and total print time
    for a posed mesh, from `mesh_io.lateral_area` -- no per-layer sectioning needed.
    """
    from mesh_io import lateral_area

    bbox = mesh.bounds
    height = float(bbox[1][2] - bbox[0][2])
    if height <= 0:
        return {"status": "skipped", "reason": "posed mesh has zero height"}

    p_mean = lateral_area(mesh) / height
    volume = float(mesh.volume)
    line_width = motion["line_width_mm"]
    perimeter_band_area = p_mean * perimeters * line_width
    cross_section_area = volume / height
    infill_area = max(0.0, cross_section_area - perimeter_band_area)
    infill_path_mm = infill_area * motion["infill_density"] / line_width

    l_layer = p_mean * perimeters + infill_path_mm
    v_achieved = max(1e-6, speed_efficiency * motion["v_cruise_mm_s"])
    t_layer = l_layer / v_achieved
    min_layer_time = motion["min_layer_time_s"]
    stalled = t_layer < min_layer_time
    n_layers = height / motion["layer_height_mm"]
    total_time_s = n_layers * (min_layer_time if stalled else t_layer)

    return {
        "status": "ok",
        "mean_layer_perimeter_mm": round(p_mean, 3),
        "infill_path_mm": round(infill_path_mm, 3),
        "t_layer_s": round(t_layer, 4),
        "stalled": stalled,
        "total_time_s": round(total_time_s, 1),
    }


def evaluate_candidate_speed_models(
    workplane: Any, mesh: Any, motion: dict, perimeters: int
) -> dict:
    """Per-candidate print-time estimate for `print_orientation.py`'s own candidate
    poses (from `enumerate_candidate_normals`), one entry per candidate.

    `print_orientation.py` is deliberately mesh-only (trimesh, no CadQuery), so it
    cannot re-section a CAD solid itself; this mirrors `fem_check.py`'s
    `evaluate_orientations` pattern instead -- one script that holds both the CAD
    geometry and the mesh precomputes a per-candidate table here, and
    `print_orientation.py` matches its own candidates against it by normal (see
    `_speed_lookup` there), the same way it already matches `--fem-stress` results.
    Each candidate's corner model is re-extracted from the union's solid rigidly
    transformed into that candidate's pose (`placement.apply_matrix`, the same 4x4
    `_rotation_to_bed` transform the mesh candidate uses) -- a corner model is not a
    per-edge property that survives a cheap rotation (see `design.md`).
    """
    from placement import apply_matrix
    from print_orientation import _rotation_to_bed, enumerate_candidate_normals

    candidates = []
    for idx, normal in enumerate(enumerate_candidate_normals(mesh)):
        rotation = _rotation_to_bed(normal)
        posed_wp = apply_matrix(workplane, rotation)
        posed_mesh = mesh.copy()
        posed_mesh.apply_transform(rotation)

        model = extract_corner_model(posed_wp, motion["junction_deviation_mm"])
        entry: dict[str, Any] = {"idx": idx, "normal": [round(float(v), 6) for v in normal]}
        if model is None or model["height_coverage"] < HEIGHT_COVERAGE_FLOOR:
            entry["status"] = "skipped"
            candidates.append(entry)
            continue

        times = compute_path_times(
            model["corners"],
            model["wall_lengths_mm"],
            motion["accel_mm_s2"],
            motion["v_cruise_mm_s"],
        )
        layer = layer_time_model(posed_mesh, motion, times["speed_efficiency"], perimeters)
        entry["status"] = "ok"
        entry["speed_efficiency"] = round(times["speed_efficiency"], 4)
        if layer["status"] == "ok":
            entry["total_time_s"] = layer["total_time_s"]
            entry["stalled"] = layer["stalled"]
        candidates.append(entry)

    return {"status": "ok", "candidates": candidates}


STALL_REMEDIES = [
    "lay the part flatter (lower build height reduces total time when stalled)",
    "thicken the stalling feature so its cross-section fills the layer faster",
    "print more copies on the same plate (multiplies path length per layer at no "
    "extra per-part time) -- requires the user's approval before changing plate layout",
]


def build_finding(
    part_id: str,
    union_id: str,
    times: dict,
    corners: list[Corner],
    wall_lengths_mm: list[float],
    accel_mm_s2: float,
    v_cruise_mm_s: float,
    layer: dict | None,
) -> dict | None:
    """One advisory finding for a union, or None when nothing is worth reporting."""
    speed_efficiency = times["speed_efficiency"]
    stalled = bool(layer and layer.get("status") == "ok" and layer["stalled"])

    if speed_efficiency >= SPEED_EFFICIENCY_REPORT_THRESHOLD:
        return None

    corner_dominant = times["T_corners"] >= times["T_crowding"]
    extra: dict[str, Any] = {
        "union": union_id,
        "speed_efficiency": round(speed_efficiency, 3),
        "stalled": stalled,
    }
    if layer and layer.get("status") == "ok":
        extra["total_time_s"] = layer["total_time_s"]

    if corner_dominant:
        rows = attribute_corners(corners, wall_lengths_mm, accel_mm_s2, v_cruise_mm_s)
        extra["attribution"] = rows
        if stalled:
            message = (
                f"Part '{part_id}' union '{union_id}': sharp/undersized corners lower "
                f"speed_efficiency to {speed_efficiency:.0%}, but this pose is minimum-"
                "layer-time stalled, so no print-time is recoverable from filleting -- "
                "the benefit is reduced vibration, ringing, and mechanical wear."
            )
        else:
            message = (
                f"Part '{part_id}' union '{union_id}': sharp/undersized corners lower "
                f"speed_efficiency to {speed_efficiency:.0%}. Ranked corners and the "
                "print time each would recover are attached."
            )
        hint = "Raise fillet radius at the ranked corners, largest time-recovery first."
    else:
        extra["dominant"] = "crowding"
        message = (
            f"Part '{part_id}' union '{union_id}': speed_efficiency is {speed_efficiency:.0%} "
            "because the toolhead never reaches cruise speed between corners -- the part's "
            "typical feature size is too small, not any single edge."
        )
        hint = "Consider fewer, larger features rather than filleting individual edges."

    if stalled:
        extra["stall_remedies"] = STALL_REMEDIES

    return make_issue(
        "toolpath_speed",
        "warning",
        "toolpath_speed",
        message,
        hint,
        **extra,
    )


def run_toolpath_speed_check(
    plan: dict, script_path: str, motion: dict | None, stl_path: str | None = None
) -> dict:
    """Run the advisor for one part script's unions.

    Returns `{"status": "skipped", "reason": ...}` when `motion` is absent, or
    `{"status": "ok", "issues": [...]}` otherwise (issues may be empty).
    """
    if not motion:
        return {"status": "skipped", "reason": "profile.json has no 'motion' block"}

    stem = os.path.splitext(os.path.basename(script_path))[0]
    part = next((p for p in plan.get("parts", []) if p.get("id") == stem), None)
    if part is None:
        return {"status": "ok", "issues": []}

    try:
        from exporters import _load_result

        result = _load_result(script_path)
        unions = resolve_unions(part, result)
    except ImportError as exc:
        return {"status": "skipped", "reason": f"CadQuery unavailable: {exc}"}
    except ValueError as exc:
        return {"status": "skipped", "reason": f"Could not resolve unions: {exc}"}

    constraints = plan.get("constraints", {})
    wall_min = constraints.get("wall_min_mm", 1.2)
    nozzle = plan.get("nozzle_mm", 0.4)
    perimeters = max(2, int((wall_min / nozzle) + 0.999))

    mesh = None
    if stl_path and os.path.isfile(stl_path):
        from mesh_io import load_mesh

        try:
            mesh = load_mesh(stl_path)
        except ValueError:
            mesh = None

    issues: list[dict] = []
    for uid, wp in unions:
        model = extract_corner_model(wp, motion["junction_deviation_mm"])
        if model is None or model["height_coverage"] < HEIGHT_COVERAGE_FLOOR:
            issues.append(
                make_issue(
                    "toolpath_speed",
                    "warning",
                    "check_skipped",
                    f"Union '{uid}': geometry is not prismatic enough for the mean-layer "
                    "-perimeter model to be trusted.",
                    "No action needed; this is a modeling limitation, not a printability issue.",
                    union=uid,
                )
            )
            continue

        times = compute_path_times(
            model["corners"],
            model["wall_lengths_mm"],
            motion["accel_mm_s2"],
            motion["v_cruise_mm_s"],
        )
        layer = None
        if mesh is not None:
            layer = layer_time_model(mesh, motion, times["speed_efficiency"], perimeters)

        finding = build_finding(
            stem,
            uid,
            times,
            model["corners"],
            model["wall_lengths_mm"],
            motion["accel_mm_s2"],
            motion["v_cruise_mm_s"],
            layer,
        )
        if finding is not None:
            issues.append(finding)

    return {"status": "ok", "issues": issues}


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    add_plan_argument(parser)
    parser.add_argument("--script", required=True, help="Path to the part's <id>.py script")
    parser.add_argument(
        "--stl",
        default=None,
        help="Posed union STL for the layer-time/stall model; omit for the build-pose "
        "corner findings only",
    )
    parser.add_argument(
        "--profile",
        default=None,
        help="Path to profile.json (default: profile.json next to --plan)",
    )
    parser.add_argument(
        "--emit-candidates",
        default=None,
        metavar="UNION_ID",
        help="Instead of the per-union finding report, emit a per-candidate speed-model "
        "table for this union (requires --stl), for print_orientation.py's --speed-model",
    )
    args = parser.parse_args()

    plan = load_plan(args.plan)
    profile_path = args.profile or os.path.join(
        os.path.dirname(os.path.abspath(args.plan)), "profile.json"
    )
    motion = None
    if os.path.isfile(profile_path):
        with open(profile_path, encoding="utf-8") as f:
            motion = json.load(f).get("motion")

    if args.emit_candidates:
        if not motion:
            print(json.dumps({"status": "skipped", "reason": "no motion block"}, indent=2))
            return
        if not args.stl:
            parser.error("--emit-candidates requires --stl")
        stem = os.path.splitext(os.path.basename(args.script))[0]
        part = next((p for p in plan.get("parts", []) if p.get("id") == stem), None)
        if part is None:
            parser.error(f"part '{stem}' not found in plan")
        from exporters import _load_result
        from mesh_io import load_mesh

        result_obj = _load_result(args.script)
        unions = dict(resolve_unions(part, result_obj))
        wp = unions[args.emit_candidates]
        mesh = load_mesh(args.stl)
        constraints = plan.get("constraints", {})
        perimeters = max(
            2, int((constraints.get("wall_min_mm", 1.2) / plan.get("nozzle_mm", 0.4)) + 0.999)
        )
        result = evaluate_candidate_speed_models(wp, mesh, motion, perimeters)
    else:
        result = run_toolpath_speed_check(plan, args.script, motion, args.stl)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
