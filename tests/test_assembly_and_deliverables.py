# mypy: ignore-errors
# type: ignore  # CAD/trimesh stub-union noise; tests are ruff-linted, not type-checked
"""Tests for write_assembly (assembled-pose STLs, manifest, keep-out STLs) and
deliverables (named 3MF, STL + fused plates, extra formats).

Uses CadQuery to produce real part scripts, so these are integration-speed.
"""

import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest
import trimesh
from conftest import minimal_plan as _plan

from deliverables import write_deliverables
from write_assembly import write_assembly

_NS = "{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}"


def _export(plan, parts_dir, out, orientations=None, formats=("3mf", "stl")):
    """Run write_assembly and write_deliverables into one directory; merge the results."""
    asm = write_assembly(plan, parts_dir, str(out), orientations)
    files = write_deliverables(
        plan, parts_dir, str(Path(out) / "deliver"), orientations or {}, list(formats)
    )["files"]
    return {
        **asm,
        "model_3mf": files.get("3mf", {}).get("model.3mf"),
        "plate_stls": {
            k.removeprefix("plate_"): v
            for k, v in files.get("stl", {}).items()
            if k.startswith("plate_")
        },
        "files": files,
    }


def _write_part(parts_dir, pid):
    (parts_dir / f"{pid}.py").write_text(
        "import cadquery as cq\nresult = cq.Workplane('XY').box(20, 20, 4)\n"
    )


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


def _read_3mf_object_ids_by_name(path):
    with zipfile.ZipFile(path) as zf:
        root = ET.fromstring(zf.read("3D/3dmodel.model"))
    return {obj.get("name"): obj.get("id") for obj in root.iter(_NS + "object")}


def _read_model_settings_plates(path):
    with zipfile.ZipFile(path) as zf:
        root = ET.fromstring(zf.read("Metadata/model_settings.config"))
    plates = []
    for plate in root.findall("plate"):
        meta = {m.get("key"): m.get("value") for m in plate.findall("metadata")}
        object_ids = [
            next(m.get("value") for m in inst.findall("metadata") if m.get("key") == "object_id")
            for inst in plate.findall("model_instance")
        ]
        plates.append(
            {
                "plater_id": meta.get("plater_id"),
                "plater_name": meta.get("plater_name"),
                "object_ids": object_ids,
            }
        )
    return plates


def test_model_settings_config_assigns_distinct_plates(tmp_path):
    """Bambu/OrcaSlicer plate metadata: each default (own-plate) union gets its
    own <plate>, so the slicer auto-distributes objects instead of stacking them
    all on plate 1 -- the quartered-parts scenario this exists for."""
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_part(parts_dir, "quad_a")
    _write_part(parts_dir, "quad_b")
    out = tmp_path / "dist"
    plan = _plan(
        [
            {"id": "quad_a", "description": "Quadrant A"},
            {"id": "quad_b", "description": "Quadrant B"},
        ]
    )

    result = _export(plan, str(parts_dir), str(out))

    ids_by_name = _read_3mf_object_ids_by_name(result["model_3mf"])
    plates = _read_model_settings_plates(result["model_3mf"])
    assert len(plates) == 2
    assert {p["plater_id"] for p in plates} == {"1", "2"}
    by_plater_id = {p["plater_id"]: p for p in plates}
    assert by_plater_id["1"]["object_ids"] == [ids_by_name["Quadrant A"]]
    assert by_plater_id["2"]["object_ids"] == [ids_by_name["Quadrant B"]]


