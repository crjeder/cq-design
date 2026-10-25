"""Tests for the templates/ archetype library: index validation and per-template
pre-verification (lint + geometry)."""

import json
import os
import sys

import jsonschema
import pytest

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL_ROOT, "src"))

from conftest import minimal_plan  # noqa: E402
from conftest import run_wrapper as run  # noqa: E402

from plan import validate_plan  # noqa: E402
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

# Volume and bbox of each template before the step-form conversion. Templates whose
# cosmetic corner fillets moved to plan `edges` (applied in the print-pose finishing
# pass) build slightly more volume; two carry deliberate fixes.
BEFORE = {
    "adapter-ring-flanged": (9600.93, (-22.5, -22.5, 0, 22.5, 22.5, 15)),
    "clip": (960.0, (-7.5, 0, 0, 7.5, 14, 8)),
    "enclosure-body": (14019.38, (-30, -20, 0, 30, 20, 25)),
    "gridfinity-baseplate": (7691.27, (-63, -42, 0, 63, 42, 4.75)),
    "gridfinity-bin": (27715.51, (-41.75, -20.75, 0, 41.75, 20.75, 24.551)),
    "hook": (7191.96, (-12.5, -20.5, 0, 12.5, 5, 40)),
    # fix: the vertical-arm hole was a Z cylinder wider than the arm (a notch, not a hole)
    "l-bracket-gusset": (6910.89, (-2, -10, 0, 40, 10, 40)),
    "lid-screwed": (7029.56, (-30, -20, 0, 30, 20, 3)),
    "lid-sliding": (6253.27, (-30.001, 0, 0, 30.001, 36, 3)),
    # fix: the clips' hook teeth pointed up into the panel; they now hang below it
    "lid-snap": (7375.22, (-30, -24, -1.9, 30, 24, 3)),
    "plate-boss-pattern": (9537.6, (-30, -25, 0, 30, 25, 9)),
    "stand": (155340.0, (-40, 0, 0, 40, 70, 45)),
}
VOLUME_REL_TOL = {
    "enclosure-body": 0.015,
    "lid-screwed": 0.005,
    "lid-snap": 0.005,
    "plate-boss-pattern": 0.005,
    "l-bracket-gusset": 0.005,
}


@pytest.fixture
def archetype_plan(tmp_path, monkeypatch):
    def _write(entry):
        path = tmp_path / "BUILD_PLAN.json"
        path.write_text(json.dumps(minimal_plan([entry["part"]])), encoding="utf-8")
        monkeypatch.setenv("CQ_PLAN", str(path))
        return str(path)

    return _write


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
def test_archetype_part_validates(entry, archetype_plan):
    assert validate_plan(archetype_plan(entry)) == []


@pytest.mark.parametrize("entry", INDEX, ids=[e["name"] for e in INDEX])
def test_template_matches_pre_conversion_build(entry, archetype_plan):
    import runpy

    archetype_plan(entry)
    shape = runpy.run_path(os.path.join(TEMPLATES_DIR, entry["file"]))["result"].findSolid()
    volume, box = BEFORE[entry["name"]]
    bb = shape.BoundingBox()
    got = (bb.xmin, bb.ymin, bb.zmin, bb.xmax, bb.ymax, bb.zmax)
    assert shape.Volume() == pytest.approx(volume, rel=VOLUME_REL_TOL.get(entry["name"], 1e-4))
    assert got == pytest.approx(box, abs=0.01)


@pytest.mark.parametrize("entry", INDEX, ids=[e["name"] for e in INDEX])
def test_template_geometry_valid(entry, archetype_plan):
    archetype_plan(entry)
    path = os.path.join(TEMPLATES_DIR, entry["file"])
    rc, data = run(path)
    assert rc == 0, f"{entry['name']}: wrapper failed: {data.get('errors')}"
    assert data["success"] is True
    assert data["watertight"] is True
    assert data["errors"] == []
