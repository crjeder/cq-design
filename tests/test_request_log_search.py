"""request_log_search.py filter helper + CLI -- fast, no CadQuery."""

import json

import request_log_search


def _plan(entries):
    return {"request_log": entries}


_ENTRIES = [
    {"ts": "2026-01-01T00:00:00Z", "kind": "initial", "text": "Build a hinge bracket"},
    {"ts": "2026-01-01T00:05:00Z", "kind": "clarification", "text": "PLA, 0.4mm nozzle"},
    {"ts": "2026-01-01T00:10:00Z", "kind": "correction", "text": "Widen the hinge pin hole"},
]


def test_query_matches_substring_case_insensitive():
    results = request_log_search.search_request_log(_plan(_ENTRIES), query="HINGE")
    assert [e["text"] for e in results] == [
        "Build a hinge bracket",
        "Widen the hinge pin hole",
    ]


def test_kind_filter():
    results = request_log_search.search_request_log(_plan(_ENTRIES), kind="correction")
    assert [e["text"] for e in results] == ["Widen the hinge pin hole"]


def test_combined_query_and_kind():
    results = request_log_search.search_request_log(
        _plan(_ENTRIES), query="hinge", kind="correction"
    )
    assert [e["text"] for e in results] == ["Widen the hinge pin hole"]


def test_no_match_returns_empty_list():
    results = request_log_search.search_request_log(_plan(_ENTRIES), query="nonexistent")
    assert results == []


def test_absent_request_log_returns_empty_list():
    results = request_log_search.search_request_log({}, query="hinge")
    assert results == []


_TYPED_ENTRIES = [
    {"ts": "2026-01-01T00:00:00Z", "kind": "initial", "text": "Build a cradle"},
    {
        "ts": "2026-01-01T00:05:00Z",
        "kind": "correction",
        "text": "saddle 40mm wide",
        "level": "parameter",
        "targets": ["cradle", "cradle.saddle_width"],
    },
    {
        "ts": "2026-01-01T00:10:00Z",
        "kind": "correction",
        "text": "add a drain slot",
        "level": "operation",
        "targets": ["base"],
    },
]


def test_level_filter_excludes_untyped_entries():
    results = request_log_search.search_request_log(_plan(_TYPED_ENTRIES), level="parameter")
    assert [e["text"] for e in results] == ["saddle 40mm wide"]


def test_target_filter_matches_part_id_and_dotted_name():
    assert [
        e["text"]
        for e in request_log_search.search_request_log(_plan(_TYPED_ENTRIES), target="cradle")
    ] == ["saddle 40mm wide"]
    assert [
        e["text"]
        for e in request_log_search.search_request_log(_plan(_TYPED_ENTRIES), target="saddle_width")
    ] == ["saddle 40mm wide"]


def test_target_filter_excludes_entries_without_targets():
    results = request_log_search.search_request_log(_plan(_TYPED_ENTRIES), target="cradle")
    assert all("targets" in e for e in results)


def test_combined_filters_are_anded():
    results = request_log_search.search_request_log(
        _plan(_TYPED_ENTRIES), kind="correction", level="operation", target="base"
    )
    assert [e["text"] for e in results] == ["add a drain slot"]


def test_cli_level_and_target(tmp_path, capsys):
    plan_path = tmp_path / "BUILD_PLAN.json"
    plan_path.write_text(json.dumps(_plan(_TYPED_ENTRIES)), encoding="utf-8")
    rc = request_log_search.main(
        ["search", str(plan_path), "--level", "parameter", "--target", "cradle"]
    )
    assert rc == 0
    output = json.loads(capsys.readouterr().out)
    assert len(output) == 1
    assert output[0]["text"] == "saddle 40mm wide"


def test_cli_query(tmp_path, capsys):
    plan_path = tmp_path / "BUILD_PLAN.json"
    plan_path.write_text(json.dumps(_plan(_ENTRIES)), encoding="utf-8")
    rc = request_log_search.main(["search", str(plan_path), "--query", "hinge"])
    assert rc == 0
    output = json.loads(capsys.readouterr().out)
    assert len(output) == 2


def test_cli_kind(tmp_path, capsys):
    plan_path = tmp_path / "BUILD_PLAN.json"
    plan_path.write_text(json.dumps(_plan(_ENTRIES)), encoding="utf-8")
    rc = request_log_search.main(["search", str(plan_path), "--kind", "initial"])
    assert rc == 0
    output = json.loads(capsys.readouterr().out)
    assert len(output) == 1
    assert output[0]["kind"] == "initial"


def test_cli_no_match_exits_zero_with_empty_array(tmp_path, capsys):
    plan_path = tmp_path / "BUILD_PLAN.json"
    plan_path.write_text(json.dumps(_plan(_ENTRIES)), encoding="utf-8")
    rc = request_log_search.main(["search", str(plan_path), "--query", "nonexistent"])
    assert rc == 0
    assert json.loads(capsys.readouterr().out) == []


