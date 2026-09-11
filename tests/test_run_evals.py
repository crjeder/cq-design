"""Eval runner scoring path -- fixture telemetry + real golden STLs, no model calls."""

import json
import shutil
import sys
from pathlib import Path

import trimesh

sys.path.insert(0, str(Path(__file__).parent.parent / "evals"))

import run_evals  # noqa: E402  # pyright: ignore[reportMissingImports]

CASE = "u-clip"
PART = "u_clip"
GOLDEN = run_evals.CASES_DIR / CASE / "golden" / f"{PART}.stl"


def _write_attempts(case_run_dir, records):
    log = case_run_dir / "build" / "attempts.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")


def _record(attempt, outcome, prompt_chars=40000, part_id=PART):
    return {
        "ts": "2026-07-15T00:00:00+00:00",
        "part_id": part_id,
        "attempt": attempt,
        "outcome": outcome,
        "error_types": [] if outcome == "pass" else ["occ_exception"],
        "visual_review": None,
        "prompt_chars": prompt_chars,
        "model": "inline",
    }


def test_identical_mesh_scores_near_zero_chamfer(tmp_path):
    case_run = tmp_path / CASE
    (case_run / "stl").mkdir(parents=True)
    # Deliberately not named after the golden part id -- correspondence is geometric.
    shutil.copy(GOLDEN, case_run / "stl" / "produced.stl")
    _write_attempts(case_run, [_record(1, "pass")])

    result = run_evals.score_case(CASE, tmp_path, run_evals.load_prices())
    assert result["mean_chamfer_mm"] < 0.5
    assert result["within_tolerance"] is True
    assert result["no_artifacts"] is False
    assert result["matched_to"][PART] == "produced.stl"
    assert result["first_shot_rate"] == 1.0
    assert result["mean_attempts_to_pass"] == 1.0


def test_deformed_mesh_scores_nonzero_chamfer(tmp_path):
    case_run = tmp_path / CASE
    (case_run / "stl").mkdir(parents=True)
    mesh = trimesh.load(GOLDEN)
    mesh.apply_scale(1.5)
    mesh.export(case_run / "stl" / f"{PART}.stl")
    _write_attempts(case_run, [_record(1, "pass")])

    result = run_evals.score_case(CASE, tmp_path, run_evals.load_prices())
    assert result["mean_chamfer_mm"] > 1.0
    assert result["within_tolerance"] is False


def test_translation_is_normalized_away(tmp_path):
    case_run = tmp_path / CASE
    (case_run / "stl").mkdir(parents=True)
    mesh = trimesh.load(GOLDEN)
    mesh.apply_translation([100, -50, 25])
    mesh.export(case_run / "stl" / f"{PART}.stl")
    _write_attempts(case_run, [_record(1, "pass")])

    result = run_evals.score_case(CASE, tmp_path, run_evals.load_prices())
    assert result["mean_chamfer_mm"] < 0.5


def test_missing_telemetry_degrades_not_crashes(tmp_path):
    case_run = tmp_path / CASE
    (case_run / "stl").mkdir(parents=True)
    shutil.copy(GOLDEN, case_run / "stl" / f"{PART}.stl")

    result = run_evals.score_case(CASE, tmp_path, run_evals.load_prices())
    assert result["telemetry"] == "unavailable"
    assert result["first_shot_rate"] is None
    assert result["cost_per_accepted_part_usd"] is None
    assert result["mean_chamfer_mm"] < 0.5


def test_base_plus_followup_counted_as_one_attempt(tmp_path):
    case_run = tmp_path / CASE
    base = _record(1, "pass")
    followup = {**base, "outcome": "fail", "error_types": ["visual_mismatch"]}
    _write_attempts(case_run, [base, followup])

    attempts = run_evals.read_attempts(case_run)
    assert attempts is not None
    assert len(attempts) == 1
    assert attempts[0]["outcome"] == "fail"

    metrics = run_evals.attempt_metrics(attempts, _FLAT_10)
    assert metrics["first_shot_rate"] == 0.0
    assert metrics["mean_attempts_to_pass"] == 2.0


def test_part_ids_need_not_agree(tmp_path):
    case = "sliding-lid"
    golden_part = "sliding_lid"
    golden = run_evals.CASES_DIR / case / "golden" / f"{golden_part}.stl"
    case_run = tmp_path / case
    (case_run / "stl").mkdir(parents=True)
    shutil.copy(golden, case_run / "stl" / "lid.stl")
    _write_attempts(case_run, [_record(1, "pass", part_id=golden_part)])

    result = run_evals.score_case(case, tmp_path, run_evals.load_prices())
    assert result["mean_chamfer_mm"] < 0.5
    assert result["matched_to"][golden_part] == "lid.stl"