def test_model_settings_config_groups_co_plated_unions(tmp_path):
    """Unions that share a `plate` id (print-in-place) land in one <plate> block
    as multiple <model_instance> entries, not split across plates."""
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_part(parts_dir, "base")
    _write_part(parts_dir, "lid")
    out = tmp_path / "dist"
    plan = _plan(
        [
            {"id": "base", "description": "Enclosure base", "plate": "shared"},
            {"id": "lid", "description": "Snap lid", "plate": "shared"},
        ]
    )

    result = _export(plan, str(parts_dir), str(out))

    plates = _read_model_settings_plates(result["model_3mf"])
    assert len(plates) == 1
    assert plates[0]["plater_id"] == "1"
    assert len(plates[0]["object_ids"]) == 2


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

    result = _export(plan, str(parts_dir), str(out))

    # 3MF carries both unions as objects named from their descriptions, with plate
    # metadata.
    objects = _read_3mf_objects(result["model_3mf"])
    assert objects == {
        "Enclosure base": "shared",
        "Hinged lid that snaps onto the base": "shared",
    }

    # Deliverables are print pose (build pose here: no orientation), so the placement
    # does not move the lid.
    scene = trimesh.load(result["model_3mf"])
    assert len(scene.geometry) == 2
    assert scene.bounds[1][2] < 10


def test_object_group_is_one_3mf_object_with_extruders(tmp_path):
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    (parts_dir / "knob.py").write_text(
        "import cadquery as cq\n"
        "result = {\n"
        "    'body': cq.Workplane('XY').box(20, 20, 4),\n"
        "    'ring': cq.Workplane('XY').box(20, 20, 2).translate((0, 0, 3)),\n"
        "}\n"
    )
    plan = _plan(
        [
            {
                "id": "knob",
                "description": "Two-color knob",
                "unions": [
                    {"id": "body", "object": "knob_obj", "filament": 1},
                    {"id": "ring", "object": "knob_obj", "filament": 2},
                ],
            }
        ]
    )

    result = _export(plan, str(parts_dir), str(tmp_path / "dist"))

    assert _read_3mf_objects(result["model_3mf"]) == {"Two-color knob": "knob_obj"}
    with zipfile.ZipFile(result["model_3mf"]) as zf:
        config = ET.fromstring(zf.read("Metadata/model_settings.config"))
    (obj,) = config.findall("object")
    parts = {
        meta["name"]: meta["extruder"]
        for meta in (
            {m.get("key"): m.get("value") for m in p.findall("metadata")}
            for p in obj.findall("part")
        )
    }
    assert parts == {"body": "1", "ring": "2"}
    assert set(result["files"]["stl"]) == {"body", "ring", "plate_knob_obj"}


def test_write_assembly_writes_only_assembly_files(tmp_path):
    import os

    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_part(parts_dir, "base")
    _write_part(parts_dir, "lid")
    out = tmp_path / "stl"
    plan = _plan([{"id": "base", "plate": "shared"}, {"id": "lid", "plate": "shared"}])

    result = write_assembly(plan, str(parts_dir), str(out))

    assert sorted(os.listdir(out)) == ["base.stl", "export_manifest.json", "lid.stl"]
    assert set(result) == {"union_stls", "keep_out_stls", "manifest", "pose_findings"}


def test_deliverables_write_only_requested_formats(tmp_path):
    import os

    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_part(parts_dir, "base")
    plan = _plan([{"id": "base"}])

    only_3mf = tmp_path / "a"
    write_deliverables(plan, str(parts_dir), str(only_3mf), {}, ["3mf"])
    assert os.listdir(only_3mf) == ["model.3mf"]

    only_stl = tmp_path / "b"
    write_deliverables(plan, str(parts_dir), str(only_stl), {}, ["stl"])
    assert os.listdir(only_stl) == ["base.stl"]

    with pytest.raises(ValueError, match="dxf"):
        write_deliverables(plan, str(parts_dir), str(tmp_path / "c"), {}, ["dxf"])
    assert not (tmp_path / "c").exists()


