"""User-facing model files: named-object 3MF, STLs, and per-union STEP/OBJ/IGES/SCAD.

`build/build.py` is the only caller. Every requested format is in print pose (the build-pose
geometry rotated by the union's accepted orientation; build pose when it has none). The
assembled-pose STLs the checks read come from `write_assembly.py` and are never delivered.
"""

import os
import re
from collections import Counter
from collections.abc import Callable

import cadquery as cq

from exporters import _REGISTRY
from exporters.threemf_multi import write_named_3mf
from placement import apply_cq
from units import is_copy, plate_of
from write_assembly import assemble

_NAME_MAX_LEN = 64

# 3mf and stl are selectable too, but are written by write_deliverables itself.
EXTRA_FORMATS = tuple(k for k in _REGISTRY if k not in ("stl", "3mf"))
FORMATS = ("3mf", "stl", *EXTRA_FORMATS)


def _object_name(description: str, fallback: str) -> str:
    """Readable 3MF object name from a part description.

    Collapses internal whitespace/newlines to single spaces, strips control
    characters, trims, and caps length. Returns `fallback` (the part id) when the
    sanitized result is empty.
    """
    cleaned = re.sub(r"\s+", " ", description)
    cleaned = re.sub(r"[\x00-\x1f\x7f]", "", cleaned).strip()
    if len(cleaned) > _NAME_MAX_LEN:
        cleaned = cleaned[:_NAME_MAX_LEN].rstrip()
    return cleaned or fallback


def _dedupe_object_names(records: list[tuple[str, dict]]) -> list[str]:
    """One unique 3MF object name per union, in order.

    `records` is `[(union_id, part), ...]`. Each base name is the part description
    (`_object_name`, falling back to the union id); when several unions share a base name
    -- the common case for the two unions of one multi-union part -- each colliding name is
    disambiguated by suffixing the union id (which is unique). Non-colliding names are left
    unchanged.
    """
    base_names = [_object_name(part.get("description", ""), uid) for uid, part in records]
    counts = Counter(base_names)
    return [
        f"{base} ({uid})" if counts[base] > 1 else base
        for base, (uid, _part) in zip(base_names, records, strict=True)
    ]


def _union_scripts(plan: dict, parts_dir: str) -> dict[str, str]:
    """Union id -> source script path, from the plan alone (a copy reads its source's)."""
    scripts = {}
    for part in plan.get("parts", []):
        stem = part["copy_of"]["part"] if is_copy(part) else part["id"]
        for uid in [u["id"] for u in part.get("unions", [])] or [part["id"]]:
            scripts[uid] = os.path.join(parts_dir, f"{stem}.py")
    return scripts


def _print_pose(asm: dict, print_orientations: dict[str, dict], uid: str) -> cq.Workplane:
    """The union's build-pose geometry rotated into its print pose (build pose if none)."""
    rotate = (print_orientations.get(uid) or {}).get("rotate")
    wp = asm["authored"][uid]
    return apply_cq(wp, {"rotate": rotate}) if rotate else wp


def _plate_members(plan: dict) -> dict[str, list[str]]:
    """Plate -> union ids, from the plan alone."""
    plates: dict[str, list[str]] = {}
    for part in plan.get("parts", []):
        declared = {u["id"]: u for u in part.get("unions", [])}
        for uid in list(declared) or [part["id"]]:
            plates.setdefault(plate_of(part, uid, declared.get(uid)), []).append(uid)
    return plates


def write_deliverables(
    plan: dict,
    parts_dir: str,
    out_dir: str,
    print_orientations: dict[str, dict],
    formats: list[str],
    *,
    progress: Callable[[str], None] | None = None,
) -> dict:
    """Write each of `formats` into `out_dir`; return what was written.

    Every format is in print pose (build pose when a union has no orientation):

    - `3mf`: `model.3mf`, each union a named object, tagged with its plate.
    - `stl`: `<union>.stl` per union and a fused `plate_<n>.stl` per plate holding more
      than one union.
    - `step`/`obj`/`iges`/`scad`: `<union>.<ext>` per union.

    Returns `{"files": {format: {name: path}}}`. An unsupported
    key raises ValueError before anything is written. `progress` is called with a
    `[k/N] <step> <id>` line per part loaded, union STL and plate, and `writing model.3mf`.
    """
    bad = [f for f in formats if f not in FORMATS]
    if bad:
        raise ValueError(f"Unsupported format(s) {bad}; supported: {', '.join(FORMATS)}")
    formats = list(dict.fromkeys(formats))
    os.makedirs(out_dir, exist_ok=True)
    report = progress or (lambda _line: None)

    multi_plates = {p: ids for p, ids in _plate_members(plan).items() if len(ids) > 1}
    asm = assemble(plan, parts_dir, print_orientations, progress)
    files: dict[str, dict[str, str]] = {}

    if "3mf" in formats:
        files["3mf"] = {"model.3mf": _write_3mf(asm, print_orientations, out_dir, report)}

    if "stl" in formats:
        stls: dict[str, str] = {}
        uids = list(_union_scripts(plan, parts_dir))
        for k, uid in enumerate(uids, 1):
            report(f"[{k}/{len(uids)}] stl {uid}")
            path = os.path.join(out_dir, f"{uid}.stl")
            cq.exporters.export(_print_pose(asm, print_orientations, uid), path)
            stls[uid] = path
        # Fuse each multi-union plate in its assembled relative poses (print-in-place), then
        # adopt the first union's print orientation so the plate sits on the bed.
        for k, (plate, ids) in enumerate(multi_plates.items(), 1):
            report(f"[{k}/{len(multi_plates)}] plate {plate}")
            fused = asm["placed"][ids[0]]
            for uid in ids[1:]:
                fused = fused.union(asm["placed"][uid])
            if orientation := print_orientations.get(ids[0]):
                fused = apply_cq(fused, {"rotate": orientation.get("rotate", [])})
            path = os.path.join(out_dir, f"plate_{plate}.stl")
            cq.exporters.export(fused, path)
            stls[f"plate_{plate}"] = path
        files["stl"] = stls

    for fmt in formats:
        if fmt in EXTRA_FORMATS:
            exporter, ext = _REGISTRY[fmt]
            files[fmt] = {}
            for uid in asm["placed"]:
                path = os.path.join(out_dir, uid + ext)
                exporter.export(_print_pose(asm, print_orientations, uid), path)
                files[fmt][uid] = path
    return {"files": files}


def _write_3mf(
    asm: dict, print_orientations: dict[str, dict], out_dir: str, report: Callable[[str], None]
) -> str:
    """Write `model.3mf` (one named object per union) and guard its index topology."""

    names = _dedupe_object_names(asm["records"])
    objects = [
        (
            name,
            asm["plate_by_uid"][uid],
            cq.Compound.makeCompound(_print_pose(asm, print_orientations, uid).vals()),  # type: ignore[arg-type]
        )
        for name, (uid, _part) in zip(names, asm["records"], strict=True)
    ]
    path = os.path.join(out_dir, "model.3mf")
    report("writing model.3mf")
    nonmanifold = write_named_3mf(objects, path)

    if nonmanifold:
        raise RuntimeError(
            f"{path} has {nonmanifold} non-manifold edges; vertex welding failed in "
            "write_named_3mf."
        )
    return path
