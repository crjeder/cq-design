import json
from pathlib import Path

import pytest

import render_prompt as rp

CASES = Path(__file__).parent.parent / "evals" / "cases"


def _plan(**over):
    part = {
        "id": "lid",
        "description": "flat lid",
        "dimensions": {"w_mm": 80, "d_mm": 50, "h_mm": 4},
        "blocks_needed": [],
        "interfaces": [
            {"type": "port_cutout", "name": "a", "wall": "south", "position_mm": [10, -25, 2]},
            {"type": "port_cutout", "name": "b", "position_mm": [30, 5, 1]},
            {"type": "port_cutout", "name": "c", "position_mm": [0, 0, 1]},
            {"type": "port_cutout", "name": "d", "position_mm": [0, 0, 3]},
            {"type": "port_cutout", "name": "e"},
        ],
    }
    plan = {
        "material": "PLA",
        "nozzle_mm": 0.4,
        "constraints": {"wall_min_mm": 1.2, "overhang_max_deg": 45, "dimension_tolerance_mm": 0.5},
        "parts": [part],
        "request_log": [
            {"ts": "t", "kind": "initial", "text": "a lid"},
            {"ts": "t", "kind": "correction", "text": "move d", "targets": ["lid.d"]},
            {"ts": "t", "kind": "clarification", "text": "c goes in the middle"},
        ],
    }
    plan.update(over)
    return plan, part


def test_stages_follow_review_policy_and_override():
    plan, part = _plan()
    assert rp.stages(plan, part, None) == ["profile_stub", "base_shape", "features", "finishing"]
    assert rp.stages({**plan, "review_policy": "minimal"}, part, None) == ["full"]
    assert rp.stages(plan, part, "autonomous") == ["full"]
    assert rp.stages(
        {**plan, "review_policy": "checkpoints"}, {**part, "interfaces": []}, None
    ) == [
        "profile_stub",
        "full",
    ]


def test_section_cuts_rank_clarification_then_correction_then_plan_order():
    plan, part = _plan()
    assert rp.section_cuts(plan, part) == ["z=1", "z=3", "y=-25"]


def test_validate_args_callouts_and_unlocated():
    plan, part = _plan()
    args = rp.validate_args(plan, part)
    assert '--callout "name=a;center=10,-25,2"' in args
    assert "--unlocated-name e" in args
    assert "--expected-dims 80,50,4" in args
    assert "--attempts-log build/attempts.jsonl --model " in args


def test_validate_args_expected_dims_only_when_final():
    plan, part = _plan()
    final = rp.validate_args(plan, part, True)
    non_final = rp.validate_args(plan, part, False)
    assert "--expected-dims" in final and "--dim-tolerance" in final
    assert "--expected-dims" not in non_final and "--dim-tolerance" not in non_final
    assert "--wall-min" in non_final and "--strict" in non_final


def test_render_builder_checks_dims_only_on_final_stage():
    plan, part = _plan()
    text, part_stages = rp.render_builder(plan, part, None, None)
    assert part_stages == ["profile_stub", "base_shape", "features", "finishing"]
    commands = text.split("# profile_stub", 1)[1]
    non_final_block, final_block = commands.rsplit("# finishing", 1)
    assert "--expected-dims" not in non_final_block
    assert "--expected-dims 80,50,4" in final_block


def test_every_eval_case_renders_without_placeholders(tmp_path):
    for case in sorted(p for p in CASES.iterdir() if p.is_dir()):
        plan = json.loads((case / "BUILD_PLAN.json").read_text(encoding="utf-8"))
        for part in plan["parts"]:
            text, _ = rp.render_builder(plan, part, None, None)
            assert "{{PART_ID}}" not in text and "{{VALIDATE_ARGS}}" not in text, case.name


def test_text_part_injects_emboss_reference_without_placeholder_error():
    plan, part = _plan()
    text, _ = rp.render_builder(
        plan, {**part, "description": "lid with an embossed label"}, None, None
    )
    assert "# Emboss & Deboss Text Reference" in text


def test_render_planning_fresh_plan_lists_inventory_and_archetypes(tmp_path):
    profile = tmp_path / "printer_profile.json"
    profile.write_text(
        json.dumps(
            {
                "printer": "Prusa MK4",
                "material": "PLA",
                "nozzle_mm": 0.4,
                "constraints": {
                    "wall_min_mm": 1.2,
                    "overhang_max_deg": 45,
                    "dimension_tolerance_mm": 0.5,
                },
            }
        ),
        encoding="utf-8",
    )
    text, status, errors = rp.render_planning("a small enclosure", None, profile)
    assert status == "loaded"
    assert errors == []
    assert "a small enclosure" in text
    assert "fillet_box" in text
    assert "enclosure-body" in text
    assert "Prusa MK4" in text
    assert "{{" not in text


def test_render_planning_replan_includes_block_tagged_fdm_section():
    plan = json.loads((CASES / "boss-plate" / "BUILD_PLAN.json").read_text(encoding="utf-8"))
    fresh_text, _, _ = rp.render_planning("req", None, Path("does-not-exist.json"))
    replan_text, _, _ = rp.render_planning("req", plan, Path("does-not-exist.json"))
    assert replan_text != fresh_text
    assert len(replan_text) > len(fresh_text)


def test_render_planning_absent_and_invalid_profile(tmp_path):
    missing = tmp_path / "printer_profile.json"
    text, status, errors = rp.render_planning("req", None, missing)
    assert status == "absent"
    assert errors == []
    assert "take printer, material, nozzle" in text

    invalid = tmp_path / "bad_profile.json"
    invalid.write_text(json.dumps({"printer": "X"}), encoding="utf-8")
    text, status, errors = rp.render_planning("req", None, invalid)
    assert status == "invalid"
    assert errors
    assert "take printer, material, nozzle" in text


def test_render_research_with_and_without_known_context():
    text = rp.render_research("- iPhone 15 Pro width", None)
    assert "iPhone 15 Pro width" in text
    assert "(none)" in text
    assert "{{" not in text

    text2 = rp.render_research("- widget width", "iPhone 15: 70.6mm per apple.com")
    assert "iPhone 15: 70.6mm per apple.com" in text2


def test_fill_raises_on_unfilled_placeholder():
    with pytest.raises(ValueError, match="unfilled placeholders"):
        rp.fill("hello {{MISSING}}", {})


def test_render_sourcing_includes_request_and_corpus():
    text = rp.render_sourcing("a wall mount for an iPhone 15")
    assert "a wall mount for an iPhone 15" in text
    assert "Adafruit_CAD_Parts" in text
    assert "{{" not in text


def test_sourcing_corpus_extracts_phase0_section():
    corpus = rp.sourcing_corpus()
    assert "Hardware & component archives" in corpus
    assert "Finished models by domain" in corpus
    assert "Blocks library candidates" not in corpus


def test_audit_parameters_block_skips_calls(tmp_path):
    script = tmp_path / "lid.py"
    script.write_text(
        "import cadquery as cq\nwidth = 40\nwall = 2 * 1.2\n"
        "result = cq.Workplane().box(width, 1, 1)\n"
    )
    assert rp.parameters_block(script) == "width = 40\nwall = 2 * 1.2"
    plan, part = _plan()
    text = rp.render_audit(plan, part, script, ["preview/lid_preview.png"])
    assert "skip group 4" in text
    assert "c goes in the middle" in text and "move d" in text