def test_deliverable_stl_is_print_pose_not_assembly_pose(tmp_path):
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_part(parts_dir, "base")  # 20 x 20 x 4 box
    plan = _plan([{"id": "base"}])
    orientations = {"base": {"rotate": [{"axis": "X", "angle_deg": 90}]}}
    asm_dir = tmp_path / "stl"
    write_assembly(plan, str(parts_dir), str(asm_dir), orientations)
    asm_bytes = (asm_dir / "base.stl").read_bytes()

    result = write_deliverables(plan, str(parts_dir), str(tmp_path / "out"), orientations, ["stl"])

    assert "union_stls_copied" not in result
    assert trimesh.load(str(tmp_path / "out" / "base.stl")).extents[2] == pytest.approx(20, abs=0.1)
    assert (asm_dir / "base.stl").read_bytes() == asm_bytes  # check meshes untouched
    assert trimesh.load(str(asm_dir / "base.stl")).extents[2] == pytest.approx(4, abs=0.1)


def test_extra_formats_are_print_pose_and_fall_back_to_build_pose(tmp_path):
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_part(parts_dir, "base")  # 20 x 20 x 4 box
    plan = _plan([{"id": "base", "placement": {"translate_mm": [0, 0, 50]}}])
    rotated = {"base": {"rotate": [{"axis": "X", "angle_deg": 90}]}}

    with_rot = write_deliverables(plan, str(parts_dir), str(tmp_path / "a"), rotated, ["obj"])
    mesh = trimesh.load(with_rot["files"]["obj"]["base"], force="mesh")
    assert mesh.extents[2] == pytest.approx(20, abs=0.1)

    # No orientation: build pose (the placement's z=50 shift is not applied).
    no_rot = write_deliverables(plan, str(parts_dir), str(tmp_path / "b"), {}, ["obj", "stl"])
    for path in (no_rot["files"]["obj"]["base"], no_rot["files"]["stl"]["base"]):
        mesh = trimesh.load(path, force="mesh")
        assert mesh.bounds[1][2] < 10


def test_deliverable_uses_print_orientation_union_stl_unchanged(tmp_path):
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_part(parts_dir, "plate")  # 20 x 20 x 4 box
    out = tmp_path / "dist"
    plan = _plan([{"id": "plate", "description": "flat plate"}])
    # Stand the plate up: rotate 90 deg about X so its 4 mm axis becomes the
    # width and the 20 mm axis points up.
    orientations = {"plate": {"rotate": [{"axis": "X", "angle_deg": 90}]}}

    result = _export(plan, str(parts_dir), str(out), orientations)

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

    result = _export(plan, str(parts_dir), str(out))

    # One assembled STL per union.
    assert set(result["union_stls"]) == {"base", "lid"}
    for path in result["union_stls"].values():
        assert trimesh.load(path, force="mesh").is_watertight

    # One fused STL for the co-plated plate.
    assert set(result["plate_stls"]) == {"shared"}
    fused = trimesh.load(result["plate_stls"]["shared"], force="mesh")
    assert fused.bounds[1][2] > 25  # spans both unions


def test_export_writes_provenance_manifest(tmp_path):
    from freshness import read_manifest, script_hash

    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_part(parts_dir, "base")
    _write_part(parts_dir, "lid")
    out = tmp_path / "dist"
    plan = _plan([{"id": "base"}, {"id": "lid"}])

    result = _export(plan, str(parts_dir), str(out))

    manifest = read_manifest(str(out))
    assert manifest is not None
    assert result["manifest"].endswith("export_manifest.json")
    assert manifest["unions"]["base"]["part_id"] == "base"
    assert manifest["unions"]["base"]["source_script_hash"] == script_hash(
        str(parts_dir / "base.py")
    )
    assert manifest["unions"]["lid"]["source_script_hash"] == script_hash(str(parts_dir / "lid.py"))
    assert "exported_at" in manifest


def test_export_manifest_covers_keep_out_zones(tmp_path):
    from freshness import read_manifest, script_hash

    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_part_with_zone(parts_dir, "enclosure")
    out = tmp_path / "dist"
    plan = _plan([{"id": "enclosure", "description": "Enclosure"}])

    _export(plan, str(parts_dir), str(out))

    manifest = read_manifest(str(out))
    entry = manifest["keep_out_zones"]["enclosure::clearance"]
    assert entry["part_id"] == "enclosure"
    assert entry["source_script_hash"] == script_hash(str(parts_dir / "enclosure.py"))


