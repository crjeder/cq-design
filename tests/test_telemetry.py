"""telemetry.py append helper + CLI -- fast, no CadQuery."""

import json
import sys

import pytest

import telemetry


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
    log = tmp_path / "build" / "attempts.jsonl"
    telemetry.append_attempt(log, _valid_record())
    (entry,) = _lines(log)
    assert entry["part_id"] == "housing"
    assert entry["error_types"] == ["silent_boolean", "thin_interface"]
    assert "ts" in entry


def test_first_append_creates_parent_dir(tmp_path):
    log = tmp_path / "build" / "attempts.jsonl"
    assert not log.parent.exists()
    telemetry.append_attempt(log, _valid_record())
    assert log.exists()
    assert len(_lines(log)) == 1


def test_missing_field_rejected_without_write(tmp_path):
    log = tmp_path / "attempts.jsonl"
    record = _valid_record()
    del record["part_id"]
    with pytest.raises(ValueError, match="part_id"):
        telemetry.append_attempt(log, record)
    assert not log.exists()


def test_bad_outcome_rejected(tmp_path):
    with pytest.raises(ValueError, match="outcome"):
        telemetry.append_attempt(tmp_path / "a.jsonl", _valid_record(outcome="maybe"))


def test_extra_keys_preserved(tmp_path):
    log = tmp_path / "attempts.jsonl"
    telemetry.append_attempt(log, _valid_record(phase="build", outcome="pass", error_types=[]))
    (entry,) = _lines(log)
    assert entry["phase"] == "build"


def test_append_only_across_calls(tmp_path):
    log = tmp_path / "attempts.jsonl"
    telemetry.append_attempt(log, _valid_record(attempt=1))
    first_bytes = log.read_bytes()
    telemetry.append_attempt(log, _valid_record(attempt=2, outcome="pass", error_types=[]))
    assert log.read_bytes().startswith(first_bytes)
    entries = _lines(log)
    assert [e["attempt"] for e in entries] == [1, 2]


def test_visual_review_object(tmp_path):
    log = tmp_path / "attempts.jsonl"
    telemetry.append_attempt(
        log, _valid_record(visual_review={"passed": False, "failed_question": "Q3"})
    )
    (entry,) = _lines(log)
    assert entry["visual_review"]["failed_question"] == "Q3"


def test_cli_json_append(tmp_path):
    log = tmp_path / "attempts.jsonl"
    rc = telemetry.main(["append", str(log), json.dumps(_valid_record())])
    assert rc == 0
    assert len(_lines(log)) == 1


def test_cli_fields_append(tmp_path):
    log = tmp_path / "attempts.jsonl"
    rc = telemetry.main(
        [
            "append",
            str(log),
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
    (entry,) = _lines(log)
    assert entry["part_id"] == "lid"
    assert entry["attempt"] == 2
    assert entry["visual_review"] is None


def test_cli_invalid_record_exits_nonzero(tmp_path):
    log = tmp_path / "attempts.jsonl"
    rc = telemetry.main(["append", str(log), '{"attempt": 1}'])
    assert rc == 1
    assert not log.exists()


# ---- fold_attempts ----------------------------------------------------------


def test_fold_empty_input():
    assert telemetry.fold_attempts([]) == []


def test_fold_single_record():
    rec = _valid_record()
    assert telemetry.fold_attempts([rec]) == [rec]


def test_fold_same_key_last_wins():
    base = _valid_record(outcome="pass", error_types=[])
    followup = _valid_record(
        outcome="fail", error_types=["visual_mismatch"], visual_review={"passed": False}
    )
    folded = telemetry.fold_attempts([base, followup])
    assert folded == [followup]


def test_fold_interleaved_keys_preserve_first_appearance_order():
    a1 = _valid_record(part_id="a", attempt=1)
    b1 = _valid_record(part_id="b", attempt=1)
    a1_followup = _valid_record(part_id="a", attempt=1, outcome="pass", error_types=[])
    folded = telemetry.fold_attempts([a1, b1, a1_followup])
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
    return telemetry.main(["--hook"])


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
    log = tmp_path / "build" / "attempts.jsonl"
    (entry,) = _lines(log)
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
    rc = telemetry.main(["--hook"])
    assert rc == 0
