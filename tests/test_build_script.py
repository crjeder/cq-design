"""Tests for the deliverable build.py (src/build_template.py).

The template is rendered (SKILL_SRC substituted with the repo src) into a build/
directory and run as a subprocess, the way the skill ships it. CadQuery-backed, so
integration-speed.
"""

import json
import subprocess
import sys

import trimesh


def _render_build_py(build_dir, skill_src):
    """Write build.py into build_dir from the template, substituting SKILL_SRC."""
    template = (skill_src / "build_template.py").read_text(encoding="utf-8")
    rendered = template.replace("{{SKILL_SRC}}", str(skill_src))
    build_py = build_dir / "build.py"
    build_py.write_text(rendered, encoding="utf-8")
    return build_py


def _write_part(build_dir, pid, body):
    (build_dir / f"{pid}.py").write_text(body, encoding="utf-8")


def _plan(parts):
    return {
        "schema_version": 1,
        "intent": "build script fixture",
        "printer": "Bambu P1S",
        "material": "PLA",
        "nozzle_mm": 0.4,
        "parts": parts,
        "constraints": {
            "wall_min_mm": 1.0,
            "overhang_max_deg": 45,
            "dimension_tolerance_mm": 0.2,
        },
    }


def _setup(tmp_path, skill_src, parts, part_bodies):
    """Lay out tmp/BUILD_PLAN.json + tmp/build/{parts, build.py}; return build dir."""
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    (tmp_path / "BUILD_PLAN.json").write_text(
        json.dumps(_plan(parts)), encoding="utf-8"
    )
    for pid, body in part_bodies.items():
        _write_part(build_dir, pid, body)
    _render_build_py(build_dir, skill_src)
    return build_dir


def _run(build_dir):
    return subprocess.run(
        [sys.executable, str(build_dir / "build.py")],
        capture_output=True,
        text=True,
        cwd=str(build_dir.parent),
    )


_FLAT = "import cadquery as cq\nresult = cq.Workplane('XY').box(20, 20, 4)\n"
# A tall post: its longest (inferred-load) axis is Z, the FDM-weak direction, so
# the optimizer lays it down — the deliverable pose is a rotation of the authored one.
_POST = "import cadquery as cq\nresult = cq.Workplane('XY').box(4, 4, 20)\n"


def test_build_py_regenerates_all_plates(tmp_path, skill_src):
    build_dir = _setup(
        tmp_path,
        skill_src,
        [
            {"id": "base", "description": "base", "plate": "shared"},
            {"id": "lid", "description": "lid", "plate": "shared"},
        ],
        {"base": _FLAT, "lid": _FLAT},
    )

    proc = _run(build_dir)

    assert proc.returncode == 0, proc.stderr
    assert (build_dir / "model.3mf").exists()
    assert (build_dir / "base.stl").exists()
    assert (build_dir / "lid.stl").exists()
    # Two unions on one plate -> one fused plate STL.
    assert (build_dir / "plate_shared.stl").exists()


def test_build_py_missing_part_fails_naming_union(tmp_path, skill_src):
    # Plan references "ghost" but no ghost.py is written.
    build_dir = _setup(
        tmp_path,
        skill_src,
        [{"id": "ghost", "description": "missing"}],
        {},
    )

    proc = _run(build_dir)

    assert proc.returncode != 0
    assert "ghost" in proc.stderr


def test_build_py_applies_print_orientation_and_is_deterministic(tmp_path, skill_src):
    build_dir = _setup(
        tmp_path,
        skill_src,
        [{"id": "post", "description": "tall post"}],
        {"post": _POST},
    )

    proc1 = _run(build_dir)
    assert proc1.returncode == 0, proc1.stderr
    model = build_dir / "model.3mf"
    z1 = float(trimesh.load(model).extents[2])

    # The authored post is 20 mm tall; laid down for strength it is ~4 mm in Z.
    assert z1 < 10

    # Re-running yields the identical orientation (deterministic selection).
    proc2 = _run(build_dir)
    assert proc2.returncode == 0, proc2.stderr
    z2 = float(trimesh.load(model).extents[2])
    assert abs(z1 - z2) < 0.1


def test_build_py_reuses_orientations_json(tmp_path, skill_src):
    build_dir = _setup(
        tmp_path,
        skill_src,
        [{"id": "plate", "description": "flat plate"}],
        {"plate": _FLAT},
    )
    # Accepted orientations stand the flat plate up (90 deg about X): the 20 mm
    # axis becomes vertical, so the deliverable is ~20 mm tall.
    (build_dir / "orientations.json").write_text(
        json.dumps({"plate": {"rotate": [{"axis": "X", "angle_deg": 90}]}}),
        encoding="utf-8",
    )

    proc = _run(build_dir)

    assert proc.returncode == 0, proc.stderr
    z = float(trimesh.load(build_dir / "model.3mf").extents[2])
    assert z > 18
