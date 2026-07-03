"""Multi-object 3MF writer: one named <object> per union, with plate metadata.

CadQuery's built-in `ThreeMFWriter` emits one object per sub-shape but bundles them
into a single unnamed component and drops any per-union identity. This writer keeps
each union as a separately named, separately built object carrying its plate id as
object-level metadata, and also emits `Metadata/model_settings.config` in Bambu
Studio / OrcaSlicer's proprietary multi-plate schema (`<plate>` / `<model_instance>`
elements keyed by object id) so those slicers auto-distribute objects across
separate build plates on import, instead of stacking every union onto plate 1. The
plain `<metadata name="plate">` on each object (below) is kept as a
slicer-independent fallback for tools that don't read the Bambu extension.

Geometry is written in the assembled pose (the caller bakes placement into each
shape before passing it in).
"""

import xml.etree.ElementTree as ET
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

_CORE = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
_REL_3DMODEL = "http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"

_RELS = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    f'<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="{_REL_3DMODEL}"/>'
    "</Relationships>"
)

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'  # noqa: E501
    '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'  # noqa: E501
    "</Types>"
)


def _weld(verts: list, tris: list) -> tuple[list, list]:
    """Merge coincident tessellation vertices and remap triangle indices.

    OCC tessellates each face independently and does not share vertices across
    face seams, so a shared edge gets two distinct index pairs. Written verbatim
    to 3MF (an index-based format) those seam edges are used by only one triangle
    each and slicers report them as non-manifold. STL hides this (no shared
    vertices at all); 3MF does not. Welding by exact position restores a single
    shared index per physical vertex so every interior edge is used twice.
    """
    remap: dict[tuple[float, float, float], int] = {}
    out_verts: list = []
    old_to_new: list[int] = [0] * len(verts)
    for i, v in enumerate(verts):
        key = (round(v.x, 6), round(v.y, 6), round(v.z, 6))
        idx = remap.get(key)
        if idx is None:
            idx = len(out_verts)
            remap[key] = idx
            out_verts.append(v)
        old_to_new[i] = idx
    out_tris = [(old_to_new[a], old_to_new[b], old_to_new[c]) for a, b, c in tris]
    return out_verts, out_tris


def _add_object(
    resources: ET.Element,
    obj_id: str,
    name: str,
    plate: str | None,
    shape: Any,
    tolerance: float,
    angular_tolerance: float,
) -> None:
    """Append one named <object>, welding tessellation vertices before writing.

    A `plate` of None omits the plate metadata (single-object exports have no
    plate grouping).
    """
    verts, tris = shape.tessellate(tolerance, angular_tolerance)
    verts, tris = _weld(verts, tris)
    obj = ET.SubElement(resources, "object", id=obj_id, name=name, type="model")
    if plate is not None:
        meta_group = ET.SubElement(obj, "metadatagroup")
        ET.SubElement(meta_group, "metadata", name="plate").text = plate
    mesh = ET.SubElement(obj, "mesh")
    vertices = ET.SubElement(mesh, "vertices")
    for v in verts:
        ET.SubElement(vertices, "vertex", x=str(v.x), y=str(v.y), z=str(v.z))
    triangles = ET.SubElement(mesh, "triangles")
    for t in tris:
        ET.SubElement(triangles, "triangle", v1=str(t[0]), v2=str(t[1]), v3=str(t[2]))


def _model_settings_config(plate_assignments: list[tuple[str, str]]) -> bytes:
    """Build `Metadata/model_settings.config` assigning objects to slicer plates.

    Matches Bambu Studio / OrcaSlicer's proprietary 3MF plate schema (reverse
    engineered from `bbs_3mf.cpp` in the BambuStudio source): a `<plate>` per
    distinct plate id, each carrying a `plater_id` (1-based, in first-seen order)
    and one `<model_instance>` per object assigned to it, referencing the same
    numeric `object_id` used for that object's `<object id="...">` in
    `3D/3dmodel.model`. `instance_id` is always `0` (we never emit more than one
    instance of an object).

    Args:
        plate_assignments: list of (object_id, plate_id) in object order.
    """
    plate_order: list[str] = []
    for _obj_id, plate in plate_assignments:
        if plate not in plate_order:
            plate_order.append(plate)

    config = ET.Element("config")
    for plate_index, plate in enumerate(plate_order, start=1):
        plate_el = ET.SubElement(config, "plate")
        ET.SubElement(plate_el, "metadata", key="plater_id", value=str(plate_index))
        ET.SubElement(plate_el, "metadata", key="plater_name", value=plate)
        ET.SubElement(plate_el, "metadata", key="locked", value="false")
        for obj_id, obj_plate in plate_assignments:
            if obj_plate != plate:
                continue
            instance = ET.SubElement(plate_el, "model_instance")
            ET.SubElement(instance, "metadata", key="object_id", value=obj_id)
            ET.SubElement(instance, "metadata", key="instance_id", value="0")
            ET.SubElement(instance, "metadata", key="identify_id", value=obj_id)
    return ET.tostring(config, xml_declaration=True, encoding="utf-8")


