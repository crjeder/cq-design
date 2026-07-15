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
    shutil.copy(GOLDEN, case_run / "stl" / f"{PART}.stl")
    _write_attempts(case_run, [_record(1, "pass")])

    result = run_evals.score_case(CASE, tmp_path, run_evals.load_prices())
    assert result["mean_chamfer_mm"] < 0.5
    assert result["within_tolerance"] is True
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


def test_cost_sums_all_attempts():
    prices = {"default": 10.0, "inline": 10.0}
    records = [_record(1, "fail"), _record(2, "fail"), _record(3, "pass")]
    metrics = run_evals.attempt_metrics(records, prices)
    # 3 attempts x 40000 chars / 4 chars-per-token = 30000 tokens at $10/MTok
    assert abs(metrics["total_cost_usd"] - 0.30) < 1e-9
    assert metrics["cost_per_accepted_part_usd"] == metrics["total_cost_usd"]
    assert metrics["first_shot_rate"] == 0.0
    assert metrics["mean_attempts_to_pass"] == 3.0


def test_never_passing_part_counts_attempts_plus_one():
    prices = {"default": 10.0}
    records = [_record(1, "fail"), _record(2, "fail")]
    metrics = run_evals.attempt_metrics(records, prices)
    assert metrics["mean_attempts_to_pass"] == 3.0
    assert metrics["unpassed_parts"] == [PART]
    assert metrics["cost_per_accepted_part_usd"] is None


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
