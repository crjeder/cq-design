"""Tests for profile.json validation and field write-back."""

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
        p = tmp_path / "profile.json"
        p.write_text(json.dumps(profile))
        return str(p)

    return _write


def test_valid_profile_passes(profile_file):
    errors = validate_profile(profile_file(VALID_PROFILE))
    assert errors == []


def test_slicer_estampo_block_accepted_and_unknown_key_rejected(profile_file):
    estampo: dict[str, Any] = {"printer": "P", "filaments": ["F"]}
    slicer = {"preferred_format": "3mf", "estampo": estampo}
    assert validate_profile(profile_file({**VALID_PROFILE, "slicer": slicer})) == []
    estampo["bogus"] = 1
    assert validate_profile(profile_file({**VALID_PROFILE, "slicer": slicer}))


def test_missing_required_field_rejected(profile_file):
    profile = {k: v for k, v in VALID_PROFILE.items() if k != "nozzle_mm"}
    errors = validate_profile(profile_file(profile))
    assert any("nozzle_mm" in e for e in errors)


def test_malformed_json_rejected(tmp_path):
    p = tmp_path / "profile.json"
    p.write_text("{not valid json")
    errors = validate_profile(str(p))
    assert errors and "Cannot load profile" in errors[0]


def test_default_template_is_valid():
    default_path = os.path.join(SKILL_ROOT, "src", "profile.default.json")
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


VALID_MOTION: dict[str, Any] = {
    "v_cruise_mm_s": 200,
    "accel_mm_s2": 5000,
    "junction_deviation_mm": 0.05,
    "min_layer_time_s": 5.0,
    "layer_height_mm": 0.2,
    "line_width_mm": 0.42,
    "infill_density": 0.15,
}


def test_motion_block_valid(profile_file):
    profile = {**VALID_PROFILE, "motion": VALID_MOTION}
    errors = validate_profile(profile_file(profile))
    assert errors == []


def test_motion_block_absent_still_valid(profile_file):
    errors = validate_profile(profile_file(VALID_PROFILE))
    assert errors == []


def test_motion_block_partial_rejected(profile_file):
    partial_motion = {k: v for k, v in VALID_MOTION.items() if k != "accel_mm_s2"}
    profile = {**VALID_PROFILE, "motion": partial_motion}
    errors = validate_profile(profile_file(profile))
    assert any("accel_mm_s2" in e for e in errors)


def test_write_profile_fields_updates_motion_field(profile_file):
    path = profile_file({**VALID_PROFILE, "motion": VALID_MOTION})
    errors = write_profile_fields(path, {"motion.accel_mm_s2": 8000})
    assert errors == []

    with open(path, encoding="utf-8") as f:
        updated = json.load(f)
    assert updated["motion"]["accel_mm_s2"] == 8000
    assert updated["motion"]["v_cruise_mm_s"] == VALID_MOTION["v_cruise_mm_s"]


def test_bridge_max_mm_optional_and_non_negative(tmp_path):
    import json

    import printer_profile_validate as ppv

    path = tmp_path / "profile.json"
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


def test_top_bottom_layers_optional_and_at_least_one(tmp_path):
    import json

    import printer_profile_validate as ppv

    path = tmp_path / "profile.json"
    prof: dict[str, Any] = {
        "printer": "x",
        "material": "PLA",
        "nozzle_mm": 0.4,
        "constraints": {"wall_min_mm": 1.2, "overhang_max_deg": 45, "dimension_tolerance_mm": 0.5},
    }
    path.write_text(json.dumps(prof))
    assert ppv.validate_profile(str(path)) == []
    prof["constraints"]["top_bottom_layers"] = 6
    path.write_text(json.dumps(prof))
    assert ppv.validate_profile(str(path)) == []
    prof["constraints"]["top_bottom_layers"] = 0
    path.write_text(json.dumps(prof))
    assert ppv.validate_profile(str(path)) != []


def _with_slicer(tmp_path, slicer):
    with open(os.path.join(SKILL_ROOT, "src", "profile.default.json"), encoding="utf-8") as f:
        profile = json.load(f)
    profile["slicer"] = slicer
    p = tmp_path / "profile.json"
    p.write_text(json.dumps(profile), encoding="utf-8")
    return str(p)


def test_slicer_block_valid(tmp_path):
    p = _with_slicer(tmp_path, {"preferred_format": "3mf", "slicer_name": "OrcaSlicer"})
    assert validate_profile(p) == []


def test_slicer_unknown_format_rejected(tmp_path):
    errors = validate_profile(_with_slicer(tmp_path, {"preferred_format": "gcode"}))
    assert any("slicer -> preferred_format" in e for e in errors)


def test_slicer_block_requires_preferred_format(tmp_path):
    errors = validate_profile(_with_slicer(tmp_path, {"slicer_name": "Cura"}))
    assert any("preferred_format" in e for e in errors)


def test_interface_min_area_optional_and_positive(profile_file):
    assert validate_profile(profile_file(VALID_PROFILE)) == []
    with open(os.path.join(SKILL_ROOT, "src", "profile.default.json")) as fh:
        default = json.load(fh)
    assert default["constraints"]["interface_min_area_mm2"] == 4.0
    for bad in (0, -1):
        prof = {**VALID_PROFILE, "constraints": {**VALID_PROFILE["constraints"]}}
        prof["constraints"]["interface_min_area_mm2"] = bad
        assert validate_profile(profile_file(prof)) != []
    prof = {**VALID_PROFILE, "constraints": {**VALID_PROFILE["constraints"]}}
    prof["constraints"]["interface_min_area_mm2"] = 2.5
    assert validate_profile(profile_file(prof)) == []


ORCA_BLOCK: dict[str, Any] = {
    "app": "Snapmaker_Orca",
    "data_dir": "/x/Snapmaker_Orca",
    "machine": "M",
    "process": "P",
    "process_purpose": "functional",
    "filaments": ["F"],
    "processes": [
        {
            "name": "P",
            "layer_height_mm": 0.2,
            "wall_loops": 2,
            "infill_density": 0.15,
            "user": False,
        }
    ],
    "digest": "sha256:0",
}


def test_orca_block_accepted_and_incomplete_rejected(profile_file):
    assert validate_profile(profile_file({**VALID_PROFILE, "orca": ORCA_BLOCK})) == []
    partial = {k: v for k, v in ORCA_BLOCK.items() if k != "digest"}
    errors = validate_profile(profile_file({**VALID_PROFILE, "orca": partial}))
    assert any("digest" in e for e in errors)


def test_build_volume_accepted_and_partial_rejected(profile_file):
    volume = {"x": 270, "y": 270, "z": 270}
    assert validate_profile(profile_file({**VALID_PROFILE, "build_volume_mm": volume})) == []
    assert validate_profile(profile_file({**VALID_PROFILE, "build_volume_mm": {"x": 270}}))


def test_design_intent_accepts_print_and_cad_rejects_other(profile_file):
    assert validate_profile(profile_file({**VALID_PROFILE, "design_intent": "cad"})) == []
    assert validate_profile(profile_file({**VALID_PROFILE, "design_intent": "print"})) == []
    assert validate_profile(profile_file({**VALID_PROFILE, "design_intent": "bogus"}))