def write_named_3mf(
    objects: list[tuple[str, str, Any]],
    path: str,
    tolerance: float = 0.01,
    angular_tolerance: float = 0.1,
) -> None:
    """Write a 3MF with one named object per union, grouped onto slicer plates.

    Args:
        objects: list of (union_name, plate_id, cq_shape) in assembled pose
        path: output .3mf path
    """
    model = ET.Element("model", {"unit": "millimeter", "xml:lang": "en-US", "xmlns": _CORE})
    resources = ET.SubElement(model, "resources")
    build = ET.SubElement(model, "build")

    plate_assignments: list[tuple[str, str]] = []
    for i, (name, plate, shape) in enumerate(objects):
        obj_id = str(i + 1)
        _add_object(resources, obj_id, name, plate, shape, tolerance, angular_tolerance)
        ET.SubElement(build, "item", objectid=obj_id)
        plate_assignments.append((obj_id, plate))

    extra_files = {"Metadata/model_settings.config": _model_settings_config(plate_assignments)}
    _write_zip(model, path, extra_files)


def write_single_3mf(
    shape: Any,
    path: str,
    name: str = "model",
    tolerance: float = 0.01,
    angular_tolerance: float = 0.1,
) -> None:
    """Write a single-object 3MF (no plate metadata) with welded vertices.

    Used by the generic 3MF exporter. CadQuery's native ThreeMFWriter emits the
    raw per-face tessellation without welding, which slicers flag as non-manifold;
    this path welds first (see `_weld`).
    """
    model = ET.Element("model", {"unit": "millimeter", "xml:lang": "en-US", "xmlns": _CORE})
    resources = ET.SubElement(model, "resources")
    build = ET.SubElement(model, "build")
    _add_object(resources, "1", name, None, shape, tolerance, angular_tolerance)
    ET.SubElement(build, "item", objectid="1")
    _write_zip(model, path)


def _write_zip(model: ET.Element, path: str, extra_files: dict[str, bytes] | None = None) -> None:
    """Pack a model element into a minimal 3MF OPC container.

    `extra_files` are additional zip entries (e.g. `Metadata/model_settings.config`)
    written verbatim; BambuStudio/OrcaSlicer locate their proprietary metadata files
    by fixed path during zip iteration, not via OPC relationships, so no `.rels` or
    `[Content_Types].xml` entry is required for them.
    """
    xml = ET.tostring(model, xml_declaration=True, encoding="utf-8")
    with ZipFile(path, "w", ZIP_DEFLATED) as zf:
        zf.writestr("_rels/.rels", _RELS)
        zf.writestr("[Content_Types].xml", _CONTENT_TYPES)
        zf.writestr("3D/3dmodel.model", xml)
        for name, data in (extra_files or {}).items():
            zf.writestr(name, data)


def count_nonmanifold_edges(path: str) -> int:
    """Count edges used by other than exactly two triangles, by raw vertex index.

    Loads the mesh *without* vertex welding (`process=False`) so the index
    topology a slicer sees is checked, not trimesh's auto-repaired copy. Returns
    0 for a closed manifold mesh. Requires trimesh + numpy.
    """
    import numpy as np
    import trimesh

    mesh = trimesh.load(path, force="mesh", process=False)
    assert isinstance(mesh, trimesh.Trimesh)  # force="mesh" guarantees a single mesh
    edges = np.sort(mesh.edges, axis=1)
    _, counts = np.unique(edges, axis=0, return_counts=True)
    return int((counts != 2).sum())