def test_single_union_plate_has_no_fused_stl(tmp_path):
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_part(parts_dir, "solo")
    out = tmp_path / "dist"
    plan = _plan([{"id": "solo"}])  # own plate by default

    result = _export(plan, str(parts_dir), str(out))

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

    result = _export(plan, str(parts_dir), str(out))

    # The slicer reads vertex indices verbatim; welding must close every seam.
    assert count_nonmanifold_edges(result["model_3mf"]) == 0


def test_object_name_sanitizes_hostile_and_oversized_description(tmp_path):
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_part(parts_dir, "widget")
    out = tmp_path / "dist"
    long_desc = "Mounting\tbracket\nwith\rcable routing " + "x" * 80
    plan = _plan([{"id": "widget", "description": long_desc}])

    result = _export(plan, str(parts_dir), str(out))

    name = next(iter(_read_3mf_objects(result["model_3mf"])))
    assert "\n" not in name and "\r" not in name and "\t" not in name
    assert len(name) <= 64
    assert name.startswith("Mounting bracket with cable routing")
    # The 3MF still loads as valid geometry.
    assert len(trimesh.load(result["model_3mf"]).geometry) == 1


def test_block_importing_part_with_rotation_exports_without_bintools_error(tmp_path):
    """Regression: a part that imports blocks (activating the cq_warehouse Shape
    patch) and carries a non-identity print orientation must export through
    apply_cq without a BinTools deepcopy round-trip / BRep_PointRepresentation error.
    """
    import pytest

    pytest.importorskip("cq_warehouse", reason="cq_warehouse not installed")

    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    # Importing blocks.hardware + building a heat-set boss installs the global
    # Shape patch in this process, the condition that previously broke the
    # oriented export.
    (parts_dir / "boss.py").write_text(
        "import cadquery as cq\n"
        "from blocks.hardware import heat_set_boss\n"
        "result = cq.Workplane('XY').box(20, 20, 6).union(\n"
        "    heat_set_boss('M3-0.5-6', d_outer=7, h=6)\n"
        ")\n"
    )
    out = tmp_path / "dist"
    plan = _plan([{"id": "boss", "description": "boss plate"}])
    # Non-identity print orientation: stand the part up.
    orientations = {"boss": {"rotate": [{"axis": "X", "angle_deg": 90}]}}

    result = _export(plan, str(parts_dir), str(out), orientations)

    # 3MF written in the print orientation, and all STLs produced + watertight.
    scene = trimesh.load(result["model_3mf"])
    assert len(scene.geometry) == 1
    union = trimesh.load(result["union_stls"]["boss"], force="mesh")
    assert union.is_watertight


def test_object_name_falls_back_to_id_when_description_empty(tmp_path):
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_part(parts_dir, "spacer")
    out = tmp_path / "dist"
    # Description sanitizes to empty (only control/whitespace chars).
    plan = _plan([{"id": "spacer", "description": "\t\n  \r"}])

    result = _export(plan, str(parts_dir), str(out))

    assert set(_read_3mf_objects(result["model_3mf"])) == {"spacer"}


def test_duplicate_descriptions_are_disambiguated_by_part_id(tmp_path):
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_part(parts_dir, "left_leaf")
    _write_part(parts_dir, "right_leaf")
    out = tmp_path / "dist"
    plan = _plan(
        [
            {"id": "left_leaf", "description": "Hinge leaf"},
            {"id": "right_leaf", "description": "Hinge leaf"},
        ]
    )

    result = _export(plan, str(parts_dir), str(out))

    names = set(_read_3mf_objects(result["model_3mf"]))
    # Two distinct names, each the shared description suffixed with its part id.
    assert names == {"Hinge leaf (left_leaf)", "Hinge leaf (right_leaf)"}


