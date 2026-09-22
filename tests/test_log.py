"""log.py journal/attempt/request helpers + CLI -- fast, no CadQuery."""

import json
import sys

import pytest

import log


def test_append_creates_file(tmp_path):
    path = tmp_path / "journal.md"
    log.append_line(path, "phase0/rung_decision", "rung 5, source none, license n/a")
    assert (
        path.read_text(encoding="utf-8")
        == "- phase0/rung_decision: rung 5, source none, license n/a\n"
    )


def test_append_does_not_disturb_existing_lines(tmp_path):
    path = tmp_path / "journal.md"
    log.append_line(path, "phase1/topology_confirmed", "single-piece bracket")
    log.append_line(
        path, "phase1/dimensions_approved", "parameters.py written, 6 dimensions recorded"
    )
    assert path.read_text(encoding="utf-8").splitlines() == [
        "- phase1/topology_confirmed: single-piece bracket",
        "- phase1/dimensions_approved: parameters.py written, 6 dimensions recorded",
    ]


def test_repeated_milestone_key_appends_new_line(tmp_path):
    path = tmp_path / "journal.md"
    log.append_line(path, "phase3/part_accepted:lid", "audit passed")
    log.append_line(path, "phase3/part_accepted:lid", "rebuilt after correction, audit passed")
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert lines[0] == "- phase3/part_accepted:lid: audit passed"
    assert lines[1] == "- phase3/part_accepted:lid: rebuilt after correction, audit passed"


def test_cli_append(tmp_path):
    path = tmp_path / "journal.md"
    rc = log.main(
        ["journal", "append", str(path), "phase4/delivered", "README.md + REGENERATE.md written"]
    )
    assert rc == 0
    assert (
        path.read_text(encoding="utf-8")
        == "- phase4/delivered: README.md + REGENERATE.md written\n"
    )


def test_cli_unwritable_path_exits_nonzero(tmp_path, capsys):
    # Parent directory does not exist and is not created -- matches journal.md's
    # contract that build/ already exists by the time any milestone is written.
    missing = tmp_path / "does-not-exist" / "journal.md"
    rc = log.main(["journal", "append", str(missing), "phase0/rung_decision", "rung 5"])
    assert rc == 1
    assert "journal" in capsys.readouterr().err


def _valid_record(**overrides):
    record = {
        "part_id": "housing",
        "attempt": 1,
        "outcome": "fail",
        "error_types": ["silent_boolean", "thin_interface"],
        "visual_review": None,
        "prompt_chars": 41250,
        "model": "inline",
    }
    record.update(overrides)
    return record


