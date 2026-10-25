"""Per-union material/color resolution, filament slots, summary warning, schema (no CadQuery)."""

import json
from pathlib import Path

import jsonschema
from conftest import minimal_plan

from plan import summarize
from units import assign_slots, color_of, material_of, union_materials

SRC = Path(__file__).resolve().parent.parent / "src"


def _plan(parts):
    plan = minimal_plan(parts)
    for p in parts:
        p.setdefault("description", p["id"])
        p.setdefault("dimensions", {"w_mm": 1, "d_mm": 1, "h_mm": 1})
    return plan


def test_resolution_order_union_part_plan():
    plan = _plan(
        [
            {"id": "body"},
            {
                "id": "grip",
                "material": "TPU",
                "unions": [{"id": "pad"}, {"id": "rim", "material": "PETG"}],
            },
        ]
    )
    assert {u: m for u, (m, _c) in union_materials(plan).items()} == {
        "body": "PLA",
        "pad": "TPU",
        "rim": "PETG",
    }


def test_color_defaults_from_material_and_explicit_wins():
    plan = _plan([{"id": "a", "color": "#ff0000"}, {"id": "b", "material": "TPU"}])
    assert color_of(plan, plan["parts"][0]) == "#FF0000"
    assert color_of(plan, plan["parts"][1]) != color_of(plan, {"id": "x"})
    assert material_of(plan, plan["parts"][1]) == "TPU"


def test_slots_follow_first_appearance_and_share_equal_pairs():
    plan = _plan(
        [{"id": "a"}, {"id": "b", "material": "TPU"}, {"id": "c"}, {"id": "d", "material": "PVA"}]
    )
    assert assign_slots(plan) == {"a": 1, "b": 2, "c": 1, "d": 3}


def test_touching_materials_say_nothing_and_single_material_has_no_block():
    single = _plan([{"id": "a"}, {"id": "b"}])
    assert "**Materials**" not in summarize(single, Path("BUILD_PLAN.json"))


def test_summary_warns_when_slots_exceeded():
    parts = [{"id": f"p{i}", "color": f"#00000{i}"} for i in range(5)]
    plan = _plan(parts)
    text = summarize(plan, Path("BUILD_PLAN.json"), max_materials=4)
    assert "5 materials, 4 slots" in text
    assert "5 materials" not in summarize(plan, Path("BUILD_PLAN.json"), max_materials=5)


def test_schema_accepts_material_color_and_profile_slots():
    plan_schema = json.loads((SRC / "build_plan_schema.json").read_text(encoding="utf-8"))
    plan = _plan([{"id": "a", "material": "PVA", "unions": [{"id": "a", "color": "#AABBCC"}]}])
    plan.update(
        schema_version=1,
        intent="x" * 40,
    )
    errors = [
        e.message
        for e in jsonschema.Draft7Validator(plan_schema).iter_errors(plan)
        if "material" in e.message or "color" in e.message or "Additional" in e.message
    ]
    assert errors == []

    profile_schema = json.loads((SRC / "printer_profile_schema.json").read_text(encoding="utf-8"))
    sub = {
        "type": "object",
        "properties": {"max_materials": profile_schema["properties"]["max_materials"]},
    }
    assert list(jsonschema.Draft7Validator(sub).iter_errors({"max_materials": 4})) == []
    assert list(jsonschema.Draft7Validator(sub).iter_errors({"max_materials": 0})) != []
