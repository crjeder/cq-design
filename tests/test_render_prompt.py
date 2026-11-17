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


def _names(plan, part):
    return [i["name"] for i in rp.ranked_interfaces(plan, part)]


def test_ranking_prompt_then_clarification_then_correction_then_mention_then_size():
    plan, part = _plan()
    for itf, size in zip(part["interfaces"], (None, 9, None, None, None), strict=False):
        if size:
            itf["diameter_mm"] = size
    # newest entry names c; clarification/correction/initial hits follow; b (unmentioned) last
    assert _names(plan, part) == ["c", "d", "a", "b"]


def test_ranking_user_changed_small_feature_beats_larger_one():
    plan, part = _plan(
        request_log=[
            {"ts": "t", "kind": "initial", "text": "a lid"},
            {"ts": "t", "kind": "correction", "text": "shrink", "targets": ["lid.d"]},
            {"ts": "t", "kind": "initial", "text": "unrelated"},
        ]
    )
    part["interfaces"][1]["diameter_mm"] = 20  # b: big, untouched
    part["interfaces"][3]["diameter_mm"] = 2  # d: small, corrected
    names = _names(plan, part)
    assert names.index("d") < names.index("b")


def test_ranking_unmentioned_sorted_by_size():
    plan, part = _plan(request_log=[{"ts": "t", "kind": "initial", "text": "nothing"}])
    part["interfaces"][2]["size_mm"] = [4, 12]  # c
    part["interfaces"][1]["diameter_mm"] = 6  # b
    assert _names(plan, part) == ["c", "b", "a", "d"]


def test_fallback_cut_uses_wall_axis_else_largest_component():
    _, part = _plan()
    assert rp.fallback_cut(part["interfaces"][0]) == "y=-25"  # south wall -> y
    assert rp.fallback_cut(part["interfaces"][1]) == "x=30"  # largest component


def test_validate_args_have_no_callouts():
    plan, part = _plan()
    args = rp.validate_args(plan, part)
    assert "--callout" not in args and "--unlocated-name" not in args
    assert "--expected-dims 80,50,4" in args
    assert "--attempts-log build/attempts.jsonl --model " in args


def test_validate_args_emits_ranked_features_and_sheet():
    plan, part = _plan()
    part["interfaces"][0]["diameter_mm"] = 5
    args = rp.validate_args(plan, part)
    feats = [a for a in args.split(" --") if a.startswith("feature ")]
    assert [f.split("name=")[1].split(";")[0] for f in feats] == ["c", "d", "a", "b"]
    assert '--feature "name=a;center=10,-25,2;diameter=5;section=y=-25"' in args
    assert args.endswith("--sheet") and "--extra-section" not in args


def test_validate_args_sheet_without_positioned_interfaces():
    plan, part = _plan()
    part["interfaces"] = [{"type": "port_cutout", "name": "e"}]
    args = rp.validate_args(plan, part)
    assert "--feature" not in args and args.endswith("--sheet")


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


