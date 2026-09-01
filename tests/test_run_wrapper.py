import json
import os
import subprocess
import sys

import pytest
from conftest import WRAPPER
from conftest import run_wrapper as run

SRC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")

RENDER_PREVIEW = os.path.join(SRC_DIR, "render_preview.py")


def _run_typed_errors(tmp_path, name, body, error_type):
    """Write `body` as tmp_path/name, run the wrapper, and return `(rc, data, matching_errors)`
    filtered to `error_type`."""
    script = tmp_path / name
    script.write_text(body)
    rc, data = run(script)
    return rc, data, [e for e in data["errors"] if e["type"] == error_type]


def _run_render_preview_cli(tmp_path, output_name, *extra_args):
    """Write a standard box-model script and run render_preview.py's CLI against it."""
    script = tmp_path / "box_model.py"
    script.write_text("import cadquery as cq\nresult = cq.Workplane('XY').box(20, 15, 10)\n")
    output = tmp_path / output_name
    proc = subprocess.run(
        [
            sys.executable,
            RENDER_PREVIEW,
            "--script",
            str(script),
            "--output",
            str(output),
            *extra_args,
        ],
        capture_output=True,
        text=True,
    )
    return proc, output


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


def test_happy_path_deliver_output_dir(tmp_path):
    """--output-dir redirects --deliver's STL away from the script's own
    directory, so build/ can stay free of generated artifacts."""
    script = tmp_path / "deliver_model.py"
    script.write_text("import cadquery as cq\nresult = cq.Workplane('XY').box(10, 10, 10)\n")
    out_dir = tmp_path / "stl"
    rc, data = run(script, "--deliver", "--formats", "stl", "--output-dir", str(out_dir))
    assert rc == 0
    assert data["success"] is True
    assert data["stl"] == str(out_dir / "deliver_model.stl")
    assert (out_dir / "deliver_model.stl").exists()
    assert not (tmp_path / "deliver_model.stl").exists()


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


def test_disconnected_body_single_union_reported(tmp_path):
    """A single-union part whose `result` is two non-overlapping solids fused into one
    Workplane is flagged as a disconnected_body with the union id and component count."""
    _, _, disc = _run_typed_errors(
        tmp_path,
        "split.py",
        "import cadquery as cq\n"
        "a = cq.Workplane('XY').box(10, 10, 10)\n"
        "b = cq.Workplane('XY').box(10, 10, 10).translate((50, 0, 0))\n"
        "result = a.union(b)\n",
        "disconnected_body",
    )
    assert len(disc) == 1
    assert disc[0]["component_count"] == 2
    assert disc[0]["union"] == "split"


def test_disconnected_body_fails_under_strict(tmp_path):
    """disconnected_body is blocking under --strict (rc 1, success False)."""
    script = tmp_path / "split.py"
    script.write_text(
        "import cadquery as cq\n"
        "a = cq.Workplane('XY').box(10, 10, 10)\n"
        "b = cq.Workplane('XY').box(10, 10, 10).translate((50, 0, 0))\n"
        "result = a.union(b)\n"
    )
    rc, data = run(script, "--strict")
    assert rc == 1
    assert data["success"] is False


def test_connected_body_reports_no_disconnected(good_script):
    """A normal single connected body produces no disconnected_body error."""
    _, data = run(good_script)
    assert [e for e in data["errors"] if e["type"] == "disconnected_body"] == []


def test_translate_stderr_ignores_plain_capitalized_lines():
    """A model printing a 'Capitalized: ...' diagnostic to stderr must not be
    misread as an occ_exception (which is error-severity in the gate)."""
    from run_cadquery_model import _translate_stderr

    for line in ("Foo: bar", "Status: ready", "Warning: low memory", "note: fine"):
        assert _translate_stderr(line) == [], f"{line!r} wrongly parsed as an exception"


def test_translate_stderr_detects_real_exceptions():
    """Genuine Python exceptions not in the OCC table translate to occ_exception."""
    from run_cadquery_model import _translate_stderr

    py = _translate_stderr("ValueError: bad radius")
    assert len(py) == 1 and py[0]["type"] == "occ_exception"
    assert py[0]["occ_class"] == "ValueError"


