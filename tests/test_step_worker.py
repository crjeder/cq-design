"""Step worker: prefix cache, stop-at-first-failure reports, snapshots, stuck detection,
and the warm worker with its cold fallback."""

import json

import pytest
from conftest import minimal_plan

import step_worker as sw

PLATE = {"name": "box", "id": "plate", "params": {"w": 40, "d": 30, "h": 4}}
BOSS = {"name": "screw_boss", "id": "boss", "params": {"d_screw": 3.2, "d_outer": 8, "h": 6}}
HOLE = {"name": "cylinder", "id": "hole", "params": {"d": 4, "h": 10}}
PLUG = {"name": "cylinder", "id": "plug", "params": {"d": 3, "h": 6}}
BORE = {
    "type": "screw_mount",
    "name": "bore",
    "instance": "boss",
    "position_mm": [10, 5, 8.5],
    "diameter_mm": 3.2,
}

SCRIPT = """from blocks import Part

part = Part("plate")
plate = part.select("box", id="plate")
part.resize(plate)
part.place(plate, op="base")
boss = part.select("screw_boss", id="boss")
part.resize(boss)
part.place(boss, at=(10, 5, part.param("plate", "h")), op="union")
hole = part.select("cylinder", id="hole")
part.resize(hole)
part.place(hole, at=HOLE_AT, op="cut")
result = part.result()
"""


@pytest.fixture
def project(tmp_path, monkeypatch):
    build = tmp_path / "build"
    build.mkdir()
    plan_path = tmp_path / "BUILD_PLAN.json"

    def _write(hole_at=(-10, -5, -1), blocks=(PLATE, BOSS, HOLE), body=SCRIPT, boss_h=6, hole_d=4):
        boss = {**BOSS, "params": {**BOSS["params"], "h": boss_h}}
        hole = {**HOLE, "params": {**HOLE["params"], "d": hole_d}}
        swap = {"boss": boss, "hole": hole}
        blocks = [swap.get(b["id"], b) for b in blocks]
        part = {
            "id": "plate",
            "description": "Plate with a boss",
            "interfaces": [BORE],
            "dimensions": {"w_mm": 40, "d_mm": 30, "h_mm": 4 + boss_h},
            "blocks_needed": blocks,
        }
        plan_path.write_text(json.dumps(minimal_plan([part])), encoding="utf-8")
        script = build / "plate.py"
        script.write_text(body.replace("HOLE_AT", repr(tuple(hole_at))), encoding="utf-8")
        return script

    monkeypatch.setenv("CQ_PLAN", str(plan_path))
    return _write


def _cached(report):
    return [s.get("cached", False) for s in report["steps"] if s["kind"] != "result"]


def test_unchanged_rerun_is_served_from_cache(project):
    script, cache = project(), {}
    first = sw.run_steps(script, cache)
    assert first["success"] and not any(_cached(first))
    assert all(_cached(sw.run_steps(script, cache)))


def test_editing_a_step_reuses_the_steps_before_it(project):
    script, cache = project(), {}
    sw.run_steps(script, cache)
    project(hole_at=(10, -5, -1))
    report = sw.run_steps(script, cache)
    assert _cached(report) == [True] * 8 + [False]


def test_plan_edit_invalidates_from_the_first_step_reading_it(project):
    script, cache = project(), {}
    sw.run_steps(script, cache)
    project(hole_d=3)
    report = sw.run_steps(script, cache)
    assert report["success"], report.get("error")
    # the hole resize (step 7) reads the edited value; everything from there re-runs
    assert _cached(report) == [True] * 7 + [False] * 2


def test_envelope_edit_invalidates_every_step(project):
    script, cache = project(), {}
    sw.run_steps(script, cache)
    project(boss_h=8)
    report = sw.run_steps(script, cache)
    assert report["success"], report.get("error")
    assert not any(_cached(report))


