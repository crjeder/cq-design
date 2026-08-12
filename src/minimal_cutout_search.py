#!/usr/bin/env python3
"""Bisect a part-script parameter to find the minimal clearance-satisfying value
against a kinematics entry's required range of motion.

Answers "how big does this clearance feature need to be for the joint to reach its
full required range?" -- the search a designer otherwise runs by hand (edit a
parameter, rerun, read the collision finding, repeat). `run_kinematic_check`
(`kinematic_check.py`) is reused unchanged as the pass/fail oracle at each
candidate; this module only drives the bisection loop and the geometry
regeneration between steps.

Precondition: the searched parameter must be monotonic with clearance across
[--lo, --hi] (increasing the value must not make the joint's sweep worse). The
tool checks this only at the two bounds (`--lo` must fail, `--hi` must pass) and
does not characterize the interior of the range.

Usage:
    python3 minimal_cutout_search.py arm.py --param CLEARANCE_MM --plan BUILD_PLAN.json \
        --part arm --joint-id arm_joint --stl-dir build/stl --lo 0 --hi 9
"""

import argparse
import ast
import json
import os
import shutil
import sys
import types
from typing import Any

import cadquery as cq

from kinematic_check import run_kinematic_check
from mate_chain import compute_mate_poses
from model_export import _pose_union
from units import load_plan, resolve_unions

_TMP_SUFFIX = "__minimal_cutout_search_tmp"


class BoundsError(Exception):
    """--lo/--hi do not bracket a pass/fail boundary for the named joint."""


def _exec_script(script_path: str) -> Any:
    """Execute a part script fresh from disk and return its `result`.

    Unlike `exporters._load_result` (ordinary import machinery, which reads/writes a
    `__pycache__` .pyc keyed on mtime+size), this compiles and execs the source
    directly on every call. The search loop rewrites the same script path many times
    per second -- faster than the pyc cache's mtime/size check reliably invalidates on
    this filesystem -- so the import path was silently re-executing stale bytecode from
    the previous candidate.
    """
    script_path = os.path.abspath(script_path)
    script_dir = os.path.dirname(script_path)
    src_dir = os.path.dirname(os.path.abspath(__file__))
    inserted = [p for p in (script_dir, src_dir) if p not in sys.path]
    for p in inserted:
        sys.path.insert(0, p)
    old_cwd = os.getcwd()
    try:
        os.chdir(script_dir)
        with open(script_path, encoding="utf-8") as f:
            source = f.read()
        module = types.ModuleType(os.path.splitext(os.path.basename(script_path))[0])
        module.__file__ = script_path
        exec(compile(source, script_path, "exec"), module.__dict__)
        if not hasattr(module, "result"):
            raise ValueError(f"Script '{script_path}' does not define a 'result' variable")
        return module.result
    finally:
        os.chdir(old_cwd)
        for p in inserted:
            sys.path.remove(p)


def _find_assignment(tree: ast.Module, name: str) -> ast.Assign | None:
    """Module-level `name = <numeric literal>` assignment, the same convention
    `import_params.parse_parameters` uses. Returns None if not found or not a
    scalar int/float literal (bool and tuple/list excluded)."""
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        if node.targets[0].id != name:
            continue
        try:
            value = ast.literal_eval(node.value)
        except (ValueError, SyntaxError):
            continue
        if isinstance(value, bool) or not isinstance(value, int | float):
            continue
        return node
    return None


def read_parameter_value(script_path: str, name: str) -> float:
    """Current value of a module-level numeric parameter in a part script."""
    with open(script_path, encoding="utf-8") as f:
        source = f.read()
    node = _find_assignment(ast.parse(source, filename=script_path), name)
    if node is None:
        raise ValueError(
            f"'{name}' is not a module-level numeric-literal assignment in {script_path}"
        )
    return float(ast.literal_eval(node.value))


def _format_number(value: float) -> str:
    rounded = round(value, 6)
    return str(int(rounded)) if rounded.is_integer() else repr(rounded)


def set_parameter_value(script_path: str, name: str, value: float) -> None:
    """Rewrite only the literal on a module-level numeric assignment's line, preserving
    the rest of the line (comments, alignment)."""
    with open(script_path, encoding="utf-8") as f:
        lines = f.readlines()
    node = _find_assignment(ast.parse("".join(lines), filename=script_path), name)
    if node is None:
        raise ValueError(
            f"'{name}' is not a module-level numeric-literal assignment in {script_path}"
        )
    v = node.value
    line_idx = v.lineno - 1
    line = lines[line_idx]
    lines[line_idx] = line[: v.col_offset] + _format_number(value) + line[v.end_col_offset :]
    with open(script_path, "w", encoding="utf-8") as f:
        f.writelines(lines)


