import json
import os
import subprocess
import sys

import pytest
import trimesh

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))
# Runs of repo scripts (templates, fixtures) must not write history/ into the repo; the
# history tests opt back in by deleting this.
os.environ["CQ_HISTORY_SKIP"] = "1"

WRAPPER = os.path.join(REPO_ROOT, "src", "run_cadquery_model.py")


def run_wrapper(script_path, *extra_args):
    """Run run_cadquery_model.py on `script_path` as a subprocess; return `(rc, data)`.
    Shared by every test that exercises the wrapper's CLI/JSON contract."""
    result = subprocess.run(
        [sys.executable, WRAPPER, str(script_path), *extra_args],
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout) if result.stdout.strip() else {}
    return result.returncode, data


def minimal_plan(parts: list[dict]) -> dict:
    """Minimal valid BUILD_PLAN.json dict wrapping the given `parts`, shared by every
    integration test that only cares about the `parts` list."""
    return {
        "schema_version": 1,
        "intent": (
            "Minimal shared integration-test fixture: the parts list under test, printed "
            "as-is with default constraints; no fits or assumptions to record here."
        ),
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


def box_stl(path, center, extents=(10, 10, 10)):
    """Write an axis-aligned box STL of `extents` centered at `center` to `path`."""
    mesh = trimesh.creation.box(extents=extents)
    mesh.apply_translation(center)
    mesh.export(str(path))


@pytest.fixture
def skill_src():
    """Path to the src/ directory holding the tool scripts."""
    import pathlib

    return pathlib.Path(REPO_ROOT) / "src"


@pytest.fixture
def tmp_stl(tmp_path):
    """Generate a watertight 10mm cube STL on demand."""
    stl = tmp_path / "cube.stl"
    script = tmp_path / "cube.py"
    script.write_text(
        "import cadquery as cq\n"
        "r = cq.Workplane('XY').box(10, 10, 10)\n"
        f"cq.exporters.export(r, {str(stl)!r},"
        " tolerance=0.01, angularTolerance=0.1)\n"
    )
    subprocess.run([sys.executable, str(script)], check=True, cwd=str(tmp_path))
    return stl


@pytest.fixture
def good_script(tmp_path):
    """CadQuery script that writes a watertight cube next to itself.

    Uses `result` as the top-level variable name per the pipeline spec so that
    render_preview.py can capture it for preview rendering.
    """
    script = tmp_path / "good_model.py"
    script.write_text(
        "import cadquery as cq\n"
        "result = cq.Workplane('XY').box(10, 10, 10)\n"
        "cq.exporters.export(result, 'good_model.stl',"
        " tolerance=0.01, angularTolerance=0.1)\n"
    )
    return script


@pytest.fixture
def bad_script(tmp_path):
    """CadQuery script that raises (fillet radius too large)."""
    script = tmp_path / "bad.py"
    script.write_text(
        "import cadquery as cq\ncq.Workplane('XY').box(10, 10, 10).edges('|Z').fillet(99)\n"
    )
    return script


@pytest.fixture
def empty_script(tmp_path):
    """Script that exits 0 without writing any STL."""
    script = tmp_path / "empty.py"
    script.write_text('print("no export called")\n')
    return script