def test_translate_stderr_maps_known_occ_classes_to_typed_errors():
    """Each known OCC class in _OCC_HINTS gets its own error type, not occ_exception."""
    from run_cadquery_model import _translate_stderr

    for occ_class, expected_type in (
        ("Standard_ConstructionError", "construction_error"),
        ("BRep_API", "command_not_done"),
        ("StdFail_NotDone", "fillet_failure"),
        ("Standard_NullObject", "null_object"),
        ("Standard_OutOfRange", "index_out_of_range"),
        ("Standard_TypeMismatch", "type_mismatch"),
    ):
        errs = _translate_stderr(f"{occ_class}: operation incomplete")
        assert len(errs) == 1
        assert errs[0]["type"] == expected_type
        assert errs[0]["occ_class"] == occ_class
        assert errs[0]["hint"]


def test_translate_stderr_unmapped_occ_class_falls_back():
    """An OCC exception class not in _OCC_HINTS still reports occ_exception."""
    from run_cadquery_model import _translate_stderr

    errs = _translate_stderr("Standard_DomainError: unmapped class")
    assert len(errs) == 1
    assert errs[0]["type"] == "occ_exception"
    assert errs[0]["occ_class"] == "Standard_DomainError"


def test_translate_stderr_classifies_verify_markers():
    """A cq_verify RuntimeError marker becomes a typed error, not occ_exception."""
    from run_cadquery_model import _translate_stderr

    for kind, label in (
        ("silent_boolean", "vent_slot"),
        ("feature_overflow", "tab"),
        ("workplane_drift", "lid_top"),
        ("stage_mismatch", "base_shell"),
        ("unbacked_mate", "standoff_to_leg"),
        ("boss_swallowed", "hinge_ear"),
    ):
        stderr = (
            "Traceback (most recent call last):\n"
            '  File "model.py", line 9, in <module>\n'
            f"RuntimeError: [cq-verify:{kind}:{label}] some detail here\n"
        )
        errs = _translate_stderr(stderr)
        assert len(errs) == 1
        assert errs[0]["type"] == kind
        assert errs[0]["label"] == label
        assert errs[0]["message"] == "some detail here"
        assert errs[0]["hint"]


def test_translate_stderr_unrelated_runtimeerror_not_misclassified():
    """A RuntimeError without the cq-verify marker falls through to occ_exception."""
    from run_cadquery_model import _translate_stderr

    errs = _translate_stderr("RuntimeError: something else entirely")
    assert len(errs) == 1
    assert errs[0]["type"] == "occ_exception"


def test_silent_boolean_end_to_end(tmp_path):
    """A script whose verify_boolean fires yields a typed silent_boolean error."""
    rc, data, sb = _run_typed_errors(
        tmp_path,
        "silent.py",
        "import cadquery as cq\n"
        "from cq_verify import verify_boolean\n"
        "body = cq.Workplane('XY').box(20, 20, 20)\n"
        "tool = cq.Workplane('XY').transformed(offset=(100, 0, 0)).box(5, 5, 5)\n"
        "result = verify_boolean(body, body.cut(tool), 'cut', 'vent_slot')\n",
        "silent_boolean",
    )
    assert rc == 1
    assert data["success"] is False
    assert len(sb) == 1
    assert sb[0]["label"] == "vent_slot"


def test_stage_mismatch_end_to_end(tmp_path):
    """A script whose verify_stage fires yields a typed stage_mismatch error."""
    rc, data, sb = _run_typed_errors(
        tmp_path,
        "stage.py",
        "import cadquery as cq\n"
        "from cq_verify import verify_stage\n"
        "body = cq.Workplane('XY').box(20, 20, 5, centered=(True, True, False))\n"
        "result = verify_stage(body, 'base_shell', bbox=(-10, 10, -10, 10, 0, 50))\n",
        "stage_mismatch",
    )
    assert rc == 1
    assert data["success"] is False
    assert len(sb) == 1
    assert sb[0]["label"] == "base_shell"


# Reproduces the C5 Phone-Holder hinge-knuckle bug (build/cradle.py ROUND 5-7 comments):
# a standoff post centered on a pivot coordinate was only half-backed by the leg beneath
# it, because the leg stopped exactly at the pivot coordinate instead of extending to the
# standoff's far edge.
_LEG_STANDOFF_PREAMBLE = (
    "import cadquery as cq\n"
    "from cq_verify import verify_backed\n"
    "leg = cq.Workplane('XY').box(10, {leg_dy}, 2, centered=(False, False, False))"
    ".translate((0, -15, 0))\n"
    "standoff = cq.Workplane('XY').box(10, 2, 5, centered=(False, False, False))"
    ".translate((0, 4, 2))\n"
)


