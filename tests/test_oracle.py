"""Tests for src/oracle.py -- acceptance.json validate / check / verify / rounds."""

import copy
import json
from typing import Any

import pytest
from conftest import minimal_plan

import oracle

INTENT = (
    "Wall-mounted J-hook for a broom handle, printed as a single part. Mounting plate is "
    "screwed to the wall through two countersunk holes 60 mm apart; the hook curls up "
    "with a retaining lip so the handle cannot lift out. Handle diameter assumed 24 mm. "
    "Rounded, friendly look. Plate no wider than 80 mm."
)

DOC: dict[str, Any] = {
    "schema_version": 1,
    "statements": [
        {
            "id": "S1",
            "kind": "part_count",
            "n": 1,
            "cites": ["single part"],
            "text": "One printed part",
        },
        {
            "id": "S2",
            "kind": "feature",
            "feature": "hole",
            "count": 2,
            "diameter_mm": 4.5,
            "cites": ["two countersunk holes"],
            "text": "Two screw holes",
        },
        {
            "id": "S3",
            "kind": "spacing",
            "distance_mm": 60,
            "between": ["hole a", "hole b"],
            "cites": ["60 mm apart"],
            "text": "Holes 60 mm apart",
        },
        {
            "id": "S4",
            "kind": "fit",
            "accepts": {"diameter_mm": "HANDLE_D_MM"},
            "clearance_min_mm": 0.5,
            "cites": ["Handle diameter assumed 24 mm"],
            "text": "Hook accepts a 24 mm handle",
        },
        {
            "id": "S5",
            "kind": "extent",
            "which": "largest",
            "max_mm": 80,
            "cites": ["no wider than 80 mm"],
            "text": "Largest extent at most 80 mm",
        },
        {
            "id": "S6",
            "kind": "probe",
            "cites": ["cannot lift out"],
            "text": "Lip blocks the handle from lifting out",
        },
        {
            "id": "S7",
            "kind": "visual",
            "cites": ["Rounded, friendly look"],
            "text": "Rounded, friendly look",
        },
    ],
}

CONSTS = {"HANDLE_D_MM": 24.0}


def _plan():
    part = {
        "id": "hook",
        "description": "J-hook",
        "dimensions": {"w_mm": 70, "d_mm": 40, "h_mm": 75},
        "interfaces": [
            {
                "type": "screw_hole",
                "name": "hole_a",
                "diameter_mm": 4.5,
                "position_mm": [-30, 0, 70],
            },
            {
                "type": "screw_hole",
                "name": "hole_b",
                "diameter_mm": 4.5,
                "position_mm": [30, 0, 70],
            },
            {"type": "bore", "name": "cradle", "diameter_mm": 25, "position_mm": [0, 25, 10]},
        ],
        "probes": [{"kind": "solid_at", "p": [0, 38, 20], "label": "S6: lip above cradle"}],
    }
    plan = minimal_plan([part])
    plan["intent"] = INTENT
    plan["acceptance_bindings"] = [
        {"statement": "S2", "part": "hook", "interfaces": ["hole_a", "hole_b"]},
        {"statement": "S3", "part": "hook", "interfaces": ["hole_a", "hole_b"]},
        {"statement": "S4", "part": "hook", "interfaces": ["cradle"]},
        {"statement": "S5", "part": "hook"},
        {"statement": "S6", "part": "hook", "probes": ["S6: lip above cradle"]},
        {"statement": "S7", "part": "hook"},
    ]
    return plan


def test_valid_doc_and_plan_pass():
    assert oracle.validate(DOC, INTENT, CONSTS) == []
    assert oracle.check(_plan(), DOC, CONSTS) == []


def test_coordinate_field_rejected():
    doc = copy.deepcopy(DOC)
    doc["statements"][1]["position_mm"] = [0, 0, 0]
    assert any("statements/1" in e for e in oracle.validate(doc, INTENT, CONSTS))


def test_uncited_statement_rejected():
    doc = copy.deepcopy(DOC)
    doc["statements"][6]["cites"] = ["dishwasher safe"]
    errors = oracle.validate(doc, INTENT, CONSTS)
    assert errors == ["oracle: S7 ('Rounded, friendly look') cites nothing found in the intent"]


def test_whitespace_and_case_collapse_in_citation():
    doc = copy.deepcopy(DOC)
    doc["statements"][1]["cites"] = ["Two   COUNTERSUNK\nholes"]
    assert oracle.validate(doc, INTENT, CONSTS) == []


def test_param_citation_deferred_before_parameters_py():
    doc = copy.deepcopy(DOC)
    doc["statements"][3]["cites"] = ["HANDLE_D_MM"]
    assert oracle.validate(doc, INTENT, None) == []
    assert oracle.validate(doc, INTENT, {}) != []


def test_unknown_param_name():
    errors = oracle.validate(DOC, INTENT, {})
    assert any("S4" in e and "HANDLE_D_MM" in e for e in errors)


