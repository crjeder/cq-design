#!/usr/bin/env python3
"""Validate printer_profile.json against its schema, and write field overrides back to it.

Usage:
    python3 printer_profile_validate.py printer_profile.json
    python3 printer_profile_validate.py printer_profile.json --set nozzle_mm=0.6
    python3 printer_profile_validate.py printer_profile.json --set constraints.overhang_max_deg=50

Exit codes: 0 valid, 1 invalid.
"""

import argparse
import json
import os
import sys
from typing import Any

import jsonschema

_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "printer_profile_schema.json")


def _load_json(path: str) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate_profile(profile_path: str, schema_path: str = _SCHEMA_PATH) -> list[str]:
    """Validate a printer_profile.json file. Returns list of error strings (empty = OK)."""
    try:
        profile = _load_json(profile_path)
    except (OSError, json.JSONDecodeError) as e:
        return [f"Cannot load profile: {e}"]

    schema = _load_json(schema_path)
    validator = jsonschema.Draft7Validator(schema)
    errors = []
    for err in sorted(
        validator.iter_errors(profile), key=lambda e: list(map(str, e.absolute_path))
    ):
        path = " -> ".join(str(p) for p in err.absolute_path) or "(root)"
        errors.append(f"Schema error at {path}: {err.message}")
    return errors


def write_profile_fields(
    profile_path: str, fields: dict[str, Any], schema_path: str = _SCHEMA_PATH
) -> list[str]:
    """Merge only the given field(s) into printer_profile.json and re-validate the result.

    Keys in `fields` may be top-level ("nozzle_mm") or dotted one level into
    `constraints` ("constraints.overhang_max_deg"). Fields not named in `fields` are
    left untouched. Returns validation errors after the merge (empty = written
    successfully); the file is not written if validation fails.
    """
    profile = _load_json(profile_path)
    for key, value in fields.items():
        if key.startswith("constraints."):
            profile.setdefault("constraints", {})[key.split(".", 1)[1]] = value
        else:
            profile[key] = value

    schema = _load_json(schema_path)
    validator = jsonschema.Draft7Validator(schema)
    errors = []
    for err in validator.iter_errors(profile):
        path = " -> ".join(str(p) for p in err.absolute_path) or "(root)"
        errors.append(f"Schema error at {path}: {err.message}")
    if errors:
        return errors

    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)
        f.write("\n")
    return []


def _parse_set(pairs: list[str]) -> dict[str, Any]:
    fields = {}
    for pair in pairs:
        key, _, raw_value = pair.partition("=")
        try:
            fields[key] = json.loads(raw_value)
        except json.JSONDecodeError:
            fields[key] = raw_value
    return fields


def main():
    parser = argparse.ArgumentParser(description="Validate printer_profile.json")
    parser.add_argument("profile", help="Path to printer_profile.json")
    parser.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="FIELD=VALUE",
        help="Write a field back (e.g. nozzle_mm=0.6, constraints.overhang_max_deg=50)",
    )
    args = parser.parse_args()

    if args.set:
        errors = write_profile_fields(args.profile, _parse_set(args.set))
        if errors:
            print(f"printer_profile.json update FAILED ({len(errors)} error(s)):")
            for e in errors:
                print(f"  - {e}")
            sys.exit(1)
        print(f"printer_profile.json updated: {', '.join(args.set)}")
        return

    errors = validate_profile(args.profile)
    if errors:
        print(f"printer_profile.json validation FAILED ({len(errors)} error(s)):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print("printer_profile.json OK")


if __name__ == "__main__":
    main()