def test_unmatched_golden_part_fails_case(tmp_path):
    case = "two-part-box"
    case_dir = run_evals.CASES_DIR / case
    case_run = tmp_path / case
    (case_run / "stl").mkdir(parents=True)
    # Only the body is produced; the lid never gets built.
    shutil.copy(case_dir / "golden" / "box_body.stl", case_run / "stl" / "body.stl")
    _write_attempts(case_run, [_record(1, "pass", part_id="box_body")])

    result = run_evals.score_case(case, tmp_path, run_evals.load_prices())
    assert result["chamfer_mm"]["box_body"] is not None
    assert result["chamfer_mm"]["box_body"] < 0.5
    assert result["chamfer_mm"]["box_lid"] is None
    assert result["matched_to"]["box_lid"] is None
    assert result["within_tolerance"] is False


def test_plate_and_keep_out_files_are_not_produced_solids(tmp_path):
    case = "two-part-box"
    case_dir = run_evals.CASES_DIR / case
    case_run = tmp_path / case
    stl_dir = case_run / "stl"
    stl_dir.mkdir(parents=True)
    shutil.copy(case_dir / "golden" / "box_body.stl", stl_dir / "box_body.stl")
    shutil.copy(case_dir / "golden" / "box_lid.stl", stl_dir / "box_lid.stl")
    shutil.copy(case_dir / "golden" / "box_body.stl", stl_dir / "plate_1.stl")
    shutil.copy(case_dir / "golden" / "box_lid.stl", stl_dir / "keep_out__box_body__cavity.stl")

    produced = run_evals.find_produced_stls(case_run)
    assert {p.name for p in produced} == {"box_body.stl", "box_lid.stl"}


def test_no_stl_dir_reports_no_artifacts(tmp_path):
    case_run = tmp_path / CASE
    case_run.mkdir(parents=True)

    result = run_evals.score_case(CASE, tmp_path, run_evals.load_prices())
    assert result["no_artifacts"] is True
    assert result["within_tolerance"] is False
    assert result["mean_chamfer_mm"] is None
    assert result["chamfer_mm"][PART] is None


def test_two_produced_two_golden_assign_one_to_one(tmp_path):
    case = "two-part-box"
    case_dir = run_evals.CASES_DIR / case
    case_run = tmp_path / case
    stl_dir = case_run / "stl"
    stl_dir.mkdir(parents=True)
    # Names deliberately swapped relative to the golden ids -- assignment must
    # go by geometry, and neither golden should collapse onto the same produced solid.
    shutil.copy(case_dir / "golden" / "box_lid.stl", stl_dir / "solid_a.stl")
    shutil.copy(case_dir / "golden" / "box_body.stl", stl_dir / "solid_b.stl")
    _write_attempts(
        case_run,
        [_record(1, "pass", part_id="box_body"), _record(1, "pass", part_id="box_lid")],
    )

    result = run_evals.score_case(case, tmp_path, run_evals.load_prices())
    assert result["matched_to"]["box_body"] == "solid_b.stl"
    assert result["matched_to"]["box_lid"] == "solid_a.stl"
    assert result["chamfer_mm"]["box_body"] < 0.5
    assert result["chamfer_mm"]["box_lid"] < 0.5
    assert result["within_tolerance"] is True


_FLAT_10 = {"default": {"input": 10.0, "output": 10.0}, "inline": {"input": 10.0, "output": 10.0}}


def test_cost_sums_all_attempts():
    records = [_record(1, "fail"), _record(2, "fail"), _record(3, "pass")]
    metrics = run_evals.attempt_metrics(records, _FLAT_10)
    # 3 attempts x 40000 chars / 4 chars-per-token = 30000 tokens at $10/MTok
    assert abs(metrics["total_cost_usd"] - 0.30) < 1e-9
    assert metrics["cost_per_accepted_part_usd"] == metrics["total_cost_usd"]
    assert metrics["cost_source"] == "estimate"
    assert metrics["first_shot_rate"] == 0.0
    assert metrics["mean_attempts_to_pass"] == 3.0


def test_never_passing_part_counts_attempts_plus_one():
    records = [_record(1, "fail"), _record(2, "fail")]
    metrics = run_evals.attempt_metrics(records, _FLAT_10)
    assert metrics["mean_attempts_to_pass"] == 3.0
    assert metrics["unpassed_parts"] == [PART]
    assert metrics["cost_per_accepted_part_usd"] is None


def test_recorded_cost_overrides_estimate():
    records = [_record(1, "pass")]
    metrics = run_evals.attempt_metrics(records, _FLAT_10, recorded_cost=0.123)
    assert metrics["total_cost_usd"] == 0.123
    assert metrics["cost_per_accepted_part_usd"] == 0.123
    assert metrics["cost_source"] == "recorded"