def test_builder_cli_prints_configured_model(tmp_path, monkeypatch, capsys):
    plan, _ = _plan()
    (tmp_path / "BUILD_PLAN.json").write_text(json.dumps(plan), encoding="utf-8")
    (tmp_path / "skill_config.json").write_text(
        json.dumps({"models": {"part_author": "claude-haiku-4-5-20251001"}}), encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    assert rp.main(["builder", "--plan", "BUILD_PLAN.json", "--part", "lid"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["model"] == "claude-haiku-4-5-20251001"


def test_builder_cli_prints_default_model_without_config(tmp_path, monkeypatch, capsys):
    plan, _ = _plan()
    (tmp_path / "BUILD_PLAN.json").write_text(json.dumps(plan), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert rp.main(["builder", "--plan", "BUILD_PLAN.json", "--part", "lid"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["model"] == "claude-sonnet-5-5"


def test_agent_model_alias():
    assert rp.agent_model_alias("claude-sonnet-5-5") == "sonnet"
    assert rp.agent_model_alias("claude-opus-5-5") == "opus"
    assert rp.agent_model_alias("claude-haiku-4-5-20251001") == "haiku"
    assert rp.agent_model_alias("claude-fable-5-1") == "fable"
    assert rp.agent_model_alias("mystery-model") == "mystery-model"


def test_builder_cli_prints_agent_model(tmp_path, monkeypatch, capsys):
    plan, _ = _plan()
    (tmp_path / "BUILD_PLAN.json").write_text(json.dumps(plan), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert rp.main(["builder", "--plan", "BUILD_PLAN.json", "--part", "lid"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert (out["model"], out["agent_model"]) == ("claude-sonnet-5-5", "sonnet")


def test_every_eval_case_renders_without_placeholders(tmp_path):
    for case in sorted(p for p in CASES.iterdir() if p.is_dir()):
        plan = json.loads((case / "BUILD_PLAN.json").read_text(encoding="utf-8"))
        for part in plan["parts"]:
            text, _ = rp.render_builder(plan, part, None, None)
            assert "{{PART_ID}}" not in text and "{{VALIDATE_ARGS}}" not in text, case.name


def test_cq_reference_default_part_gets_only_always_sections():
    plan, part = _plan()
    text, _ = rp.render_builder(plan, part, None, None)
    assert "## CadQuery Workplane Naming" in text
    assert "## Advanced 3D Operations" not in text
    assert "## Non-Overlapping Part Assembly" not in text
    assert "Booleans are expensive" not in text
    assert "Origin drift after" not in text


def test_cq_reference_multi_union_part_gets_compound_assembly_section():
    plan, part = _plan()
    part = {**part, "unions": [{"id": "a"}, {"id": "b"}]}
    text, _ = rp.render_builder(plan, part, None, None)
    assert "## Non-Overlapping Part Assembly" in text


def test_cq_reference_revolve_description_gets_adv3d_section():
    plan, part = _plan()
    part = {**part, "description": "a knob you revolve around its axis"}
    text, _ = rp.render_builder(plan, part, None, None)
    assert "## Advanced 3D Operations" in text


def test_text_part_injects_emboss_reference_without_placeholder_error():
    plan, part = _plan()
    text, _ = rp.render_builder(
        plan, {**part, "description": "lid with an embossed label"}, None, None
    )
    assert "# Emboss & Deboss Text Reference" in text


def test_render_planning_fresh_plan_lists_inventory_and_archetypes(tmp_path):
    profile = tmp_path / "profile.json"
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
    assert "hollow_box" in text
    assert "enclosure-body" in text
    assert "Prusa MK4" in text
    assert "{{" not in text
    assert "## Print Orientation" in text
    assert "## Vase Mode" not in text
    assert "Every unprobed request dimension becomes an authored probe" in text
    assert '"kind": "solid_at"' in text and '"kind": "empty_at"' in text


def test_render_planning_replan_includes_block_tagged_fdm_section():
    plan = json.loads((CASES / "boss-plate" / "BUILD_PLAN.json").read_text(encoding="utf-8"))
    fresh_text, _, _ = rp.render_planning("req", None, Path("does-not-exist.json"))
    replan_text, _, _ = rp.render_planning("req", plan, Path("does-not-exist.json"))
    assert replan_text != fresh_text
    assert len(replan_text) > len(fresh_text)


def test_render_planning_absent_and_invalid_profile(tmp_path):
    missing = tmp_path / "profile.json"
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
    assert '"candidates"' in text
    assert "rung-3-only (ND, redistribution permitted)" in text


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


def test_builder_prompt_has_horizontal_hole_rule(tmp_path, monkeypatch, capsys):
    plan, _ = _plan()
    (tmp_path / "BUILD_PLAN.json").write_text(json.dumps(plan), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert rp.main(["builder", "--plan", "BUILD_PLAN.json", "--part", "lid"]) == 0
    prompt = Path(json.loads(capsys.readouterr().out)["out"]).read_text(encoding="utf-8")
    assert "teardrop_bore" in prompt and '`"auto"`' in prompt
    assert 'script_lint.py" --step' in prompt and 'step_worker.py" run' in prompt


def test_audit_with_passing_step_report_drops_settled_questions(tmp_path):
    script = tmp_path / "lid.py"
    script.write_text("from blocks import Part\npart = Part('lid')\nresult = part.result()\n")
    plan, part = _plan()
    report = {"success": True, "unprobed_interfaces": ["a", "e"]}
    settled = rp.render_audit(plan, part, script, ["preview/lid_preview.png"], report)
    asked = rp.render_audit(plan, part, script, ["preview/lid_preview.png"])
    assert "U1 single connected body: **settled**" in settled
    assert "Cite a **section** crossing" in asked and "settled" not in asked
    assert (
        "plan probes** (do not ask presence, position or through-continuity): b, c, d." in settled
    )


def test_planning_inventory_lists_params_and_edge_sets():
    lines = rp._inventory_lines(
        [
            {
                "name": "box",
                "kind": "primitive",
                "use": "A box.",
                "params": {"w": "mm", "h": "mm"},
                "edge_sets": {"vertical": "x"},
            },
            {
                "name": "torus",
                "kind": "primitive",
                "use": "A rod.",
                "params": {"r": "mm", "angle": "deg"},
                "optional": ["angle"],
                "edge_sets": {},
            },
        ]
    )
    assert "Params: w, h; edges: vertical" in lines and "Params: r, angle?" in lines


def test_oracle_prompt_has_request_and_no_plan(tmp_path, monkeypatch, capsys):
    plan, _ = _plan(intent="PLAN_ONLY_MARKER")
    (tmp_path / "BUILD_PLAN.json").write_text(json.dumps(plan), encoding="utf-8")
    req = tmp_path / "oracle_request.md"
    req.write_text("Broom hook, handle assumed 24 mm (HANDLE_DIAMETER_MM)", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert rp.main(["oracle", "--request-file", str(req)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert (out["model"], out["agent_model"]) == ("claude-sonnet-5-5", "sonnet")
    text = Path(out["out"]).read_text(encoding="utf-8")
    assert "handle assumed 24 mm" in text and "PLAN_ONLY_MARKER" not in text
    assert "{{" not in text


def test_audit_cli_adds_bound_visual_statements(tmp_path, monkeypatch, capsys):
    script = tmp_path / "lid.py"
    script.write_text("result = None\n")
    plan, _ = _plan(acceptance_bindings=[{"statement": "S2", "part": "lid"}])
    (tmp_path / "BUILD_PLAN.json").write_text(json.dumps(plan), encoding="utf-8")
    doc = {
        "schema_version": 1,
        "statements": [
            {"id": "S1", "kind": "visual", "cites": ["x"], "text": "unbound look"},
            {"id": "S2", "kind": "visual", "cites": ["x"], "text": "rounded, friendly look"},
        ],
    }
    (tmp_path / "acceptance.json").write_text(json.dumps(doc), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    argv = [
        "audit",
        "--plan",
        "BUILD_PLAN.json",
        "--part",
        "lid",
        "--script",
        str(script),
        "--previews",
        "preview/lid_preview.png",
    ]
    assert rp.main(argv) == 0
    text = Path(json.loads(capsys.readouterr().out)["out"]).read_text(encoding="utf-8")
    assert "- S2: rounded, friendly look" in text and "unbound look" not in text
    assert "result = None" not in text


def test_render_builder_scope_line():
    plan, part = _plan()
    text, _ = rp.render_builder(plan, part, None, None)
    assert f"Your scope is part `{part['id']}`" in text