def _write_multi_union_part(parts_dir, pid, uid_a, uid_b, sep_y=30):
    (parts_dir / f"{pid}.py").write_text(
        "import cadquery as cq\n"
        "result = {\n"
        f"  {uid_a!r}: cq.Workplane('XY').box(20, 20, 4),\n"
        f"  {uid_b!r}: cq.Workplane('XY').box(20, 20, 4).translate((0, {sep_y}, 0)),\n"
        "}\n"
    )


def test_multi_union_part_exports_object_and_stl_per_union(tmp_path):
    """One part declaring two unions exports two named 3MF objects + two STLs, one per union,
    on the two plates declared per union."""
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_multi_union_part(parts_dir, "hinge", "leaf_a", "leaf_b")
    out = tmp_path / "dist"
    plan = _plan(
        [
            {
                "id": "hinge",
                "description": "Hinge",
                "unions": [{"id": "leaf_a", "plate": "p1"}, {"id": "leaf_b", "plate": "p2"}],
            }
        ]
    )

    result = _export(plan, str(parts_dir), str(out))

    # Two distinct unions, keyed by union id (not part id).
    assert set(result["union_stls"]) == {"leaf_a", "leaf_b"}
    for path in result["union_stls"].values():
        assert trimesh.load(path, force="mesh").is_watertight
    # Two named 3MF objects, deduped by union id since they share the part description.
    objects = _read_3mf_objects(result["model_3mf"])
    assert set(objects) == {"Hinge (leaf_a)", "Hinge (leaf_b)"}
    assert objects == {"Hinge (leaf_a)": "p1", "Hinge (leaf_b)": "p2"}
    # Each union on its own plate -> no fused multi-union plate STL.
    assert result["plate_stls"] == {}


def test_multi_union_part_co_plated_produces_fused_plate(tmp_path):
    """Two unions of one part sharing a plate fuse into one plate STL (print-in-place)."""
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_multi_union_part(parts_dir, "hinge", "leaf_a", "leaf_b")
    out = tmp_path / "dist"
    plan = _plan(
        [
            {
                "id": "hinge",
                "description": "Hinge",
                "unions": [
                    {"id": "leaf_a", "plate": "shared"},
                    {"id": "leaf_b", "plate": "shared"},
                ],
            }
        ]
    )

    result = _export(plan, str(parts_dir), str(out))

    assert set(result["union_stls"]) == {"leaf_a", "leaf_b"}
    assert set(result["plate_stls"]) == {"shared"}


def test_multi_union_result_key_mismatch_errors(tmp_path):
    """A part declaring `unions` whose script result keys differ is a structured error."""
    import pytest

    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_multi_union_part(parts_dir, "hinge", "leaf_a", "WRONG")
    out = tmp_path / "dist"
    plan = _plan(
        [{"id": "hinge", "description": "Hinge", "unions": [{"id": "leaf_a"}, {"id": "leaf_b"}]}]
    )

    with pytest.raises(ValueError, match="do not match declared unions"):
        _export(plan, str(parts_dir), str(out))


def test_single_union_part_unchanged(tmp_path):
    """Backward compat: a plain-Workplane part is one union keyed by the part id."""
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_part(parts_dir, "solo")
    out = tmp_path / "dist"
    plan = _plan([{"id": "solo", "description": "Solo"}])

    result = _export(plan, str(parts_dir), str(out))

    assert set(result["union_stls"]) == {"solo"}
    assert set(_read_3mf_objects(result["model_3mf"])) == {"Solo"}


def test_distinct_descriptions_keep_plain_names(tmp_path):
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_part(parts_dir, "base")
    _write_part(parts_dir, "lid")
    out = tmp_path / "dist"
    plan = _plan(
        [
            {"id": "base", "description": "Enclosure base"},
            {"id": "lid", "description": "Snap lid"},
        ]
    )

    result = _export(plan, str(parts_dir), str(out))

    # No collision -> no id suffix appended.
    assert set(_read_3mf_objects(result["model_3mf"])) == {"Enclosure base", "Snap lid"}


