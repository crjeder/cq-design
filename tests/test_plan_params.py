import pytest

import plan_params as pp

C = {"BASKET_RIM_OD_MM": 70.0, "GROOVE_CLEARANCE_MM": 1.0}


def test_expression_resolves():
    assert pp.evaluate("BASKET_RIM_OD_MM + GROOVE_CLEARANCE_MM", C) == 71.0
    assert pp.evaluate("max(2, -(3 - 1)) * 2.5", C) == 5.0
    assert pp.evaluate("round(10 / 4)", C) == 2


@pytest.mark.parametrize(
    "bad", ["NOPE_MM", "__import__('os')", "a.b", "[1]", "2 ** 3", "x if 1 else 2"]
)
def test_unsafe_or_unknown_rejected(bad):
    with pytest.raises(pp.PlanParamError):
        pp.evaluate(bad, C)


def test_load_constants_skips_non_numeric_and_chains(tmp_path):
    f = tmp_path / "parameters.py"
    f.write_text('"""doc"""\nA = 10  # user\nB = A * 2\nNAME = "x"\nT = (1, 2)\n', encoding="utf-8")
    assert pp.load_constants(f) == {"A": 10, "B": 20}
    assert pp.load_constants(tmp_path / "missing.py") == {}


def _plan(w):
    return {
        "parts": [
            {"id": "p", "blocks_needed": [{"name": "b", "id": "i", "params": {"w": w, "h": 5}}]}
        ]
    }


def test_resolve_plan_and_errors():
    out, errs = pp.resolve_plan(_plan("BASKET_RIM_OD_MM + 1"), C)
    assert not errs and out["parts"][0]["blocks_needed"][0]["params"]["w"] == 71.0
    _, errs = pp.resolve_plan(_plan("NOPE"), C)
    assert errs and "NOPE" in errs[0]


def test_literal_and_expression_hash_equal_and_change_detected():
    a = pp.resolved_hashes(pp.resolve_plan(_plan("BASKET_RIM_OD_MM + 1"), C)[0])
    b = pp.resolved_hashes(_plan(71.0))
    assert a == b
    c = pp.resolved_hashes(pp.resolve_plan(_plan("BASKET_RIM_OD_MM + 2"), C)[0])
    assert pp.changed_parts(a, c) == ["p"]
    assert pp.changed_parts(a, a) == []
    assert pp.changed_parts(None, a) == []


def test_enum_word_param_left_alone():
    out, errs = pp.resolve_plan(_plan("auto"), C)
    assert not errs and out["parts"][0]["blocks_needed"][0]["params"]["w"] == "auto"
    _, errs = pp.resolve_plan(_plan("NOPE_MM"), C)
    assert errs
