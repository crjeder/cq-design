#!/usr/bin/env python3
"""
Quality gate for the CAD skill build pipeline.

Runs these checks against the final model script:
  1. Wrapper DFM checks (thin walls, non-manifold edges) via run_cadquery_model.py
  2. Geometry + overhang analysis via trimesh (in-process)
  3. Kinematic range-of-motion sweep when the plan declares joints (once, outside the
     fix loop) via kinematic_check.py
  4. Plate clearance: co-plated unions must keep a gap above one layer height or they
     fuse in the print (once, outside the fix loop) via plate_clearance_check.py
  5. Keep-out zones: no union may intrude on a declared keep-out zone, excluding the
     zone's own declaring part (once, outside the fix loop) via keep_out_check.py

Aggregates issues with severity (error/warning) and emits a report. Report-only by
default; pass --fix to generate a targeted fix prompt and invoke `claude -p` for up
to MAX_FIX_ROUNDS (cold-context, no plan/render/attempt history) before re-running
the gate. On a clean pass emits a print recipe JSON.

Usage:
    python3 quality_gate.py --script build/body.py --plan BUILD_PLAN.json
    python3 quality_gate.py --script build/body.py --plan BUILD_PLAN.json --stl build/body.stl
    python3 quality_gate.py --script build/body.py --plan BUILD_PLAN.json --fix
"""

import argparse
import ast
import json
import math
import os
import subprocess
import sys
from collections.abc import Callable

SKILL_ROOT = os.path.dirname(os.path.abspath(__file__))
MAX_FIX_ROUNDS = 2
# Call names that satisfy the hinge-guard-lint stage (see _run_hinge_guard_stage): a
# hinge-associated union's script must call one of these, whether imported bare
# (`verify_seated(...)`) or via attribute access (`cq_verify.verify_seated(...)`).
_HINGE_GUARD_CALL_NAMES = {"verify_seated", "verify_backed", "pin_hinge"}
# Up-facing gentle-incline area (mm^2) below which the cosmetic-slope finding is suppressed
# as trivial. Advisory only, so this is tunable without affecting pass/fail.
COSMETIC_SLOPE_MIN_AREA_MM2 = 20.0

# Per-type overrides for the caller's routing action, keyed by finding `type`. Every
# type not listed here takes the severity default (see _DEFAULT_ACTION): a single
# mechanical fix isn't the right response for these -- see design.md's Decisions.
_ACTION_OVERRIDE = {
    "stale_artifact": "re_export",
    "motion_collision": "ask_user",
    "range_exceeds_limit": "ask_user",
    "contact_limited_stop": "ask_user",
}
_DEFAULT_ACTION = {"error": "fix", "warning": "warn_only", "info": "warn_only"}


def _classify_action(issue: dict) -> str:
    """Caller-routing action for a finding, derived from its `type` and `severity`."""
    return _ACTION_OVERRIDE.get(issue["type"], _DEFAULT_ACTION[issue["severity"]])


# ---------------------------------------------------------------------------
# DFM check via wrapper
# ---------------------------------------------------------------------------


def _material_density(material: str | None) -> float:
    """density_g_cm3 for `material` from material_properties.json, else PLA's."""
    with open(os.path.join(SKILL_ROOT, "material_properties.json"), encoding="utf-8") as f:
        materials = json.load(f)["materials"]
    entry = materials.get(material) or materials["PLA"]
    return entry["density_g_cm3"]


