"""regen_prompt.py rendering + CLI -- fast, no CadQuery."""

import json

import regen_prompt

_INTENT = "A wall hook that carries a broom by its handle, screwed to a stud."

_PLAN = {
    "intent": _INTENT,
    "printer": "Bambu P1S",
    "material": "PETG",
    "nozzle_mm": 0.4,
    "constraints": {"wall_min_mm": 1.2},
    "request_log": [
        {
            "ts": "2026-01-01T00:00:00Z",
            "kind": "initial",
            "text": "hook for my broom",
            "images": ["sketches/broom.jpg"],
        },
        {
            "ts": "2026-01-01T00:10:00Z",
            "kind": "correction",
            "text": "make the throat 2mm wider",
            "level": "parameter",
            "targets": ["hook.throat_mm"],
        },
    ],
    "parts": [
        {
            "id": "hook",
            "description": "J-hook | plate",
            "dimensions": {"w_mm": 20},
            "engineering_rationale": {
                "load_path": "hook arm cantilevers from the wall plate",
                "worst_case_stress": "arm root",
                "check": "strain = 1.5*t*d/L^2 = 1.0% <= 4.0% allowable (PETG)",
            },
        }
    ],
    "joints": [
        {
            "joint_id": "j1",
            "block": "dovetail",
            "members": [
                {"part": "hook", "member": "tongue"},
                {"part": "plate", "member": "groove"},
            ],
        }
    ],
    "root_part": "plate",
}


def test_render_includes_intent_history_and_target():
    out = regen_prompt.render(_PLAN)
    assert _INTENT in out
    assert "> hook for my broom" in out
    assert "> make the throat 2mm wider" in out
    assert "sketches/broom.jpg" in out
    assert "targets: hook.throat_mm" in out
    assert "wall_min_mm: 1.2" in out
    assert "`j1`: dovetail -- hook.tongue + plate.groove" in out
    assert r"J-hook \| plate" in out


def test_render_omits_optional_sections_when_absent():
    out = regen_prompt.render({"intent": "x" * 130, "parts": []})
    assert "Request history" not in out
    assert "Sourced measurements" not in out
    assert "User-supplied drawings" not in out
    assert "Engineering rationale" not in out


def test_render_includes_engineering_rationale_object_form():
    out = regen_prompt.render(_PLAN)
    assert "## Engineering rationale" in out
    assert "hook arm cantilevers from the wall plate" in out
    assert "arm root" in out
    assert "strain = 1.5*t*d/L^2 = 1.0% <= 4.0% allowable (PETG)" in out


def test_render_includes_engineering_rationale_string_form():
    plan = json.loads(json.dumps(_PLAN))
    plan["parts"][0]["engineering_rationale"] = "no load-bearing features (decorative hook)"
    out = regen_prompt.render(plan)
    assert "no load-bearing features (decorative hook)" in out


def test_render_embeds_parameters_and_sketches():
    out = regen_prompt.render(
        _PLAN, parameters_src="BROOM_D_MM = 24  # measured\n", sketches=["sketches/broom.jpg"]
    )
    assert "BROOM_D_MM = 24  # measured" in out
    assert "User-supplied drawings" in out


def test_cli_writes_file_and_picks_up_side_artifacts(tmp_path):
    (tmp_path / "BUILD_PLAN.json").write_text(json.dumps(_PLAN), encoding="utf-8")
    (tmp_path / "parameters.py").write_text("BROOM_D_MM = 24\n", encoding="utf-8")
    (tmp_path / "sketches").mkdir()
    (tmp_path / "sketches" / "broom.jpg").write_bytes(b"x")
    out = tmp_path / "REGENERATE.md"

    assert regen_prompt.main(["--plan", str(tmp_path / "BUILD_PLAN.json"), "--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert "BROOM_D_MM = 24" in text
    assert "- `sketches/broom.jpg`" in text


def test_cli_missing_plan_returns_1(tmp_path):
    assert regen_prompt.main(["--plan", str(tmp_path / "nope.json")]) == 1
