"""Quality-gate plan_probes stage: authored probes checked on a plain part script."""

from conftest import minimal_plan

import quality_gate

WALL = [
    {"kind": "solid_at", "p": [0, 0, 0], "label": "A-A: wall"},
    {"kind": "empty_at", "p": [0, 0, 20], "label": "A-A: past wall"},
]


def _setup(tmp_path, offset, probes=WALL):
    script = tmp_path / "wall.py"
    script.write_text(
        "import cadquery as cq\n"
        f"result = cq.Workplane().box(10, 10, 2).translate((0, 0, {offset}))\n"
    )
    plan = minimal_plan([{"id": "wall", "description": "wall", "probes": probes}])
    return plan, str(script)


def test_wall_on_wrong_side_fails(tmp_path):
    plan, script = _setup(tmp_path, 5)
    issues = quality_gate._run_plan_probes_stage(plan, script)
    assert [i["label"] for i in issues] == ["A-A: wall"]
    assert issues[0]["type"] == "probe_unmet" and issues[0]["severity"] == "error"
    assert issues[0]["observed"] == "OUT"


def test_matching_profile_passes(tmp_path):
    plan, script = _setup(tmp_path, 0)
    assert quality_gate._run_plan_probes_stage(plan, script) == []


def test_oracle_bound_label_skipped(tmp_path):
    plan, script = _setup(tmp_path, 5)
    plan["acceptance_bindings"] = [{"statement": "S1", "part": "wall", "probes": ["A-A: wall"]}]
    assert quality_gate._run_plan_probes_stage(plan, script) == []


def test_no_probes_emits_nothing(tmp_path):
    plan, script = _setup(tmp_path, 5, probes=[])
    assert quality_gate._run_plan_probes_stage(plan, script) == []
