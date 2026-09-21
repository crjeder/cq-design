"""Tests for printer_profile.json validation and field write-back."""

import json
import os
import sys
from typing import Any

import pytest

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL_ROOT, "src"))

from printer_profile_validate import validate_profile, write_profile_fields  # noqa: E402

VALID_PROFILE: dict[str, Any] = {
    "printer": "Bambu P1S",
    "material": "PLA",
    "nozzle_mm": 0.4,
    "constraints": {
        "wall_min_mm": 1.2,
        "overhang_max_deg": 45,
        "dimension_tolerance_mm": 0.5,
    },
}


@pytest.fixture
def profile_file(tmp_path):
    def _write(profile):
        p = tmp_path / "printer_profile.json"
        p.write_text(json.dumps(profile))
        return str(p)

    return _write


def test_valid_profile_passes(profile_file):
    errors = validate_profile(profile_file(VALID_PROFILE))
    assert errors == []


def test_missing_required_field_rejected(profile_file):
    profile = {k: v for k, v in VALID_PROFILE.items() if k != "nozzle_mm"}
    errors = validate_profile(profile_file(profile))
    assert any("nozzle_mm" in e for e in errors)


def test_malformed_json_rejected(tmp_path):
    p = tmp_path / "printer_profile.json"
    p.write_text("{not valid json")
    errors = validate_profile(str(p))
    assert errors and "Cannot load profile" in errors[0]


def test_default_template_is_valid():
    default_path = os.path.join(SKILL_ROOT, "src", "printer_profile.default.json")
    errors = validate_profile(default_path)
    assert errors == []


def test_write_profile_fields_updates_only_named_field(profile_file):
    path = profile_file(VALID_PROFILE)
    errors = write_profile_fields(path, {"nozzle_mm": 0.6})
    assert errors == []

    with open(path, encoding="utf-8") as f:
        updated = json.load(f)
    assert updated["nozzle_mm"] == 0.6
    assert updated["printer"] == VALID_PROFILE["printer"]
    assert updated["material"] == VALID_PROFILE["material"]
    assert updated["constraints"] == VALID_PROFILE["constraints"]


def test_write_profile_fields_updates_nested_constraint(profile_file):
    path = profile_file(VALID_PROFILE)
    errors = write_profile_fields(path, {"constraints.overhang_max_deg": 50})
    assert errors == []

    with open(path, encoding="utf-8") as f:
        updated = json.load(f)
    assert updated["constraints"]["overhang_max_deg"] == 50
    assert updated["constraints"]["wall_min_mm"] == VALID_PROFILE["constraints"]["wall_min_mm"]


def test_write_profile_fields_rejects_invalid_value_without_writing(profile_file):
    path = profile_file(VALID_PROFILE)
    errors = write_profile_fields(path, {"nozzle_mm": 1.5})
    assert errors != []

    with open(path, encoding="utf-8") as f:
        unchanged = json.load(f)
    assert unchanged["nozzle_mm"] == VALID_PROFILE["nozzle_mm"]


def test_bridge_max_mm_optional_and_non_negative(tmp_path):
    import json

    import printer_profile_validate as ppv

    path = tmp_path / "printer_profile.json"
    prof: dict[str, Any] = {
        "printer": "x",
        "material": "PLA",
        "nozzle_mm": 0.4,
        "constraints": {"wall_min_mm": 1.2, "overhang_max_deg": 45, "dimension_tolerance_mm": 0.5},
    }
    path.write_text(json.dumps(prof))
    assert ppv.validate_profile(str(path)) == []
    prof["constraints"]["bridge_max_mm"] = 10.0
    path.write_text(json.dumps(prof))
    assert ppv.validate_profile(str(path)) == []
    prof["constraints"]["bridge_max_mm"] = -1
    path.write_text(json.dumps(prof))
    assert ppv.validate_profile(str(path)) != []
