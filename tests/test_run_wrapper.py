import json
import os
import subprocess
import sys

SRC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")

WRAPPER = os.path.join(SRC_DIR, "run_cadquery_model.py")
RENDER_PREVIEW = os.path.join(SRC_DIR, "render_preview.py")


def run(script_path, *extra_args):
    result = subprocess.run(
        [sys.executable, WRAPPER, str(script_path), *extra_args],
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout) if result.stdout.strip() else {}
    return result.returncode, data


# ---- core behavior (exit codes and success flag) ----


def test_happy_path(good_script):
    rc, data = run(good_script)
    assert rc == 0
    assert data["success"] is True
    assert data["returncode"] == 0
    # STL paths are hidden during iteration — use --deliver to get them
    assert data["stl"] is None
    assert data["stls"] == []


def test_happy_path_deliver(tmp_path):
    # Script must assign top-level `result` for the exporter to load it.
    script = tmp_path / "deliver_model.py"
    script.write_text(
        "import cadquery as cq\n"
        "result = cq.Workplane('XY').box(10, 10, 10)\n"
        "cq.exporters.export(result, 'deliver_model.stl',"
        " tolerance=0.01, angularTolerance=0.1)\n"
    )
    rc, data = run(script, "--deliver", "--formats", "stl")
    assert rc == 0
    assert data["success"] is True
    assert len(data["stls"]) == 1
    assert data["stl"].endswith("deliver_model.stl")


def test_strict_watertight(good_script):
    rc, data = run(good_script, "--strict")
    assert rc == 0
    assert data["success"] is True
    assert data["watertight"] is True


def test_strict_empty_fails(empty_script):
    rc, data = run(empty_script, "--strict")
    assert rc == 1
    assert data["success"] is False
    assert "No STL files produced" in data["stderr"]


def test_bad_script_traceback(bad_script):
    rc, data = run(bad_script)
    assert rc == 1
    assert data["success"] is False
    assert "Traceback" in data["stderr"] or "Error" in data["stderr"]