def test_run_stops_at_the_first_failing_step(project):
    script = project(hole_at=(100, 100, 0))  # the cut misses the body
    report = sw.run_steps(script, None)
    assert not report["success"] and report["failed_step"] == 8
    assert report["steps"][-1]["index"] == 8
    diff = report["diff_vs_last_good"]
    assert diff["last_good"]["volume"] == diff["failed"]["volume"]


def test_later_step_breaking_a_plan_probe_names_the_plan_probe(project):
    body = SCRIPT.replace('"cylinder", id="hole"', '"cylinder", id="plug"').replace(
        'part.resize(hole)\npart.place(hole, at=HOLE_AT, op="cut")',
        'part.resize(hole)\npart.place(hole, at=(10, 5, 4), op="union")',
    )
    script = project(blocks=(PLATE, BOSS, PLUG), body=body)
    report = sw.run_steps(script, None)
    assert report["failed_step"] == 8
    assert [(p["owner"], p["label"]) for p in report["failing_probes"]] == [("plan", "bore")]


def test_snapshot_restore_rewrites_the_script_and_compare_reports(project):
    script, cache = project(), {}
    assert sw.snapshot("save", ["v1"], script, cache)["success"]
    original = script.read_text(encoding="utf-8")
    project(hole_at=(10, -5, -1))
    assert sw.snapshot("save", ["v2"], script, cache)["success"]
    assert sw.snapshot("restore", ["v1"], script, cache)["restored"] == "v1"
    assert script.read_text(encoding="utf-8") == original
    assert all(_cached(sw.run_steps(script, cache)))
    cmp = sw.snapshot("compare", ["v1", "v2"], script, cache)
    assert cmp["v1"]["volume"] == pytest.approx(cmp["v2"]["volume"])
    assert cmp["v1"]["bbox"] == cmp["v2"]["bbox"]


def _plug_script(project, at):
    body = SCRIPT.replace('"cylinder", id="hole"', '"cylinder", id="plug"').replace(
        'part.place(hole, at=HOLE_AT, op="cut")', f'part.place(hole, at={at!r}, op="union")'
    )
    return project(blocks=(PLATE, BOSS, PLUG), body=body)


def test_same_probe_failing_after_a_changed_step_is_stuck(project):
    assert not sw.run_steps(_plug_script(project, (10, 5, 4)), None)["probe_stuck"]
    report = sw.run_steps(_plug_script(project, (10, 5, 4.5)), None)
    assert report["probe_stuck"] and report["stuck_occurrences"]


def test_rerun_of_the_same_step_is_not_stuck(project):
    script = _plug_script(project, (10, 5, 4))
    sw.run_steps(script, None)
    assert not sw.run_steps(script, None)["probe_stuck"]


def test_a_different_probe_failing_is_not_stuck(project):
    sw.run_steps(_plug_script(project, (10, 5, 4)), None)  # fails the plan bore probe
    report = sw.run_steps(_plug_script(project, (100, 100, 0)), None)  # floating plug
    assert report["failed_step"] == 8 and not report["probe_stuck"]


def test_warm_worker_reused_then_cold_fallback_after_crash(project):
    script = project()
    try:
        first = sw.request_worker({"cmd": "run", "script": str(script)})
        pid = json.loads((script.parent / sw.ADDRESS_FILE).read_text())["pid"]
        second = sw.request_worker({"cmd": "run", "script": str(script)})
        assert first["worker"] == second["worker"] == "warm"
        assert json.loads((script.parent / sw.ADDRESS_FILE).read_text())["pid"] == pid
        assert all(_cached(second))

        crash = "import os\nif os.environ.get('CQ_STEP_WORKER'):\n    os._exit(3)\n"
        script.write_text(crash + script.read_text(encoding="utf-8"), encoding="utf-8")
        report = sw.request_worker({"cmd": "run", "script": str(script)})
        assert report["worker"] == "fallback" and report["success"]
    finally:
        _, info = sw._connect(script.parent)
        sw._kill(info)
