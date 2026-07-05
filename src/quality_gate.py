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

Aggregates issues with severity (error/warning), generates a targeted fix prompt
if any errors are found, invokes `claude -p` for up to MAX_FIX_ROUNDS, then
re-runs the gate. On a clean pass emits a print recipe JSON.

Usage:
    python3 quality_gate.py --script build/body.py --plan BUILD_PLAN.json
    python3 quality_gate.py --script build/body.py --plan BUILD_PLAN.json --stl build/body.stl
    python3 quality_gate.py --script build/body.py --plan BUILD_PLAN.json --no-fix
"""

import argparse
import json
import os
import subprocess
import sys

SKILL_ROOT = os.path.dirname(os.path.abspath(__file__))
MAX_FIX_ROUNDS = 2

# ---------------------------------------------------------------------------
# DFM check via wrapper
# ---------------------------------------------------------------------------


def _run_wrapper_check(script_path: str, plan: dict) -> tuple[list[dict], str | None, dict | None]:
    """Run run_cadquery_model.py DFM checks; return list of issue dicts."""
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
        )

    issues = []
    for err in data.get("errors", []):
        severity = (
            "error"
            if err["type"]
            in (
                "non_manifold_edge",
                "non_watertight",
                "occ_exception",
                "dimension_mismatch",
            )
            else "warning"
        )
        issues.append(
            {
                "source": "wrapper",
                "severity": severity,
                "type": err["type"],
                "message": err["message"],
                "hint": err.get("hint", ""),
            }
        )
    # Expose STL path for downstream MCP checks
    stl_path: str | None = data.get("stl")
    return issues, stl_path, data.get("geometry")


# ---------------------------------------------------------------------------
# Geometry + overhang analysis (trimesh, in-process)
# ---------------------------------------------------------------------------


def _analyze_stl(stl_path: str, overhang_deg: float) -> list[dict]:
    """Analyze STL geometry and overhangs using trimesh. Returns issues."""
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

    metrics = overhang_metrics(tm, overhang_deg)
    if metrics["worst_angle_deg"] is not None:
        overhang_area = metrics["overhang_area_mm2"]
        worst_angle = metrics["worst_angle_deg"]
        issues.append(
            {
                "source": "geometry",
                "severity": "warning",
                "type": "overhang_exceeded",
                "message": (
                    f"Worst overhang {worst_angle:.1f}° exceeds limit "
                    f"{overhang_deg}° over {overhang_area:.1f} mm² of faces"
                ),
                "hint": "Add chamfers or redesign overhanging features.",
                "overhang_area_mm2": overhang_area,
                "worst_angle_deg": worst_angle,
                "location_xyz_mm": metrics["worst_location_xyz_mm"],
            }
        )

    return issues


# ---------------------------------------------------------------------------
# Print recipe
# ---------------------------------------------------------------------------


def _emit_print_recipe(plan: dict, geometry: dict | None, orientation: dict | None = None) -> dict:
    """Build a recommended print recipe from plan constraints + geometry.

    When `orientation` (a print_orientation.py result) is supplied, the recipe's
    `orientation` field carries the computed rotation and its rationale; otherwise
    it falls back to the default flat-bottom-down assumption.
    """
    constraints = plan.get("constraints", {})
    wall_min = constraints.get("wall_min_mm", 1.2)
    nozzle = plan.get("nozzle_mm", 0.4)

    # Walls = ceil(wall_min / nozzle), at least 2
    walls = max(2, int((wall_min / nozzle) + 0.999))

    if orientation:
        orientation_field: dict | str = {
            "rotate": orientation.get("rotate"),
            "strength_score": orientation.get("strength_score"),
            "support_score": orientation.get("support_score"),
            "rationale": orientation.get("rationale"),
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
        "supports": False,
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


def _render_fix_prompt(script_path: str, issues: list[dict], prompt_template: str) -> str:
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


def _call_claude(prompt_text: str) -> str:
    """Call claude -p with the prompt text, return generated code."""
    result = subprocess.run(
        ["claude", "-p", prompt_text],
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
    from plan_validate import validate_plan

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


def _run_kinematic_stage(plan: dict, stl_dir: str | None) -> list[dict]:
    """Run the kinematic range check when the plan declares any joints.

    Runs once (not inside the fix loop): the auto-fixer operates on a single
    script and cannot regenerate the separate part STLs a joint sweep compares.
    """
    if not plan.get("kinematics"):
        return []
    from kinematic_check import run_kinematic_check

    return run_kinematic_check(plan, stl_dir or ".")


def _run_plate_clearance_stage(plan: dict, stl_dir: str | None) -> list[dict]:
    """Check co-plated unions keep a gap above one layer height (once, outside the fix loop).

    No-op unless some plate holds more than one union; the auto-fixer operates on a
    single script and cannot regenerate the separate per-union STLs the check compares.
    """
    from plate_clearance_check import run_plate_clearance_check

    return run_plate_clearance_check(plan, stl_dir or ".")


def _run_keep_out_stage(plan: dict, stl_dir: str | None) -> list[dict]:
    """Check every declared keep-out zone against every foreign union (once, outside the
    fix loop). No-op unless the model export produced at least one zone STL.
    """
    from keep_out_check import run_keep_out_check

    return run_keep_out_check(plan, stl_dir or ".")


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
    allow_fix: bool = True,
    stl_dir: str | None = None,
    model_3mf_path: str | None = None,
    orientation: dict | None = None,
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
    if stl_dir is None:
        stl_dir = os.path.dirname(os.path.abspath(script_path))

    all_issues: list = []
    geometry = None
    fix_round = 0
    for fix_round in range(MAX_FIX_ROUNDS + 1):
        # ---- wrapper DFM ----
        wrapper_issues, discovered_stl, geometry = _run_wrapper_check(script_path, plan)

        effective_stl = stl_path or discovered_stl

        # ---- geometry + overhang ----
        if effective_stl and os.path.exists(effective_stl):
            geo_issues = _analyze_stl(effective_stl, overhang_deg)
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
        fix_prompt = _render_fix_prompt(script_path, all_issues, "")
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
        # ---- kinematic range check (once, outside the fix loop) ----
        all_issues += _run_kinematic_stage(plan, stl_dir)
        # ---- plate clearance check (once, outside the fix loop) ----
        all_issues += _run_plate_clearance_stage(plan, stl_dir)
        # ---- keep-out zone check (once, outside the fix loop) ----
        all_issues += _run_keep_out_stage(plan, stl_dir)
    errors = [i for i in all_issues if i["severity"] == "error"]
    passed = not errors

    return {
        "passed": passed,
        "issues": all_issues,
        "print_recipe": _emit_print_recipe(plan, geometry, orientation) if passed else None,
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
        "--no-fix",
        action="store_true",
        help="Report issues only; do not invoke claude for fixes",
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
        allow_fix=not args.no_fix,
        stl_dir=args.stl_dir,
        model_3mf_path=args.model_3mf,
        orientation=orientation,
    )

    print(json.dumps(report, indent=2))
    sys.exit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
