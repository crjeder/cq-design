"""Validate blocks/inventory.json against its schema.

Used by plan_validate.py to check that block names in BUILD_PLAN
exist in the inventory.
"""

import json
import os
import sys
from typing import Any

_INVENTORY_PATH = os.path.join(os.path.dirname(__file__), "inventory.json")
_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "inventory_schema.json")

_VALID_INTERFACE_TYPES = frozenset(
    {
        "face_mount",
        "screw_hole",
        "snap_hook",
        "snap_socket",
        "axis",
        "pin",
        "socket",
        "slot",
        "port_cutout",
        "sliding_interface",
        "nut_trap",
        "hinge_axis",
        "ball",
        "ball_socket",
        "finger",
        "mortise",
        "tenon",
        "dowel",
        "seam",
        "union",
    }
)

_VALID_MOTION = frozenset({"rigid", "hinge", "ball"})


def load_inventory(path: str = _INVENTORY_PATH) -> list[Any]:
    """Load and return the block inventory list. Raises ValueError on error."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("inventory.json must be a JSON array")
    return data


def validate_inventory(inventory: list[Any]) -> list[str]:
    """Validate inventory entries. Returns list of error strings (empty = OK)."""
    errors = []
    seen_names = set()

    for i, entry in enumerate(inventory):
        tag = f"block[{i}] {entry.get('name', '(no name)')!r}"

        for field in (
            "name",
            "module",
            "function",
            "use",
            "params",
            "dimensions",
            "interfaces",
        ):
            if field not in entry:
                errors.append(f"{tag}: missing required field '{field}'")

        name = entry.get("name", "")
        if name in seen_names:
            errors.append(f"{tag}: duplicate name '{name}'")
        seen_names.add(name)

        if "motion" in entry and entry["motion"] not in _VALID_MOTION:
            allowed = ", ".join(sorted(_VALID_MOTION))
            errors.append(
                f"{tag}: motion '{entry['motion']}' not in allowed vocabulary ({allowed})"
            )
        if "reversible" in entry and not isinstance(entry["reversible"], bool):
            errors.append(f"{tag}: reversible must be a boolean")
        if "carries" in entry and not (
            isinstance(entry["carries"], list) and all(isinstance(c, str) for c in entry["carries"])
        ):
            errors.append(f"{tag}: carries must be a list of strings")

        for iface in entry.get("interfaces", []):
            itype = iface.get("type", "")
            if itype not in _VALID_INTERFACE_TYPES:
                allowed = ", ".join(sorted(_VALID_INTERFACE_TYPES))
                errors.append(
                    f"{tag}: interface type '{itype}' not in allowed vocabulary ({allowed})"
                )
            if "orientation" not in iface:
                errors.append(f"{tag}: interface missing 'orientation'")
            if "origin" not in iface or len(iface.get("origin", [])) != 3:
                errors.append(f"{tag}: interface missing or invalid 'origin' (must be [x,y,z])")

    return errors


def get_block_names(path: str = _INVENTORY_PATH) -> set[str]:
    """Return the set of valid block names from inventory."""
    inventory = load_inventory(path)
    return {entry["name"] for entry in inventory}


def get_block(name: str, path: str = _INVENTORY_PATH) -> dict[str, Any] | None:
    """Return a single block descriptor by name, or None if not found."""
    for entry in load_inventory(path):
        if entry["name"] == name:
            return entry
    return None


def get_blocks_for_part(
    block_names: list[str], path: str = _INVENTORY_PATH
) -> tuple[list[dict[str, Any]], list[str]]:
    """Return (found_blocks, missing_names) for a list of block names."""
    inventory = {e["name"]: e for e in load_inventory(path)}
    found = []
    missing = []
    for name in block_names:
        if name in inventory:
            found.append(inventory[name])
        else:
            missing.append(name)
    return found, missing


if __name__ == "__main__":
    inv = load_inventory()
    errs = validate_inventory(inv)
    if errs:
        print(f"Inventory validation FAILED ({len(errs)} errors):")
        for e in errs:
            print(f"  - {e}")
        sys.exit(1)
    print(f"Inventory OK — {len(inv)} blocks validated")
