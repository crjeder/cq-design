"""Tests for the templates/ archetype library: index validation and per-template
pre-verification (lint + geometry)."""

import json
import os
import sys

import jsonschema
import pytest

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL_ROOT, "src"))

from conftest import run_wrapper as run  # noqa: E402

from script_lint import lint_script  # noqa: E402

TEMPLATES_DIR = os.path.join(SKILL_ROOT, "templates")
INDEX_PATH = os.path.join(TEMPLATES_DIR, "archetypes.json")
SCHEMA_PATH = os.path.join(TEMPLATES_DIR, "archetypes_schema.json")


def _load_index():
    with open(INDEX_PATH, encoding="utf-8") as f:
        return json.load(f)


def _load_schema():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


INDEX = _load_index()


def test_index_validates_against_schema():
    schema = _load_schema()
    jsonschema.Draft7Validator(schema).validate(INDEX)


def test_index_names_unique():
    names = [e["name"] for e in INDEX]
    assert len(names) == len(set(names)), f"duplicate archetype names: {names}"


def test_every_listed_file_exists():
    for entry in INDEX:
        path = os.path.join(TEMPLATES_DIR, entry["file"])
        assert os.path.isfile(path), f"{entry['name']}: file {entry['file']} does not exist"


def test_every_template_file_is_listed():
    listed = {entry["file"] for entry in INDEX}
    on_disk = {f for f in os.listdir(TEMPLATES_DIR) if f.endswith(".py") and f != "__init__.py"}
    orphans = on_disk - listed
    assert not orphans, f"template file(s) with no archetypes.json descriptor: {orphans}"


@pytest.mark.parametrize("entry", INDEX, ids=[e["name"] for e in INDEX])
def test_template_lint_clean(entry):
    path = os.path.join(TEMPLATES_DIR, entry["file"])
    findings = lint_script(path)
    assert findings == [], f"{entry['name']}: lint findings {[f.to_dict() for f in findings]}"


@pytest.mark.parametrize("entry", INDEX, ids=[e["name"] for e in INDEX])
def test_template_geometry_valid(entry):
    path = os.path.join(TEMPLATES_DIR, entry["file"])
    rc, data = run(path)
    assert rc == 0, f"{entry['name']}: wrapper failed: {data.get('errors')}"
    assert data["success"] is True
    assert data["watertight"] is True
    assert data["errors"] == []
