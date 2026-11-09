#!/usr/bin/env python3
"""
Run a CadQuery model script and emit a structured JSON result.

During the iteration loop the STL is written to a private temp directory
and its path is NOT reported — the LLM works in code space only.
Use --deliver to invoke the modular exporter and get deliverable files.

Usage:
    python3 run_cadquery_model.py path/to/model.py
    python3 run_cadquery_model.py path/to/model.py --preview
    python3 run_cadquery_model.py path/to/model.py --strict
    python3 run_cadquery_model.py path/to/model.py --expected-dims 50,30,20
    python3 run_cadquery_model.py path/to/model.py --deliver --formats stl,3mf

JSON output keys:
    success       bool
    script        str
    geometry      {bbox:{x_mm,y_mm,z_mm}, volume_cm3, weight_g, face_count,
                   thin_regions:[...]} | null   (thin_regions present when --wall-min set)
    errors        [{type, message, hint, ...}]   always present, [] on clean run
                  thin_interface errors carry thickness_mm, equiv_diameter_mm,
                  orientation, location_xyz_mm, thin_direction, nearest_feature
                  disconnected_body errors carry union, component_count (a union
                  body that split into more than one connected component)
    stls          []  (always empty during iteration; populated by --deliver)
    stl           null (populated by --deliver)
    previews      [path, ...]  (populated by --preview)
    preview       path | null
    threemfs      []  (legacy compat, use --deliver)
    threemf       null
    watertight    bool | null
    stdout        str
    stderr        str
    returncode    int

Exit codes:
    0  success
    1  script/preview/--strict failure
    2  interpreter / script path not launchable
    3  timeout
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# OCC exception → structured hint translation table
# ---------------------------------------------------------------------------
_OCC_HINTS = {
    "Standard_ConstructionError": (
        "construction_error",
        "geometry construction failed — check that boolean bodies overlap "
        "and no faces are coincident",
    ),
    "BRep_API": (
        "command_not_done",
        "boolean operation failed — ensure the inner body extends at least "
        "0.01 mm past the outer boundary (use inner height = outer height + 0.02)",
    ),
    "StdFail_NotDone": (
        "fillet_failure",
        "operation left incomplete — fillet radius may exceed an adjacent face "
        "dimension; reduce the radius or apply fillets before cutting holes",
    ),
    "Standard_NullObject": (
        "null_object",
        "referenced a shape that does not exist — check selector strings "
        "('.faces(\">Z\")', etc.) and workplane offsets",
    ),
    "Standard_OutOfRange": (
        "index_out_of_range",
        "index out of range — check pushPoints list or loop bounds",
    ),
    "Standard_TypeMismatch": (
        "type_mismatch",
        "wrong shape type for this operation — verify the workplane and "
        "selector are targeting the correct geometry",
    ),
}

_OCC_HINT_DEFAULT = (
    "check CadQuery documentation for this exception class; common causes: "
    "coincident faces, zero-thickness geometry, invalid boolean order"
)

# Runtime cq_verify helper failures surface as a RuntimeError whose message carries a
# "[cq-verify:<kind>:<label>] <detail>" marker. Classify those into typed errors instead
# of the generic occ_exception fallback so the fix loop knows the exact feature.
_VERIFY_MARKER_RE = re.compile(r"\[cq-verify:(?P<kind>\w+):(?P<label>[^\]]*)\]\s*(?P<detail>.*)")

_VERIFY_HINTS = {
    "silent_boolean": (
        "the boolean tool did not overlap the body — reposition the tool so it "
        "intersects, or check the offset that places it"
    ),
    "feature_overflow": (
        "constrain the feature within the base body, or intersect it with the body "
        "profile to clip the overflow"
    ),
    "workplane_drift": (
        "the workplane origin moved (often from a prior .center()/.hole()) — re-anchor "
        "with .workplane(origin=...) or a fresh cq.Workplane before placing the feature"
    ),
    "stage_mismatch": (
        "the construction stage's bbox/volume didn't match the plan — the wrong-topology "
        "step is the stage named in this error, not a later one"
    ),
    "unbacked_mate": (
        "the feature's declared mating face is not fully backed by its named neighbor — "
        "extend the neighboring feature (or reposition this one) so it fully covers the "
        "mating face, not just the shared centerline/axis coordinate"
    ),
    "boss_swallowed": (
        "a flat support body is seated at the round boss's center coordinate, not its "
        "tangent — offset the support's mating face by the boss radius (pivot ± r), or "
        "route the join through blocks.joints.pin_hinge which seats at the tangent"
    ),
    "fillet_radius": (
        "the fillet radius does not fit the adjacent edges — reduce it below the stated "
        "limit, or select fewer edges, before calling .fillet()"
    ),
    "chamfer_size": (
        "the chamfer length does not fit the adjacent edges — reduce it below the stated "
        "limit, or select fewer edges, before calling .chamfer()"
    ),
    "probe_failed": (
        "a step broke a probe (solid count, volume sign, or a plan/block probe at a point) "
        "-- fix the step named in this error, not a later one; a plan probe is the plan's "
        "intent and cannot be worked around in the script"
    ),
    "step_plan": (
        "the step does not match BUILD_PLAN.json (missing instance, wrong entry, unknown or "
        "missing param) -- dimensions are plan-owned: fix the plan instance, not the script"
    ),
    "finishing_probe_failed": (
        "a plan edge treatment (chamfer/fillet size from BUILD_PLAN.json `edges`) broke a "
        "plan probe or matched no edge -- edge sizes are plan values: ask the user to change "
        "or drop the edge treatment"
    ),
    "step_unrepairable": (
        "the imported file is itself an invalid solid and blocks.import_solid could not "
        "repair it within the volume limit -- the faulty region must be rebuilt rather "
        "than edited, or raise max_volume_deviation if the reported delta is acceptable"
    ),
    "thin_ligament": (
        "too little material beside the hole — widen the wall, shrink the hole, or move "
        "it, until the ligament meets the minimum"
    ),
}


def _translate_verify_marker(stderr: str) -> dict | None:
    """Return a typed error for a cq_verify RuntimeError marker in stderr, else None."""
    m = _VERIFY_MARKER_RE.search(stderr)
    if not m or m.group("kind") not in _VERIFY_HINTS:
        return None
    kind = m.group("kind")
    label = m.group("label").strip()
    err = {
        "type": kind,
        "label": label,
        "message": m.group("detail").strip(),
        "hint": _VERIFY_HINTS[kind],
    }
    if kind == "finishing_probe_failed":
        err["action"] = "ask_user"
    return err


def _translate_stderr(stderr: str) -> list[dict]:
    """Parse raw stderr and return structured error objects where possible."""
    errors: list[dict] = []
    if not stderr:
        return errors

    # A cq_verify helper failure takes precedence over the generic OCC/traceback path:
    # its exception line ("RuntimeError: [cq-verify:...]") would otherwise be classified
    # as an occ_exception.
    verify_err = _translate_verify_marker(stderr)
    if verify_err is not None:
        return [verify_err]

    lines = stderr.splitlines()
    exc_class = None
    exc_message = None

    for line in lines:
        stripped = line.strip()
        # Python exception line: "ExceptionClass: message" at the end of traceback
        if (
            stripped
            and ":" in stripped
            and not stripped.startswith(" ")
            and not stripped.startswith("File ")
        ):
            parts = stripped.split(":", 1)
            # OCP prints the module path ("OCP.OCP.StdFail.StdFail_NotDone"); keep the class.
            candidate = parts[0].strip().rsplit(".", 1)[-1]
            # Must look like an exception class, not just any "Capitalized: ..." line a
            # model prints to stderr. Real Python exceptions end in Error/Exception/etc.;
            # OCC kernel classes carry a known prefix. A bare uppercase first letter is
            # too loose ("Foo: bar" must not register as an occ_exception).
            if (
                candidate
                and " " not in candidate
                and (
                    candidate.endswith(("Error", "Exception", "Failure", "Interrupt", "Exit"))
                    or candidate.startswith(
                        ("Standard_", "StdFail", "BRep", "Geom_", "TopoDS_", "OCC", "OSD_")
                    )
                )
            ):
                exc_class = candidate
                exc_message = parts[1].strip() if len(parts) > 1 else ""

    if exc_class:
        err_type = "occ_exception"
        hint = _OCC_HINT_DEFAULT
        for key, (t, h) in _OCC_HINTS.items():
            if key in exc_class or exc_class in key:
                err_type, hint = t, h
                break
        errors.append(
            {
                "type": err_type,
                "occ_class": exc_class,
                "message": exc_message or exc_class,
                "hint": hint,
            }
        )

    return errors


# ---------------------------------------------------------------------------
# Geometry analysis
# ---------------------------------------------------------------------------


def _compute_geometry(
    stl_path: str, density_g_cm3: float = 1.24
) -> tuple[dict | None, list[dict], object | None]:
    """Load STL, compute geometry metrics and detect topology errors.

    Returns (geometry_dict, errors_list, mesh).
    geometry_dict and mesh are None if the mesh cannot be loaded. The loaded
    trimesh is returned so the caller can run the per-union connected-component
    check without re-loading the file.
    """
    import numpy as np

    import mesh_io

    errors = []

    try:
        tm = mesh_io.load_mesh(stl_path)
    except ValueError as e:
        errors.append(
            {
                "type": "mesh_load_error",
                "message": str(e),
                "hint": "the script may have produced a corrupt or empty STL; "
                "check that cq.exporters.export() was called on a valid solid",
            }
        )
        return None, errors, None

    extents = tm.bounding_box.extents
    vol = None
    weight = None
    try:
        v = abs(tm.volume)
        if v > 0 and tm.is_volume:
            vol = round(v / 1000, 3)
            weight = round(vol * density_g_cm3, 1)
    except Exception:
        pass

    geo = {
        "bbox": {
            "x_mm": round(float(extents[0]), 2),
            "y_mm": round(float(extents[1]), 2),
            "z_mm": round(float(extents[2]), 2),
        },
        "volume_cm3": vol,
        "weight_g": weight,
        "face_count": int(len(tm.faces)),
    }

    # Non-manifold edge detection
    if not tm.is_watertight:
        try:
            nm_edges = mesh_io.nonmanifold_edges(tm, max_report=5)

            if nm_edges:
                for edge_verts, face_ids in nm_edges[:3]:
                    v0 = tm.vertices[edge_verts[0]]
                    v1 = tm.vertices[edge_verts[1]]
                    gap = float(np.linalg.norm(v1 - v0))
                    face_tags = [f"face-{fi:04x}" for fi in face_ids]
                    errors.append(
                        {
                            "type": "non_manifold_edge",
                            "message": (
                                f"edge between {' and '.join(face_tags)}, gap {round(gap, 4)} mm"
                            ),
                            "gap_mm": str(round(gap, 4)),
                            "hint": (
                                "boolean subtraction left a gap — extend the inner "
                                "body at least 0.01 mm past the outer boundary; "
                                "add a small epsilon (0.01) to inner dimensions"
                            ),
                        }
                    )
            elif not tm.is_watertight:
                errors.append(
                    {
                        "type": "non_watertight",
                        "message": "mesh has open boundaries (non-watertight)",
                        "hint": (
                            "check for zero-thickness faces, unclosed shells, or "
                            "boolean operations that did not complete cleanly"
                        ),
                    }
                )
        except Exception as e:
            errors.append(
                {
                    "type": "topology_analysis_error",
                    "message": str(e),
                    "hint": "could not perform topology analysis; check mesh manually",
                }
            )

    return geo, errors, tm


def _disconnected_body_error(tm, uid: str, multi: bool) -> dict | None:
    """Return a disconnected_body error if a union body splits into >1 component.

    Each declared union maps to one rigid printed body, so its mesh is expected to
    be a single connected component. When trimesh splits the body into more than one,
    the part that should be one solid rendered as separate pieces (each may itself be
    watertight, so the watertight check does not catch it). The error carries the
    union id and component count; the message is prefixed with the union id for a
    multi-union part, matching the per-union reporting convention.
    """
    try:
        components = tm.split(only_watertight=False)
    except Exception:
        return None
    if len(components) <= 1:
        return None

    summaries = []
    for i, c in enumerate(components, 1):
        lo, hi = c.bounds
        try:
            vol = abs(c.volume) / 1000.0 if c.is_volume else None
        except Exception:
            vol = None
        s = (
            f"body {i}: x {lo[0]:.1f}..{hi[0]:.1f}, y {lo[1]:.1f}..{hi[1]:.1f}, "
            f"z {lo[2]:.1f}..{hi[2]:.1f} mm"
        )
        if vol is not None:
            s += f", {vol:.2f} cm3"
        summaries.append(s)

    msg = f"union tessellated into {len(components)} disconnected bodies ({'; '.join(summaries)})"
    if multi:
        msg = f"[{uid}] {msg}"
    return {
        "type": "disconnected_body",
        "union": uid,
        "component_count": len(components),
        "message": msg,
        "hint": (
            "a part expected to be one body split into separate solids — compare the "
            "per-body ranges above first: if they do not overlap on some axis, a body "
            "is misplaced (a workplane change moves a box's origin) and must be moved "
            "back, not merely overlapped; only once the pieces do meet should you add "
            "overlap so they fuse into a single component"
        ),
    }


def _aggregate_geometry(per_union: list[tuple[str, dict | None]]) -> dict | None:
    """Combine per-union geometry into one `geometry` block for a multi-union part.

    Sums volume/weight/face_count and reports a per-axis bounding-box envelope across the
    unions (a loose summary; the unions are in their own build poses). A single union
    returns its own geometry unchanged.
    """
    geos = [g for _, g in per_union if g is not None]
    if not geos:
        return None
    if len(per_union) == 1:
        return per_union[0][1]

    def _sum(key: str) -> float | None:
        vals = [g[key] for g in geos if g.get(key) is not None]
        return round(sum(vals), 3) if vals else None

    return {
        "bbox": {
            "x_mm": max(g["bbox"]["x_mm"] for g in geos),
            "y_mm": max(g["bbox"]["y_mm"] for g in geos),
            "z_mm": max(g["bbox"]["z_mm"] for g in geos),
        },
        "volume_cm3": _sum("volume_cm3"),
        "weight_g": _sum("weight_g"),
        "face_count": int(sum(g["face_count"] for g in geos)),
    }


def _attribute_to_union(errs: list[dict], uid: str, multi: bool) -> list[dict]:
    """Tag each error with its union id (and prefix the message) when a part has many unions."""
    if not multi:
        return errs
    return [{**e, "union": uid, "message": f"[{uid}] {e['message']}"} for e in errs]


def _check_dimensions(geo: dict, expected_dims: list[float], tolerance: float = 1.0) -> list[dict]:
    """Compare actual bbox against expected [w, d, h]. Return mismatch errors."""
    if not geo or not expected_dims or len(expected_dims) != 3:
        return []
    errors = []
    axes = [
        ("x", geo["bbox"]["x_mm"]),
        ("y", geo["bbox"]["y_mm"]),
        ("z", geo["bbox"]["z_mm"]),
    ]
    for (axis, actual), expected in zip(axes, expected_dims, strict=True):
        delta = actual - expected
        if abs(delta) > tolerance:
            errors.append(
                {
                    "type": "dimension_mismatch",
                    "message": f"{axis} is {actual} mm, expected {expected} mm",
                    "axis": axis,
                    "actual_mm": actual,
                    "expected_mm": expected,
                    "delta_mm": round(delta, 2),
                    "hint": (
                        f"{axis.upper()}-axis is {abs(delta):.1f} mm "
                        f"{'too small' if delta < 0 else 'too large'} — "
                        f"check the parameter for this dimension"
                    ),
                }
            )
    return errors


def _thin_interface_hint(region: dict, wall_min_mm: float, line_width_mm: float) -> str:
    """Build a remedy hint for an XY-thin region, keyed to its measurements."""
    t = region["thickness_mm"]
    dx, dy, _ = region["thin_direction"]
    # The thin direction lies in the build plane; rotating about the orthogonal
    # horizontal axis lays the wall flat (thin direction -> Z).
    rot_axis = "Y" if abs(dx) >= abs(dy) else "X"
    parts = [
        f"wall is {t:.2f} mm thick in the XY plane (min {wall_min_mm} mm)",
        f"thicken past {wall_min_mm} mm, or rotate ~90 deg about {rot_axis} to lay "
        "it flat (may convert it to an overhang -- verify orientation tradeoff)",
    ]
    if region.get("brittle"):
        parts.append(
            f"below ~4 line widths ({4 * line_width_mm:.1f} mm) so it prints as all "
            "perimeters and is brittle"
        )
    if region["thickness_mean_mm"] > 1.5 * t:
        parts.append("tapers sharply -- add a fillet at the shoulder to spread stress")
    nf = region.get("nearest_feature")
    if nf:
        parts.append(f"near {nf['feature']} ({nf['distance_mm']} mm)")
    return "; ".join(parts)


def _check_thin_interfaces(
    stl_path: str, wall_min_mm: float, line_width_mm: float
) -> tuple[list[dict], list[dict]]:
    """Detect thin regions via local thickness; classify by XY/Z direction.

    Returns (thin_regions, errors). Every thin region (below wall_min_mm) is
    returned for the geometry block; only XY-thin regions become typed errors,
    because a region thin only along Z is a flat, well-bonded slab and is benign
    for printing.
    """
    try:
        import measure_stl

        data = measure_stl.measure(stl_path, thin_max_mm=wall_min_mm, line_width_mm=line_width_mm)
        thin_regions = data.get("thin_regions", [])
    except Exception as exc:
        print(f"thin-interface check failed for {stl_path}: {exc}", file=sys.stderr)
        return [], [
            {
                "type": "thin_interface_check_error",
                "message": str(exc),
                "hint": "could not measure wall thickness; check mesh manually",
            }
        ]

    errors = []
    for r in thin_regions:
        if r["orientation"] != "xy" or r["thickness_mm"] >= wall_min_mm:
            continue
        errors.append(
            {
                "type": "thin_interface",
                "thickness_mm": r["thickness_mm"],
                "equiv_diameter_mm": r["equiv_diameter_mm"],
                "min_mm": wall_min_mm,
                "orientation": "xy",
                "location_xyz_mm": r["location_xyz_mm"],
                "thin_direction": r["thin_direction"],
                "nearest_feature": r["nearest_feature"],
                "hint": _thin_interface_hint(r, wall_min_mm, line_width_mm),
            }
        )
    return thin_regions, errors


# ---------------------------------------------------------------------------
# STL discovery
# ---------------------------------------------------------------------------


def _new_files_by_ext(search_dir: str, after_mtime: float, exts: tuple) -> dict:
    import glob

    buckets: dict = {ext: {} for ext in exts}
    for ext in exts:
        for case in (ext.lower(), ext.upper()):
            for path in glob.glob(os.path.join(search_dir, f"*.{case}")):
                real = os.path.realpath(path)
                if real in buckets[ext]:
                    continue
                try:
                    mtime = os.path.getmtime(path)
                except OSError:
                    continue
                if mtime >= after_mtime:
                    buckets[ext][real] = (mtime, path)
    return {
        ext: [p for _, p in sorted(entries.values(), reverse=True)]
        for ext, entries in buckets.items()
    }


# ---------------------------------------------------------------------------
# Preview via render_preview.py subprocess (CQ-native, no OpenGL)
# ---------------------------------------------------------------------------


def _render_preview(
    script_path: str,
    skill_root: str,
    views: str,
    env: dict,
    cross_sections: bool = False,
    extra_sections: list[str] | None = None,
    details: list[str] | None = None,
    callouts: list[str] | None = None,
    unlocated_names: list[str] | None = None,
    preview_dir: str | None = None,
    density_g_cm3: float = 1.24,
    material: str = "PLA",
    auto_sections: bool = False,
    features: list[str] | None = None,
    sheet: bool = False,
    timeout: int | None = None,
) -> tuple[list[str], str | None]:
    """Invoke render_preview.py as a subprocess.

    `extra_sections` is a list of raw "AXIS=VALUE_MM" strings (e.g. "x=50"),
    forwarded as repeated --extra-section flags. `details` is a list of raw
    "name=...;center=x,y,z;size=..." specs, forwarded as repeated --detail flags
    (see render_preview.py --help for the full format); each produces one or two
    additional standalone, feature-named preview files. `callouts` is a list of
    raw "name=...;center=x,y,z" specs, forwarded as repeated --callout flags: a
    numbered badge + leader line on the tile's three orthographic panels, plus a
    legend line. `unlocated_names` is a list of raw feature-name strings,
    forwarded as repeated --unlocated-name flags: unbadged legend entries for
    named features with no known position. `features` is a list of raw
    "name=...;center=x,y,z[;diameter=..|size=..]" specs forwarded as --feature
    flags, and `sheet` forwards --sheet. render_preview.py parses and
    validates all of these.

    `preview_dir` is where the preview PNG(s) are written; omit it to write
    alongside the script (legacy behavior). The project's own preview/ directory
    is kept separate from build/ (which holds only edited part scripts) -- pass
    it explicitly to redirect previews there.

    Returns (preview_png_paths, error_message): the first path is the main
    overview preview, followed by any detail-view/detail-section paths, in the
    order render_preview.py reported them via its final `extra_previews` JSON
    line. On success: (paths, None). On failure: ([], error_text). Raises
    `subprocess.TimeoutExpired` past `timeout` seconds.
    """
    script_dir = preview_dir or os.path.dirname(script_path)
    os.makedirs(script_dir, exist_ok=True)
    script_stem = os.path.splitext(os.path.basename(script_path))[0]
    preview_dest = os.path.join(script_dir, f"{script_stem}_preview.png")
    render_script = os.path.join(skill_root, "render_preview.py")

    cmd = [
        sys.executable,
        render_script,
        "--script",
        script_path,
        "--output",
        preview_dest,
        "--views",
        views,
        "--density",
        str(density_g_cm3),
        "--material",
        material,
    ]
    if cross_sections:
        cmd.append("--cross-sections")
    if auto_sections:
        cmd.append("--auto-sections")
    for spec in extra_sections or []:
        cmd.extend(["--extra-section", spec])
    for spec in details or []:
        cmd.extend(["--detail", spec])
    for spec in callouts or []:
        cmd.extend(["--callout", spec])
    for name in unlocated_names or []:
        cmd.extend(["--unlocated-name", name])
    for spec in features or []:
        cmd.extend(["--feature", spec])
    if sheet:
        cmd.append("--sheet")

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )

    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "Preview render subprocess failed").strip()
        return [], err

    extra_previews: list[str] = []
    for line in reversed(proc.stdout.splitlines()):
        try:
            parsed = json.loads(line)
        except ValueError:
            continue
        if isinstance(parsed, dict) and "extra_previews" in parsed:
            extra_previews = parsed["extra_previews"]
            break

    return [preview_dest, *extra_previews], None


def _append_stderr(result: dict, msg: str) -> None:
    result["stderr"] = (result["stderr"] or "") + msg + "\n"


def _run_geometry_checks(union_stls: list[str], args, result: dict) -> bool:
    """Run per-union geometry/DFM checks and populate `result`.

    Returns True if the checks fail the run under --strict (non-watertight).
    """
    multi = len(union_stls) > 1
    per_union_geo: list[tuple[str, dict | None]] = []
    thin_regions_all: list = []
    watertight_all = True

    for stl in union_stls:
        uid = os.path.splitext(os.path.basename(stl))[0]

        geo_i, geo_errors_i, tm_i = _compute_geometry(stl, args.density)
        per_union_geo.append((uid, geo_i))
        result["errors"].extend(_attribute_to_union(geo_errors_i, uid, multi))
        # Per-union connectedness: a union expected to be one body that splits
        # into multiple components is a disconnected_body error (always carries
        # its own union id, so it is not routed through _attribute_to_union).
        if tm_i is not None:
            disc = _disconnected_body_error(tm_i, uid, multi)
            if disc is not None:
                result["errors"].append(disc)
        clean = geo_i is not None and not any(
            e["type"] in ("non_manifold_edge", "non_watertight") for e in geo_errors_i
        )
        watertight_all = watertight_all and clean

        if args.wall_min > 0:
            thin_regions_i, thin_errors_i = _check_thin_interfaces(
                stl, args.wall_min, args.line_width
            )
            for r in thin_regions_i:
                thin_regions_all.append({**r, "union": uid} if multi else r)
            result["errors"].extend(_attribute_to_union(thin_errors_i, uid, multi))

    result["geometry"] = _aggregate_geometry(per_union_geo)
    result["watertight"] = watertight_all
    if result["geometry"] is not None and args.wall_min > 0:
        result["geometry"]["thin_regions"] = thin_regions_all

    # Dimension check against plan expectations (single-union parts only; a multi-union
    # part has no single bounding box to compare against the plan's w/d/h).
    if args.expected_dims and not multi and result["geometry"] is not None:
        try:
            expected = [float(x) for x in args.expected_dims.split(",")]
            result["errors"].extend(
                _check_dimensions(result["geometry"], expected, args.dim_tolerance)
            )
        except ValueError:
            _append_stderr(result, f"Invalid --expected-dims value: {args.expected_dims}")

    return bool(args.strict and not result["watertight"])


def _brep_errors(run_dir: str) -> list[dict]:
    """One invalid_brep error per body the shim's BRepCheck flagged (none without a sidecar)."""
    path = os.path.join(run_dir, "brep_check.json")
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as f:
        checks = json.load(f)
    multi = len(checks) > 1
    errors = []
    for uid, statuses in checks.items():
        if not statuses:
            continue
        if statuses[0].startswith("Mesh: "):
            err = {
                "type": "invalid_mesh",
                "message": "STEP does not tessellate to a closed manifold: " + statuses[0][6:],
                "hint": (
                    "the solid is BRep-valid but its delivered STEP meshes with open or "
                    "over-shared edges (graders reject it) -- usually coincident faces left by "
                    "a clean=False union/cut; overlap the tool into the body (or past it, for a "
                    "cut) instead of making it face-flush or coaxial with an existing surface"
                ),
            }
            errors.extend(_attribute_to_union([err], uid, multi))
            continue
        err = {
            "type": "invalid_brep",
            "message": "BRepCheck failed: " + "; ".join(statuses),
            "hint": (
                "the result body is not a valid solid (STEP consumers and graders reject it) -- "
                "find the last boolean/fillet/chamfer that produced it and change it; for an "
                "imported file, import it with blocks.import_solid, which repairs it"
            ),
        }
        errors.extend(_attribute_to_union([err], uid, multi))
    return errors


