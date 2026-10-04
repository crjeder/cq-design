"""Tests for bundle_project.py stamping, pruning, check, and pyproject handling -- no CadQuery."""

import json

import bundle_project as bp


def test_stamp_written(tmp_path):
    bp.bundle(tmp_path)
    stamp = json.loads((tmp_path / bp.STAMP).read_text(encoding="utf-8"))
    assert "commit" in stamp and stamp["bundled_at"]


def test_prune_keeps_user_files(tmp_path):
    bp.bundle(tmp_path)
    (tmp_path / "lib" / "blocks" / "old.py").write_text("x", encoding="utf-8")
    (tmp_path / "lib" / "my_helper.py").write_text("x", encoding="utf-8")
    stamp = json.loads((tmp_path / bp.STAMP).read_text(encoding="utf-8"))
    stamp["modules"].append("retired.py")
    (tmp_path / bp.STAMP).write_text(json.dumps(stamp), encoding="utf-8")
    (tmp_path / "lib" / "retired.py").write_text("x", encoding="utf-8")
    bp.bundle(tmp_path)
    assert not (tmp_path / "lib" / "blocks" / "old.py").exists()
    assert not (tmp_path / "lib" / "retired.py").exists()
    assert (tmp_path / "lib" / "my_helper.py").exists()


def test_existing_pyproject_kept(tmp_path, capsys):
    (tmp_path / "pyproject.toml").write_text("mine", encoding="utf-8")
    bp.bundle(tmp_path)
    assert (tmp_path / "pyproject.toml").read_text(encoding="utf-8") == "mine"
    assert "Kept existing pyproject.toml" in capsys.readouterr().out


def test_check_states(tmp_path, monkeypatch):
    assert bp.check(tmp_path) == "unknown"
    monkeypatch.setattr(bp.skill_version, "describe_installed", lambda: {"commit": "abc"})
    bp.bundle(tmp_path)
    assert bp.check(tmp_path) == "current"
    monkeypatch.setattr(bp.skill_version, "describe_installed", lambda: {"commit": "def"})
    monkeypatch.setattr(bp.skill_version, "compare", lambda *_: {"status": "behind"})
    assert bp.check(tmp_path) == "behind"


def test_main_merges_permissions(tmp_path, monkeypatch):
    monkeypatch.setattr("sys.argv", ["bundle_project.py", str(tmp_path)])
    assert bp.main() == 0
    settings = json.loads(
        (tmp_path / ".claude" / "settings.local.json").read_text(encoding="utf-8")
    )
    assert settings["permissions"]["allow"]
