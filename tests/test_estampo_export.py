"""Tests for src/estampo_export.py -- fast, no CadQuery."""

import os
import sys

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL_ROOT, "src"))

from estampo_export import estampo_toml, write_estampo_toml  # noqa: E402

PROFILE = {"motion": {"layer_height_mm": 0.2, "infill_density": 0.15}}


def test_one_parts_entry_per_stl_in_print_pose():
    text = estampo_toml(["body.stl", "plate_1.stl"], PROFILE)
    assert text.count("[[parts]]") == 2
    assert 'file = "body.stl"' in text
    assert 'file = "plate_1.stl"' in text
    assert text.count("rotate = [0, 0, 0]") == 2


def test_overrides_from_profile():
    text = estampo_toml(["a.stl"], PROFILE)
    assert "[slicer.orca.overrides]" in text
    assert "layer_height = 0.2" in text
    assert 'sparse_infill_density = "15%"' in text


def test_absent_values_are_omitted():
    text = estampo_toml(["a.stl"], {"motion": {"layer_height_mm": 0.28}})
    assert "layer_height = 0.28" in text
    assert "sparse_infill_density" not in text
    assert "[slicer.orca.overrides]" not in estampo_toml(["a.stl"], {})


def test_profile_names_are_commented_placeholders_by_default():
    text = estampo_toml(["a.stl"], PROFILE)
    live = [ln for ln in text.splitlines() if not ln.startswith("#")]
    assert not any(ln.startswith(("printer", "process", "filaments")) for ln in live)
    assert "# printer" in text and "# process" in text and "# filaments" in text


def test_profile_names_written_when_supplied():
    names = {"printer": "P", "process": "Q", "filaments": ["F"]}
    text = estampo_toml(["a.stl"], {"slicer": {"estampo": names}})
    assert 'printer = "P"' in text
    assert 'process = "Q"' in text
    assert 'filaments = ["F"]' in text


def test_write_uses_basenames(tmp_path):
    path = write_estampo_toml([str(tmp_path / "x" / "a.stl")], PROFILE, str(tmp_path))
    assert os.path.basename(path) == "estampo.toml"
    with open(path, encoding="utf-8") as f:
        assert 'file = "a.stl"' in f.read()