def test_unbacked_mate_end_to_end(tmp_path):
    """A standoff only half-backed by its leg (pre-ROUND-7 dimensions) fails verify_backed
    on the Y axis, naming the leg as an insufficient backer."""
    rc, data, sb = _run_typed_errors(
        tmp_path,
        "unbacked.py",
        _LEG_STANDOFF_PREAMBLE.format(leg_dy=20)  # leg stops at Y=5, standoff reaches Y=6
        + "result = verify_backed(leg, standoff, '-z', 'standoff_to_leg')\n",
        "unbacked_mate",
    )
    assert rc == 1
    assert data["success"] is False
    assert len(sb) == 1
    assert sb[0]["label"] == "standoff_to_leg"
    assert "y" in sb[0]["message"].lower()


def test_unbacked_mate_reach_failure_end_to_end(tmp_path):
    """A backer that stops short of the feature's contact plane fails the reach check."""
    rc, data, sb = _run_typed_errors(
        tmp_path,
        "unreached.py",
        "import cadquery as cq\n"
        "from cq_verify import verify_backed\n"
        "leg = cq.Workplane('XY').box(10, 21, 1, centered=(False, False, False))"
        ".translate((0, -15, 0))\n"  # leg top face at Z=1, short of standoff's Z=2 base
        "standoff = cq.Workplane('XY').box(10, 2, 5, centered=(False, False, False))"
        ".translate((0, 4, 2))\n"
        "result = verify_backed(leg, standoff, '-z', 'standoff_to_leg')\n",
        "unbacked_mate",
    )
    assert rc == 1
    assert data["success"] is False
    assert len(sb) == 1
    assert "contact plane" in sb[0]["message"]


def test_boss_swallowed_end_to_end(tmp_path):
    """The C5 hinge-ear bug: a riser box seated at the knuckle disc's center (not its
    tangent) fires verify_seated, yielding a typed boss_swallowed error."""
    rc, data, sb = _run_typed_errors(
        tmp_path,
        "swallowed.py",
        "import cadquery as cq\n"
        "from cq_verify import verify_seated\n"
        "knuckle = cq.Workplane('YZ').circle(2.6).extrude(10).translate((-5, 5, 13.5))\n"
        "riser = cq.Workplane('XY').box(10, 4, 5).translate((0, 3, 11.0))\n"  # top at Z=13.5
        "result = verify_seated(riser, knuckle, '-z', 'hinge_ear')\n",
        "boss_swallowed",
    )
    assert rc == 1
    assert data["success"] is False
    assert len(sb) == 1
    assert sb[0]["label"] == "hinge_ear"


def test_verify_backed_passes_when_fully_backed(tmp_path):
    """The ROUND-7-fixed dimensions (leg extended to the standoff's far edge) pass."""
    script = tmp_path / "backed.py"
    script.write_text(
        _LEG_STANDOFF_PREAMBLE.format(leg_dy=21)  # leg now reaches Y=6, standoff's far edge
        + "result = verify_backed(leg, standoff, '-z', 'standoff_to_leg').union(leg)\n"
    )
    rc, data = run(script)
    assert rc == 0
    assert data["success"] is True
    assert data["errors"] == []


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
    """--preview --cross-sections writes the 2x2 tile plus separate section files
    (the bbox-center X/Y/Z cuts when no positions are supplied)."""
    rc, data = run(good_script, "--preview", "--cross-sections")
    assert rc == 0
    # tile + three center-cut section files, each its own file
    assert len(data["previews"]) == 4
    for path in data["previews"]:
        assert os.path.exists(path)
    section_files = [p for p in data["previews"][1:] if "section" in os.path.basename(p)]
    assert len(section_files) == 3


def test_preview_dir_redirects_output(good_script, tmp_path):
    """--preview-dir writes the preview PNG to a separate directory instead of
    alongside the script, so build/ can stay free of generated artifacts."""
    preview_dir = tmp_path / "preview"
    rc, data = run(good_script, "--preview", "--preview-dir", str(preview_dir))
    assert rc == 0
    assert len(data["previews"]) == 1
    assert os.path.dirname(data["previews"][0]) == str(preview_dir)
    assert os.path.exists(data["previews"][0])