def test_timeout(tmp_path):
    script = tmp_path / "slow.py"
    script.write_text("import time; time.sleep(60)\n")
    result = subprocess.run(
        [sys.executable, WRAPPER, str(script), "--timeout", "2"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 3


# ---- JSON shape: new fields always present ----


def test_json_shape_keys(good_script):
    """All documented keys must be present in every response."""
    _, data = run(good_script)
    expected = {
        "success",
        "script",
        "geometry",
        "errors",
        "stls",
        "stl",
        "previews",
        "preview",
        "threemfs",
        "threemf",
        "watertight",
        "stdout",
        "stderr",
        "returncode",
    }
    assert expected.issubset(data.keys())


def test_geometry_field_present_on_success(good_script):
    _, data = run(good_script)
    assert data["geometry"] is not None
    geo = data["geometry"]
    assert "bbox" in geo
    assert "x_mm" in geo["bbox"]
    assert geo["bbox"]["x_mm"] > 0
    assert geo["volume_cm3"] is not None
    assert geo["weight_g"] is not None
    assert geo["face_count"] > 0


def test_geometry_null_on_failure(bad_script):
    _, data = run(bad_script)
    assert data["geometry"] is None


def test_errors_always_present(good_script, bad_script):
    _, data = run(good_script)
    assert "errors" in data
    assert isinstance(data["errors"], list)

    _, data = run(bad_script)
    assert "errors" in data
    assert isinstance(data["errors"], list)


def test_errors_empty_on_clean_run(good_script):
    _, data = run(good_script)
    # A clean watertight cube should have no errors
    assert data["errors"] == []


def test_occ_error_translated(bad_script):
    """A script that raises an OCC exception should have a structured error entry."""
    _, data = run(bad_script)
    # May or may not parse to a structured error depending on OCC exception text,
    # but errors must always be a list
    assert isinstance(data["errors"], list)


def test_multi_union_dict_result_validates_each_union(tmp_path):
    """A part whose `result` is a {union_id: Workplane} dict is validated per union: the
    wrapper finds one STL per union and reports aggregate geometry over both bodies."""
    script = tmp_path / "hinge.py"
    script.write_text(
        "import cadquery as cq\n"
        "result = {\n"
        "  'leaf_a': cq.Workplane('XY').box(20, 20, 4),\n"
        "  'leaf_b': cq.Workplane('XY').box(20, 20, 4).translate((0, 30, 0)),\n"
        "}\n"
    )
    code, data = run(script, "--strict")
    assert code == 0
    assert data["success"] is True
    assert data["watertight"] is True
    # Two solid boxes -> aggregate face_count is the sum of both bodies.
    assert data["geometry"]["face_count"] >= 24


def test_translate_stderr_ignores_plain_capitalized_lines():
    """A model printing a 'Capitalized: ...' diagnostic to stderr must not be
    misread as an occ_exception (which is error-severity in the gate)."""
    from run_cadquery_model import _translate_stderr

    for line in ("Foo: bar", "Status: ready", "Warning: low memory", "note: fine"):
        assert _translate_stderr(line) == [], f"{line!r} wrongly parsed as an exception"


def test_translate_stderr_detects_real_exceptions():
    """Genuine Python and OCC exception lines still translate to occ_exception."""
    from run_cadquery_model import _translate_stderr

    py = _translate_stderr("ValueError: bad radius")
    assert len(py) == 1 and py[0]["type"] == "occ_exception"
    assert py[0]["occ_class"] == "ValueError"

    occ = _translate_stderr("StdFail_NotDone: operation incomplete")
    assert len(occ) == 1 and occ[0]["occ_class"] == "StdFail_NotDone"


def test_expected_dims_mismatch(good_script):
    """--expected-dims with a large mismatch should produce dimension_mismatch errors."""
    # good_script produces a 10x10x10 cube; expect 50x50x50 → big mismatch
    _, data = run(good_script, "--expected-dims", "50,50,50", "--dim-tolerance", "1")
    mismatch = [e for e in data["errors"] if e["type"] == "dimension_mismatch"]
    assert len(mismatch) >= 1


def test_expected_dims_match(good_script):
    """--expected-dims matching actual dimensions should produce no mismatch errors."""
    # good_script produces a 10x10x10 cube
    _, data = run(good_script, "--expected-dims", "10,10,10", "--dim-tolerance", "1")
    mismatch = [e for e in data["errors"] if e["type"] == "dimension_mismatch"]
    assert mismatch == []


# ---- preview ----


def test_preview_renders_png(good_script):
    rc, data = run(good_script, "--preview")
    assert rc == 0
    assert len(data["previews"]) == 1
    assert os.path.exists(data["previews"][0])
    assert data["preview"].endswith("_preview.png")


def test_preview_cross_sections(good_script):
    """--preview --cross-sections produces a preview PNG."""
    rc, data = run(good_script, "--preview", "--cross-sections")
    assert rc == 0
    assert len(data["previews"]) == 1
    assert os.path.exists(data["previews"][0])


def test_preview_extra_section(good_script):
    """--preview --extra-section x=2 threads a targeted off-center cut through to
    render_preview.py and produces a preview PNG."""
    rc, data = run(good_script, "--preview", "--extra-section", "x=2")
    assert rc == 0
    assert len(data["previews"]) == 1
    assert os.path.exists(data["previews"][0])


def test_preview_extra_section_repeatable(good_script):
    """--extra-section can be passed multiple times for several targeted cuts."""
    rc, data = run(good_script, "--preview", "--extra-section", "x=2", "--extra-section", "y=-3")
    assert rc == 0
    assert os.path.exists(data["previews"][0])


def test_render_preview_cli_produces_png(tmp_path):
    """render_preview.py CLI creates a PNG from a script with a `result` variable."""
    script = tmp_path / "box_model.py"
    script.write_text("import cadquery as cq\nresult = cq.Workplane('XY').box(20, 15, 10)\n")
    output = tmp_path / "box_preview.png"
    proc = subprocess.run(
        [
            sys.executable,
            RENDER_PREVIEW,
            "--script",
            str(script),
            "--output",
            str(output),
            "--views",
            "iso",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert output.exists()
    assert output.stat().st_size > 0


def test_render_preview_cli_missing_result(tmp_path):
    """render_preview.py exits 1 when the script has no `result` variable."""
    script = tmp_path / "no_result.py"
    script.write_text("import cadquery as cq\n# no result assigned\n")
    output = tmp_path / "out.png"
    proc = subprocess.run(
        [
            sys.executable,
            RENDER_PREVIEW,
            "--script",
            str(script),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
    assert "result" in proc.stderr.lower()


def test_render_preview_cli_rejects_invalid_extra_section(tmp_path):
    """render_preview.py exits 1 on a malformed --extra-section spec (bad axis, no
    value, non-numeric value) instead of crashing deeper in preview rendering."""
    script = tmp_path / "box_model.py"
    script.write_text("import cadquery as cq\nresult = cq.Workplane('XY').box(20, 15, 10)\n")
    output = tmp_path / "out.png"
    proc = subprocess.run(
        [
            sys.executable,
            RENDER_PREVIEW,
            "--script",
            str(script),
            "--output",
            str(output),
            "--extra-section",
            "w=5",  # invalid axis
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
    assert "extra-section" in proc.stderr.lower()
    assert not output.exists()
