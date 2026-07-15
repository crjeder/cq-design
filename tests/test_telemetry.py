"""telemetry.py append helper + CLI -- fast, no CadQuery."""

import json

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