def _handle_preview(args, script_path: str, skill_root: str, env: dict, result: dict) -> bool:
    """Render the preview into `result`. Returns True if rendering failed."""
    preview_paths, render_err = _render_preview(
        script_path,
        skill_root,
        args.views,
        env,
        args.cross_sections,
        args.extra_section,
        args.detail,
        args.callout,
        args.unlocated_name,
        args.preview_dir,
        args.density,
        args.material,
        args.auto_sections,
        args.feature,
        args.sheet,
        args.timeout,
    )
    if render_err:
        _append_stderr(result, render_err)
        result["success"] = False
        return True
    result["previews"] = preview_paths
    result["preview"] = preview_paths[0] if preview_paths else None
    return False


_EXPORT_SNIPPET = (
    "import json, sys\n"
    "from exporters import run_exporters\n"
    "paths = run_exporters(sys.argv[1], sys.argv[2].split(','), sys.argv[3])\n"
    "print(json.dumps(paths))\n"
)


def _handle_deliver(
    args, script_path: str, result: dict, env: dict, manifest_path: str | None = None
) -> None:
    """Populate stl/stls/threemf paths in `result` from the delivered files.

    Reads the shim's delivery manifest when it wrote one (no second script import);
    otherwise runs the modular exporter in a subprocess bounded by `--timeout`, which
    re-imports the script in the build pose. Raises `subprocess.TimeoutExpired`.
    """
    try:
        if manifest_path and os.path.isfile(manifest_path):
            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)
            if "error" in manifest:
                raise RuntimeError(manifest["error"])
            delivered = manifest["paths"]
        else:
            out_dir = args.output_dir or os.path.dirname(script_path)
            os.makedirs(out_dir, exist_ok=True)
            formats = ",".join(f.strip() for f in args.formats.split(",") if f.strip())
            build_env = {k: v for k, v in env.items() if k != "CQ_PRINT_ROTATE"}
            proc = subprocess.run(
                [sys.executable, "-c", _EXPORT_SNIPPET, script_path, formats, out_dir],
                capture_output=True,
                text=True,
                env=build_env,
                timeout=args.timeout,
            )
            if proc.returncode != 0:
                raise RuntimeError((proc.stderr or "exporter subprocess failed").strip()[-500:])
            # The script may print; the exporter's JSON is the last stdout line.
            delivered = json.loads(proc.stdout.strip().splitlines()[-1])
        result["stls"] = [p for p in delivered if p.endswith(".stl")]
        result["threemfs"] = [p for p in delivered if p.endswith(".3mf")]
        result["stl"] = result["stls"][0] if result["stls"] else None
        result["threemf"] = result["threemfs"][0] if result["threemfs"] else None
    except subprocess.TimeoutExpired:
        raise
    except Exception as e:
        _append_stderr(result, f"Exporter failed: {e}")
        result["success"] = False


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a CadQuery model script and report a JSON result",
        epilog="Exit codes: 0 success, 1 failure, 2 cannot launch, 3 timeout.",
    )
    parser.add_argument("script", help="Path to the CadQuery .py file")
    parser.add_argument("--preview", action="store_true", help="Render a multi-view preview PNG")
    parser.add_argument(
        "--cross-sections",
        action="store_true",
        help=(
            "Render cross-sections as separate files (requires --preview): through the "
            "--extra-section positions when given, else the bounding-box-center cuts"
        ),
    )
    parser.add_argument(
        "--auto-sections",
        action="store_true",
        help=(
            "Forward --auto-sections to render_preview.py (requires --preview): fill up to "
            "3 section cuts after --extra-section with cuts through bore/boss axes"
        ),
    )
    parser.add_argument(
        "--extra-section",
        action="append",
        default=[],
        metavar="AXIS=VALUE_MM",
        help=(
            "Additional targeted cross-section beyond the default center cuts, e.g. "
            "--extra-section x=50 (requires --preview). AXIS is x/y/z. Repeatable. "
            "Use when a feature's footprint is away from the bounding-box center and "
            "so would not be crossed by the default cuts."
        ),
    )
    parser.add_argument(
        "--detail",
        action="append",
        default=[],
        metavar="SPEC",
        help=(
            "Standalone high-resolution detail view for a small feature (requires "
            "--preview): 'name=<feature>;center=x,y,z;size=<mm>', optionally with a "
            "matching detail cross-section: '...;section=<axis>=<pos>'. Written as "
            "separate feature-named files. Repeatable. Use for a feature added or "
            "changed at the user's request that would be imperceptible in the "
            "default overview tile."
        ),
    )
    parser.add_argument(
        "--feature",
        action="append",
        default=[],
        metavar="SPEC",
        help=(
            "Per-feature preview (requires --preview): "
            "'name=<feature>;center=x,y,z[;diameter=<mm>|;size=<w>,<h>]'. Renders a "
            "marked view along the feature normal and, for features with depth, a "
            "section through their axis. Repeatable; supply order is relevance order."
        ),
    )
    parser.add_argument(
        "--sheet",
        action="store_true",
        help=(
            "Forward --sheet to render_preview.py (requires --preview): a 2 x 2 sheet of at "
            "most 4 tiles (--feature tiles, then whole-part sections)"
        ),
    )
    parser.add_argument(
        "--callout",
        action="append",
        default=[],
        metavar="SPEC",
        help=(
            "Numbered badge + leader line for a named feature (requires --preview): "
            "'name=<feature>;center=x,y,z'. Repeatable; badge numbers follow supply "
            "order. Adds a legend line mapping badges to names to the tile caption."
        ),
    )
    parser.add_argument(
        "--unlocated-name",
        action="append",
        default=[],
        metavar="NAME",
        help=(
            "Named feature with no known position (requires --preview): listed in "
            "the tile legend as 'NAME (not located)' without a badge. Repeatable."
        ),
    )
    parser.add_argument(
        "--preview-dir",
        default=None,
        help="Directory for preview PNG(s) (requires --preview; default: alongside the script)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if any STL is not watertight or no STL produced",
    )
    parser.add_argument(
        "--print-rotate",
        default=None,
        metavar="ORIENTATION_JSON",
        help=(
            "Orientation JSON (print_orientation.py output, with a `rotate` list). Sets "
            "CQ_PRINT_ROTATE for the run so blocks.print_up() resolves the print pose "
            "(the finishing pass); omit for the authoring default (+Z)."
        ),
    )
    parser.add_argument("--views", choices=["iso", "multi"], default="multi")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument(
        "--expected-dims",
        default=None,
        help="Expected bounding box as W,D,H in mm (e.g. 50,30,20)",
    )
    parser.add_argument(
        "--dim-tolerance",
        type=float,
        default=1.0,
        help="Tolerance in mm for --expected-dims check (default 1.0)",
    )
    parser.add_argument(
        "--wall-min",
        type=float,
        default=0.0,
        help="Minimum wall thickness in mm for DFM check (0 = skip)",
    )
    parser.add_argument(
        "--line-width",
        type=float,
        default=0.42,
        help="Extrusion line width in mm for the brittle thin-wall threshold",
    )
    parser.add_argument(
        "--density",
        type=float,
        default=1.24,
        help="Filament density in g/cm3 for weight estimation (default: PLA, 1.24)",
    )
    parser.add_argument(
        "--material", default="PLA", help="Material name for the preview footer label"
    )
    parser.add_argument(
        "--deliver",
        action="store_true",
        help="Run modular exporter and populate stl/stls in output",
    )
    parser.add_argument(
        "--formats",
        default="stl",
        help="Comma-separated export formats for --deliver (default: stl)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory for --deliver (default: alongside the script)",
    )
    parser.add_argument(
        "--attempts-log",
        default=None,
        help="Append this run's attempt record to the given attempts.jsonl (part id = script stem)",
    )
    parser.add_argument("--model", default=None, help="Model name for the attempt record")
    return parser


