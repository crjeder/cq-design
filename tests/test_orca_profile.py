"""Tests for orca_profile.py against the fixture Orca tree in tests/fixtures/orca/."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = SKILL_ROOT / "src" / "orca_profile.py"
sys.path.insert(0, str(SKILL_ROOT / "src"))

import orca_profile  # noqa: E402

FIXTURES = SKILL_ROOT / "tests" / "fixtures" / "orca"
DATA = FIXTURES / "Snapmaker_Orca"
U1 = "Test U1 (0.4 nozzle)"
SINGLE = "Test Single (0.4 nozzle)"


def run(*args: str) -> tuple[int, dict]:
    env = {**os.environ, "PYTHONPATH": str(SKILL_ROOT / "src")}
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=env
    )
    return proc.returncode, json.loads(proc.stdout)


@pytest.fixture
def profile(tmp_path) -> Path:
    p = tmp_path / "profile.json"
    shutil.copyfile(SKILL_ROOT / "src" / "profile.default.json", p)
    return p


def do_import(profile: Path, *extra: str) -> tuple[int, dict]:
    return run("import", str(profile), "--data-dir", str(DATA), "--filament", "Jayo PETG", *extra)


def load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def test_discover_finds_fixture_with_selected_machine():
    found = orca_profile.discover(FIXTURES)
    assert [(f["app"], f["machine"]) for f in found] == [("Snapmaker_Orca", U1)]


def test_discover_empty_root(tmp_path):
    assert orca_profile.discover(tmp_path) == []


def test_ambiguous_data_dir(tmp_path, monkeypatch, profile):
    for app in ("OrcaSlicer", "Snapmaker_Orca"):
        (tmp_path / app / "system").mkdir(parents=True)
    monkeypatch.setattr(orca_profile, "_config_root", lambda: tmp_path)
    with pytest.raises(orca_profile.OrcaError) as e:
        orca_profile._pick_data_dir(None, {})
    assert e.value.entry["type"] == "ambiguous_data_dir"
    assert len(e.value.entry["candidates"]) == 2


def test_user_delta_over_system_chain():
    index = orca_profile.build_index(DATA)
    merged, chain = orca_profile.resolve(index, "filament", "Jayo PETG")
    assert merged["nozzle_temperature"] == ["250"]
    assert merged["filament_type"] == ["PETG"]
    assert merged["slow_down_layer_time"] == ["12"]
    assert len(chain) == 3


def test_missing_parent():
    index = orca_profile.build_index(DATA)
    with pytest.raises(orca_profile.OrcaError) as e:
        orca_profile.resolve(index, "process", "Broken")
    assert e.value.entry["type"] == "missing_parent"
    assert "Nonexistent parent" in e.value.entry["message"]


def test_import_maps_fields(profile):
    code, out = do_import(profile)
    assert code == 0, out
    p = load(profile)
    assert p["constraints"]["overhang_max_deg"] == 60
    assert p["constraints"]["top_bottom_layers"] == 4
    assert p["max_materials"] == 4
    assert p["build_volume_mm"] == {"x": 270, "y": 270, "z": 270}
    assert p["material"] == "PETG"
    assert p["motion"]["min_layer_time_s"] == 12
    assert p["slicer"]["estampo"]["filaments"] == ["Jayo PETG"]
    assert "elefant_foot_compensation = 0.15" in out["compensation_warnings"]


def test_auto_support_threshold_skipped(tmp_path, profile):
    data = tmp_path / "Snapmaker_Orca"
    shutil.copytree(DATA, data)
    base = data / "system" / "TestVendor" / "process" / "fdm_process_base.json"
    raw = json.loads(base.read_text(encoding="utf-8"))
    raw["support_threshold_angle"] = "0"
    base.write_text(json.dumps(raw), encoding="utf-8")
    before = load(profile)["constraints"]["overhang_max_deg"]
    code, out = run("import", str(profile), "--data-dir", str(data), "--filament", "Jayo PETG")
    assert code == 0, out
    assert "constraints.overhang_max_deg" in out["skipped"]
    assert load(profile)["constraints"]["overhang_max_deg"] == before


def test_cruise_capped_by_volumetric_flow():
    machine = {"gcode_flavor": "klipper", "machine_max_jerk_x": ["9"]}
    process = {
        "layer_height": "0.16",
        "outer_wall_line_width": "0.42",
        "outer_wall_acceleration": ["5000"],
        "outer_wall_speed": ["200"],
        "sparse_infill_density": "15%",
    }
    filament = {"slow_down_layer_time": ["12"], "filament_max_volumetric_speed": ["12"]}
    motion, _ = orca_profile._motion(machine, process, filament, 0.4)
    assert motion is not None
    assert motion["v_cruise_mm_s"] == round(12 / (0.16 * 0.42), 1) == 178.6
    assert motion["junction_deviation_mm"] == round(81 * (2**0.5 - 1) / 5000, 4)


def test_line_width_percent_of_nozzle():
    assert orca_profile._num("105%", 0.4) == pytest.approx(0.42)


def test_ams_slot_count_given(profile):
    code, out = do_import(profile, "--machine", SINGLE, "--max-materials", "4")
    assert code == 0, out
    assert load(profile)["max_materials"] == 4


def test_process_list_only_compatible(profile):
    do_import(profile)
    names = [p["name"] for p in load(profile)["orca"]["processes"]]
    assert f"0.20mm Standard @{SINGLE}" not in names
    assert "Broken" not in names
    assert {p["layer_height_mm"] for p in load(profile)["orca"]["processes"]} == {
        0.12,
        0.16,
        0.20,
        0.28,
    }


def test_calibration_fields_untouched(profile):
    p = load(profile)
    p["fit_clearance_mm"]["sliding"] = 0.3
    profile.write_text(json.dumps(p))
    do_import(profile)
    after = load(profile)
    assert after["fit_clearance_mm"]["sliding"] == 0.3
    assert after["constraints"]["wall_min_mm"] == p["constraints"]["wall_min_mm"]
    assert after["slicer"]["preferred_format"] == p["slicer"]["preferred_format"]


def test_unmapped_material_writes_nothing(profile):
    before = profile.read_text(encoding="utf-8")
    code, out = run("import", str(profile), "--data-dir", str(DATA), "--filament", "Generic PVA")
    assert code == 1
    assert out["errors"][0]["type"] == "unmapped_material"
    assert out["errors"][0]["raw_type"] == "PVA"
    assert profile.read_text(encoding="utf-8") == before


def test_material_base_type_map():
    assert orca_profile._base_material("PETG-CF") == "PETG"
    assert orca_profile._base_material("PLA+") == "PLA"
    assert orca_profile._base_material("PAHT-CF") == "PA"
    assert orca_profile._base_material("PCTG") == "PETG"
    assert orca_profile._base_material("PVA") is None


def test_hole_compensation_reported():
    assert orca_profile._compensation({"xy_hole_compensation": "0.1"}, {}) == [
        "xy_hole_compensation = 0.1"
    ]


def test_no_junction_deviation_skips_motion(profile):
    before = load(profile)["motion"]
    code, out = do_import(profile, "--machine", SINGLE)
    assert code == 0, out
    assert "motion" in out["skipped"]
    assert load(profile)["motion"] == before


def test_filament_required_lists_choices(profile):
    code, out = run("import", str(profile), "--data-dir", str(DATA))
    assert code == 1
    err = out["errors"][0]
    assert err["type"] == "filament_required"
    assert err["choices"]["user"] == ["Jayo PETG"]


def test_visual_purpose_picks_0_16(profile):
    do_import(profile)
    code, out = run("select-process", str(profile), "--purpose", "visual")
    assert code == 0, out
    assert "0.16mm Standard" in out["process"]
    assert out["process_reason"].startswith("selected 0.16mm Standard")
    assert out["process_reason"].endswith("(layer 0.16 mm) for visual quality")


def test_functional_tie_break_prefers_more_walls(profile):
    code, out = do_import(profile)
    assert out["process_reason"].startswith(f"selected 0.20mm Strength @{U1}")


def test_user_override(profile):
    do_import(profile)
    name = f"0.28mm Draft @{U1}"
    code, out = run("select-process", str(profile), "--process", name, "--write")
    assert code == 0, out
    p = load(profile)
    assert p["orca"]["process"] == name
    assert p["orca"]["process_purpose"] == "user"
    assert p["motion"]["layer_height_mm"] == 0.28
    assert out["process_reason"].endswith("chosen by user")


def test_planner_choice_records_purpose(profile):
    do_import(profile)
    name = f"0.12mm Fine @{U1}"
    run("select-process", str(profile), "--process", name, "--purpose", "visual", "--write")
    assert load(profile)["orca"]["process_purpose"] == "visual"


def test_incompatible_process(profile):
    do_import(profile)
    before = profile.read_text(encoding="utf-8")
    code, out = run(
        "select-process", str(profile), "--process", f"0.20mm Standard @{SINGLE}", "--write"
    )
    assert code == 1
    assert out["errors"][0]["type"] == "incompatible_process"
    assert profile.read_text(encoding="utf-8") == before


def test_sync_keeps_recorded_user_process(profile):
    do_import(profile)
    name = f"0.28mm Draft @{U1}"
    run("select-process", str(profile), "--process", name, "--write")
    code, out = run("import", str(profile))
    assert code == 0, out
    assert load(profile)["orca"]["process"] == name


def test_check_fresh_then_stale(tmp_path, profile):
    data = tmp_path / "Snapmaker_Orca"
    shutil.copytree(DATA, data)
    run("import", str(profile), "--data-dir", str(data), "--filament", "Jayo PETG")
    assert run("check", str(profile))[1]["state"] == "fresh"
    process_file = data / "system" / "TestVendor" / "process" / f"0.20mm Strength @{U1}.json"
    raw = json.loads(process_file.read_text(encoding="utf-8"))
    raw["layer_height"] = "0.24"
    process_file.write_text(json.dumps(raw), encoding="utf-8")
    code, out = run("check", str(profile))
    assert code == 0
    assert out["state"] == "stale"
    assert out["changed"]["motion.layer_height_mm"] == {"old": 0.2, "new": 0.24}


def test_check_unavailable(profile):
    do_import(profile)
    p = load(profile)
    p["orca"]["data_dir"] = "/nonexistent/Snapmaker_Orca"
    profile.write_text(json.dumps(p))
    code, out = run("check", str(profile))
    assert code == 0
    assert out["state"] == "unavailable"


def test_check_not_imported(profile):
    assert run("check", str(profile))[1]["state"] == "not_imported"
