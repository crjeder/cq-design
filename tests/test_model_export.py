# mypy: ignore-errors
# type: ignore  # CAD/trimesh stub-union noise; tests are ruff-linted, not type-checked
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

    result = export_model(plan, str(parts_dir), str(out))

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

    result = export_model(plan, str(parts_dir), str(out))

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


def test_stl_dir_splits_stl_output_from_model_dir(tmp_path):
    """model.3mf lands in model_dir (the project root); STLs land in the separate
    stl_dir when given, keeping the two artifact kinds apart."""
    import os

    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_part(parts_dir, "base")
    model_dir = tmp_path / "root"
    stl_dir = tmp_path / "root" / "stl"
    plan = _plan([{"id": "base"}])

    result = export_model(plan, str(parts_dir), str(model_dir), stl_dir=str(stl_dir))

    assert result["model_3mf"] == os.path.join(str(model_dir), "model.3mf")
    assert os.path.exists(result["model_3mf"])
    assert result["union_stls"]["base"] == os.path.join(str(stl_dir), "base.stl")
    assert os.path.exists(result["union_stls"]["base"])
    # STL did not also land in model_dir.
    assert not os.path.exists(os.path.join(str(model_dir), "base.stl"))


def test_stl_dir_omitted_falls_back_to_model_dir(tmp_path):
    """Backward compat: omitting stl_dir keeps the old single-directory behavior."""
    import os

    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_part(parts_dir, "base")
    out = tmp_path / "dist"

    result = export_model(_plan([{"id": "base"}]), str(parts_dir), str(out))

    assert os.path.dirname(result["model_3mf"]) == str(out)
    assert os.path.dirname(result["union_stls"]["base"]) == str(out)


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

    result = export_model(plan, str(parts_dir), str(out), orientations)

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

    result = export_model(plan, str(parts_dir), str(out))

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

    result = export_model(plan, str(parts_dir), str(out))

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

    result = export_model(plan, str(parts_dir), str(out))

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

    result = export_model(plan, str(parts_dir), str(out))

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
        export_model(plan, str(parts_dir), str(out))


def test_single_union_part_unchanged(tmp_path):
    """Backward compat: a plain-Workplane part is one union keyed by the part id."""
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir()
    _write_part(parts_dir, "solo")
    out = tmp_path / "dist"
    plan = _plan([{"id": "solo", "description": "Solo"}])

    result = export_model(plan, str(parts_dir), str(out))

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

    result = export_model(plan, str(parts_dir), str(out))

    # No collision -> no id suffix appended.
    assert set(_read_3mf_objects(result["model_3mf"])) == {"Enclosure base", "Snap lid"}


# ---- joint-mate-entity: derived pose replaces placement ----


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
    plan["joints"] = [
        {
            "joint_id": "hinge1",
            "block": "pin_hinge",
            "params": {},
            "members": [
                {"member": "leaf_a", "part": "door"},
                {"member": "leaf_b", "part": "wall", "dock": {"translate_mm": [0, 0, 10]}},
            ],
        }
    ]

    result = export_model(plan, str(parts_dir), str(out))

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
    plan["joints"] = [
        {
            "joint_id": "hinge1",
            "block": "pin_hinge",
            "params": {},
            "members": [
                {"member": "leaf_a", "part": "door"},
                {"member": "leaf_b", "part": "wall"},
            ],
        }
    ]

    result = export_model(plan, str(parts_dir), str(out))

    standalone_stl = trimesh.load(result["union_stls"]["standalone"], force="mesh")
    assert abs(standalone_stl.bounds[0][2] - 28) < 0.01
    assert abs(standalone_stl.bounds[1][2] - 32) < 0.01