# ---- joint-mate-entity: derived pose replaces placement ----


def _hinge_joint(wall_dock=None):
    """A single revolute door/wall `pin_hinge` `joints` entry: the mate-chain fixture
    shared by the mate-chain and keep-out-zone-inheritance tests below."""
    leaf_b = {"member": "leaf_b", "part": "wall"}
    if wall_dock is not None:
        leaf_b["dock"] = wall_dock
    return [
        {
            "joint_id": "hinge1",
            "block": "pin_hinge",
            "params": {},
            "members": [{"member": "leaf_a", "part": "door"}, leaf_b],
        }
    ]


def test_mate_chain_part_pose_replaces_placement(tmp_path):
    """A part reached via a `joints` mate chain is positioned by its derived pose,
    not by (absent) `placement`."""
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_part(parts_dir, "door")  # 20x20x4 box centered at origin (z in [-2, 2])
    _write_part(parts_dir, "wall")
    out = tmp_path / "dist"
    plan = _plan(
        [
            {"id": "door", "description": "Door leaf"},
            {"id": "wall", "description": "Wall leaf"},
        ]
    )
    plan["root_part"] = "door"
    plan["joints"] = _hinge_joint(wall_dock={"translate_mm": [0, 0, 10]})

    result = _export(plan, str(parts_dir), str(out))

    # wall's dock offsets leaf_b by +10mm in Z within wall's own frame, so wall's
    # derived world pose is -10mm in Z: its box (authored at z in [-2, 2]) lands
    # at z in [-12, -8].
    wall_stl = trimesh.load(result["union_stls"]["wall"], force="mesh")
    assert abs(wall_stl.bounds[0][2] - (-12)) < 0.01
    assert abs(wall_stl.bounds[1][2] - (-8)) < 0.01

    # door (root, identity placement) is unaffected.
    door_stl = trimesh.load(result["union_stls"]["door"], force="mesh")
    assert abs(door_stl.bounds[0][2] - (-2)) < 0.01
    assert abs(door_stl.bounds[1][2] - 2) < 0.01


# ---- keep-out-zones: reserved key excluded from export/plate/union-STL --------


def _write_part_with_zone(parts_dir, pid, zone_name="clearance"):
    (parts_dir / f"{pid}.py").write_text(
        "import cadquery as cq\n"
        "result = {\n"
        f"  {pid!r}: cq.Workplane('XY').box(20, 20, 4),\n"
        "  'keep_out': {\n"
        f"    {zone_name!r}: cq.Workplane('XY').box(5, 5, 5),\n"
        "  },\n"
        "}\n"
    )


def test_keep_out_zone_excluded_from_3mf_plate_and_union_stl(tmp_path):
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_part_with_zone(parts_dir, "enclosure")
    out = tmp_path / "dist"
    plan = _plan([{"id": "enclosure", "description": "Enclosure"}])

    result = _export(plan, str(parts_dir), str(out))

    assert set(result["union_stls"]) == {"enclosure"}
    assert result["plate_stls"] == {}
    assert set(_read_3mf_objects(result["model_3mf"])) == {"Enclosure"}
    assert set(result["keep_out_stls"]) == {"enclosure::clearance"}
    zone_mesh = trimesh.load(result["keep_out_stls"]["enclosure::clearance"], force="mesh")
    assert zone_mesh.is_watertight


def test_keep_out_zone_inherits_part_placement(tmp_path):
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_part_with_zone(parts_dir, "enclosure")
    out = tmp_path / "dist"
    plan = _plan(
        [
            {
                "id": "enclosure",
                "description": "Enclosure",
                "placement": {"translate_mm": [0, 0, 50]},
            }
        ]
    )

    result = _export(plan, str(parts_dir), str(out))

    # zone box is 5x5x5 authored at the origin; the part's placement shifts it +50 in Z.
    zone_mesh = trimesh.load(result["keep_out_stls"]["enclosure::clearance"], force="mesh")
    assert abs(zone_mesh.bounds[0][2] - 47.5) < 0.01
    assert abs(zone_mesh.bounds[1][2] - 52.5) < 0.01


