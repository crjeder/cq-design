"""Tests for the deliverable build.py (src/build_template.py).

The template is copied verbatim into a build/ directory; the build tooling is
bundled into a sibling lib/ directory (not build/ itself, which holds only the
edited part scripts), the way the skill ships it. build.py resolves its imports
from ../lib relative to its own directory (no SKILL_SRC). Run as a subprocess.
CadQuery-backed, so integration-speed.
"""

import json
import subprocess
import sys

import trimesh
from conftest import minimal_plan

from bundle_project import bundle


def _render_build_py(build_dir):
    """Bundle build.py and the lib/ tooling the way the skill ships it."""
    bundle(build_dir.parent)
    return build_dir / "build.py"


def _write_part(build_dir, pid, body):
    (build_dir / f"{pid}.py").write_text(body, encoding="utf-8")


def _setup(tmp_path, skill_src, parts, part_bodies):
    """Lay out tmp/BUILD_PLAN.json + tmp/build/{parts, build.py}; return build dir."""
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    (tmp_path / "BUILD_PLAN.json").write_text(json.dumps(minimal_plan(parts)), encoding="utf-8")
    for pid, body in part_bodies.items():
        _write_part(build_dir, pid, body)
    _render_build_py(build_dir)
    return build_dir


def _run(build_dir, env=None, *args):
    return subprocess.run(
        [sys.executable, str(build_dir / "build.py"), *args],
        capture_output=True,
        text=True,
        cwd=str(build_dir.parent),
        env=env,
    )


_FLAT = "import cadquery as cq\nresult = cq.Workplane('XY').box(20, 20, 4)\n"
# A tall post: its longest (inferred-load) axis is Z, the FDM-weak direction, so
# the optimizer lays it down — the deliverable pose is a rotation of the authored one.
_POST = "import cadquery as cq\nresult = cq.Workplane('XY').box(4, 4, 20)\n"


def test_template_has_no_skill_src_placeholder(skill_src):
    # build.py is now copied verbatim and resolves tooling from its own dir; the
    # SKILL_SRC placeholder / bootstrap must be gone.
    template = (skill_src / "build_template.py").read_text(encoding="utf-8")
    assert "{{SKILL_SRC}}" not in template
    assert "SKILL_SRC" not in template


def test_build_py_resolves_tooling_without_src_on_pythonpath(tmp_path, skill_src):
    import os

    build_dir = _setup(
        tmp_path,
        skill_src,
        [{"id": "base", "description": "base"}],
        {"base": _FLAT},
    )
    # Strip PYTHONPATH so the only way imports resolve is the bundled tooling in
    # ../lib (added to sys.path by build.py itself) -- proving build.py does not
    # need the skill installed.
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}

    proc = _run(build_dir, env=env)

    assert proc.returncode == 0, proc.stderr
    assert (build_dir.parent / "model.3mf").exists()
    assert (build_dir.parent / "stl" / "base.stl").exists()


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
    assert (build_dir.parent / "model.3mf").exists()
    assert (build_dir.parent / "stl" / "base.stl").exists()
    assert (build_dir.parent / "stl" / "lid.stl").exists()
    # Two unions on one plate -> one fused plate STL.
    assert (build_dir.parent / "stl" / "plate_shared.stl").exists()


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
    model = build_dir.parent / "model.3mf"
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
    # axis becomes vertical, so the deliverable is ~20 mm tall. No stamp on the
    # entry -- an unstamped entry is reused unconditionally.
    (build_dir / "orientations.json").write_text(
        json.dumps({"plate": {"rotate": [{"axis": "X", "angle_deg": 90}]}}),
        encoding="utf-8",
    )

    proc = _run(build_dir)

    assert proc.returncode == 0, proc.stderr
    z = float(trimesh.load(build_dir.parent / "model.3mf").extents[2])
    assert z > 18


def test_build_py_reuses_orientations_json_with_matching_stamp(tmp_path, skill_src):
    from freshness import script_hash

    build_dir = _setup(
        tmp_path,
        skill_src,
        [{"id": "plate", "description": "flat plate"}],
        {"plate": _FLAT},
    )
    stamp = script_hash(str(build_dir / "plate.py"))
    (build_dir / "orientations.json").write_text(
        json.dumps(
            {
                "plate": {
                    "rotate": [{"axis": "X", "angle_deg": 90}],
                    "source_script_hash": stamp,
                }
            }
        ),
        encoding="utf-8",
    )

    proc = _run(build_dir)

    assert proc.returncode == 0, proc.stderr
    z = float(trimesh.load(build_dir.parent / "model.3mf").extents[2])
    assert z > 18