def test_cli_missing_file_exits_nonzero(tmp_path, capsys):
    rc = request_log_search.main(["search", str(tmp_path / "missing.json")])
    assert rc == 1
    assert "request_log_search" in capsys.readouterr().err


def test_cli_invalid_json_exits_nonzero(tmp_path, capsys):
    plan_path = tmp_path / "BUILD_PLAN.json"
    plan_path.write_text("{not json", encoding="utf-8")
    rc = request_log_search.main(["search", str(plan_path)])
    assert rc == 1
    assert "invalid JSON" in capsys.readouterr().err


def _minimal_plan(request_log=None):
    plan = {
        "schema_version": 1,
        "intent": (
            "Open-top enclosure for an Arduino Nano, printed as a single body with 1.2 mm "
            "walls and a USB-C pass-through on the front wall."
        ),
        "printer": "Bambu P1S",
        "material": "PLA",
        "nozzle_mm": 0.4,
        "parts": [
            {
                "id": "cradle",
                "description": "Main bracket",
                "dimensions": {"w_mm": 40, "d_mm": 30, "h_mm": 10},
                "interfaces": [],
                "blocks_needed": ["fillet_box"],
            }
        ],
        "constraints": {
            "wall_min_mm": 1.2,
            "overhang_max_deg": 45,
            "dimension_tolerance_mm": 1.0,
        },
    }
    if request_log is not None:
        plan["request_log"] = request_log
    return plan


def test_add_appends_entry_with_generated_ts(tmp_path):
    plan_path = tmp_path / "BUILD_PLAN.json"
    plan_path.write_text(json.dumps(_minimal_plan(list(_ENTRIES))), encoding="utf-8")
    rc = request_log_search.main(
        [
            "add",
            str(plan_path),
            "--kind",
            "correction",
            "--text",
            "make the lid 2mm taller",
            "--level",
            "parameter",
            "--target",
            "lid",
        ]
    )
    assert rc == 0
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert plan["request_log"][:3] == _ENTRIES
    new_entry = plan["request_log"][3]
    assert new_entry["kind"] == "correction"
    assert new_entry["text"] == "make the lid 2mm taller"
    assert new_entry["level"] == "parameter"
    assert new_entry["targets"] == ["lid"]
    assert "ts" in new_entry and new_entry["ts"]


def test_add_repeated_target_produces_array(tmp_path):
    plan_path = tmp_path / "BUILD_PLAN.json"
    plan_path.write_text(json.dumps(_minimal_plan()), encoding="utf-8")
    rc = request_log_search.main(
        [
            "add",
            str(plan_path),
            "--kind",
            "correction",
            "--text",
            "match lid and base widths",
            "--target",
            "lid",
            "--target",
            "base",
        ]
    )
    assert rc == 0
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert plan["request_log"][0]["targets"] == ["lid", "base"]


def test_add_omitting_level_and_target_leaves_fields_unset(tmp_path):
    plan_path = tmp_path / "BUILD_PLAN.json"
    plan_path.write_text(json.dumps(_minimal_plan()), encoding="utf-8")
    rc = request_log_search.main(
        ["add", str(plan_path), "--kind", "clarification", "--text", "PLA, 0.4mm nozzle"]
    )
    assert rc == 0
    entry = json.loads(plan_path.read_text(encoding="utf-8"))["request_log"][0]
    assert "level" not in entry
    assert "targets" not in entry


def test_add_kind_initial_is_rejected(tmp_path):
    plan_path = tmp_path / "BUILD_PLAN.json"
    original = json.dumps(_minimal_plan())
    plan_path.write_text(original, encoding="utf-8")
    rc = request_log_search.main(
        ["add", str(plan_path), "--kind", "initial", "--text", "build a bracket"]
    )
    assert rc == 1
    assert plan_path.read_text(encoding="utf-8") == original


def test_add_empty_text_fails_schema_validation_and_leaves_file_unchanged(tmp_path, capsys):
    plan_path = tmp_path / "BUILD_PLAN.json"
    original = json.dumps(_minimal_plan())
    plan_path.write_text(original, encoding="utf-8")
    rc = request_log_search.main(["add", str(plan_path), "--kind", "correction", "--text", ""])
    assert rc == 1
    assert "request_log_search" in capsys.readouterr().err
    assert plan_path.read_text(encoding="utf-8") == original


def test_add_creates_request_log_when_absent(tmp_path):
    plan_path = tmp_path / "BUILD_PLAN.json"
    plan_path.write_text(json.dumps(_minimal_plan()), encoding="utf-8")
    rc = request_log_search.main(
        ["add", str(plan_path), "--kind", "correction", "--text", "widen the base"]
    )
    assert rc == 0
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert len(plan["request_log"]) == 1
    assert plan["request_log"][0]["text"] == "widen the base"