def test_keep_out_zone_inherits_mate_chain_pose(tmp_path):
    """A zone declared by a part reached via a `joints` mate chain uses that part's
    derived pose, exactly like the part's own real union does."""
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_part(parts_dir, "door")
    _write_part_with_zone(parts_dir, "wall")
    out = tmp_path / "dist"
    plan = _plan(
        [
            {"id": "door", "description": "Door leaf"},
            {"id": "wall", "description": "Wall leaf"},
        ]
    )
    plan["root_part"] = "door"
    plan["joints"] = _hinge_joint(wall_dock={"translate_mm": [0, 0, 10]})

    result = _export(plan, str(parts_dir), str(out))

    # wall's derived pose is -10mm in Z (see test_mate_chain_part_pose_replaces_placement);
    # the zone (5x5x5 box authored at the origin in wall's own frame) follows the same pose.
    zone_mesh = trimesh.load(result["keep_out_stls"]["wall::clearance"], force="mesh")
    assert abs(zone_mesh.bounds[0][2] - (-12.5)) < 0.01
    assert abs(zone_mesh.bounds[1][2] - (-7.5)) < 0.01


def test_part_outside_mate_chain_still_uses_own_placement(tmp_path):
    """A part not named in any `joints` entry is unaffected by the mate chain."""
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_part(parts_dir, "door")
    _write_part(parts_dir, "wall")
    _write_part(parts_dir, "standalone")
    out = tmp_path / "dist"
    plan = _plan(
        [
            {"id": "door", "description": "Door leaf"},
            {"id": "wall", "description": "Wall leaf"},
            {
                "id": "standalone",
                "description": "Standalone part",
                "placement": {"translate_mm": [0, 0, 30]},
            },
        ]
    )
    plan["root_part"] = "door"
    plan["joints"] = _hinge_joint()

    result = _export(plan, str(parts_dir), str(out))

    standalone_stl = trimesh.load(result["union_stls"]["standalone"], force="mesh")
    assert abs(standalone_stl.bounds[0][2] - 28) < 0.01
    assert abs(standalone_stl.bounds[1][2] - 32) < 0.01


def test_copy_of_mirrored_and_identical(tmp_path):
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    (parts_dir / "wall_a.py").write_text(
        "import cadquery as cq\nresult = cq.Workplane('XY').box(10, 4, 2, centered=False)\n"
    )
    plan = {
        "parts": [
            {"id": "wall_a"},
            {"id": "wall_b", "copy_of": {"part": "wall_a", "mirror": "X"}},
            {
                "id": "wall_c",
                "copy_of": {"part": "wall_a"},
                "placement": {"translate_mm": [20, 0, 0]},
            },
        ]
    }
    out = _export(plan, str(parts_dir), str(tmp_path / "out"))
    assert not (parts_dir / "wall_b.py").exists()
    b = trimesh.load(out["union_stls"]["wall_b"]).bounds
    c = trimesh.load(out["union_stls"]["wall_c"]).bounds
    assert b[:, 0].tolist() == pytest.approx([-10, 0])
    assert c[:, 0].tolist() == pytest.approx([20, 30])
    manifest = json.loads(Path(out["manifest"]).read_text(encoding="utf-8"))
    assert manifest["unions"]["wall_b"]["script_part"] == "wall_a"


def _placed_plan(parts_dir):
    _write_part(parts_dir, "a")
    _write_part(parts_dir, "b")
    return _plan(
        [
            {"id": "a", "placement": {"translate": [0, 0, 0]}},
            {"id": "b", "placement": {"translate": [30, 0, 0]}},
        ]
    )


