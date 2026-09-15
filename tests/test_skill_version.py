import json
import subprocess
from pathlib import Path

import pytest

import skill_version as sv


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=path, check=True)
    (path / "f.txt").write_text("1", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "one"], cwd=path, check=True)


def _head(path: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()


def test_describe_installed_reads_version_file(tmp_path, monkeypatch):
    monkeypatch.setattr(sv, "SKILL_ROOT", tmp_path)
    monkeypatch.setattr(sv, "VERSION_FILE", tmp_path / ".version.json")
    sv.VERSION_FILE.write_text(json.dumps({"commit": "abc123", "dirty": False}), encoding="utf-8")
    info = sv.describe_installed()
    assert info == {"source": "version_file", "commit": "abc123", "dirty": False}


def test_describe_installed_reports_unknown_with_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(sv, "SKILL_ROOT", tmp_path)
    monkeypatch.setattr(sv, "VERSION_FILE", tmp_path / ".version.json")
    assert sv.describe_installed() == {"source": "unknown"}


def test_describe_installed_reads_live_checkout(tmp_path, monkeypatch):
    _init_repo(tmp_path)
    monkeypatch.setattr(sv, "SKILL_ROOT", tmp_path)
    monkeypatch.setattr(sv, "VERSION_FILE", tmp_path / ".version.json")
    info = sv.describe_installed()
    assert info["source"] == "checkout"
    assert info["commit"] == _head(tmp_path)
    assert info["dirty"] is False


def test_describe_installed_follows_symlink(tmp_path, monkeypatch):
    target = tmp_path / "repo"
    target.mkdir()
    _init_repo(target)
    link = tmp_path / "link"
    try:
        link.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not permitted in this environment")
    monkeypatch.setattr(sv, "SKILL_ROOT", link)
    monkeypatch.setattr(sv, "VERSION_FILE", link / ".version.json")
    info = sv.describe_installed()
    assert info["source"] == "linked"
    assert info["commit"] == _head(target)


def test_compare_up_to_date(tmp_path):
    _init_repo(tmp_path)
    result = sv.compare({"commit": _head(tmp_path)}, tmp_path)
    assert result == {"status": "up_to_date", "commit": _head(tmp_path)}


def test_compare_behind_counts_commits(tmp_path):
    _init_repo(tmp_path)
    old = _head(tmp_path)
    (tmp_path / "f.txt").write_text("2", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "two"], cwd=tmp_path, check=True)
    result = sv.compare({"commit": old}, tmp_path)
    assert result["status"] == "behind"
    assert result["commits_behind"] == 1
    assert result["repo_head"] == _head(tmp_path)


def test_compare_diverged_when_commit_unknown_to_repo(tmp_path):
    _init_repo(tmp_path)
    result = sv.compare({"commit": "0" * 40}, tmp_path)
    assert result["status"] == "diverged"


def test_compare_unknown_when_installed_has_no_commit(tmp_path):
    _init_repo(tmp_path)
    result = sv.compare({"source": "unknown"}, tmp_path)
    assert result["status"] == "unknown"


def test_compare_error_on_non_repo(tmp_path):
    result = sv.compare({"commit": "abc"}, tmp_path)
    assert result["status"] == "error"


def test_main_exit_code_reflects_compare_status(tmp_path, monkeypatch, capsys):
    _init_repo(tmp_path)
    monkeypatch.setattr(sv, "SKILL_ROOT", tmp_path)
    monkeypatch.setattr(sv, "VERSION_FILE", tmp_path / ".version.json")
    assert sv.main(["--compare", str(tmp_path)]) == 0
    assert sv.main([]) == 0

    old = _head(tmp_path)
    (tmp_path / "f.txt").write_text("2", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "two"], cwd=tmp_path, check=True)
    monkeypatch.setattr(sv, "describe_installed", lambda: {"source": "version_file", "commit": old})
    assert sv.main(["--compare", str(tmp_path)]) == 1


def test_main_json_output(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sv, "SKILL_ROOT", tmp_path)
    monkeypatch.setattr(sv, "VERSION_FILE", tmp_path / ".version.json")
    sv.main(["--json"])
    out = json.loads(capsys.readouterr().out)
    assert out["installed"] == {"source": "unknown"}
    assert out["compare"] is None
