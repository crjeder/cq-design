"""Tests for src/init_permissions.py permission bootstrap."""

import json

import init_permissions


def _write_settings(working_dir, data):
    path = working_dir / ".claude" / "settings.local.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_canonical_list_parses_and_has_sentinel():
    canonical = init_permissions.load_canonical()
    assert isinstance(canonical["allow"], list)
    assert canonical["allow"], "allow list must not be empty"
    assert canonical["sentinel"] in canonical["allow"]


def test_fresh_dir_creates_file(tmp_path):
    added = init_permissions.merge_permissions(str(tmp_path))

    path = tmp_path / ".claude" / "settings.local.json"
    assert path.exists()
    settings = json.loads(path.read_text(encoding="utf-8"))
    canonical = init_permissions.load_canonical()
    assert settings["permissions"]["allow"] == canonical["allow"]
    assert added == canonical["allow"]


def test_merge_preserves_existing_entries_and_keys(tmp_path):
    _write_settings(
        tmp_path,
        {
            "permissions": {"allow": ["Bash(echo hi)", "WebSearch"]},
            "env": {"FOO": "bar"},
        },
    )

    init_permissions.merge_permissions(str(tmp_path))

    settings = json.loads(
        (tmp_path / ".claude" / "settings.local.json").read_text(encoding="utf-8")
    )
    allow = settings["permissions"]["allow"]
    # user's entries kept, in their original leading position
    assert allow[0] == "Bash(echo hi)"
    assert allow[1] == "WebSearch"
    # other keys untouched
    assert settings["env"] == {"FOO": "bar"}
    # WebSearch (already present) not duplicated
    assert allow.count("WebSearch") == 1
    # canonical sentinel now present
    assert init_permissions.load_canonical()["sentinel"] in allow


def test_all_present_is_noop(tmp_path):
    canonical = init_permissions.load_canonical()
    _write_settings(tmp_path, {"permissions": {"allow": list(canonical["allow"])}})

    added = init_permissions.merge_permissions(str(tmp_path))

    assert added == []
    settings = json.loads(
        (tmp_path / ".claude" / "settings.local.json").read_text(encoding="utf-8")
    )
    assert settings["permissions"]["allow"] == canonical["allow"]


def test_check_reports_uninitialized_then_initialized(tmp_path):
    sentinel = init_permissions.load_canonical()["sentinel"]

    assert init_permissions.is_initialized(str(tmp_path), sentinel) is False

    init_permissions.merge_permissions(str(tmp_path))

    assert init_permissions.is_initialized(str(tmp_path), sentinel) is True