def test_formats_step_written_per_union_in_print_pose(tmp_path):
    import cadquery as cq

    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    plan = _placed_plan(parts_dir)
    out = tmp_path / "dist"
    orientations = {"a": {"rotate": [{"axis": "X", "angle_deg": 90}]}}

    result = _export(plan, str(parts_dir), str(out), orientations, formats=["step"])

    assert set(result["files"]["step"]) == {"a", "b"}
    assert result["model_3mf"] is None
    for uid, path in result["files"]["step"].items():
        assert Path(path) == out / "deliver" / f"{uid}.step"
    # a: rotated into print pose (20 mm tall); b: no orientation -> build pose (4 mm tall)
    a_bb = cq.importers.importStep(result["files"]["step"]["a"]).val().BoundingBox()
    b_bb = cq.importers.importStep(result["files"]["step"]["b"]).val().BoundingBox()
    assert a_bb.zlen == pytest.approx(20, abs=1e-3)
    assert b_bb.zlen == pytest.approx(4, abs=1e-3)
    assert b_bb.xmin == pytest.approx(-10, abs=1e-3)  # build pose: placement not applied


@pytest.mark.parametrize("bad", ["dxf", "gcode"])
def test_formats_unsupported_key_raises_before_writing(tmp_path, bad):
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    out = tmp_path / "dist"

    with pytest.raises(ValueError, match=bad):
        write_deliverables(_placed_plan(parts_dir), str(parts_dir), str(out), {}, ["step", bad])

    assert not out.exists()


def test_write_assembly_progress_reports_numbered_lines(tmp_path):
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_part(parts_dir, "base")
    _write_multi_union_part(parts_dir, "hinge", "leaf_a", "leaf_b")
    plan = _plan(
        [
            {"id": "base", "description": "Base", "plate": "p"},
            {
                "id": "hinge",
                "description": "Hinge",
                "unions": [{"id": "leaf_a", "plate": "p"}, {"id": "leaf_b", "plate": "p"}],
            },
        ]
    )
    lines = []

    write_assembly(plan, str(parts_dir), str(tmp_path / "dist"), progress=lines.append)

    assert lines == [
        "[1/2] loading base",
        "[2/2] loading hinge",
        "[1/3] stl base",
        "[2/3] stl leaf_a",
        "[3/3] stl leaf_b",
    ]


def test_write_assembly_without_progress_prints_nothing(tmp_path, capsys):
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_part(parts_dir, "base")
    plan = _plan([{"id": "base", "description": "Base"}])

    plain = write_assembly(plan, str(parts_dir), str(tmp_path / "a"))
    assert capsys.readouterr().out == ""
    with_cb = write_assembly(plan, str(parts_dir), str(tmp_path / "b"), progress=lambda _s: None)

    assert plain.keys() == with_cb.keys()
    assert sorted(Path(p).name for p in plain["union_stls"].values()) == sorted(
        Path(p).name for p in with_cb["union_stls"].values()
    )


def test_multi_material_3mf_carries_extruders(tmp_path):
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_part(parts_dir, "body")
    _write_part(parts_dir, "grip")
    plan = _plan(
        [
            {"id": "body", "description": "Rigid body"},
            {"id": "grip", "description": "Soft grip", "material": "TPU"},
        ]
    )

    result = _export(plan, str(parts_dir), str(tmp_path / "dist"), formats=("3mf",))

    with zipfile.ZipFile(result["model_3mf"]) as zf:
        settings = ET.fromstring(zf.read("Metadata/model_settings.config"))
    extruders = [
        next(m.get("value") for m in o.findall("metadata") if m.get("key") == "extruder")
        for o in settings.findall("object")
    ]
    assert extruders == ["1", "2"]


def test_single_material_3mf_has_no_extruder_or_color_metadata(tmp_path):
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_part(parts_dir, "body")
    plan = _plan([{"id": "body", "description": "Rigid body"}])

    result = _export(plan, str(parts_dir), str(tmp_path / "dist"), formats=("3mf",))

    with zipfile.ZipFile(result["model_3mf"]) as zf:
        assert b'key="extruder"' not in zf.read("Metadata/model_settings.config")