def _lines(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_valid_append_stamps_ts(tmp_path):
    attempts_log = tmp_path / "build" / "attempts.jsonl"
    log.append_attempt(attempts_log, _valid_record())
    (entry,) = _lines(attempts_log)
    assert entry["part_id"] == "housing"
    assert entry["error_types"] == ["silent_boolean", "thin_interface"]
    assert "ts" in entry


def test_first_append_creates_parent_dir(tmp_path):
    attempts_log = tmp_path / "build" / "attempts.jsonl"
    assert not attempts_log.parent.exists()
    log.append_attempt(attempts_log, _valid_record())
    assert attempts_log.exists()
    assert len(_lines(attempts_log)) == 1


def test_missing_field_rejected_without_write(tmp_path):
    attempts_log = tmp_path / "attempts.jsonl"
    record = _valid_record()
    del record["part_id"]
    with pytest.raises(ValueError, match="part_id"):
        log.append_attempt(attempts_log, record)
    assert not attempts_log.exists()


def test_bad_outcome_rejected(tmp_path):
    with pytest.raises(ValueError, match="outcome"):
        log.append_attempt(tmp_path / "a.jsonl", _valid_record(outcome="maybe"))


def test_extra_keys_preserved(tmp_path):
    attempts_log = tmp_path / "attempts.jsonl"
    log.append_attempt(attempts_log, _valid_record(phase="build", outcome="pass", error_types=[]))
    (entry,) = _lines(attempts_log)
    assert entry["phase"] == "build"


def test_append_only_across_calls(tmp_path):
    attempts_log = tmp_path / "attempts.jsonl"
    log.append_attempt(attempts_log, _valid_record(attempt=1))
    first_bytes = attempts_log.read_bytes()
    log.append_attempt(attempts_log, _valid_record(attempt=2, outcome="pass", error_types=[]))
    assert attempts_log.read_bytes().startswith(first_bytes)
    entries = _lines(attempts_log)
    assert [e["attempt"] for e in entries] == [1, 2]


def test_visual_review_object(tmp_path):
    attempts_log = tmp_path / "attempts.jsonl"
    log.append_attempt(
        attempts_log, _valid_record(visual_review={"passed": False, "failed_question": "Q3"})
    )
    (entry,) = _lines(attempts_log)
    assert entry["visual_review"]["failed_question"] == "Q3"


def test_cli_json_append(tmp_path):
    attempts_log = tmp_path / "attempts.jsonl"
    rc = log.main(["attempt", "append", str(attempts_log), json.dumps(_valid_record())])
    assert rc == 0
    assert len(_lines(attempts_log)) == 1


def test_cli_fields_append(tmp_path):
    attempts_log = tmp_path / "attempts.jsonl"
    rc = log.main(
        [
            "attempt",
            "append",
            str(attempts_log),
            "--field",
            "part_id=lid",
            "--field",
            "attempt=2",
            "--field",
            "outcome=pass",
            "--field",
            "error_types=[]",
            "--field",
            "prompt_chars=1000",
            "--field",
            "model=inline",
        ]
    )
    assert rc == 0
    (entry,) = _lines(attempts_log)
    assert entry["part_id"] == "lid"
    assert entry["attempt"] == 2
    assert entry["visual_review"] is None


def test_cli_invalid_record_exits_nonzero(tmp_path):
    attempts_log = tmp_path / "attempts.jsonl"
    rc = log.main(["attempt", "append", str(attempts_log), '{"attempt": 1}'])
    assert rc == 1
    assert not attempts_log.exists()


# ---- fold_attempts ----------------------------------------------------------


def test_fold_empty_input():
    assert log.fold_attempts([]) == []


def test_fold_single_record():
    rec = _valid_record()
    assert log.fold_attempts([rec]) == [rec]


def test_fold_same_key_last_wins():
    base = _valid_record(outcome="pass", error_types=[])
    followup = _valid_record(
        outcome="fail", error_types=["visual_mismatch"], visual_review={"passed": False}
    )
    folded = log.fold_attempts([base, followup])
    assert folded == [followup]


def test_fold_interleaved_keys_preserve_first_appearance_order():
    a1 = _valid_record(part_id="a", attempt=1)
    b1 = _valid_record(part_id="b", attempt=1)
    a1_followup = _valid_record(part_id="a", attempt=1, outcome="pass", error_types=[])
    folded = log.fold_attempts([a1, b1, a1_followup])
    assert [(r["part_id"], r["attempt"]) for r in folded] == [("a", 1), ("b", 1)]
    assert folded[0] == a1_followup


# ---- --hook -----------------------------------------------------------------


def _hook_payload(tmp_path, command, stdout, transcript_lines=()):
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(
        "".join(json.dumps(line) + "\n" for line in transcript_lines), encoding="utf-8"
    )
    return {
        "session_id": "s1",
        "transcript_path": str(transcript),
        "cwd": str(tmp_path),
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "tool_response": {"stdout": stdout, "stderr": "", "exit_code": 0},
    }


def _run_hook_with_payload(monkeypatch, capsys, payload):
    import io

    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    return log.main(["--hook"])


def test_hook_appends_base_record(tmp_path, monkeypatch):
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "housing_prompt_attempt1.txt").write_text("x" * 500, encoding="utf-8")
    payload = _hook_payload(
        tmp_path,
        command='uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/run_cadquery_model.py" '
        "build/housing.py --preview",
        stdout=json.dumps({"success": False, "errors": [{"type": "thin_interface"}]}),
        transcript_lines=[
            {"type": "assistant", "message": {"model": "claude-sonnet-5", "usage": {}}}
        ],
    )
    rc = _run_hook_with_payload(monkeypatch, None, payload)
    assert rc == 0
    attempts_log = tmp_path / "build" / "attempts.jsonl"
    (entry,) = _lines(attempts_log)
    assert entry["part_id"] == "housing"
    assert entry["attempt"] == 1
    assert entry["outcome"] == "fail"
    assert entry["error_types"] == ["thin_interface"]
    assert entry["visual_review"] is None
    assert entry["model"] == "claude-sonnet-5"
    assert entry["prompt_chars"] == 500


