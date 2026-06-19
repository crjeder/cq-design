#!/usr/bin/env python3
"""Validate BUILD_PLAN.json against its schema and cross-check block names.

Usage:
    python3 plan_validate.py BUILD_PLAN.json
    python3 plan_validate.py BUILD_PLAN.json --inventory blocks/inventory.json

Exit codes: 0 valid, 1 invalid.
"""

import argparse
import json
import os
import sys
from typing import Any

_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "build_plan_schema.json")
_INVENTORY_PATH = os.path.join(os.path.dirname(__file__), "blocks", "inventory.json")


def _load_json(path: str) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate_plan(plan_path: str, inventory_path: str = _INVENTORY_PATH) -> list[str]:
    """Validate a BUILD_PLAN.json file. Returns list of error strings (empty = OK).

    plan_path is used as-is (resolved relative to the caller's cwd, not this file's
    location). Schema and inventory paths are always resolved relative to this file.
    """
    errors = []

    try:
        plan = _load_json(plan_path)
    except (OSError, json.JSONDecodeError) as e:
        return [f"Cannot load plan: {e}"]

    # JSON Schema validation via jsonschema if available, else manual checks
    try:
        import jsonschema  # type: ignore[import-untyped]

        schema = _load_json(_SCHEMA_PATH)
        validator = jsonschema.Draft7Validator(schema)
        for err in sorted(validator.iter_errors(plan), key=lambda e: e.path):
            path = " -> ".join(str(p) for p in err.absolute_path) or "(root)"
            errors.append(f"Schema error at {path}: {err.message}")
    except ImportError:
        # Fallback: manual required-field checks
        errors.extend(_manual_check(plan))

    if errors:
        return errors

    # Cross-check block names against inventory
    try:
        from blocks.validate import get_block_names

        valid_blocks = get_block_names(inventory_path)
    except Exception as e:
        errors.append(f"Cannot load block inventory: {e}")
        return errors

    for part in plan.get("parts", []):
        pid = part.get("id", "(unknown)")
        for block in part.get("blocks_needed", []):
            block_name = block if isinstance(block, str) else block.get("name")
            if block_name not in valid_blocks:
                errors.append(
                    f"Part '{pid}': unknown block '{block_name}' "
                    f"(not in inventory). Available: {sorted(valid_blocks)}"
                )

    errors.extend(_check_placements(plan))
    errors.extend(_check_loads(plan))
    errors.extend(_check_kinematics(plan, inventory_path))

    return errors


def _check_loads(plan: dict[str, Any]) -> list[str]:
    """Validate each part's optional `load` hint: the direction must be non-zero.

    Shape (3-vector) is enforced by the schema; a zero vector has no orientation
    and cannot drive strength scoring, so it is rejected here.
    """
    errors = []
    for part in plan.get("parts", []):
        load = part.get("load")
        if not load:
            continue
        direction = load.get("dir", [])
        if len(direction) == 3 and not any(abs(c) > 0 for c in direction):
            pid = part.get("id", "(unknown)")
            errors.append(f"Part '{pid}': load.dir must be a non-zero direction")
    return errors


def _check_placements(plan: dict[str, Any]) -> list[str]:
    """Validate each part's optional `placement` (always-run, no jsonschema needed).

    Rotation axes must be X/Y/Z. This guards the assembled-frame placement the model
    export and kinematic check consume.
    """
    errors = []
    for part in plan.get("parts", []):
        pid = part.get("id", "(unknown)")
        placement = part.get("placement")
        if not placement:
            continue
        for step in placement.get("rotate", []):
            axis = step.get("axis")
            if axis not in ("X", "Y", "Z"):
                errors.append(
                    f"Part '{pid}': placement rotate axis '{axis}' is not X, Y, or Z"
                )
    return errors


