"""Tests for the model-level export (placement, named 3MF, STL fallback).

Uses CadQuery to produce real part scripts, so these are integration-speed.
"""

import xml.etree.ElementTree as ET
import zipfile

import trimesh

from model_export import export_model

_NS = "{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}"


def _write_part(parts_dir, pid):
    (parts_dir / f"{pid}.py").write_text(
        "import cadquery as cq\nresult = cq.Workplane('XY').box(20, 20, 4)\n"
    )


def _plan(parts):
    return {
        "schema_version": 1,
        "intent": "model export fixture",
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


def _read_3mf_objects(path):
    with zipfile.ZipFile(path) as zf:
        root = ET.fromstring(zf.read("3D/3dmodel.model"))
    objects = {}
    for obj in root.iter(_NS + "object"):
        plate = next(
            (m.text for m in obj.iter(_NS + "metadata") if m.get("name") == "plate"),
            None,
        )
        objects[obj.get("name")] = plate
    return objects


def test_named_3mf_with_plate_and_placement(tmp_path):
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_part(parts_dir, "base")
    _write_part(parts_dir, "lid")
    out = tmp_path / "dist"
    plan = _plan(
        [
            {"id": "base", "description": "Enclosure base", "plate": "shared"},
            {
                "id": "lid",
                "description": "Hinged lid that snaps onto the base",
                "plate": "shared",
                "placement": {
                    "rotate": [{"axis": "X", "angle_deg": 90}],
                    "translate_mm": [0, 0, 30],
                },
            },
        ]
    )

    result = export_model(plan, str(parts_dir), str(out))

    # 3MF carries both unions as objects named from their descriptions, with plate
    # metadata.
    objects = _read_3mf_objects(result["model_3mf"])
    assert objects == {
        "Enclosure base": "shared",
        "Hinged lid that snaps onto the base": "shared",
    }

    # Placement was applied: the lid sits high in Z, the base near zero.
    scene = trimesh.load(result["model_3mf"])
    assert len(scene.geometry) == 2
    assert scene.bounds[1][2] > 25  # lid lifted by the placement


def test_deliverable_uses_print_orientation_union_stl_unchanged(tmp_path):
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_part(parts_dir, "plate")  # 20 x 20 x 4 box
    out = tmp_path / "dist"
    plan = _plan([{"id": "plate", "description": "flat plate"}])
    # Stand the plate up: rotate 90 deg about X so its 4 mm axis becomes the
    # width and the 20 mm axis points up.
    orientations = {"plate": {"rotate": [{"axis": "X", "angle_deg": 90}]}}

    result = export_model(plan, str(parts_dir), str(out), orientations)

    # The 3MF deliverable is written in the print orientation: ~20 mm tall now.
    scene = trimesh.load(result["model_3mf"])
    assert scene.extents[2] > 18

    # The per-union assembled-pose STL (kinematic-check input) is untouched: the
    # original 4 mm Z extent.
    union = trimesh.load(result["union_stls"]["plate"], force="mesh")
    assert abs(union.extents[2] - 4) < 0.1


def test_per_union_and_fused_plate_stl(tmp_path):
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_part(parts_dir, "base")
    _write_part(parts_dir, "lid")
    out = tmp_path / "dist"
    plan = _plan(
        [
            {"id": "base", "plate": "shared"},
            {"id": "lid", "plate": "shared", "placement": {"translate_mm": [0, 0, 30]}},
        ]
    )

    result = export_model(plan, str(parts_dir), str(out))

    # One assembled STL per union.
    assert set(result["union_stls"]) == {"base", "lid"}
    for path in result["union_stls"].values():
        assert trimesh.load(path, force="mesh").is_watertight

    # One fused STL for the co-plated plate.
    assert set(result["plate_stls"]) == {"shared"}
    fused = trimesh.load(result["plate_stls"]["shared"], force="mesh")
    assert fused.bounds[1][2] > 25  # spans both unions


def test_single_union_plate_has_no_fused_stl(tmp_path):
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_part(parts_dir, "solo")
    out = tmp_path / "dist"
    plan = _plan([{"id": "solo"}])  # own plate by default

    result = export_model(plan, str(parts_dir), str(out))

    assert set(result["union_stls"]) == {"solo"}
    assert result["plate_stls"] == {}  # no multi-union plate


def _write_holed_part(parts_dir, pid):
    """A box with a through-hole: curved faces produce many tessellation seams."""
    (parts_dir / f"{pid}.py").write_text(
        "import cadquery as cq\n"
        "result = cq.Workplane('XY').box(20, 20, 6).faces('>Z').workplane()"
        ".hole(8)\n"
    )


def test_named_3mf_has_no_nonmanifold_edges(tmp_path):
    from exporters.threemf_multi import count_nonmanifold_edges

    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_holed_part(parts_dir, "bracket")
    out = tmp_path / "dist"
    plan = _plan([{"id": "bracket"}])

    result = export_model(plan, str(parts_dir), str(out))

    # The slicer reads vertex indices verbatim; welding must close every seam.
    assert count_nonmanifold_edges(result["model_3mf"]) == 0


def test_object_name_sanitizes_hostile_and_oversized_description(tmp_path):
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_part(parts_dir, "widget")
    out = tmp_path / "dist"
    long_desc = "Mounting\tbracket\nwith\rcable routing " + "x" * 80
    plan = _plan([{"id": "widget", "description": long_desc}])

    result = export_model(plan, str(parts_dir), str(out))

    name = next(iter(_read_3mf_objects(result["model_3mf"])))
    assert "\n" not in name and "\r" not in name and "\t" not in name
    assert len(name) <= 64
    assert name.startswith("Mounting bracket with cable routing")
    # The 3MF still loads as valid geometry.
    assert len(trimesh.load(result["model_3mf"]).geometry) == 1


def test_object_name_falls_back_to_id_when_description_empty(tmp_path):
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_part(parts_dir, "spacer")
    out = tmp_path / "dist"
    # Description sanitizes to empty (only control/whitespace chars).
    plan = _plan([{"id": "spacer", "description": "\t\n  \r"}])

    result = export_model(plan, str(parts_dir), str(out))

    assert set(_read_3mf_objects(result["model_3mf"])) == {"spacer"}
