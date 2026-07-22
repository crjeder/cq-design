#!/usr/bin/env python3
"""Reconcile a hand-edited part script's PARAMETERS block back into BUILD_PLAN.json.

Usage:
    python3 import_params.py <part_script.py> --part <id> [--plan BUILD_PLAN.json] [--write]

Default is a dry-run diff. --write re-validates the updated plan against the schema
(via plan_validate) before persisting, refusing to write an invalid plan.

Exit codes: 0 success (dry-run or write), 1 on parse/reconcile/validation error.
"""

import argparse
import ast
import copy
import json
import os
import sys
import tempfile
from typing import Any

_DIM_NAME_MAP = {"width": "w_mm", "depth": "d_mm", "height": "h_mm"}

Number = int | float


def parse_parameters(script_path: str) -> dict[str, Any]:
    """Extract module-level numeric-literal assignments from a part script via AST.

    Never imports or executes the script. Accepts a value only when it is an
    int/float (bool excluded) or a tuple/list of such. Returns {} on an unparseable
    file; caller distinguishes via a separate existence/syntax check if needed.
    """
    with open(script_path, encoding="utf-8") as f:
        source = f.read()
    tree = ast.parse(source, filename=script_path)

    params: dict[str, Any] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        name = node.targets[0].id
        try:
            value = ast.literal_eval(node.value)
        except (ValueError, SyntaxError):
            continue
        if _is_numeric(value):
            params[name] = value
    return params


def _is_numeric(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int | float):
        return True
    if isinstance(value, tuple | list):
        return len(value) > 0 and all(_is_numeric(v) for v in value)
    return False


def reconcile(parsed: dict[str, Any], plan: dict[str, Any], part_id: str) -> dict[str, Any]:
    """Diff parsed parameters against a plan part's dimensions.

    Returns {"changed": [...], "unchanged": [...], "unmapped": [...]}. Raises
    KeyError if part_id is not present in plan["parts"] -- caller maps to a
    structured error.
    """
    part = next((p for p in plan.get("parts", []) if p.get("id") == part_id), None)
    if part is None:
        raise KeyError(part_id)

    dimensions = part.get("dimensions", {})
    changed = []
    unchanged = []
    unmapped = []

    for name, value in parsed.items():
        field = _DIM_NAME_MAP.get(name)
        if field is None:
            unmapped.append(name)
            continue
        current = dimensions.get(field)
        if current == value:
            unchanged.append(field)
        else:
            changed.append({"field": field, "from": current, "to": value})

    return {"changed": changed, "unchanged": unchanged, "unmapped": unmapped}


def _apply_changes(
    plan: dict[str, Any], part_id: str, changed: list[dict[str, Any]]
) -> dict[str, Any]:
    """Return a deep copy of plan with `changed` dimension diffs applied to part_id."""
    updated = copy.deepcopy(plan)
    part = next(p for p in updated["parts"] if p["id"] == part_id)
    for entry in changed:
        part["dimensions"][entry["field"]] = entry["to"]
    return updated


def run(script_path: str, part_id: str, plan_path: str, write: bool) -> dict[str, Any]:
    """Run the full import-params flow. Returns the report dict (never raises)."""
    report: dict[str, Any] = {
        "part": part_id,
        "changed": [],
        "unchanged": [],
        "unmapped": [],
        "written": False,
        "errors": [],
    }

    try:
        parsed = parse_parameters(script_path)
    except OSError as e:
        report["errors"].append(f"Cannot read script '{script_path}': {e}")
        return report
    except SyntaxError as e:
        report["errors"].append(f"Cannot parse script '{script_path}' as Python: {e}")
        return report

    try:
        with open(plan_path, encoding="utf-8") as f:
            plan = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        report["errors"].append(f"Cannot load plan '{plan_path}': {e}")
        return report

    try:
        diff = reconcile(parsed, plan, part_id)
    except KeyError:
        report["errors"].append(f"Part '{part_id}' is not present in plan '{plan_path}'")
        return report

    report["changed"] = diff["changed"]
    report["unchanged"] = diff["unchanged"]
    report["unmapped"] = diff["unmapped"]

    if not write or not diff["changed"]:
        return report

    updated_plan = _apply_changes(plan, part_id, diff["changed"])

    from plan_validate import validate_plan

    fd, tmp_path = tempfile.mkstemp(suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(updated_plan, f)
        validation_errors = validate_plan(tmp_path)
    finally:
        os.remove(tmp_path)

    if validation_errors:
        report["errors"] = validation_errors
        return report

    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(updated_plan, f, indent=2, ensure_ascii=False)
        f.write("\n")
    report["written"] = True
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reconcile a part script's PARAMETERS block into BUILD_PLAN.json"
    )
    parser.add_argument("script", help="Path to the part .py script")
    parser.add_argument("--part", required=True, help="Part id in the plan")
    parser.add_argument("--plan", default="BUILD_PLAN.json", help="Path to BUILD_PLAN.json")
    parser.add_argument("--write", action="store_true", help="Persist the reconciled plan")
    args = parser.parse_args()

    report = run(args.script, args.part, args.plan, args.write)
    print(json.dumps(report, indent=2))
    sys.exit(1 if report["errors"] else 0)


if __name__ == "__main__":
    main()
