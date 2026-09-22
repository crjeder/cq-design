"""Eval corpus sanity: every case is self-contained and its plan validates.

No CadQuery needed (plan validation + STL bbox via trimesh).
"""

import json
from pathlib import Path

import pytest
import trimesh

from plan import validate_plan

CASES_DIR = Path(__file__).parent.parent / "evals" / "cases"
CASES = sorted(p.name for p in CASES_DIR.iterdir() if p.is_dir())


def test_corpus_has_about_ten_cases():
    assert 8 <= len(CASES) <= 15


@pytest.mark.parametrize("case", CASES)
def test_case_is_self_contained(case):
    d = CASES_DIR / case
    assert (d / "request.md").read_text(encoding="utf-8").strip()
    assert (d / "BUILD_PLAN.json").is_file()
    meta = json.loads((d / "case.json").read_text(encoding="utf-8"))
    assert meta["tolerance_mm"] > 0
    goldens = list((d / "golden").glob("*.stl"))
    assert goldens, f"{case} has no golden mesh"
    plan = json.loads((d / "BUILD_PLAN.json").read_text(encoding="utf-8"))
    assert meta["expected_parts"] == len(plan["parts"])
    part_ids = {p["id"] for p in plan["parts"]}
    assert {g.stem for g in goldens} == part_ids


@pytest.mark.parametrize("case", CASES)
def test_case_plan_validates(case):
    errors = validate_plan(str(CASES_DIR / case / "BUILD_PLAN.json"))
    assert errors == [], f"{case}: {errors}"


@pytest.mark.parametrize("case", CASES)
def test_golden_bbox_matches_plan_dimensions(case):
    d = CASES_DIR / case
    plan = json.loads((d / "BUILD_PLAN.json").read_text(encoding="utf-8"))
    tol = json.loads((d / "case.json").read_text(encoding="utf-8"))["tolerance_mm"]
    for part in plan["parts"]:
        mesh = trimesh.load(d / "golden" / f"{part['id']}.stl")
        extents = sorted(mesh.extents)
        dims = part["dimensions"]
        declared = sorted([dims["w_mm"], dims["d_mm"], dims["h_mm"]])
        for got, want in zip(extents, declared, strict=True):
            assert abs(got - want) <= max(tol, 0.5), (
                f"{case}/{part['id']}: golden extents {extents} vs declared {declared}"
            )
