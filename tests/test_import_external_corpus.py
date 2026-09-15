"""External-corpus importer: filter/sampling determinism (fast) and golden
generation against a small offline fixture corpus (CadQuery, a few seconds)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "evals"))

import import_external_corpus as iec  # noqa: E402  # pyright: ignore[reportMissingImports]

FIXTURE = Path(__file__).parent / "fixtures" / "external_corpus_sample.jsonl"


def test_off_domain_pairs_excluded():
    pairs = iec.load_pairs(FIXTURE)
    filtered = [p for p in pairs if iec.is_on_domain(p["description"])]
    assert {p["id"] for p in filtered} == {"0001", "0002"}


def test_sampling_is_deterministic():
    pairs = iec.load_pairs(FIXTURE)
    a = iec.sample_pairs(pairs, sample_size=1, seed=7)
    b = iec.sample_pairs(pairs, sample_size=1, seed=7)
    assert [p["id"] for p in a] == [p["id"] for p in b]


def test_sample_size_at_or_above_filtered_count_keeps_all():
    pairs = iec.load_pairs(FIXTURE)
    sampled = iec.sample_pairs(pairs, sample_size=10, seed=1)
    assert {p["id"] for p in sampled} == {"0001", "0002"}


def test_unrecorded_source_hard_errors(tmp_path, monkeypatch):
    monkeypatch.setattr(iec, "CASES_DIR", tmp_path)
    rc = iec.main(["--source", "not-a-real-source", "--input", str(FIXTURE)])
    assert rc == 1
    assert list(tmp_path.iterdir()) == []


def test_import_writes_working_pair_and_skips_broken(tmp_path, monkeypatch):
    monkeypatch.setattr(iec, "CASES_DIR", tmp_path)
    iec.SOURCE_LICENSES["fixture-source"] = "test-only license (unit test)"
    iec.SOURCE_PREFIX["fixture-source"] = "ext-fix"
    try:
        rc = iec.main(
            [
                "--source",
                "fixture-source",
                "--input",
                str(FIXTURE),
                "--sample-size",
                "10",
                "--seed",
                "1",
            ]
        )
        assert rc == 0

        cases = sorted(p.name for p in tmp_path.iterdir())
        assert len(cases) == 1  # 0001 written, 0002 broken (skipped), 0003 off-domain
        case_dir = tmp_path / cases[0]

        assert (case_dir / "request.md").is_file()
        golden = list((case_dir / "golden").glob("*.stl"))
        assert len(golden) == 1

        plan_path = case_dir / "BUILD_PLAN.json"
        assert plan_path.is_file()
        assert iec.validate_plan(str(plan_path)) == []

        case_json = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
        assert case_json["source"] == "fixture-source"
        assert case_json["source_id"] == "0001"
        assert set(case_json["tags"]) >= {"external", "fixture-source"}
        assert case_json["license"] == "test-only license (unit test)"
    finally:
        del iec.SOURCE_LICENSES["fixture-source"]
        del iec.SOURCE_PREFIX["fixture-source"]