def test_hook_noop_on_non_matching_command(tmp_path, monkeypatch):
    (tmp_path / "build").mkdir()
    payload = _hook_payload(tmp_path, command="echo hi", stdout="")
    rc = _run_hook_with_payload(monkeypatch, None, payload)
    assert rc == 0
    assert not (tmp_path / "build" / "attempts.jsonl").exists()


def test_hook_noop_when_build_missing(tmp_path, monkeypatch):
    payload = _hook_payload(
        tmp_path,
        command="python run_cadquery_model.py build/housing.py",
        stdout=json.dumps({"success": True, "errors": []}),
    )
    rc = _run_hook_with_payload(monkeypatch, None, payload)
    assert rc == 0
    assert not (tmp_path / "build" / "attempts.jsonl").exists()


def test_hook_noop_on_malformed_payload(monkeypatch):
    import io

    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    rc = log.main(["--hook"])
    assert rc == 0


def test_record_attempt_numbers_attempts_and_skips_stubs(tmp_path):
    attempts_log = tmp_path / "build" / "attempts.jsonl"
    attempts_log.parent.mkdir()
    (attempts_log.parent / "lid_prompt.txt").write_text("x" * 42, encoding="utf-8")
    fail = {"success": False, "errors": [{"type": "occ_exception"}]}
    log.record_attempt(attempts_log, "lid", fail, "claude-sonnet-5")
    log.record_attempt(attempts_log, "lid", {"success": True, "errors": []}, "claude-sonnet-5")
    log.record_attempt(attempts_log, "lid_stub", {"success": True, "errors": []}, "claude-sonnet-5")
    records = [json.loads(line) for line in attempts_log.read_text(encoding="utf-8").splitlines()]
    assert [(r["attempt"], r["outcome"], r["prompt_chars"]) for r in records] == [
        (1, "fail", 42),
        (2, "pass", 42),
    ]
    assert records[0]["error_types"] == ["occ_exception"]