def test_build_py_recomputes_stale_orientation(tmp_path, skill_src):
    build_dir = _setup(
        tmp_path,
        skill_src,
        [{"id": "plate", "description": "flat plate"}],
        {"plate": _FLAT},
    )
    # Stamp is for content that no longer matches plate.py -- the entry is stale, so
    # the accepted 90-degree-about-X pose must be recomputed rather than reused. The
    # flat plate's own best-strength/least-support pose keeps it lying flat.
    (build_dir / "orientations.json").write_text(
        json.dumps(
            {
                "plate": {
                    "rotate": [{"axis": "X", "angle_deg": 90}],
                    "source_script_hash": "0" * 64,
                }
            }
        ),
        encoding="utf-8",
    )

    proc = _run(build_dir)

    assert proc.returncode == 0, proc.stderr
    z = float(trimesh.load(build_dir.parent / "model.3mf").extents[2])
    assert z < 10
    assert "plate" in proc.stdout
    assert "recomputed" in proc.stdout


def test_build_py_formats_step_writes_step_per_union(tmp_path, skill_src):
    build_dir = _setup(
        tmp_path, skill_src, [{"id": "base", "description": "base"}], {"base": _FLAT}
    )

    proc = _run(build_dir, None, "--formats", "step")

    assert proc.returncode == 0, proc.stderr
    assert (build_dir.parent / "stl" / "base.step").exists()
    assert (build_dir.parent / "stl" / "base.stl").exists()
    assert "base.step" in proc.stdout


def test_build_py_formats_unsupported_key_exits_nonzero(tmp_path, skill_src):
    build_dir = _setup(
        tmp_path, skill_src, [{"id": "base", "description": "base"}], {"base": _FLAT}
    )

    proc = _run(build_dir, None, "--formats", "dxf")

    assert proc.returncode != 0
    assert "step" in proc.stderr
    assert not (build_dir.parent / "model.3mf").exists()

def test_build_py_prints_numbered_progress_before_summary(tmp_path, skill_src):
    build_dir = _setup(
        tmp_path,
        skill_src,
        [{"id": "base", "description": "base"}, {"id": "lid", "description": "lid"}],
        {"base": _FLAT, "lid": _FLAT},
    )

    proc = _run(build_dir)

    assert proc.returncode == 0, proc.stderr
    out = proc.stdout
    # No orientations.json: both unions are computed, so numbered over those two.
    assert "[1/2] orientation base" in out
    assert "[2/2] orientation lid" in out
    assert "[1/2] loading base" in out
    assert "[2/2] loading lid" in out
    assert "writing model.3mf" in out
    assert out.index("[2/2] loading lid") < out.index("model.3mf:")


def test_build_py_reused_orientations_print_no_orientation_lines(tmp_path, skill_src):
    build_dir = _setup(
        tmp_path,
        skill_src,
        [{"id": "plate", "description": "flat plate"}],
        {"plate": _FLAT},
    )
    (build_dir / "orientations.json").write_text(
        json.dumps({"plate": {"rotate": []}}), encoding="utf-8"
    )

    proc = _run(build_dir)

    assert proc.returncode == 0, proc.stderr
    assert "orientation plate" not in proc.stdout
    assert "[1/1] loading plate" in proc.stdout


def test_build_py_recomputed_orientations_numbered_over_recomputed_only(tmp_path, skill_src):
    build_dir = _setup(
        tmp_path,
        skill_src,
        [
            {"id": "a", "description": "a"},
            {"id": "b", "description": "b"},
            {"id": "c", "description": "c"},
        ],
        {"a": _FLAT, "b": _FLAT, "c": _FLAT},
    )
    (build_dir / "orientations.json").write_text(
        json.dumps({"b": {"rotate": []}}), encoding="utf-8"
    )

    proc = _run(build_dir)

    assert proc.returncode == 0, proc.stderr
    assert "[1/2] orientation a" in proc.stdout
    assert "[2/2] orientation c" in proc.stdout
    assert "orientation b" not in proc.stdout