def _emit(args: argparse.Namespace, result: dict) -> None:
    """Print the JSON contract; with --attempts-log, also append the attempt record
    (sub-agent tool calls do not reach the PostToolUse telemetry hook)."""
    if args.attempts_log:
        try:
            from log import record_attempt

            record_attempt(Path(args.attempts_log), Path(args.script).stem, result, args.model)
        except Exception as exc:  # telemetry must never break a validate run
            _append_stderr(result, f"attempt telemetry not written: {exc}")
    _record_history(args.script, result)
    print(json.dumps(result, indent=2))


def _record_history(script: str, result: dict) -> None:
    """Record the run in script history (with the plan revision when the script is a part)
    and flag a script changed outside script_ops (`unmanaged_edit`)."""
    from script_history import current_attempt, record_run, unmanaged

    path = Path(script).resolve()
    ok = bool(result["success"])
    result["unmanaged_edit"] = unmanaged(path)
    try:
        attempt = current_attempt(path)
    except Exception:
        attempt = None
    record_run(path, ok, attempt=attempt)


def main():
    args = _build_arg_parser().parse_args()

    script_path = os.path.abspath(args.script)
    skill_root = os.path.dirname(os.path.abspath(__file__))

    result = {
        "success": False,
        "script": args.script,
        "geometry": None,
        "errors": [],
        "stls": [],
        "stl": None,
        "previews": [],
        "preview": None,
        "threemfs": [],
        "threemf": None,
        "watertight": None,
        "stdout": "",
        "stderr": "",
        "returncode": -1,
    }

    # Run the script in a private temp directory so STL exports land there
    run_dir = tempfile.mkdtemp(prefix="cq_run_")
    try:
        env = os.environ.copy()
        env["PYTHONPATH"] = skill_root + os.pathsep + env.get("PYTHONPATH", "")
        if args.print_rotate:
            from units import InputFileError, read_json

            try:
                env["CQ_PRINT_ROTATE"] = json.dumps(
                    read_json(args.print_rotate, "print-rotate file")["rotate"]
                )
            except InputFileError as e:
                result["errors"].append(
                    {
                        "type": "file_error",
                        "message": e.message,
                        "hint": "check the --print-rotate path, or re-run print_orientation.py",
                    }
                )
                _emit(args, result)
                sys.exit(1)

        # A rotated run holds the posed frame but --deliver exports the build pose, so
        # only an unrotated run can have the shim deliver from its own load.
        deliver_manifest = None
        if args.deliver and not args.print_rotate:
            deliver_manifest = os.path.join(run_dir, "deliver_manifest.json")
            env["CQ_DELIVER_MANIFEST"] = deliver_manifest
            env["CQ_DELIVER_FORMATS"] = ",".join(
                f.strip() for f in args.formats.split(",") if f.strip()
            )
            env["CQ_DELIVER_DIR"] = os.path.abspath(args.output_dir or os.path.dirname(script_path))

        shim = os.path.join(skill_root, "run_model_shim.py")
        started = time.time()
        try:
            proc = subprocess.run(
                [sys.executable, shim, script_path],
                capture_output=True,
                text=True,
                timeout=args.timeout,
                cwd=run_dir,
                env=env,
            )
        except subprocess.TimeoutExpired as e:
            _append_stderr(result, f"Timeout after {args.timeout}s: {e}")
            _emit(args, result)
            sys.exit(3)
        except FileNotFoundError as e:
            _append_stderr(result, f"Cannot launch interpreter: {e}")
            _emit(args, result)
            sys.exit(2)

        result["stdout"] = proc.stdout
        result["stderr"] = proc.stderr
        result["returncode"] = proc.returncode
        result["success"] = proc.returncode == 0

        # Translate any OCC exception in stderr to structured errors
        if proc.returncode != 0:
            result["errors"].extend(_translate_stderr(proc.stderr))

        if not result["success"]:
            _emit(args, result)
            sys.exit(1)

        # Find STLs written to run_dir
        found = _new_files_by_ext(run_dir, started, ("stl", "3mf"))
        stls_in_temp = found["stl"]

        # --strict: require at least one STL
        if args.strict and not stls_in_temp:
            _append_stderr(result, "No STL files produced by the script (--strict set).")
            result["errors"].append(
                {
                    "type": "no_geometry",
                    "message": "script exited 0 but produced no STL",
                    "hint": "ensure the script calls cq.exporters.export(result, 'output.stl') "
                    "and that the result variable contains a valid solid",
                }
            )
            result["success"] = False
            _emit(args, result)
            sys.exit(1)

        # Geometry analysis. A part may emit several union STLs (one per named union);
        # validate EACH so a thin wall / open mesh in any union is caught, attributing each
        # finding to its union when there is more than one. The `geometry` block aggregates
        # to keep the JSON contract a single object.
        if stls_in_temp:
            strict_fail = _run_geometry_checks(sorted(stls_in_temp), args, result)
            if strict_fail:
                result["success"] = False
                _emit(args, result)
                sys.exit(1)

        # Invalid BRep is blocking regardless of --strict: the shim skipped delivery.
        brep_errors = _brep_errors(run_dir)
        if brep_errors:
            result["errors"].extend(brep_errors)
            result["success"] = False
            _emit(args, result)
            sys.exit(1)

        try:
            # Preview rendering via render_preview.py subprocess (CQ-native, no OpenGL)
            if (
                args.preview
                and stls_in_temp
                and _handle_preview(args, script_path, skill_root, env, result)
            ):
                _emit(args, result)
                sys.exit(1)

            # --deliver: run modular exporter and expose output paths
            if args.deliver and stls_in_temp:
                _handle_deliver(args, script_path, result, env, deliver_manifest)
        except subprocess.TimeoutExpired as e:
            _append_stderr(result, f"Timeout after {args.timeout}s: {e}")
            result["success"] = False
            _emit(args, result)
            sys.exit(3)

        # Mark success=False if any error-severity issues were found
        error_types = {e["type"] for e in result["errors"]}
        if args.strict and error_types & {
            "mesh_load_error",
            "non_manifold_edge",
            "non_watertight",
            "disconnected_body",
            "dimension_mismatch",
            "occ_exception",
        }:
            result["success"] = False

    finally:
        shutil.rmtree(run_dir, ignore_errors=True)

    _emit(args, result)
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
