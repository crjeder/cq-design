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
    added, removed = init_permissions.merge_permissions(str(tmp_path))

    path = tmp_path / ".claude" / "settings.local.json"
    assert path.exists()
    settings = json.loads(path.read_text(encoding="utf-8"))
    canonical = init_permissions.load_canonical()
    assert settings["permissions"]["allow"] == canonical["allow"]
    assert added == canonical["allow"]
    assert removed == []


def test_merge_preserves_existing_entries_and_keys(tmp_path):
    _write_settings(
        tmp_path,
        {
            "permissions": {"allow": ["Bash(echo hi)", "WebFetch(domain:example.com)"]},
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
    assert allow[1] == "WebFetch(domain:example.com)"
    # other keys untouched
    assert settings["env"] == {"FOO": "bar"}
    assert allow.count("WebFetch(domain:example.com)") == 1
    # canonical sentinel now present
    assert init_permissions.load_canonical()["sentinel"] in allow


def test_all_present_is_noop(tmp_path):
    canonical = init_permissions.load_canonical()
    _write_settings(tmp_path, {"permissions": {"allow": list(canonical["allow"])}})

    added, removed = init_permissions.merge_permissions(str(tmp_path))

    assert added == [] and removed == []
    settings = json.loads(
        (tmp_path / ".claude" / "settings.local.json").read_text(encoding="utf-8")
    )
    assert settings["permissions"]["allow"] == canonical["allow"]


def test_check_reports_uninitialized_then_initialized(tmp_path):
    sentinel = init_permissions.load_canonical()["sentinel"]

    assert init_permissions.is_initialized(str(tmp_path), sentinel) is False

    init_permissions.merge_permissions(str(tmp_path))

    assert init_permissions.is_initialized(str(tmp_path), sentinel) is True


def _allow(working_dir):
    path = working_dir / ".claude" / "settings.local.json"
    return json.loads(path.read_text(encoding="utf-8"))["permissions"]["allow"]


def test_no_broad_or_destructive_patterns():
    canonical = init_permissions.load_canonical()
    skill_dir = init_permissions._SKILL_DIR
    for p in canonical["allow"]:
        assert p != "WebSearch"
        assert not any(v in p for v in ("cp ", "mkdir", "Copy-Item", "New-Item"))
        if ".py" in p and "build/build.py" not in p:
            assert skill_dir in p, p


def test_retired_patterns_pruned_and_user_entries_kept(tmp_path):
    _write_settings(
        tmp_path,
        {
            "permissions": {
                "allow": [
                    "Bash(echo hi)",
                    "Bash(cp *)",
                    "WebSearch",
                    "Bash(python * log.py *)",
                    "Bash(ls)",
                ]
            }
        },
    )

    added, removed = init_permissions.merge_permissions(str(tmp_path))

    assert removed == ["Bash(cp *)", "WebSearch", "Bash(python * log.py *)"]
    assert _allow(tmp_path)[:2] == ["Bash(echo hi)", "Bash(ls)"]
    assert init_permissions.merge_permissions(str(tmp_path)) == ([], [])


def test_stale_skill_path_replaced(tmp_path):
    stale = 'Bash(python "/old/cache/1.0/src/log.py" *)'
    _write_settings(tmp_path, {"permissions": {"allow": [stale]}})

    _, removed = init_permissions.merge_permissions(str(tmp_path))

    assert removed == [stale]
    allow = _allow(tmp_path)
    assert stale not in allow
    assert f'Bash(python "{init_permissions._SKILL_DIR}/src/log.py" *)' in allow
    assert init_permissions.merge_permissions(str(tmp_path)) == ([], [])


def test_old_sentinel_reads_uninitialized(tmp_path):
    _write_settings(
        tmp_path,
        {"permissions": {"allow": ["Bash(uv run --project * python * run_cadquery_model.py *)"]}},
    )
    sentinel = init_permissions.load_canonical()["sentinel"]

    assert init_permissions.is_initialized(str(tmp_path), sentinel) is False


def _stop_commands(working_dir):
    settings = json.loads(
        (working_dir / ".claude" / "settings.local.json").read_text(encoding="utf-8")
    )
    return [h["command"] for g in settings["hooks"]["Stop"] for h in g["hooks"]]


def test_fresh_dir_gets_session_cost_hook(tmp_path):
    init_permissions.merge_permissions(str(tmp_path))

    assert init_permissions.merge_hooks(str(tmp_path)) is True
    cmds = _stop_commands(tmp_path)
    assert any("session_cost.py" in c and "--hook" in c for c in cmds)
    assert all("{session_cost_path}" not in c for c in cmds)


def test_hook_merge_is_idempotent(tmp_path):
    init_permissions.merge_hooks(str(tmp_path))

    assert init_permissions.merge_hooks(str(tmp_path)) is False
    assert len(_stop_commands(tmp_path)) == 1


def test_hook_merge_preserves_user_stop_hook(tmp_path):
    _write_settings(
        tmp_path,
        {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo bye"}]}]}},
    )

    init_permissions.merge_hooks(str(tmp_path))

    cmds = _stop_commands(tmp_path)
    assert "echo bye" in cmds
    assert any("session_cost.py" in c for c in cmds)


def test_scaffold_directories_creates_expected_tree(tmp_path):
    created = init_permissions.scaffold_directories(str(tmp_path))

    assert set(created) == {"build", "stl", "preview"}
    for name in ("build", "stl", "preview"):
        assert (tmp_path / name).is_dir()


def test_scaffold_directories_is_idempotent(tmp_path):
    init_permissions.scaffold_directories(str(tmp_path))

    created_again = init_permissions.scaffold_directories(str(tmp_path))

    assert created_again == []
    for name in ("build", "stl", "preview"):
        assert (tmp_path / name).is_dir()


def test_scaffold_directories_preserves_existing_contents(tmp_path):
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    (build_dir / "body.py").write_text("# existing part script", encoding="utf-8")

    created = init_permissions.scaffold_directories(str(tmp_path))

    assert "build" not in created
    assert (build_dir / "body.py").exists()


def test_seed_default_files_creates_then_never_overwrites(tmp_path):
    created = init_permissions.seed_default_files(str(tmp_path))
    assert set(created) == {"profile.json", "skill_config.json"}
    json.loads((tmp_path / "profile.json").read_text(encoding="utf-8"))

    (tmp_path / "skill_config.json").write_text("{}", encoding="utf-8")
    assert init_permissions.seed_default_files(str(tmp_path)) == []
    assert (tmp_path / "skill_config.json").read_text(encoding="utf-8") == "{}"


def test_merge_env_sets_once_and_preserves_keys(tmp_path):
    _write_settings(tmp_path, {"permissions": {"allow": ["Bash(x)"]}})

    assert init_permissions.merge_env(str(tmp_path), "/data/venv") is True
    assert init_permissions.merge_env(str(tmp_path), "/data/venv") is False

    path = tmp_path / ".claude" / "settings.local.json"
    settings = json.loads(path.read_text(encoding="utf-8"))
    assert settings["env"]["UV_PROJECT_ENVIRONMENT"] == "/data/venv"
    assert settings["permissions"]["allow"] == ["Bash(x)"]


def test_merge_hooks_replaces_stale_install_path(tmp_path):
    old = 'python "/old/cache/1.0/src/session_cost.py" --hook'
    _write_settings(
        tmp_path, {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": old}]}]}}
    )

    assert init_permissions.merge_hooks(str(tmp_path)) is True

    path = tmp_path / ".claude" / "settings.local.json"
    stop = json.loads(path.read_text(encoding="utf-8"))["hooks"]["Stop"]
    commands = [h["command"] for g in stop for h in g["hooks"]]
    assert old not in commands
    assert len(commands) == 1 and commands[0].endswith('session_cost.py" --hook')
    assert init_permissions.merge_hooks(str(tmp_path)) is False