def test_duplicate_id():
    doc = copy.deepcopy(DOC)
    doc["statements"][2]["id"] = "S2"
    assert "oracle: duplicate statement id S2" in oracle.validate(doc, INTENT, CONSTS)


def test_unbound_statement():
    plan = _plan()
    plan["acceptance_bindings"] = [b for b in plan["acceptance_bindings"] if b["statement"] != "S3"]
    errors = oracle.check(plan, DOC, CONSTS)
    assert len(errors) == 1 and "S3" in errors[0] and "unbound" in errors[0]


def test_spacing_contradiction():
    plan = _plan()
    plan["parts"][0]["interfaces"][1]["position_mm"] = [90, 0, 70]
    errors = oracle.check(plan, DOC, CONSTS)
    assert len(errors) == 1 and "S3" in errors[0] and "120.00" in errors[0]


def test_feature_wrong_family_and_count():
    plan = _plan()
    plan["parts"][0]["interfaces"][0]["type"] = "boss"
    assert any("not of feature family" in e for e in oracle.check(plan, DOC, CONSTS))
    plan = _plan()
    plan["acceptance_bindings"][0]["interfaces"] = ["hole_a"]
    assert any("expects 2 bound" in e for e in oracle.check(plan, DOC, CONSTS))


def test_fit_too_tight():
    plan = _plan()
    plan["parts"][0]["interfaces"][2]["diameter_mm"] = 24.2
    assert any("S4" in e and "does not accept" in e for e in oracle.check(plan, DOC, CONSTS))


def test_extent_and_part_count():
    plan = _plan()
    plan["parts"][0]["dimensions"]["h_mm"] = 95
    assert any("S5" in e and "exceeds" in e for e in oracle.check(plan, DOC, CONSTS))
    plan = _plan()
    plan["parts"].append(dict(copy.deepcopy(plan["parts"][0]), id="hook2"))
    assert any("S1" in e and "expected 1" in e for e in oracle.check(plan, DOC, CONSTS))


def test_probe_label_and_missing_names():
    plan = _plan()
    plan["parts"][0]["probes"][0]["label"] = "lip above cradle"
    plan["acceptance_bindings"][4]["probes"] = ["lip above cradle"]
    assert any("no bound probe labelled 'S6" in e for e in oracle.check(plan, DOC, CONSTS))
    plan = _plan()
    plan["acceptance_bindings"][2]["interfaces"] = ["nope"]
    assert any("['nope'] not found" in e for e in oracle.check(plan, DOC, CONSTS))


def test_visual_statements_for_part():
    plan = _plan()
    assert [s["id"] for s in oracle.visual_statements(DOC, plan, "hook")] == ["S7"]
    assert oracle.visual_statements(None, plan, "hook") == []


class _BB:
    def __init__(self, x, y, z):
        self.xlen, self.ylen, self.zlen = x, y, z


class _Body:
    def __init__(self, x, y, z):
        self._bb = _BB(x, y, z)

    def BoundingBox(self):  # noqa: N802 -- mirrors the CadQuery Shape API
        return self._bb


def test_verify_extent_and_feature_absent(monkeypatch):
    import probes

    monkeypatch.setattr(probes, "evaluate", lambda probe, body: (True, "IN"))
    plan = _plan()
    feature_issues = [
        {"part": "hook", "type": "feature_absent", "position_mm": [30, 0, 70]},
    ]
    issues = oracle.verify(plan, DOC, "hook", _Body(70, 40, 131), feature_issues, CONSTS)
    by_stmt = {i["statement"]: i for i in issues}
    assert set(by_stmt) == {"S2", "S3", "S5"}
    assert "131" in by_stmt["S5"]["message"]
    assert all(i["source"] == "oracle" and i["type"] == "oracle_unmet" for i in issues)


def test_verify_probe_failure(monkeypatch):
    import probes

    monkeypatch.setattr(probes, "evaluate", lambda probe, body: (False, "OUT"))
    issues = oracle.verify(_plan(), DOC, "hook", _Body(70, 40, 75), [], CONSTS)
    assert [i["statement"] for i in issues] == ["S6"]


@pytest.mark.parametrize(
    ("prior", "round_", "action"), [(None, 1, "fix"), (1, 2, "fix"), (2, 3, "ask_user")]
)
def test_rounds(prior, round_, action):
    previous = (
        {"issues": [{"type": "oracle_unmet", "statement": "S5", "round": prior}]} if prior else None
    )
    issues = [{"type": "oracle_unmet", "statement": "S5", "round": 1}]
    oracle.apply_rounds(issues, previous)
    assert issues[0]["round"] == round_ and issues[0]["action"] == action


def test_cli_validate(tmp_path, capsys):
    path = tmp_path / "acceptance.json"
    path.write_text(json.dumps(DOC), encoding="utf-8")
    assert (
        oracle.main(
            ["validate", str(path), "--intent", INTENT, "--params", str(tmp_path / "none.py")]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["success"] is True
    assert (
        oracle.main(
            [
                "validate",
                str(path),
                "--intent",
                "unrelated text",
                "--params",
                str(tmp_path / "none.py"),
            ]
        )
        == 1
    )