def _export_part_stls(script_path: str, plan: dict, part_id: str, stl_dir: str) -> list[str]:
    """Regenerate the assembled-frame STL(s) for one part's union(s), posed the same way
    `model_export.export_model` poses them (`placement`, or a `joints` mate-chain pose when
    present) -- so the result matches what `run_kinematic_check` expects in `stl_dir`. Every
    other union's STL already in `stl_dir` is left untouched."""
    part = next(p for p in plan["parts"] if p["id"] == part_id)
    result = _exec_script(script_path)
    mate_pose = compute_mate_poses(plan).get(part_id)

    os.makedirs(stl_dir, exist_ok=True)
    paths = []
    for uid, wp in resolve_unions(part, result):
        posed = _pose_union(wp, part, mate_pose)
        out_path = os.path.join(stl_dir, f"{uid}.stl")
        cq.exporters.export(posed, out_path)
        paths.append(out_path)
    return paths


def _joint_has_issue(issues: list[dict], joint_id: str) -> bool:
    return any(i.get("joint_id") == joint_id for i in issues)


def evaluate_candidate(
    script_path: str,
    part_id: str,
    plan: dict,
    stl_dir: str,
    joint_id: str,
    param: str,
    value: float,
) -> bool:
    """Apply a candidate parameter value, regenerate that part's STL, and re-run the
    sweep. Returns True (passes) when the named joint achieves its full required range."""
    set_parameter_value(script_path, param, value)
    _export_part_stls(script_path, plan, part_id, stl_dir)
    issues = run_kinematic_check(plan, stl_dir)
    return not _joint_has_issue(issues, joint_id)


def _temp_copy(script_path: str) -> str:
    stem, ext = os.path.splitext(script_path)
    tmp_path = f"{stem}{_TMP_SUFFIX}{ext}"
    shutil.copyfile(script_path, tmp_path)
    return tmp_path


def search(
    script_path: str,
    part_id: str,
    plan: dict,
    stl_dir: str,
    joint_id: str,
    param: str,
    lo: float,
    hi: float,
    tolerance_mm: float = 0.1,
) -> float:
    """Bisect between `lo` (must fail the sweep) and `hi` (must pass) until the bracket is
    `tolerance_mm` or narrower. Returns the converged passing value (`hi`).

    Evaluates candidates on a throwaway copy of `script_path`; the original file is never
    written by this function (see `main`'s `--apply` handling for the only write-back path).
    Raises `BoundsError` if either bound violates the pass/fail precondition.
    """
    tmp_script = _temp_copy(script_path)
    try:
        if evaluate_candidate(tmp_script, part_id, plan, stl_dir, joint_id, param, lo):
            raise BoundsError(
                f"--lo {lo} already clears joint '{joint_id}'; --lo must be a value "
                "that still collides"
            )
        if not evaluate_candidate(tmp_script, part_id, plan, stl_dir, joint_id, param, hi):
            raise BoundsError(
                f"--hi {hi} still collides for joint '{joint_id}'; --hi must be a value that clears"
            )

        while hi - lo > tolerance_mm:
            mid = (lo + hi) / 2.0
            if evaluate_candidate(tmp_script, part_id, plan, stl_dir, joint_id, param, mid):
                hi = mid
            else:
                lo = mid
        return hi
    finally:
        os.remove(tmp_script)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bisect a part-script parameter to the minimal value that clears a "
        "kinematics entry's required range of motion"
    )
    parser.add_argument("script", help="Path to the part .py script")
    parser.add_argument("--param", required=True, help="Module-level numeric parameter name")
    parser.add_argument("--plan", required=True, help="Path to BUILD_PLAN.json")
    parser.add_argument("--part", required=True, help="Part id (in the plan) owning the script")
    parser.add_argument(
        "--joint-id", required=True, help="kinematics entry joint_id to search against"
    )
    parser.add_argument(
        "--stl-dir", required=True, help="Directory of exported <union_id>.stl files"
    )
    parser.add_argument("--lo", type=float, required=True, help="Bound that must still collide")
    parser.add_argument("--hi", type=float, required=True, help="Bound that must already clear")
    parser.add_argument(
        "--tolerance-mm", type=float, default=0.1, help="Bisection convergence width (default 0.1)"
    )
    parser.add_argument(
        "--margin-mm", type=float, default=0.2, help="Safety margin added to the converged value"
    )
    parser.add_argument(
        "--apply", action="store_true", help="Write the recommended value back into the script"
    )
    args = parser.parse_args()

    plan = load_plan(args.plan)
    try:
        converged = search(
            args.script,
            args.part,
            plan,
            args.stl_dir,
            args.joint_id,
            args.param,
            args.lo,
            args.hi,
            args.tolerance_mm,
        )
    except BoundsError as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

    recommended = converged + args.margin_mm
    result = {
        "converged": converged,
        "recommended": recommended,
        "margin_mm": args.margin_mm,
        "applied": False,
    }
    if args.apply:
        set_parameter_value(args.script, args.param, recommended)
        result["applied"] = True

    print(json.dumps(result, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
