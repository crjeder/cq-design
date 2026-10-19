"""Doc-example checks: the claims prompts make about code must hold."""

import inspect
import re
from collections.abc import Callable
from pathlib import Path

import cadquery as cq
import pytest

import render_prompt as rp
from plan import validate_plan

ROOT = Path(__file__).parent.parent
PROMPTS = ROOT / "prompts"

# Prompt -> renderer functions whose source decides which reference files get filled in.
RENDERERS: dict[str, list[Callable]] = {
    "audit.md": [rp.render_audit],
    "builder.md": [rp.render_builder],
    "part.md": [rp.part_spec],
    "planning.md": [rp.render_planning],
    "research.md": [rp.render_research],
    "sourcing.md": [rp.render_sourcing, rp.sourcing_corpus],
}


def _fences(name: str, lang: str) -> list[str]:
    text = (PROMPTS / name).read_text(encoding="utf-8")
    return re.findall(rf"^```{lang}\n(.*?)^```", text, re.M | re.S)


def test_planning_example_matches_schema(tmp_path):
    plan = tmp_path / "BUILD_PLAN.json"
    plan.write_text(_fences("planning.md", "json")[0], encoding="utf-8")
    assert validate_plan(str(plan)) == []


def _namespace() -> dict:
    """Geometry that satisfies every check in part.md's examples when they are correct."""
    body = cq.Workplane("XY").box(40, 30, 20)
    return {
        "cq": cq,
        "body": body,
        "slot": cq.Workplane("XY").box(5, 40, 5).translate((10, 0, 10)),
        "wp": cq.Workplane("XY", origin=(0, 0, 12)),
        "leg": cq.Workplane("XY").box(10, 10, 10, centered=(True, True, False)),
        "standoff": cq.Workplane("XY").workplane(offset=10).circle(3).extrude(5),
        "riser": cq.Workplane("XY").box(6, 10, 10.5, centered=(True, True, False)),
        "knuckle": cq.Workplane("XZ").center(0, 13).circle(3).extrude(5, both=True),
        "R": 1.0,
        "width": 40,
        "depth": 30,
        "wall": 3,
        "boss_w": 20,
        "boss_d": 15,
        "boss_r": 2,
        "boss_h": 5,
        "base_volume": 40 * 30 * 3,
    }


@pytest.mark.parametrize("code", _fences("part.md", "python"))
def test_part_python_examples_run(code):
    exec(compile(code, "part.md", "exec"), _namespace())


def test_prompts_have_renderers():
    assert {p.name for p in PROMPTS.glob("*.md")} == RENDERERS.keys()


@pytest.mark.parametrize("name", sorted(RENDERERS))
def test_reference_paths_resolve(name):
    text = (PROMPTS / name).read_text(encoding="utf-8")
    source = "".join(inspect.getsource(f) for f in RENDERERS[name])
    bad = []
    for prefix, ref in re.findall(r"(\{\{SKILL_DIR\}\}/)?\breference/([\w .-]+?\.\w+)", text):
        assert (ROOT / "reference" / ref).exists(), ref
        if not prefix and ref not in source:
            bad.append(ref)
    assert not bad, f"bare reference/ path neither filled nor {{{{SKILL_DIR}}}}-prefixed: {bad}"
