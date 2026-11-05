"""Script history: run recording, restore targets, marks (no CadQuery)."""

import json

import pytest
from conftest import minimal_plan

import script_history as sh


@pytest.fixture
def script(tmp_path, monkeypatch):
    monkeypatch.delenv(sh.SKIP_ENV, raising=False)
    build = tmp_path / "build"
    build.mkdir()
    return build / "plate.py"


def _run(script, text, ok=True, **kw):
    script.write_text(text, encoding="utf-8")
    sh.record_run(script, ok, **kw)


def _blobs(script):
    return sorted(p.name for p in sh.history_dir(script).glob("*.py"))


def test_distinct_sources_get_one_blob_each(script):
    _run(script, "a = 1\n")
    _run(script, "a = 1\n")
    _run(script, "a = 2\n")
    assert len(_blobs(script)) == 2
    runs = [e for e in sh._events(script) if e["event"] == "run"]
    assert [r["src"] for r in runs] == [
        sh.source_hash("a = 1\n"),
        sh.source_hash("a = 1\n"),
        sh.source_hash("a = 2\n"),
    ]


def test_skip_env_records_nothing(script, monkeypatch):
    monkeypatch.setenv(sh.SKIP_ENV, "1")
    _run(script, "a = 1\n")
    assert not sh.history_dir(script).exists()


def test_unwritable_history_only_warns(script, capsys):
    (script.parent / "history").write_text("not a dir", encoding="utf-8")
    _run(script, "a = 1\n")
    assert "run not recorded" in capsys.readouterr().err


def test_restore_prev_undoes_the_last_edit(script):
    _run(script, "a = 1\n")
    _run(script, "a = 2\n", ok=False)
    result = sh.restore(script, "@prev")
    assert result["success"] and script.read_text(encoding="utf-8") == "a = 1\n"
    restores = [e for e in sh._events(script) if e["event"] == "restore"]
    assert restores[-1]["replaced"] == sh.source_hash("a = 2\n")


def test_restore_last_ok_skips_failed_and_suppressed_runs(script):
    _run(script, "a = 1\n")
    _run(script, "a = 2\n", suppressed=["boss"])
    _run(script, "a = 3\n", ok=False)
    assert sh.restore(script, "@last_ok")["success"]
    assert script.read_text(encoding="utf-8") == "a = 1\n"


def test_mark_and_restore_by_name(script):
    _run(script, "a = 1\n")
    assert sh.mark(script, "accepted")["success"]
    _run(script, "a = 2\n")
    assert sh.restore(script, "accepted")["success"]
    assert script.read_text(encoding="utf-8") == "a = 1\n"


def test_mark_rejects_reserved_prefix(script):
    _run(script, "a = 1\n")
    assert not sh.mark(script, "@mine")["success"]


def test_restore_by_hash_prefix_and_ambiguity(script):
    _run(script, "a = 1\n")
    _run(script, "a = 2\n")
    sha = sh.source_hash("a = 1\n")
    assert sh.restore(script, f"@{sha[:6]}")["success"]
    assert script.read_text(encoding="utf-8") == "a = 1\n"
    (sh.history_dir(script) / f"{sha[:4]}zz.py").write_text("x\n", encoding="utf-8")
    before = script.read_text(encoding="utf-8")
    result = sh.restore(script, f"@{sha[:4]}")
    assert not result["success"] and "ambiguous" in result["error"]
    assert script.read_text(encoding="utf-8") == before


def test_unknown_target_leaves_script_unchanged(script):
    _run(script, "a = 1\n")
    result = sh.restore(script, "nope")
    assert not result["success"] and script.read_text(encoding="utf-8") == "a = 1\n"


def test_restore_appends_step_worker_restore_event(script):
    steps = script.parent / "plate.steps.jsonl"
    steps.write_text("", encoding="utf-8")
    _run(script, "a = 1\n")
    _run(script, "a = 2\n")
    sh.restore(script, "@prev")
    events = [json.loads(line) for line in steps.read_text(encoding="utf-8").splitlines()]
    assert events[-1]["event"] == "restore" and events[-1]["name"] == "@prev"


def test_restore_across_plan_revisions_warns(script):
    plan = minimal_plan([{"id": "plate", "description": "plate"}])
    plan_path = script.parent.parent / "BUILD_PLAN.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    _run(script, "a = 1\n", attempt=1)
    plan["request_log"] = [{"kind": "correction", "text": "wider", "targets": ["plate"]}]
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    _run(script, "a = 2\n", attempt=2)
    result = sh.restore(script, "@prev")
    assert result["warning"] == "attempt_mismatch"
    assert result["attempts"] == {"source": 1, "current": 2}