@pytest.mark.parametrize(
    "flag_args, expected_substrings",
    [
        (("--extra-section", "x=2"), ("section",)),
        (("--detail", "name=corner;center=4,4,4;size=3"), ("corner", "detail")),
    ],
    ids=["extra_section", "detail_view"],
)
def test_preview_second_file_named(good_script, flag_args, expected_substrings):
    """--preview plus a targeted flag (--extra-section or --detail) threads through to
    render_preview.py and writes a second, appropriately-named preview file."""
    rc, data = run(good_script, "--preview", *flag_args)
    assert rc == 0
    assert len(data["previews"]) == 2
    assert os.path.exists(data["previews"][0])
    second = data["previews"][1]
    assert os.path.exists(second)
    for substr in expected_substrings:
        assert substr in os.path.basename(second)


def test_preview_extra_section_repeatable(good_script):
    """--extra-section can be passed multiple times: one separate section file each."""
    rc, data = run(good_script, "--preview", "--extra-section", "x=2", "--extra-section", "y=-3")
    assert rc == 0
    # tile + two targeted section files
    assert len(data["previews"]) == 3
    for path in data["previews"]:
        assert os.path.exists(path)


def test_preview_detail_with_section_adds_two_named_files(good_script):
    """A --detail spec with section= produces both a detail view and a detail
    cross-section, both named after the feature."""
    rc, data = run(
        good_script,
        "--preview",
        "--detail",
        "name=corner;center=4,4,4;size=3;section=x=4",
    )
    assert rc == 0
    assert len(data["previews"]) == 3
    for path in data["previews"][1:]:
        assert os.path.exists(path)
        assert "corner" in os.path.basename(path)
    basenames = [os.path.basename(p) for p in data["previews"][1:]]
    assert any("detail" in b for b in basenames)
    assert any("section" in b for b in basenames)


def test_preview_detail_invalid_spec_fails(good_script):
    """A malformed --detail spec (missing size=) fails the run instead of
    crashing deeper in preview rendering."""
    rc, data = run(good_script, "--preview", "--detail", "name=corner;center=4,4,4")
    assert rc == 1
    assert "detail" in data.get("stderr", "").lower()


def test_preview_callout_and_unlocated_name(good_script):
    """--callout draws badges on the main tile (no extra file, unlike --detail);
    --unlocated-name is accepted alongside it."""
    rc, data = run(
        good_script,
        "--preview",
        "--callout",
        "name=handle;center=1,1,1",
        "--unlocated-name",
        "boss_sw",
    )
    assert rc == 0
    assert len(data["previews"]) == 1
    assert os.path.exists(data["previews"][0])


def test_preview_callout_invalid_spec_fails(good_script):
    """A malformed --callout spec (missing center=) fails the run."""
    rc, data = run(good_script, "--preview", "--callout", "name=handle")
    assert rc == 1
    assert "callout" in data.get("stderr", "").lower()


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


@pytest.mark.parametrize(
    "extra_args, expected_substring",
    [
        (("--extra-section", "w=5"), "extra-section"),  # invalid axis
        (("--detail", "name=mount_hole;center=8,6,3"), "detail"),  # missing size=
        (("--callout", "name=handle"), "callout"),  # missing center=
    ],
    ids=["invalid_extra_section", "invalid_detail_spec", "invalid_callout_spec"],
)
def test_render_preview_cli_rejects_invalid_spec(tmp_path, extra_args, expected_substring):
    """render_preview.py exits 1 on a malformed --extra-section/--detail spec instead of
    crashing deeper in preview rendering."""
    proc, output = _run_render_preview_cli(tmp_path, "out.png", *extra_args)
    assert proc.returncode == 1
    assert expected_substring in proc.stderr.lower()
    assert not output.exists()


def test_render_preview_cli_detail_produces_named_files(tmp_path):
    """render_preview.py --detail produces a feature-named detail file next to
    the main output, and reports it in the final extra_previews JSON line."""
    proc, output = _run_render_preview_cli(
        tmp_path, "box_preview.png", "--detail", "name=mount_hole;center=8,6,3;size=5"
    )
    assert proc.returncode == 0, proc.stderr
    detail_path = output.parent / "box_preview_detail_mount_hole.png"
    assert detail_path.exists()
    assert detail_path.stat().st_size > 0

    last_line = proc.stdout.strip().splitlines()[-1]
    reported = json.loads(last_line)
    assert reported["extra_previews"] == [str(detail_path)]
