"""quality_gate.py parameters.py provenance-presence stage -- fast, no CadQuery."""

from quality_gate import _run_parameters_presence_stage


def _write_journal(
    tmp_path, line="- phase1/dimensions_approved: parameters.py written, 3 dimensions recorded\n"
):
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    (build_dir / "journal.md").write_text(line, encoding="utf-8")


def test_sourced_and_file_absent_warns(tmp_path):
    _write_journal(tmp_path)
    (issue,) = _run_parameters_presence_stage(str(tmp_path))
    assert issue["source"] == "parameters"
    assert issue["severity"] == "warning"
    assert issue["type"] == "parameters_missing"


def test_sourced_and_file_empty_warns(tmp_path):
    _write_journal(tmp_path)
    (tmp_path / "parameters.py").write_text("", encoding="utf-8")
    (issue,) = _run_parameters_presence_stage(str(tmp_path))
    assert issue["type"] == "parameters_missing"


def test_no_journal_is_silent(tmp_path):
    assert _run_parameters_presence_stage(str(tmp_path)) == []


def test_journal_without_milestone_is_silent(tmp_path):
    _write_journal(tmp_path, line="- phase2/plan_written: BUILD_PLAN.json validated, 4 parts\n")
    assert _run_parameters_presence_stage(str(tmp_path)) == []


def test_sourced_and_file_present_is_silent(tmp_path):
    _write_journal(tmp_path)
    (tmp_path / "parameters.py").write_text("WIDTH_MM = 385.0\n", encoding="utf-8")
    assert _run_parameters_presence_stage(str(tmp_path)) == []


def test_default_path_resolves_from_plan_dir(tmp_path, monkeypatch):
    import quality_gate

    monkeypatch.setattr(
        quality_gate, "_run_wrapper_check", lambda script_path, plan: ([], None, None)
    )
    monkeypatch.setattr(quality_gate, "_analyze_stl", lambda *a, **k: [])

    called = {}

    def fake_stage(project_root):
        called["root"] = project_root
        return []

    monkeypatch.setattr(quality_gate, "_run_parameters_presence_stage", fake_stage)

    build_dir = tmp_path / "build"
    build_dir.mkdir()
    script = build_dir / "lid.py"
    script.write_text("result = None\n", encoding="utf-8")
    plan = tmp_path / "BUILD_PLAN.json"
    plan.write_text('{"parts": []}', encoding="utf-8")

    quality_gate.run_gate(str(script), str(plan))

    assert called["root"] == str(tmp_path)


def test_finding_surfaces_without_failing_gate(tmp_path, monkeypatch):
    import quality_gate

    monkeypatch.setattr(
        quality_gate, "_run_wrapper_check", lambda script_path, plan: ([], None, None)
    )
    monkeypatch.setattr(quality_gate, "_analyze_stl", lambda *a, **k: [])

    _write_journal(tmp_path)

    build_dir = tmp_path / "build"
    script = build_dir / "lid.py"
    script.write_text("result = None\n", encoding="utf-8")
    plan = tmp_path / "BUILD_PLAN.json"
    plan.write_text('{"parts": []}', encoding="utf-8")

    report = quality_gate.run_gate(str(script), str(plan))

    types = [i["type"] for i in report["issues"]]
    assert "parameters_missing" in types
