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
        "joint_axis",
        "ball",
        "ball_socket",
        "finger",
        "mortise",
        "tenon",
        "dowel",
        "seam",
        "union",
        "dovetail_corner",
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


_REQUIRED_FIELDS = ("name", "module", "function", "use", "params", "dimensions", "interfaces")


def _check_required_fields(tag: str, entry: dict) -> list[str]:
    return [
        f"{tag}: missing required field '{field}'"
        for field in _REQUIRED_FIELDS
        if field not in entry
    ]


def _check_scalar_fields(tag: str, entry: dict) -> list[str]:
    """Check the optional motion/reversible/carries/emits fields' shape and vocabulary."""
    errors = []
    if "motion" in entry and entry["motion"] not in _VALID_MOTION:
        allowed = ", ".join(sorted(_VALID_MOTION))
        errors.append(f"{tag}: motion '{entry['motion']}' not in allowed vocabulary ({allowed})")
    if "reversible" in entry and not isinstance(entry["reversible"], bool):
        errors.append(f"{tag}: reversible must be a boolean")
    if "carries" in entry and not (
        isinstance(entry["carries"], list) and all(isinstance(c, str) for c in entry["carries"])
    ):
        errors.append(f"{tag}: carries must be a list of strings")
    if "emits" in entry and not (
        isinstance(entry["emits"], list)
        and len(entry["emits"]) == 2
        and all(isinstance(m, str) for m in entry["emits"])
    ):
        errors.append(f"{tag}: emits must be a list of exactly two strings")
    return errors


def _check_interfaces(tag: str, entry: dict) -> list[str]:
    errors = []
    for iface in entry.get("interfaces", []):
        itype = iface.get("type", "")
        if itype not in _VALID_INTERFACE_TYPES:
            allowed = ", ".join(sorted(_VALID_INTERFACE_TYPES))
            errors.append(f"{tag}: interface type '{itype}' not in allowed vocabulary ({allowed})")
        if "orientation" not in iface:
            errors.append(f"{tag}: interface missing 'orientation'")
        if "origin" not in iface or len(iface.get("origin", [])) != 3:
            errors.append(f"{tag}: interface missing or invalid 'origin' (must be [x,y,z])")
    return errors


def _validate_entry(i: int, entry: dict, seen_names: set[str]) -> list[str]:
    tag = f"block[{i}] {entry.get('name', '(no name)')!r}"
    errors = _check_required_fields(tag, entry)

    name = entry.get("name", "")
    if name in seen_names:
        errors.append(f"{tag}: duplicate name '{name}'")
    seen_names.add(name)

    errors.extend(_check_scalar_fields(tag, entry))
    errors.extend(_check_interfaces(tag, entry))
    return errors


def validate_inventory(inventory: list[Any]) -> list[str]:
    """Validate inventory entries. Returns list of error strings (empty = OK)."""
    errors = []
    seen_names: set[str] = set()
    for i, entry in enumerate(inventory):
        errors.extend(_validate_entry(i, entry, seen_names))
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


def search_inventory(keyword: str, path: str = _INVENTORY_PATH) -> list[dict[str, Any]]:
    """Return inventory entries whose name/use/params/interfaces mention `keyword`.

    Case-insensitive substring match over each entry's full JSON serialization, so
    a search for e.g. "hinge" or "dof" also matches entries where the term only
    appears in a nested field (interfaces, dof, params) rather than the name.
    """
    keyword = keyword.lower()
    return [e for e in load_inventory(path) if keyword in json.dumps(e).lower()]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--search", metavar="KEYWORD", help="find blocks mentioning KEYWORD")
    args = parser.parse_args()

    if args.search:
        matches = search_inventory(args.search)
        if not matches:
            print(f"No blocks match {args.search!r}")
            sys.exit(1)
        for e in matches:
            print(f"{e['name']} - {e.get('use', '')}")
            print(f"  {json.dumps(e)}")
        sys.exit(0)

    inv = load_inventory()
    errs = validate_inventory(inv)
    if errs:
        print(f"Inventory validation FAILED ({len(errs)} errors):")
        for err in errs:
            print(f"  - {err}")
        sys.exit(1)
    print(f"Inventory OK — {len(inv)} blocks validated")
