"""Quality-gate oracle stage: bound statements verified on the built body."""

import json

from conftest import minimal_plan

import quality_gate

DOC = {
    "schema_version": 1,
    "statements": [
        {
            "id": "S1",
            "kind": "extent",
            "which": "largest",
            "max_mm": 80,
            "cites": ["at most 80 mm"],
            "text": "Largest extent at most 80 mm",
        },
        {"id": "S2", "kind": "probe", "cites": ["solid core"], "text": "Solid at the centre"},
    ],
}


def _setup(tmp_path, height):
    script = tmp_path / "block.py"
    script.write_text(f"import cadquery as cq\nresult = cq.Workplane().box(40, 30, {height})\n")
    plan = minimal_plan(
        [
            {
                "id": "block",
                "description": "block",
                "dimensions": {"w_mm": 40, "d_mm": 30, "h_mm": 60},
                "probes": [{"kind": "solid_at", "p": [0, 0, 0], "label": "S2: centre"}],
            }
        ]
    )
    plan["intent"] = "A block at most 80 mm tall with a solid core."
    plan["acceptance_bindings"] = [
        {"statement": "S1", "part": "block"},
        {"statement": "S2", "part": "block", "probes": ["S2: centre"]},
    ]
    plan_path = tmp_path / "BUILD_PLAN.json"
    plan_path.write_text(json.dumps(plan))
    return plan, str(plan_path), str(script)


def test_no_acceptance_file_no_stage(tmp_path):
    plan, plan_path, script = _setup(tmp_path, 131)
    assert quality_gate._run_oracle_stage(plan, plan_path, script, []) == []


def test_extent_exceeded_on_built_body(tmp_path):
    plan, plan_path, script = _setup(tmp_path, 131)
    (tmp_path / "acceptance.json").write_text(json.dumps(DOC))
    issues = quality_gate._run_oracle_stage(plan, plan_path, script, [])
    assert [i["statement"] for i in issues] == ["S1"]
    assert "131" in issues[0]["message"] and issues[0]["type"] == "oracle_unmet"


def test_statements_met(tmp_path):
    plan, plan_path, script = _setup(tmp_path, 60)
    (tmp_path / "acceptance.json").write_text(json.dumps(DOC))
    assert quality_gate._run_oracle_stage(plan, plan_path, script, []) == []