def test_audit_fail_appends_derived_record(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    attempts_log = tmp_path / "build" / "attempts.jsonl"
    attempts_log.parent.mkdir()
    (attempts_log.parent / "lid_prompt_attempt2.txt").write_text("x" * 77, encoding="utf-8")
    (tmp_path / "skill_config.json").write_text(
        json.dumps({"models": {"part_author": "claude-sonnet-5"}}), encoding="utf-8"
    )
    log.append_attempt(attempts_log, _valid_record(part_id="lid", attempt=1, outcome="pass"))
    log.append_attempt(attempts_log, _valid_record(part_id="lid", attempt=2, outcome="pass"))
    audit_path = tmp_path / "lid_audit.json"
    audit_path.write_text(
        json.dumps({"verdict": "fail", "failed_questions": ["Does the lid seat flush?"]}),
        encoding="utf-8",
    )
    log.audit_fail(attempts_log, "lid", audit_path)
    records = [r for r in _lines(attempts_log) if r["part_id"] == "lid"]
    folded = log.fold_attempts(records)
    (entry,) = [r for r in folded if r["attempt"] == 2]
    assert entry["outcome"] == "fail"
    assert entry["error_types"] == ["visual_mismatch"]
    assert entry["model"] == "claude-sonnet-5"
    assert entry["prompt_chars"] == 77
    assert entry["visual_review"] == {
        "passed": False,
        "failed_question": "Does the lid seat flush?",
    }


def test_audit_fail_errors_without_prior_attempt(tmp_path):
    attempts_log = tmp_path / "build" / "attempts.jsonl"
    audit_path = tmp_path / "lid_audit.json"
    audit_path.write_text(
        json.dumps({"verdict": "fail", "failed_questions": ["q"]}), encoding="utf-8"
    )
    with pytest.raises(ValueError):
        log.audit_fail(attempts_log, "lid", audit_path)
    assert not attempts_log.exists()


def test_audit_fail_errors_on_no_failed_questions(tmp_path):
    attempts_log = tmp_path / "build" / "attempts.jsonl"
    attempts_log.parent.mkdir()
    log.append_attempt(attempts_log, _valid_record(part_id="lid", attempt=1))
    audit_path = tmp_path / "lid_audit.json"
    audit_path.write_text(json.dumps({"verdict": "fail", "failed_questions": []}), encoding="utf-8")
    with pytest.raises(ValueError):
        log.audit_fail(attempts_log, "lid", audit_path)
    assert len(_lines(attempts_log)) == 1


def _plan(entries):
    return {"request_log": entries}


_ENTRIES = [
    {"ts": "2026-01-01T00:00:00Z", "kind": "initial", "text": "Build a hinge bracket"},
    {"ts": "2026-01-01T00:05:00Z", "kind": "clarification", "text": "PLA, 0.4mm nozzle"},
    {"ts": "2026-01-01T00:10:00Z", "kind": "correction", "text": "Widen the hinge pin hole"},
]


def test_query_matches_substring_case_insensitive():
    results = log.search_request_log(_plan(_ENTRIES), query="HINGE")
    assert [e["text"] for e in results] == [
        "Build a hinge bracket",
        "Widen the hinge pin hole",
    ]


def test_kind_filter():
    results = log.search_request_log(_plan(_ENTRIES), kind="correction")
    assert [e["text"] for e in results] == ["Widen the hinge pin hole"]


def test_combined_query_and_kind():
    results = log.search_request_log(_plan(_ENTRIES), query="hinge", kind="correction")
    assert [e["text"] for e in results] == ["Widen the hinge pin hole"]


def test_no_match_returns_empty_list():
    results = log.search_request_log(_plan(_ENTRIES), query="nonexistent")
    assert results == []


def test_absent_request_log_returns_empty_list():
    results = log.search_request_log({}, query="hinge")
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
    results = log.search_request_log(_plan(_TYPED_ENTRIES), level="parameter")
    assert [e["text"] for e in results] == ["saddle 40mm wide"]


def test_target_filter_matches_part_id_and_dotted_name():
    assert [e["text"] for e in log.search_request_log(_plan(_TYPED_ENTRIES), target="cradle")] == [
        "saddle 40mm wide"
    ]
    assert [
        e["text"] for e in log.search_request_log(_plan(_TYPED_ENTRIES), target="saddle_width")
    ] == ["saddle 40mm wide"]


def test_target_filter_excludes_entries_without_targets():
    results = log.search_request_log(_plan(_TYPED_ENTRIES), target="cradle")
    assert all("targets" in e for e in results)


def test_combined_filters_are_anded():
    results = log.search_request_log(
        _plan(_TYPED_ENTRIES), kind="correction", level="operation", target="base"
    )
    assert [e["text"] for e in results] == ["add a drain slot"]


def test_cli_level_and_target(tmp_path, capsys):
    plan_path = tmp_path / "BUILD_PLAN.json"
    plan_path.write_text(json.dumps(_plan(_TYPED_ENTRIES)), encoding="utf-8")
    rc = log.main(
        ["request", "search", str(plan_path), "--level", "parameter", "--target", "cradle"]
    )
    assert rc == 0
    output = json.loads(capsys.readouterr().out)
    assert len(output) == 1
    assert output[0]["text"] == "saddle 40mm wide"


def test_cli_query(tmp_path, capsys):
    plan_path = tmp_path / "BUILD_PLAN.json"
    plan_path.write_text(json.dumps(_plan(_ENTRIES)), encoding="utf-8")
    rc = log.main(["request", "search", str(plan_path), "--query", "hinge"])
    assert rc == 0
    output = json.loads(capsys.readouterr().out)
    assert len(output) == 2


def test_cli_kind(tmp_path, capsys):
    plan_path = tmp_path / "BUILD_PLAN.json"
    plan_path.write_text(json.dumps(_plan(_ENTRIES)), encoding="utf-8")
    rc = log.main(["request", "search", str(plan_path), "--kind", "initial"])
    assert rc == 0
    output = json.loads(capsys.readouterr().out)
    assert len(output) == 1
    assert output[0]["kind"] == "initial"


def test_cli_no_match_exits_zero_with_empty_array(tmp_path, capsys):
    plan_path = tmp_path / "BUILD_PLAN.json"
    plan_path.write_text(json.dumps(_plan(_ENTRIES)), encoding="utf-8")
    rc = log.main(["request", "search", str(plan_path), "--query", "nonexistent"])
    assert rc == 0
    assert json.loads(capsys.readouterr().out) == []


def test_cli_missing_file_exits_nonzero(tmp_path, capsys):
    rc = log.main(["request", "search", str(tmp_path / "missing.json")])
    assert rc == 1
    assert "request_log_search" in capsys.readouterr().err


def test_cli_invalid_json_exits_nonzero(tmp_path, capsys):
    plan_path = tmp_path / "BUILD_PLAN.json"
    plan_path.write_text("{not json", encoding="utf-8")
    rc = log.main(["request", "search", str(plan_path)])
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
    rc = log.main(
        [
            "request",
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
    rc = log.main(
        [
            "request",
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
    rc = log.main(
        ["request", "add", str(plan_path), "--kind", "clarification", "--text", "PLA, 0.4mm nozzle"]
    )
    assert rc == 0
    entry = json.loads(plan_path.read_text(encoding="utf-8"))["request_log"][0]
    assert "level" not in entry
    assert "targets" not in entry


def test_add_kind_initial_is_rejected(tmp_path):
    plan_path = tmp_path / "BUILD_PLAN.json"
    original = json.dumps(_minimal_plan())
    plan_path.write_text(original, encoding="utf-8")
    rc = log.main(
        ["request", "add", str(plan_path), "--kind", "initial", "--text", "build a bracket"]
    )
    assert rc == 1
    assert plan_path.read_text(encoding="utf-8") == original


def test_add_empty_text_fails_schema_validation_and_leaves_file_unchanged(tmp_path, capsys):
    plan_path = tmp_path / "BUILD_PLAN.json"
    original = json.dumps(_minimal_plan())
    plan_path.write_text(original, encoding="utf-8")
    rc = log.main(["request", "add", str(plan_path), "--kind", "correction", "--text", ""])
    assert rc == 1
    assert "request_log_search" in capsys.readouterr().err
    assert plan_path.read_text(encoding="utf-8") == original


def test_add_creates_request_log_when_absent(tmp_path):
    plan_path = tmp_path / "BUILD_PLAN.json"
    plan_path.write_text(json.dumps(_minimal_plan()), encoding="utf-8")
    rc = log.main(
        ["request", "add", str(plan_path), "--kind", "correction", "--text", "widen the base"]
    )
    assert rc == 0
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert len(plan["request_log"]) == 1
    assert plan["request_log"][0]["text"] == "widen the base"


def _add(tmp_path, *extra):
    plan_path = tmp_path / "BUILD_PLAN.json"
    plan_path.write_text(json.dumps(_minimal_plan(list(_ENTRIES))), encoding="utf-8")
    argv = ["request", "add", str(plan_path), "--kind", "correction", "--text", "x", *extra]
    assert log.main(argv) == 0
    return json.loads(plan_path.read_text(encoding="utf-8"))


def test_add_reconciled_stamps_intent_ts(tmp_path):
    plan = _add(tmp_path, "--reconciled")
    assert plan["intent_ts"] == plan["request_log"][-1]["ts"]


def test_add_without_reconciled_leaves_intent_ts(tmp_path):
    assert "intent_ts" not in _add(tmp_path)
