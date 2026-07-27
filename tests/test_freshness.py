"""Tests for src/freshness.py -- provenance stamp hash, comparison, and manifest I/O.

Stdlib only, no CadQuery import, fast.
"""

from freshness import is_stale, read_manifest, script_hash, write_manifest


def _write(path, content):
    path.write_text(content, encoding="utf-8")
    return str(path)


def test_hash_is_deterministic(tmp_path):
    script = _write(tmp_path / "part.py", "result = 1\n")
    assert script_hash(script) == script_hash(script)


def test_hash_changes_on_any_content_edit(tmp_path):
    script = tmp_path / "part.py"
    path = _write(script, "result = 1\n")
    before = script_hash(path)
    _write(script, "result = 1  # comment only, geometry-neutral edit\n")
    after = script_hash(path)
    assert before != after


def test_is_stale_matching_hash(tmp_path):
    script = _write(tmp_path / "part.py", "result = 1\n")
    assert is_stale(script_hash(script), script) is False


def test_is_stale_mismatching_hash(tmp_path):
    script = tmp_path / "part.py"
    path = _write(script, "result = 1\n")
    stamped = script_hash(path)
    _write(script, "result = 2\n")
    assert is_stale(stamped, path) is True


def test_is_stale_absent_stamp_is_not_stale(tmp_path):
    script = _write(tmp_path / "part.py", "result = 1\n")
    assert is_stale(None, script) is False


def test_write_manifest_round_trip(tmp_path):
    part_a = _write(tmp_path / "a.py", "result = 1\n")
    part_b = _write(tmp_path / "b.py", "result = 2\n")
    stl_dir = tmp_path / "stl"
    stl_dir.mkdir()

    manifest_path = write_manifest(
        str(stl_dir),
        {"union_a": ("part_a", part_a), "union_b": ("part_b", part_b)},
        {"part_a::zone1": ("part_a", part_a)},
    )

    manifest = read_manifest(str(stl_dir))
    assert manifest is not None
    assert manifest_path.endswith("export_manifest.json")
    assert manifest["unions"]["union_a"]["source_script_hash"] == script_hash(part_a)
    assert manifest["unions"]["union_a"]["part_id"] == "part_a"
    assert manifest["unions"]["union_b"]["source_script_hash"] == script_hash(part_b)
    assert manifest["keep_out_zones"]["part_a::zone1"]["source_script_hash"] == script_hash(part_a)
    assert "exported_at" in manifest


def test_write_manifest_without_keep_out_zones(tmp_path):
    part_a = _write(tmp_path / "a.py", "result = 1\n")
    stl_dir = tmp_path / "stl"
    stl_dir.mkdir()

    write_manifest(str(stl_dir), {"union_a": ("part_a", part_a)})

    manifest = read_manifest(str(stl_dir))
    assert manifest is not None
    assert manifest["keep_out_zones"] == {}


def test_read_manifest_absent_returns_none(tmp_path):
    assert read_manifest(str(tmp_path)) is None
