import json
from pathlib import Path

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
