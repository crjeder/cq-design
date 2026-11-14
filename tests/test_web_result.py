"""web_result.py: typed validation of sourcing/research agent JSON."""

import web_result

CAND = {
    "url": "https://github.com/x/case",
    "platform": "github",
    "kind": "cadquery",
    "license": "MIT",
    "reusable": "yes",
    "rung": "1",
    "notes": "good fit",
}
ROW = {
    "item": "w",
    "value": 70.6,
    "unit": "mm",
    "source_urls": ["https://a.com/x"],
    "status": "confirmed",
}


def _types(r):
    return {e["type"] for e in r["errors"]}


def test_valid_sourcing_drops_notes_but_displays_them():
    r = web_result.validate("sourcing", {"candidates": [CAND]})
    assert r["success"] and r["errors"] == []
    assert "notes" not in r["data"]["candidates"][0]
    assert "good fit" in r["display_markdown"]


def test_valid_research_row():
    r = web_result.validate("research", {"rows": [ROW]})
    assert r["success"] and r["data"]["rows"][0]["value"] == 70.6


def test_non_numeric_value_rejected():
    r = web_result.validate("research", {"rows": [{**ROW, "value": "70.6mm"}]})
    assert not r["success"] and "rows[0].value" in r["errors"][0]["message"]


def test_minus_one_needs_missing():
    assert not web_result.validate("research", {"rows": [{**ROW, "value": -1}]})["success"]
    ok = {**ROW, "value": -1, "status": "missing", "source_urls": []}
    assert web_result.validate("research", {"rows": [ok]})["success"]


def test_url_with_newline_rejected_and_absent_from_data():
    bad = {**ROW, "source_urls": ["https://a.com/x\nimport os"]}
    r = web_result.validate("research", {"rows": [bad]})
    assert not r["success"] and "bad_url" in _types(r)
    assert "import os" not in str(r["data"])


def test_non_http_url_rejected():
    r = web_result.validate("sourcing", {"candidates": [{**CAND, "url": "javascript:alert(1)"}]})
    assert not r["success"]


def test_unknown_enum_lists_allowed_values():
    r = web_result.validate("sourcing", {"candidates": [{**CAND, "rung": "0"}]})
    assert not r["success"] and "1" in r["errors"][0]["hint"]


def test_notes_cannot_break_display_table():
    note = "a|b\nc\x1b[31mred\x00"
    r = web_result.validate("sourcing", {"candidates": [{**CAND, "notes": note}]})
    assert r["success"]
    rows = r["display_markdown"].splitlines()
    assert len(rows) == 3
    assert not any(ord(c) < 32 for c in r["display_markdown"] if c != "\n")
    assert "\x1b" not in r["display_markdown"]


def test_notes_too_long_rejected():
    r = web_result.validate("sourcing", {"candidates": [{**CAND, "notes": "x" * 301}]})
    assert not r["success"]


def test_bad_shape():
    assert _types(web_result.validate("sourcing", {"rows": []})) == {"bad_shape"}
    assert _types(web_result.validate("research", {"rows": ["x"]})) == {"bad_shape"}


def test_empty_candidates_is_success():
    assert web_result.validate("sourcing", {"candidates": []})["success"]