def test_score_case_prefers_envelope_cost(tmp_path):
    case_run = tmp_path / CASE
    (case_run / "stl").mkdir(parents=True)
    shutil.copy(GOLDEN, case_run / "stl" / f"{PART}.stl")
    _write_attempts(case_run, [_record(1, "pass")])
    (case_run / "cost.json").write_text(json.dumps({"total_cost_usd": 0.42}), encoding="utf-8")

    result = run_evals.score_case(CASE, tmp_path, run_evals.load_prices())
    assert result["cost_source"] == "recorded"
    assert result["cost_per_accepted_part_usd"] == 0.42


def test_score_case_falls_back_to_session_record(tmp_path):
    case_run = tmp_path / CASE
    (case_run / "stl").mkdir(parents=True)
    shutil.copy(GOLDEN, case_run / "stl" / f"{PART}.stl")
    _write_attempts(case_run, [_record(1, "pass")])
    (case_run / "build" / "cost.json").write_text(
        json.dumps({"combined": {"cost_usd": 0.07}}), encoding="utf-8"
    )

    result = run_evals.score_case(CASE, tmp_path, run_evals.load_prices())
    assert result["cost_source"] == "recorded"
    assert result["cost_per_accepted_part_usd"] == 0.07


def test_score_case_estimate_when_no_record(tmp_path):
    case_run = tmp_path / CASE
    (case_run / "stl").mkdir(parents=True)
    shutil.copy(GOLDEN, case_run / "stl" / f"{PART}.stl")
    _write_attempts(case_run, [_record(1, "pass")])

    result = run_evals.score_case(CASE, tmp_path, run_evals.load_prices())
    assert result["cost_source"] == "estimate"


def test_aggregate_reports_contributing_case_count():
    case_results: list[dict] = [
        {"mean_chamfer_mm": 0.1},
        {"mean_chamfer_mm": 0.3},
        {"mean_chamfer_mm": None},
    ]
    agg = run_evals.aggregate(case_results)
    assert agg["chamfer_cases"] == 2
    assert abs(agg["mean_chamfer_mm"] - 0.2) < 1e-9


def test_end_to_end_scorecard_files(tmp_path):
    case_run = tmp_path / CASE
    (case_run / "stl").mkdir(parents=True)
    shutil.copy(GOLDEN, case_run / "stl" / f"{PART}.stl")
    _write_attempts(case_run, [_record(1, "pass")])

    rc = run_evals.main(["--run-dir", str(tmp_path), "--cases", CASE])
    assert rc == 0
    scorecard = json.loads((tmp_path / "scorecard.json").read_text(encoding="utf-8"))
    assert scorecard["aggregate"]["cases_scored"] == 1
    assert "| u-clip |" in (tmp_path / "scorecard.md").read_text(encoding="utf-8")


def test_unknown_case_rejected(tmp_path):
    assert run_evals.main(["--run-dir", str(tmp_path), "--cases", "nope"]) == 1


def test_filter_by_tags_no_filter_returns_all():
    assert run_evals.filter_by_tags(["a", "b"], None) == ["a", "b"]
    assert run_evals.filter_by_tags(["a", "b"], "") == ["a", "b"]


def test_filter_by_tags_real_case_intersection():
    assert run_evals.filter_by_tags(["hinged-latch", "wall-hook"], "hinge") == ["hinged-latch"]


def test_filter_by_tags_treats_missing_key_as_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(run_evals, "CASES_DIR", tmp_path)
    (tmp_path / "no-tags").mkdir()
    (tmp_path / "no-tags" / "case.json").write_text(json.dumps({}), encoding="utf-8")
    (tmp_path / "tagged").mkdir()
    (tmp_path / "tagged" / "case.json").write_text(
        json.dumps({"tags": ["external"]}), encoding="utf-8"
    )

    result = run_evals.filter_by_tags(["no-tags", "tagged"], "external")
    assert result == ["tagged"]


def test_main_tags_combines_with_cases_by_intersection(tmp_path):
    case_run = tmp_path / CASE
    (case_run / "stl").mkdir(parents=True)
    shutil.copy(GOLDEN, case_run / "stl" / f"{PART}.stl")
    _write_attempts(case_run, [_record(1, "pass")])

    # u-clip is tagged ["u", "clip"] -- no match means zero cases scored.
    rc = run_evals.main(["--run-dir", str(tmp_path), "--cases", CASE, "--tags", "nonexistent-tag"])
    assert rc == 0
    scorecard = json.loads((tmp_path / "scorecard.json").read_text(encoding="utf-8"))
    assert scorecard["aggregate"]["cases_scored"] == 0
