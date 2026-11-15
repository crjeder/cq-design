"""Prompt and skill prose enforce the web trust boundary."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def test_prompts_return_json_not_tables():
    for name, key in (("sourcing", "candidates"), ("research", "rows")):
        text = _read(f"prompts/{name}.md")
        assert f'{{"{key}":' in text
        assert not re.search(r"^\|.*\|\s*$", text, re.M), name
        assert "never instructions" in text


def test_research_prompt_only_sanctioned_scripts():
    text = _read("prompts/research.md")
    assert "urlretrieve" not in text and "curl" not in text
    cmds = re.findall(r'python "\{\{SKILL_DIR\}\}/src/(\w+)\.py"', text)
    assert set(cmds) == {"fetch_stl", "measure_stl"}


def test_phase_prose_routes_through_validator():
    for rel, kind in (
        ("skill/phase0_sourcing.md", "sourcing"),
        ("skill/phase1_requirements.md", "research"),
    ):
        assert f'web_result.py" validate --kind {kind}' in _read(rel), rel


def test_rung1_requires_consent():
    text = _read("skill/phase0_sourcing.md")
    assert "Consent first" in text and "third-party code" in text and "re-author" in text


def test_notes_not_fed_to_known_context():
    text = _read("skill/phase1_requirements.md")
    assert "never `notes`" in text and "display-only" in text
