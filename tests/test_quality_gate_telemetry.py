"""quality_gate.py telemetry-presence stage -- fast, no CadQuery."""

from quality_gate import _run_telemetry_stage


def test_absent_file_warns(tmp_path):
    (issue,) = _run_telemetry_stage(str(tmp_path / "attempts.jsonl"))
    assert issue["source"] == "telemetry"
    assert issue["severity"] == "warning"
    assert issue["type"] == "telemetry_missing"


def test_empty_file_warns(tmp_path):
    log = tmp_path / "attempts.jsonl"
    log.write_text("", encoding="utf-8")
    (issue,) = _run_telemetry_stage(str(log))
    assert issue["type"] == "telemetry_missing"


def test_blank_lines_only_warns(tmp_path):
    log = tmp_path / "attempts.jsonl"
    log.write_text("\n\n   \n", encoding="utf-8")
    (issue,) = _run_telemetry_stage(str(log))
    assert issue["type"] == "telemetry_missing"


def test_unparseable_content_warns(tmp_path):
    log = tmp_path / "attempts.jsonl"
    log.write_text("not json\nstill not json\n", encoding="utf-8")
    (issue,) = _run_telemetry_stage(str(log))
    assert issue["type"] == "telemetry_missing"


def test_populated_log_is_silent(tmp_path):
    log = tmp_path / "attempts.jsonl"
    log.write_text('{"part_id": "lid", "attempt": 1}\n', encoding="utf-8")
    assert _run_telemetry_stage(str(log)) == []


def test_populated_log_after_bad_lines_is_silent(tmp_path):
    log = tmp_path / "attempts.jsonl"
    log.write_text('not json\n{"part_id": "lid"}\n', encoding="utf-8")
    assert _run_telemetry_stage(str(log)) == []


def test_default_path_resolves_alongside_script(tmp_path, monkeypatch):
    import quality_gate

    called = {}

    def fake_wrapper_check(script_path, plan):
        return [], None, None, []

    def fake_analyze_stl(*a, **k):
        return []

    monkeypatch.setattr(quality_gate, "_run_wrapper_check", fake_wrapper_check)
    monkeypatch.setattr(quality_gate, "_analyze_stl", fake_analyze_stl)

    def fake_telemetry_stage(attempts_log):
        called["path"] = attempts_log
        return []

    monkeypatch.setattr(quality_gate, "_run_telemetry_stage", fake_telemetry_stage)

    build_dir = tmp_path / "build"
    build_dir.mkdir()
    script = build_dir / "lid.py"
    script.write_text("result = None\n", encoding="utf-8")
    plan = tmp_path / "BUILD_PLAN.json"
    plan.write_text('{"parts": []}', encoding="utf-8")

    quality_gate.run_gate(str(script), str(plan))

    assert called["path"] == str(build_dir / "attempts.jsonl")


def test_explicit_override_wins(tmp_path, monkeypatch):
    import quality_gate

    called = {}

    monkeypatch.setattr(
        quality_gate, "_run_wrapper_check", lambda script_path, plan: ([], None, None, [])
    )
    monkeypatch.setattr(quality_gate, "_analyze_stl", lambda *a, **k: [])

    def fake_telemetry_stage(attempts_log):
        called["path"] = attempts_log
        return []

    monkeypatch.setattr(quality_gate, "_run_telemetry_stage", fake_telemetry_stage)

    build_dir = tmp_path / "build"
    build_dir.mkdir()
    script = build_dir / "lid.py"
    script.write_text("result = None\n", encoding="utf-8")
    plan = tmp_path / "BUILD_PLAN.json"
    plan.write_text('{"parts": []}', encoding="utf-8")
    override = tmp_path / "custom" / "attempts.jsonl"

    quality_gate.run_gate(str(script), str(plan), attempts_log=str(override))

    assert called["path"] == str(override)