def _run_wrapper_check(
    script_path: str, plan: dict
) -> tuple[list[dict], str | None, dict | None, list[str]]:
    """Run run_cadquery_model.py DFM checks; return list of issue dicts.

    The 4th element is every union STL the wrapper produced (`data["stls"]`), not just
    the first (`data["stl"]`) -- a multi-union part's overhang/watertightness analysis
    must cover every union, not only the one `stl` happens to point at.
    """
    constraints = plan.get("constraints", {})
    # Line width approximates nozzle diameter * 1.1; drives the brittle thin-wall
    # threshold in the wrapper's thin-interface check.
    line_width = round(plan.get("nozzle_mm", 0.4) * 1.1, 2)
    cmd = [
        sys.executable,
        os.path.join(SKILL_ROOT, "run_cadquery_model.py"),
        script_path,
        "--wall-min",
        str(constraints.get("wall_min_mm", 1.2)),
        "--line-width",
        str(line_width),
        "--density",
        str(_material_density(plan.get("material"))),
        "--material",
        plan.get("material") or "PLA",
        "--deliver",
        "--formats",
        "stl",
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = SKILL_ROOT + os.pathsep + env.get("PYTHONPATH", "")

    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return (
            [
                {
                    "source": "wrapper",
                    "severity": "error",
                    "type": "wrapper_error",
                    "message": "Wrapper produced no JSON output",
                    "hint": result.stdout + result.stderr,
                }
            ],
            None,
            None,
            [],
        )

    # The wrapper's own success=False (script crashed / produced no valid geometry)
    # overrides the type allowlist below -- every error from a failed run is blocking,
    # not just the types this list happens to enumerate.
    run_failed = data.get("success") is False

    issues = []
    for err in data.get("errors", []):
        severity = (
            "error"
            if run_failed
            or err["type"]
            in (
                "non_manifold_edge",
                "non_watertight",
                "occ_exception",
                "construction_error",
                "command_not_done",
                "fillet_failure",
                "null_object",
                "index_out_of_range",
                "type_mismatch",
                "dimension_mismatch",
                "disconnected_body",
                "mesh_load_error",
                "thin_interface_check_error",
            )
            else "warning"
        )
        issues.append(
            {
                "source": "wrapper",
                "severity": severity,
                "type": err["type"],
                "message": err.get("message", err.get("hint", "")),
                "hint": err.get("hint", ""),
            }
        )
    if run_failed and not issues:
        issues.append(
            {
                "source": "wrapper",
                "severity": "error",
                "type": "run_failed",
                "message": "wrapper reported success=False with no structured errors",
                "hint": data.get("stderr", ""),
            }
        )

    # Expose STL path for downstream MCP checks
    stl_path: str | None = data.get("stl")
    return issues, stl_path, data.get("geometry"), data.get("stls") or []


# ---------------------------------------------------------------------------
# Geometry + overhang analysis (trimesh, in-process)
# ---------------------------------------------------------------------------


def _clearance_opening_zones(plan: dict, part: dict, rotate: list[dict] | None) -> list[dict]:
    """Build-frame `{center, radius_mm}` for each of `part`'s `clearance_opening`
    interfaces (see [Hitstertower oversupport](TODO.md#hitstertower-oversupport)).

    `position_mm` is the interface's center in the part's authored frame; mapped
    through the part's `placement` (assembled frame, matching the exported STL) and
    then the chosen print orientation's `rotate` (matching `_analyze_stl`'s posed
    mesh), so it lands in the same frame as `overhang_metrics`' `worst_location_xyz_mm`.
    `radius_mm` is the opening's half-diagonal (from `size_mm`) plus a small margin
    for tessellation/rounding slop; unsized openings fall back to a fixed radius.
    """
    from placement import transform_direction, transform_point

    zones = []
    for interface in part.get("interfaces", []):
        if interface.get("type") != "clearance_opening":
            continue
        position = interface.get("position_mm")
        if position is None:
            continue
        center = transform_point(position, part.get("placement"))
        if rotate:
            center = transform_direction(center, {"rotate": rotate})
        size = interface.get("size_mm")
        radius = math.hypot(*(s / 2 for s in size)) + 1.0 if size else 5.0
        zones.append({"center": center, "radius_mm": radius, "name": interface.get("name")})
    return zones


def _analyze_stl(
    stl_path: str,
    overhang_deg: float,
    rotate: list[dict] | None = None,
    clearance_zones: list[dict] | None = None,
    bridge_max_mm: float = 10.0,
) -> list[dict]:
    """Analyze STL geometry and overhangs using trimesh. Returns issues.

    ``rotate`` is the chosen print orientation's `[{axis, angle_deg}, ...]` steps
    (``print_orientation.py``'s `rotate`, same convention as `placement`). The STL is
    exported in the part's authored/placement frame, so the overhang test would
    otherwise judge a face that the optimizer rotated onto the bed (or into a wall)
    as if it printed in the authored pose -- a false positive whenever the two frames
    differ. Applying the steps here evaluates overhang at the pose that actually prints.
    """
    try:
        import trimesh
    except ImportError as exc:
        return [
            {
                "source": "geometry",
                "severity": "warning",
                "type": "check_skipped",
                "message": f"trimesh/numpy not available: {exc}",
                "hint": "pip install trimesh numpy",
            }
        ]

    try:
        tm = trimesh.load(stl_path, force="mesh")
        if rotate:
            from placement import to_matrix

            tm.apply_transform(to_matrix({"rotate": rotate}))
    except Exception as exc:
        return [
            {
                "source": "geometry",
                "severity": "error",
                "type": "mesh_load_error",
                "message": f"Failed to load STL: {exc}",
                "hint": "Check that the STL was exported correctly.",
            }
        ]

    issues: list[dict] = []

    if not hasattr(tm, "faces") or len(tm.faces) == 0:
        issues.append(
            {
                "source": "geometry",
                "severity": "error",
                "type": "invalid_geometry",
                "message": "STL has no triangles",
                "hint": "Check for degenerate faces or zero-volume bodies.",
            }
        )
        return issues

    if not tm.is_watertight:  # type: ignore[attr-defined]
        issues.append(
            {
                "source": "geometry",
                "severity": "error",
                "type": "non_watertight",
                "message": "Mesh is not watertight",
                "hint": "Close all open edges before printing.",
            }
        )

    # Overhang: faces whose normals point downward (nz < 0). Faces with overhang
    # angle strictly greater than overhang_deg need support. Shared definition with
    # the print-orientation optimizer (mesh_io.overhang_metrics).
    from mesh_io import overhang_metrics

    metrics = overhang_metrics(tm, overhang_deg, bridge_max_mm)
    if metrics["bridge_count"]:
        issues.append(
            {
                "source": "geometry",
                "severity": "info",
                "type": "bridges_detected",
                "message": (
                    f"{metrics['bridge_count']} bridge(s) up to {bridge_max_mm:g} mm over "
                    f"{metrics['bridge_area_mm2']:.1f} mm2 -- printable without support"
                ),
                "hint": "Bridges are not counted as overhangs.",
                "bridge_area_mm2": metrics["bridge_area_mm2"],
            }
        )
    if metrics["worst_angle_deg"] is not None:
        overhang_area = metrics["overhang_area_mm2"]
        worst_angle = metrics["worst_angle_deg"]
        location = metrics["worst_location_xyz_mm"]
        zone = next(
            (
                z
                for z in (clearance_zones or [])
                if math.dist(location, z["center"]) <= z["radius_mm"]
            ),
            None,
        )
        if zone:
            severity = "info"
            message = (
                f"Worst overhang {worst_angle:.1f}° exceeds limit {overhang_deg}° over "
                f"{overhang_area:.1f} mm² of faces, at the declared clearance opening "
                f"'{zone['name']}'"
            )
            hint = (
                "This overhang bounds a declared clearance_opening interface -- see the "
                "part's engineering_rationale/part_notes for its load path instead of "
                "adding support here."
            )
        else:
            severity = "warning"
            message = (
                f"Worst overhang {worst_angle:.1f}° exceeds limit "
                f"{overhang_deg}° over {overhang_area:.1f} mm² of faces"
            )
            hint = "Add chamfers or redesign overhanging features."
        issues.append(
            {
                "source": "geometry",
                "severity": severity,
                "type": "overhang_exceeded",
                "message": message,
                "hint": hint,
                "overhang_area_mm2": overhang_area,
                "worst_angle_deg": worst_angle,
                "location_xyz_mm": location,
            }
        )

    return issues


# ---------------------------------------------------------------------------
# Print recipe
# ---------------------------------------------------------------------------


def _emit_print_recipe(
    plan: dict,
    geometry: dict | None,
    orientation: dict | None = None,
    needs_support: bool = False,
) -> dict:
    """Build a recommended print recipe from plan constraints + geometry.

    When `orientation` (a print_orientation.py result) is supplied, the recipe's
    `orientation` field carries the computed rotation and its rationale; otherwise
    it falls back to the default flat-bottom-down assumption.

    `needs_support` SHALL be derived from whether the geometry analysis emitted a
    (non-advisory) `overhang_exceeded` finding at the chosen pose, not guessed --
    see [Silica Tray support claim](TODO.md#silica-tray-support-claim): this field
    used to be hardcoded `False` regardless of `orientation["support_score"]` or
    any overhang finding, so the delivered recipe always claimed no support was
    needed even when the gate had just flagged one.
    """
    constraints = plan.get("constraints", {})
    wall_min = constraints.get("wall_min_mm", 1.2)
    nozzle = plan.get("nozzle_mm", 0.4)

    # Walls = ceil(wall_min / nozzle), at least 2
    walls = max(2, int((wall_min / nozzle) + 0.999))

    if orientation:
        # Present only when print_orientation.py was run with --speed-model and a
        # candidate matched (see toolpath-speed-advisor); absent otherwise, exactly
        # as before this capability existed.
        speed_fields = (
            {
                "estimated_print_time_s": orientation["total_time_s"],
                "speed_efficiency": orientation["speed_efficiency"],
                "stalled": orientation["stalled"],
            }
            if orientation.get("total_time_s") is not None
            else {}
        )
        orientation_field: dict | str = {
            "rotate": orientation.get("rotate"),
            "strength_score": orientation.get("strength_score"),
            "support_score": orientation.get("support_score"),
            "rationale": orientation.get("rationale"),
            **speed_fields,
        }
    else:
        orientation_field = "flat_bottom_down"

    recipe = {
        "material": plan.get("material", "PLA"),
        "printer": plan.get("printer", ""),
        "nozzle_mm": nozzle,
        "layer_height_mm": round(nozzle * 0.5, 2),
        "walls": walls,
        "top_bottom_layers": 4,
        "infill_percent": 20,
        "infill_pattern": "gyroid",
        "supports": needs_support,
        "support_threshold_deg": constraints.get("overhang_max_deg", 45),
        "orientation": orientation_field,
    }
    if geometry:
        recipe["estimated_weight_g"] = geometry.get("weight_g")
        recipe["volume_cm3"] = geometry.get("volume_cm3")

    return recipe


# ---------------------------------------------------------------------------
# Fix prompt
# ---------------------------------------------------------------------------


def _render_fix_prompt(script_path: str, issues: list[dict]) -> str:
    """Render a targeted fix prompt listing only failing checks."""
    errors = [i for i in issues if i["severity"] == "error"]
    warnings = [i for i in issues if i["severity"] == "warning"]

    lines = [
        "## Quality Gate Failed — Fix the following issues\n",
        "You are a CadQuery expert. Fix the script below to resolve these issues.",
        "Output only valid Python code. No explanation, no markdown fences.\n",
        "### Errors (must fix)\n",
    ]
    for e in errors:
        lines.append(f"- **[{e['source']}] {e['type']}**: {e['message']}")
        if e.get("hint"):
            lines.append(f"  Hint: {e['hint']}")
    if warnings:
        lines.append("\n### Warnings (fix if possible)\n")
        for w in warnings:
            lines.append(f"- **[{w['source']}] {w['type']}**: {w['message']}")
            if w.get("hint"):
                lines.append(f"  Hint: {w['hint']}")

    lines.append("\n### Script to fix\n")
    try:
        with open(script_path, encoding="utf-8") as f:
            code = f.read()
    except OSError:
        code = "(script not readable)"
    lines.append(f"```python\n{code}\n```")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Gate runner
# ---------------------------------------------------------------------------


def _fix_loop_model() -> str | None:
    """Read models.fix_loop from ./skill_config.json; None means no --model flag."""
    try:
        with open("skill_config.json", encoding="utf-8") as f:
            config = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    model = (config.get("models") or {}).get("fix_loop", "inline")
    return None if model == "inline" else model


def _call_claude(prompt_text: str) -> str:
    """Call claude -p with the prompt text, return generated code.

    `--tools ""` disables every tool (and, per its own contract, ignores project/local
    settings files) -- this call's only job is to transcode a prompt into Python text,
    so it needs no tool access. Without this, a script's exception message embedded
    verbatim in the prompt (see `_render_fix_prompt`) could steer a `claude -p` that
    inherits this project's `.claude/settings.local.json` -- including the Bash grants
    `init_permissions.py` seeds -- into running commands unattended.
    """
    cmd = ["claude", "-p", prompt_text, "--tools", ""]
    model = _fix_loop_model()
    if model:
        cmd += ["--model", model]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude -p failed (exit {result.returncode}):\n{result.stderr}")
    return result.stdout.strip()


def _extract_python(raw: str) -> str:
    import re

    fenced = re.search(r"```(?:python)?\n(.*?)```", raw, re.DOTALL)
    if fenced:
        return fenced.group(1).strip()
    return raw.strip()


def _run_plan_validation_stage(plan_path: str) -> list[dict]:
    """Validate BUILD_PLAN.json before any plan-consuming stage runs.

    Maps each `plan_validate.validate_plan` error string to a structured `plan_invalid`
    issue. An invalid plan would otherwise crash the kinematic stage (which raw-indexes
    plan fields) with a bare traceback; the gate skips that stage when this returns errors.
    """
    from plan import validate_plan

    return [
        {
            "source": "plan",
            "severity": "error",
            "type": "plan_invalid",
            "message": err,
            "hint": "Fix BUILD_PLAN.json so it passes plan validation (schema + cross-checks).",
        }
        for err in validate_plan(plan_path)
    ]


def _run_telemetry_stage(attempts_log: str) -> list[dict]:
    """Warn when the per-attempt telemetry log is absent, empty, or unparseable (once,
    outside the fix loop; advisory only -- geometry is unaffected either way).

    Folds by (part_id, attempt) first, so a base record plus its visual-review
    follow-up for the same attempt is not mistaken for two records when only one
    of them would parse (both parse here, but the fold keeps this consistent
    with every other consumer of attempts.jsonl).
    """
    from log import fold_attempts
    from units import make_issue

    if os.path.isfile(attempts_log):
        records = []
        with open(attempts_log, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        if fold_attempts(records):
            return []

    return [
        make_issue(
            "telemetry",
            "warning",
            "telemetry_missing",
            f"No attempt telemetry found at {attempts_log}.",
            "Attempts are logged by the telemetry.py PostToolUse hook (see init_permissions.py).",
        )
    ]


def _run_parameters_presence_stage(project_root: str) -> list[dict]:
    """Warn when Phase 1's dimension checkpoint recorded that real-world sourcing
    happened (a `phase1/dimensions_approved` line in build/journal.md) but
    parameters.py is missing or empty at the project root (advisory only -- geometry
    is unaffected either way)."""
    from units import make_issue

    journal_path = os.path.join(project_root, "build", "journal.md")
    if not os.path.isfile(journal_path):
        return []

    with open(journal_path, encoding="utf-8") as f:
        sourced = any(line.startswith("- phase1/dimensions_approved") for line in f)
    if not sourced:
        return []

    params_path = os.path.join(project_root, "parameters.py")
    if os.path.isfile(params_path) and os.path.getsize(params_path) > 0:
        return []

    return [
        make_issue(
            "parameters",
            "warning",
            "parameters_missing",
            f"No sourced-measurement provenance found at {params_path}.",
            "Write parameters.py per skill/phase1_requirements.md's Provenance write, at approval.",
        )
    ]


def _run_parameters_unresolved_stage(project_root: str) -> list[dict]:
    """Warn when parameters.py assigns the `-1` unresolved-dimension placeholder.

    parameters.py records the Phase 1 dimension table verbatim; a `-1` there means a
    `missing` row was approved despite the exit gate forbidding it. Advisory only --
    the geometry was built from some concrete value regardless.
    """
    import ast

    from units import make_issue

    params_path = os.path.join(project_root, "parameters.py")
    if not os.path.isfile(params_path):
        return []

    try:
        with open(params_path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=params_path)
    except SyntaxError:
        return []

    def _is_neg_one(node: ast.expr) -> bool:
        return (
            isinstance(node, ast.UnaryOp)
            and isinstance(node.op, ast.USub)
            and isinstance(node.operand, ast.Constant)
            and node.operand.value == 1
        )

    issues = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and _is_neg_one(node.value):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            for name in names:
                issues.append(
                    make_issue(
                        "parameters",
                        "warning",
                        "parameters_unresolved",
                        f"parameters.py assigns the -1 unresolved-dimension placeholder to {name}.",
                        "Resolve the dimension to a sourced value or record it as `assumed` "
                        "with a concrete value (skill/phase1_requirements.md exit checkpoint).",
                    )
                )
    return issues


def _run_kinematic_stage(plan: dict, stl_dir: str | None, parts_dir: str | None) -> list[dict]:
    """Run the kinematic range check when the plan declares any joints.

    Runs once (not inside the fix loop): the auto-fixer operates on a single
    script and cannot regenerate the separate part STLs a joint sweep compares.
    """
    if not plan.get("kinematics"):
        return []
    from kinematic_check import run_kinematic_check

    return run_kinematic_check(plan, stl_dir or ".", parts_dir=parts_dir)


def _run_stl_dir_stage(
    check_fn: Callable[..., list[dict]], plan: dict, stl_dir: str | None, parts_dir: str | None
) -> list[dict]:
    """Shared call shape for a whole-model check stage that takes `(plan, stl_dir,
    parts_dir=...)`, defaulting `stl_dir` to the current directory."""
    return check_fn(plan, stl_dir or ".", parts_dir=parts_dir)


def _run_plate_clearance_stage(
    plan: dict, stl_dir: str | None, parts_dir: str | None
) -> list[dict]:
    """Check co-plated unions keep a gap above one layer height (once, outside the fix loop).

    No-op unless some plate holds more than one union; the auto-fixer operates on a
    single script and cannot regenerate the separate per-union STLs the check compares.
    """
    from plate_clearance_check import run_plate_clearance_check

    return _run_stl_dir_stage(run_plate_clearance_check, plan, stl_dir, parts_dir)


def _run_keep_out_stage(plan: dict, stl_dir: str | None, parts_dir: str | None) -> list[dict]:
    """Check every declared keep-out zone against every foreign union (once, outside the
    fix loop). No-op unless the model export produced at least one zone STL.
    """
    from keep_out_check import run_keep_out_check

    return _run_stl_dir_stage(run_keep_out_check, plan, stl_dir, parts_dir)


def _run_edge_treatment_stage(plan: dict, script_path: str, orientation: dict | None) -> list[dict]:
    """Enforce the Chamfer / Fillet rule on this part's fillet/chamfer calls (once, outside
    the fix loop; advisory warnings only).

    Classifies each treated edge in the build frame, so it needs the per-union print
    orientation: reads `orientations.json` next to the script (the pipeline's
    `build/orientations.json`, keyed by union id) and falls back to the single
    `--orientation` result for this part's own union when that file is absent.
    """
    from edge_treatment_check import run_edge_treatment_check

    orientations: dict = {}
    orientations_path = os.path.join(
        os.path.dirname(os.path.abspath(script_path)), "orientations.json"
    )
    if os.path.isfile(orientations_path):
        with open(orientations_path, encoding="utf-8") as f:
            orientations = json.load(f)
    stem = os.path.splitext(os.path.basename(script_path))[0]
    if orientation and stem not in orientations:
        orientations[stem] = orientation

    return run_edge_treatment_check(plan, script_path, orientations)


def _run_toolpath_speed_stage(
    plan: dict, plan_path: str, script_path: str, stl_dir: str
) -> list[dict]:
    """Corner/crowding print-time advisory findings, in the build frame (once, outside
    the fix loop; always advisory).

    Reads `motion` from `printer_profile.json` next to the plan; a missing block is a
    stated skip, not an error. Passes the union's posed STL (from `stl_dir`, the
    assembled-pose STL every whole-model stage reads) so the layer-time/stall model can
    run alongside the corner model; a missing STL still yields the authored-corner-only
    findings.
    """
    from toolpath_speed import run_toolpath_speed_check
    from units import resolve_unions

    profile_path = os.path.join(os.path.dirname(os.path.abspath(plan_path)), "printer_profile.json")
    motion = None
    if os.path.isfile(profile_path):
        with open(profile_path, encoding="utf-8") as f:
            motion = json.load(f).get("motion")
    if not motion:
        return []

    stem = os.path.splitext(os.path.basename(script_path))[0]
    part = next((p for p in plan.get("parts", []) if p.get("id") == stem), None)
    stl_for_union: str | None = None
    if part is not None:
        try:
            from exporters import _load_result

            script_result = _load_result(script_path)
            unions = resolve_unions(part, script_result)
            if len(unions) == 1:
                stl_for_union = os.path.join(stl_dir, f"{unions[0][0]}.stl")
        except Exception as exc:
            print(
                f"toolpath-speed stage: could not resolve STL for {stem}: {exc}",
                file=sys.stderr,
            )
            stl_for_union = None

    check_result = run_toolpath_speed_check(plan, script_path, motion, stl_for_union)
    if check_result.get("status") != "ok":
        return []
    return check_result.get("issues", [])


def _run_feature_presence_stage(plan: dict, script_path: str) -> list[dict]:
    """Assert this part's declared-position interface features were actually built (once,
    outside the fix loop). `feature_absent` is blocking; drift/skips are advisory."""
    from feature_presence_check import run_feature_presence_check

    return run_feature_presence_check(plan, script_path)


def _is_hinge_associated_union(plan: dict, union_id: str) -> bool:
    """True when `union_id` is the moving_union of a revolute kinematics entry, or is
    named in a `pin_hinge` joints entry's members[].part (see hinge-guard-lint spec)."""
    from units import iter_kinematics_entries

    for entry in iter_kinematics_entries(plan.get("kinematics", [])):
        if entry.get("type") == "revolute" and entry.get("moving_union") == union_id:
            return True
    for joint in plan.get("joints", []):
        if joint.get("block") != "pin_hinge":
            continue
        if any(m.get("part") == union_id for m in joint.get("members", [])):
            return True
    return False


def _run_hinge_guard_stage(plan: dict, script_path: str) -> list[dict]:
    """Flag a hinge-associated union whose script builds a boolean union but never calls
    `verify_seated`/`verify_backed`/`pin_hinge` (once, outside the fix loop; advisory).

    Makes a pre-existing, hand-rolled revolute-hinge script's missing guard visible even
    though it was never re-authored under the guard's own rule (see hinge-guard-lint spec).
    """
    from units import iter_unions, make_issue

    stem = os.path.splitext(os.path.basename(script_path))[0]
    part = next((p for p in plan.get("parts", []) if p.get("id") == stem), None)
    if part is None:
        return []

    hinge_unions = sorted(
        uid
        for p, uid, _plate in iter_unions(plan)
        if p is part and _is_hinge_associated_union(plan, uid)
    )
    if not hinge_unions:
        return []

    try:
        with open(script_path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=script_path)
    except (OSError, SyntaxError):
        return []

    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    has_union_call = any(
        isinstance(c.func, ast.Attribute) and c.func.attr == "union" for c in calls
    )
    if not has_union_call:
        return []

    has_guard_call = any(
        (isinstance(c.func, ast.Name) and c.func.id in _HINGE_GUARD_CALL_NAMES)
        or (isinstance(c.func, ast.Attribute) and c.func.attr in _HINGE_GUARD_CALL_NAMES)
        for c in calls
    )
    if has_guard_call:
        return []

    return [
        make_issue(
            "hinge_guard",
            "warning",
            "hinge_guard_missing",
            f"Union(s) {', '.join(hinge_unions)} are hinge-associated (a revolute "
            "kinematics moving_union or a pin_hinge joints member) but the script has "
            "no call to verify_seated, verify_backed, or pin_hinge.",
            "Guard the hinge seating with cq_verify.verify_seated/verify_backed, or "
            "build the joint via blocks.joints.pin_hinge, per prompts/part.md rule 8.",
            unions=hinge_unions,
        )
    ]


def _run_gridfinity_stage(script_path: str) -> list[dict]:
    """Check Gridfinity conformance for a part built on the Gridfinity blocks (once,
    outside the fix loop).

    Auto-scoped: no-op unless the part script actually reaches for a Gridfinity block, so
    ordinary parts never pay for it and a Gridfinity part cannot silently skip it. Grid,
    height, foot-profile, and mating findings are blocking -- a part that misses the
    standard does not fit anything, which no amount of print tuning fixes.
    """
    try:
        with open(script_path, encoding="utf-8") as f:
            source = f.read()
    except OSError:
        return []
    if "gridfinity" not in source:
        return []

    from gridfinity_check import run_gridfinity_check

    issues, _ = run_gridfinity_check(script_path)
    return issues


def _run_cosmetic_slope_stage(plan: dict, script_path: str, orientation: dict | None) -> list[dict]:
    """Report up-facing cosmetic stair-step area for a visual_quality part (advisory).

    Surfaces the up-facing gentle-incline area the print-orientation step measured at the
    chosen pose (`cosmetic_slope_area_mm2` in the `--orientation` result). No-op unless the
    part's effective `optimize_for` is `visual_quality`; degrades to `check_skipped` when
    the orientation result (or that field) is unavailable, since the metric is only
    meaningful in the chosen print frame -- never measured in the authored frame.
    """
    from units import make_issue

    stem = os.path.splitext(os.path.basename(script_path))[0]
    part = next((p for p in plan.get("parts", []) if p.get("id") == stem), None)
    if part is None:
        return []
    effective = part.get("optimize_for") or plan.get("optimize_for", "strength")
    if effective != "visual_quality":
        return []

    if not orientation or "cosmetic_slope_area_mm2" not in orientation:
        return [
            make_issue(
                "cosmetic_slope",
                "warning",
                "check_skipped",
                "No print orientation available; cannot measure cosmetic slope area in the "
                "print frame.",
                "Pass --orientation (the part's print_orientation result) so the "
                "cosmetic-slope check can run.",
            )
        ]

    area = orientation["cosmetic_slope_area_mm2"]
    if area <= COSMETIC_SLOPE_MIN_AREA_MM2:
        return []
    return [
        make_issue(
            "cosmetic_slope",
            "warning",
            "cosmetic_slope",
            f"{area:.1f} mm2 of up-facing surface sits in the 5-45 deg stair-step band at the "
            "chosen print orientation -- visible layer stepping on a visual_quality part.",
            "Reshape the shallow slope to >= 45 deg or vertical, chamfer-step it, or lower "
            "layer height for the 20-45 deg range (see the FDM 'Cosmetic Slopes' guideline). "
            "The optimizer already picked the least-stepping orientation, so rotation alone "
            "will not remove it.",
            area_mm2=area,
        )
    ]


def _run_parameter_routing_stage(plan: dict, script_path: str) -> list[dict]:
    """Flag a part script edited outside the newest parameter-entry baseline's targets (advisory).

    `log.py request add --snapshot-scripts` records each part script's hash on a
    `parameter`-level entry. A script whose hash has since changed, whose part is not in
    the entry's `targets`, and that no `joints` entry links to a targeted part, was edited
    by hand instead of being routed through `joints`/`mate_chain.py`.
    """
    from freshness import script_hash
    from units import make_issue

    entry = max(
        (e for e in plan.get("request_log") or [] if e.get("script_baseline")),
        key=lambda e: e["ts"],
        default=None,
    )
    if entry is None:
        return []
    targeted = {t.split(".")[0] for t in entry.get("targets") or []}
    exempt = set(targeted)
    for joint in plan.get("joints") or []:
        members = {m["part"] for m in joint["members"]}
        if members & targeted:
            exempt |= members
    build_dir = os.path.dirname(os.path.abspath(script_path))
    issues = []
    for part_id, baseline in sorted(entry["script_baseline"].items()):
        path = os.path.join(build_dir, f"{part_id}.py")
        if part_id in exempt or not os.path.isfile(path) or script_hash(path) == baseline:
            continue
        issues.append(
            make_issue(
                "request_log",
                "warning",
                "routing_violation",
                f"{part_id}.py changed since the parameter-level request {entry['text']!r} "
                f"(targets: {', '.join(sorted(targeted)) or 'none'}), but {part_id} is neither "
                "targeted nor joint-linked to a target.",
                "Revert the edit and route the shared value through `joints`/`mate_chain.py` "
                "(a derived pose or shared block parameter), or, if the change is intended, "
                "add the part to the entry's targets.",
                part_id=part_id,
            )
        )
    return issues


def _analyze_3mf(model_3mf_path: str) -> list[dict]:
    """Check a 3MF deliverable for non-manifold edges as a slicer reads it.

    Loads the mesh without vertex welding (process=False) so unwelded
    tessellation seams surface here instead of being silently auto-repaired the
    way the STL/trimesh path does. An STL cannot use this check (it stores no
    shared vertices), so it is 3MF-only.
    """
    try:
        from exporters.threemf_multi import count_nonmanifold_edges
    except ImportError as exc:
        return [
            {
                "source": "geometry",
                "severity": "warning",
                "type": "check_skipped",
                "message": f"trimesh not available for 3MF manifold check: {exc}",
                "hint": "pip install trimesh numpy",
            }
        ]

    nonmanifold = count_nonmanifold_edges(model_3mf_path)
    if nonmanifold:
        return [
            {
                "source": "geometry",
                "severity": "error",
                "type": "non_manifold_edge",
                "message": (
                    f"3MF has {nonmanifold} non-manifold edges by vertex index "
                    "(a slicer will reject or repair it)"
                ),
                "hint": "Weld coincident tessellation vertices before writing the 3MF.",
            }
        ]
    return []


def run_gate(
    script_path: str,
    plan_path: str,
    stl_path: str | None = None,
    allow_fix: bool = False,
    stl_dir: str | None = None,
    model_3mf_path: str | None = None,
    orientation: dict | None = None,
    attempts_log: str | None = None,
) -> dict:
    """
    Run all quality checks against script_path.

    Returns a report dict:
        {
            "passed": bool,
            "issues": [...],
            "print_recipe": {...} | null,
            "fix_rounds": int,
        }
    """
    with open(plan_path, encoding="utf-8") as f:
        plan = json.load(f)
    overhang_deg = plan.get("constraints", {}).get("overhang_max_deg", 45)
    bridge_max_mm = plan.get("constraints", {}).get("bridge_max_mm", 10.0)
    if stl_dir is None:
        stl_dir = os.path.dirname(os.path.abspath(script_path))

    all_issues: list = []
    geometry = None
    fix_round = 0
    for fix_round in range(MAX_FIX_ROUNDS + 1):
        # ---- wrapper DFM ----
        wrapper_issues, discovered_stl, geometry, discovered_stls = _run_wrapper_check(
            script_path, plan
        )

        # An explicit `stl_path` override names one specific STL to analyze. Otherwise
        # analyze every union STL the wrapper produced -- a multi-union part's `stl`
        # (== stls[0]) would silently skip the geometry/overhang check for every other
        # union.
        effective_stls = (
            [stl_path]
            if stl_path
            else (discovered_stls or ([discovered_stl] if discovered_stl else []))
        )
        effective_stls = [p for p in effective_stls if p and os.path.exists(p)]

        # ---- geometry + overhang ----
        if effective_stls:
            rotate = (orientation or {}).get("rotate")
            stem = os.path.splitext(os.path.basename(script_path))[0]
            part = next((p for p in plan.get("parts", []) if p.get("id") == stem), None)
            clearance_zones = _clearance_opening_zones(plan, part, rotate) if part else []
            multi = len(effective_stls) > 1
            geo_issues = []
            for stl in effective_stls:
                uid = os.path.splitext(os.path.basename(stl))[0]
                stl_issues = _analyze_stl(stl, overhang_deg, rotate, clearance_zones, bridge_max_mm)
                if multi:
                    stl_issues = [
                        {**i, "union": uid, "message": f"[{uid}] {i['message']}"}
                        for i in stl_issues
                    ]
                geo_issues.extend(stl_issues)
        else:
            geo_issues = [
                {
                    "source": "geometry",
                    "severity": "warning",
                    "type": "check_skipped",
                    "message": "No STL available for geometry analysis",
                    "hint": "Run with --stl <path> or ensure wrapper produces an STL.",
                }
            ]

        all_issues = wrapper_issues + geo_issues
        errors = [i for i in all_issues if i["severity"] == "error"]

        if not errors:
            break

        if not allow_fix or fix_round >= MAX_FIX_ROUNDS:
            break

        # ---- fix round ----
        print(f"[QUALITY GATE] Round {fix_round + 1}: {len(errors)} error(s) — invoking fix...")
        fix_prompt = _render_fix_prompt(script_path, all_issues)
        try:
            raw = _call_claude(fix_prompt)
            code = _extract_python(raw)
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(code)
        except Exception as exc:
            print(f"[QUALITY GATE] Fix attempt failed: {exc}")
            break

    # ---- 3MF deliverable manifold check (index topology, as a slicer reads it) ----
    if model_3mf_path and os.path.exists(model_3mf_path):
        all_issues += _analyze_3mf(model_3mf_path)

    # ---- telemetry presence check (once, outside the fix loop; runs unconditionally --
    # even a malformed plan is exactly when telemetry matters) ----
    resolved_attempts_log = attempts_log or os.path.join(
        os.path.dirname(os.path.abspath(script_path)), "attempts.jsonl"
    )
    all_issues += _run_telemetry_stage(resolved_attempts_log)

    # ---- parameters.py provenance presence check (once, outside the fix loop) ----
    project_root = os.path.dirname(os.path.abspath(plan_path))
    all_issues += _run_parameters_presence_stage(project_root)
    all_issues += _run_parameters_unresolved_stage(project_root)

    # ---- plan validation (once, before any plan-consuming stage) ----
    # The wrapper/geometry stages above read the plan only through defaulted .get
    # lookups, so they are safe on a malformed plan; the kinematic stage raw-indexes
    # plan fields, so it must not run unless the plan validates.
    plan_issues = _run_plan_validation_stage(plan_path)
    all_issues += plan_issues

    # The kinematic and plate-clearance stages raw-index plan fields, so they run only
    # when the plan validates; a malformed plan fails on the structured plan_invalid error
    # instead of crashing those stages.
    if not any(i["severity"] == "error" for i in plan_issues):
        # Every part script lives alongside script_path, so that directory doubles as
        # parts_dir for the freshness check the three whole-model stages below run.
        parts_dir = os.path.dirname(os.path.abspath(script_path))
        # ---- kinematic range check (once, outside the fix loop) ----
        all_issues += _run_kinematic_stage(plan, stl_dir, parts_dir)
        # ---- plate clearance check (once, outside the fix loop) ----
        all_issues += _run_plate_clearance_stage(plan, stl_dir, parts_dir)
        # ---- keep-out zone check (once, outside the fix loop) ----
        all_issues += _run_keep_out_stage(plan, stl_dir, parts_dir)
        # ---- edge-treatment (chamfer/fillet) check (once, outside the fix loop) ----
        all_issues += _run_edge_treatment_stage(plan, script_path, orientation)
        # ---- toolpath-speed advisor (corner/crowding print-time; once, outside the fix loop) ----
        all_issues += _run_toolpath_speed_stage(plan, plan_path, script_path, stl_dir)
        # ---- feature-presence check (declared interfaces built; once, outside the fix loop) ----
        all_issues += _run_feature_presence_stage(plan, script_path)
        # ---- hinge-guard-lint (revolute-hinge script missing its seating guard; advisory) ----
        all_issues += _run_hinge_guard_stage(plan, script_path)
        # ---- cosmetic-slope check (visual_quality parts only, once, outside the fix loop) ----
        all_issues += _run_cosmetic_slope_stage(plan, script_path, orientation)
        # ---- Gridfinity conformance (Gridfinity parts only, once, outside the fix loop) ----
        all_issues += _run_gridfinity_stage(script_path)
        # ---- parameter-routing check (edit outside a parameter entry's targets; advisory) ----
        all_issues += _run_parameter_routing_stage(plan, script_path)
    for issue in all_issues:
        issue["action"] = _classify_action(issue)
    errors = [i for i in all_issues if i["severity"] == "error"]
    passed = not errors
    needs_support = any(
        i["type"] == "overhang_exceeded" and i["severity"] == "warning" for i in all_issues
    )

    return {
        "passed": passed,
        "issues": all_issues,
        "print_recipe": (
            _emit_print_recipe(plan, geometry, orientation, needs_support) if passed else None
        ),
        "fix_rounds": fix_round,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Run quality gate on a CAD model script")
    parser.add_argument("--script", required=True, help="Path to the part/union Python script")
    parser.add_argument("--plan", required=True, help="Path to BUILD_PLAN.json")
    parser.add_argument("--stl", default=None, help="Pre-exported STL path (optional)")
    parser.add_argument(
        "--model-3mf",
        default=None,
        help="3MF deliverable to check for non-manifold edges (optional)",
    )
    parser.add_argument(
        "--stl-dir",
        default=None,
        help="Directory holding every union's assembled STL for the kinematic/plate-"
        "clearance sweep (default: alongside --script). Pass this when STLs live in a "
        "separate stl/ directory rather than next to the part scripts.",
    )
    parser.add_argument(
        "--orientation",
        default=None,
        help="JSON file with this union's print_orientation.py result; drives the "
        "recipe's orientation field",
    )
    parser.add_argument(
        "--attempts-log",
        default=None,
        help="Path to the per-attempt telemetry log (default: attempts.jsonl alongside --script)",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Invoke claude to fix errors (cold-context, no plan/render/attempt history); "
        "default is report-only",
    )
    args = parser.parse_args()

    orientation = None
    if args.orientation:
        with open(args.orientation, encoding="utf-8") as f:
            orientation = json.load(f)

    report = run_gate(
        args.script,
        args.plan,
        stl_path=args.stl,
        allow_fix=args.fix,
        stl_dir=args.stl_dir,
        model_3mf_path=args.model_3mf,
        orientation=orientation,
        attempts_log=args.attempts_log,
    )

    print(json.dumps(report, indent=2))
    sys.exit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