def _check_kinematics(plan: dict[str, Any], inventory_path: str) -> list[str]:
    """Cross-check kinematics entries against parts and inventory dof descriptors.

    Each entry's `moving_union` must reference an existing part id, the `block` must
    exist and carry a `dof`, and the entry `unit` must match the block's `dof.unit`.
    """
    kinematics = plan.get("kinematics", [])
    if not kinematics:
        return []

    from blocks.validate import get_block

    part_ids = {part.get("id") for part in plan.get("parts", [])}
    errors = []
    for entry in kinematics:
        jid = entry.get("joint_id", "(unknown)")
        ref = entry.get("moving_union")
        if ref not in part_ids:
            errors.append(f"Kinematics '{jid}': moving_union '{ref}' is not a part id")
        block_name = entry.get("block")
        block = get_block(block_name, inventory_path)
        if block is None:
            errors.append(
                f"Kinematics '{jid}': unknown block '{block_name}' (not in inventory)"
            )
            continue
        dof = block.get("dof")
        if dof is None:
            errors.append(
                f"Kinematics '{jid}': block '{block_name}' has no 'dof' descriptor"
            )
            continue
        if entry.get("unit") != dof.get("unit"):
            errors.append(
                f"Kinematics '{jid}': unit '{entry.get('unit')}' does not match "
                f"block '{block_name}' dof.unit '{dof.get('unit')}'"
            )

    return errors


def check_block_thinness(plan: dict[str, Any]) -> list[str]:
    """Flag blocks whose smallest declared extent is below the wall minimum.

    Script-level thin-interface check: runs on the plan before any code or mesh,
    with full attribution to the part, block, and axis. Returns advisory findings
    (not hard validation errors). Blocks without declared `extents_mm` are skipped.
    """
    findings = []
    wall_min = plan.get("constraints", {}).get("wall_min_mm")
    if not wall_min:
        return findings

    for part in plan.get("parts", []):
        pid = part.get("id", "(unknown)")
        for block in part.get("blocks_needed", []):
            if not isinstance(block, dict):
                continue
            extents = block.get("extents_mm")
            if not extents:
                continue
            smallest = min(extents)
            if smallest < wall_min:
                axis = ["x", "y", "z"][extents.index(smallest)]
                findings.append(
                    f"Part '{pid}' block '{block.get('name')}': {axis}-extent "
                    f"{smallest} mm is below wall_min {wall_min} mm; increase this "
                    f"block dimension or the part will have an unprintable thin wall"
                )

    return findings


def _manual_check(plan: dict[str, Any]) -> list[str]:
    """Minimal required-field check used when jsonschema is not installed."""
    errors = []
    for field in (
        "schema_version",
        "intent",
        "printer",
        "material",
        "nozzle_mm",
        "parts",
        "constraints",
    ):
        if field not in plan:
            errors.append(f"Missing required field: '{field}'")

    for i, part in enumerate(plan.get("parts", [])):
        tag = f"parts[{i}] id={part.get('id', '?')!r}"
        for field in (
            "id",
            "description",
            "dimensions",
            "interfaces",
            "blocks_needed",
        ):
            if field not in part:
                errors.append(f"{tag}: missing required field '{field}'")
        dims = part.get("dimensions", {})
        for d in ("w_mm", "d_mm", "h_mm"):
            if d not in dims:
                errors.append(f"{tag}: dimensions missing '{d}'")

    if not plan.get("parts"):
        errors.append("'parts' array must have at least one entry")

    return errors


def main():
    parser = argparse.ArgumentParser(description="Validate BUILD_PLAN.json")
    parser.add_argument("plan", help="Path to BUILD_PLAN.json")
    parser.add_argument(
        "--inventory", default=_INVENTORY_PATH, help="Path to blocks/inventory.json"
    )
    args = parser.parse_args()

    errors = validate_plan(args.plan, args.inventory)
    if errors:
        print(f"BUILD_PLAN validation FAILED ({len(errors)} error(s)):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    plan = _load_json(args.plan)
    n_parts = len(plan.get("parts", []))
    print(
        f"BUILD_PLAN OK — {n_parts} part(s), schema_version={plan.get('schema_version')}"
    )

    findings = check_block_thinness(plan)
    if findings:
        print(f"\nThin-block findings ({len(findings)}):")
        for f in findings:
            print(f"  - {f}")


if __name__ == "__main__":
    main()
