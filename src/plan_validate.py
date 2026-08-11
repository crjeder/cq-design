#!/usr/bin/env python3
"""Validate BUILD_PLAN.json against its schema and cross-check block names.

Usage:
    python3 plan_validate.py BUILD_PLAN.json
    python3 plan_validate.py BUILD_PLAN.json --inventory blocks/inventory.json

Exit codes: 0 valid, 1 invalid.
"""

import argparse
import json
import os
import re
import sys
from typing import Any

import jsonschema

_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "build_plan_schema.json")
_INVENTORY_PATH = os.path.join(os.path.dirname(__file__), "blocks", "inventory.json")
_ARCHETYPES_PATH = os.path.join(os.path.dirname(__file__), "..", "templates", "archetypes.json")

# Fields the planning prompt explicitly forbids but an LLM may still emit out of habit
# (e.g. from an older convention). Surfaced as a hint on the matching schema error
# instead of leaving the user to guess why an "additional property" is rejected.
_LEGACY_FIELD_HINTS = {
    "assembly": (
        "'assembly' is not part of the schema -- multi-part connections are expressed "
        "through each part's own `placement`, or via `joints` for a mate chain "
        "(see prompts/planning.md rules 5, 7-8)"
    ),
}
_ADDITIONAL_PROPS_RE = re.compile(r"'([^']+)'")


def _hint_for_error(err: jsonschema.exceptions.ValidationError) -> str:
    """Extra guidance for a known-legacy additional-property error, else ''."""
    if err.validator != "additionalProperties":
        return ""
    names = _ADDITIONAL_PROPS_RE.findall(err.message)
    hints = [_LEGACY_FIELD_HINTS[n] for n in names if n in _LEGACY_FIELD_HINTS]
    return " (" + "; ".join(hints) + ")" if hints else ""


def _load_json(path: str) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate_plan(
    plan_path: str,
    inventory_path: str = _INVENTORY_PATH,
    archetypes_path: str = _ARCHETYPES_PATH,
) -> list[str]:
    """Validate a BUILD_PLAN.json file. Returns list of error strings (empty = OK).

    plan_path is used as-is (resolved relative to the caller's cwd, not this file's
    location). Schema and inventory paths are always resolved relative to this file.
    """
    errors = []

    try:
        plan = _load_json(plan_path)
    except (OSError, json.JSONDecodeError) as e:
        return [f"Cannot load plan: {e}"]

    schema = _load_json(_SCHEMA_PATH)
    validator = jsonschema.Draft7Validator(schema)
    for err in sorted(validator.iter_errors(plan), key=lambda e: list(map(str, e.absolute_path))):
        path = " -> ".join(str(p) for p in err.absolute_path) or "(root)"
        errors.append(f"Schema error at {path}: {err.message}{_hint_for_error(err)}")

    if errors:
        return errors

    # Cross-check block names against inventory
    try:
        from blocks.validate import get_block_names

        valid_blocks = get_block_names(inventory_path)
    except Exception as e:
        errors.append(f"Cannot load block inventory: {e}")
        return errors

    for part in plan.get("parts", []):
        pid = part.get("id", "(unknown)")
        for block in part.get("blocks_needed", []):
            block_name = block if isinstance(block, str) else block.get("name")
            if block_name not in valid_blocks:
                errors.append(
                    f"Part '{pid}': unknown block '{block_name}' "
                    f"(not in inventory). Available: {sorted(valid_blocks)}"
                )

    errors.extend(_check_archetypes(plan, archetypes_path))
    errors.extend(_check_unions(plan))
    errors.extend(_check_placements(plan))
    errors.extend(_check_nonzero_dir(plan, "load"))
    errors.extend(_check_nonzero_dir(plan, "show_face"))
    errors.extend(_check_kinematics(plan, inventory_path))
    errors.extend(_check_joints(plan, inventory_path))
    errors.extend(_check_request_log(plan))

    return errors


def _check_archetypes(plan: dict[str, Any], archetypes_path: str = _ARCHETYPES_PATH) -> list[str]:
    """Cross-check each part's optional `archetype` against templates/archetypes.json
    names, mirroring the `blocks_needed` inventory cross-check."""
    parts = plan.get("parts", [])
    if not any("archetype" in part for part in parts):
        return []

    try:
        archetypes = _load_json(archetypes_path)
        valid_names = {entry["name"] for entry in archetypes}
    except (OSError, json.JSONDecodeError) as e:
        return [f"Cannot load archetype index: {e}"]

    errors = []
    for part in parts:
        name = part.get("archetype")
        if name is None or name in valid_names:
            continue
        pid = part.get("id", "(unknown)")
        errors.append(
            f"Part '{pid}': unknown archetype '{name}' (not in templates/archetypes.json). "
            f"Available: {sorted(valid_names)}"
        )
    return errors


def _check_unions(plan: dict[str, Any]) -> list[str]:
    """Union ids (a part's declared `unions`, else the part id) must be unique across the
    model, and none may use the reserved `keep_out` name (see `units.KEEP_OUT_KEY`)."""
    from units import KEEP_OUT_KEY, iter_unions

    errors = []
    seen: dict[str, str] = {}
    for part, uid, _plate in iter_unions(plan):
        pid = part.get("id", "(unknown)")
        if uid == KEEP_OUT_KEY:
            errors.append(
                f"Part '{pid}': union id '{KEEP_OUT_KEY}' is reserved for declared "
                "keep-out zones and cannot be used as a union id"
            )
        if uid in seen:
            errors.append(
                f"Union id '{uid}' is declared more than once (parts '{seen[uid]}' and '{pid}')"
            )
        seen[uid] = pid
    return errors


def _check_nonzero_dir(plan: dict[str, Any], field: str) -> list[str]:
    """Reject a zero `field`.dir vector on any part.

    Shape (3-vector) is enforced by the schema; a zero vector has no orientation
    and cannot drive scoring, so it is rejected here. Used for `load` (strength
    scoring) and `show_face` (visual-quality scoring).
    """
    errors = []
    for part in plan.get("parts", []):
        hint = part.get(field)
        if not hint:
            continue
        direction = hint.get("dir", [])
        if len(direction) == 3 and not any(abs(c) > 0 for c in direction):
            pid = part.get("id", "(unknown)")
            errors.append(f"Part '{pid}': {field}.dir must be a non-zero direction")
    return errors


def _check_placements(plan: dict[str, Any]) -> list[str]:
    """Validate each part's optional `placement` (always-run, no jsonschema needed).

    Rotation axes must be X/Y/Z. This guards the assembled-frame placement the model
    export and kinematic check consume.
    """
    errors = []
    for part in plan.get("parts", []):
        pid = part.get("id", "(unknown)")
        placement = part.get("placement")
        if not placement:
            continue
        for step in placement.get("rotate", []):
            axis = step.get("axis")
            if axis not in ("X", "Y", "Z"):
                errors.append(f"Part '{pid}': placement rotate axis '{axis}' is not X, Y, or Z")
    return errors


# Joint-contract satisfaction tolerances (task 3.3).
_AXIS_PARALLEL_EPS = 1e-6  # dimensionless: |cos angle| within this of 1.0 counts as parallel
_AXIS_ORIGIN_EPS_MM = 1e-4  # a pivot this far (mm) off the axis line still counts as on it

_WISH_AXIS_VEC = {"X": (1.0, 0.0, 0.0), "Y": (0.0, 1.0, 0.0), "Z": (0.0, 0.0, 1.0)}


def _parallel(a: Any, b: Any) -> bool:
    """True when two vectors are parallel up to sign (normalized |dot| near 1)."""
    import math

    na = math.sqrt(sum(c * c for c in a))
    nb = math.sqrt(sum(c * c for c in b))
    if na < _AXIS_PARALLEL_EPS or nb < _AXIS_PARALLEL_EPS:
        return False
    cos = sum(x * y for x, y in zip(a, b, strict=True)) / (na * nb)
    return abs(abs(cos) - 1.0) <= _AXIS_PARALLEL_EPS


def _point_on_line(p: Any, q: Any, direction: Any) -> bool:
    """True when point p lies on the line through q in direction (perp distance ~ 0)."""
    import math

    nd = math.sqrt(sum(c * c for c in direction))
    if nd < _AXIS_PARALLEL_EPS:
        return False
    w = (p[0] - q[0], p[1] - q[1], p[2] - q[2])
    cx = w[1] * direction[2] - w[2] * direction[1]
    cy = w[2] * direction[0] - w[0] * direction[2]
    cz = w[0] * direction[1] - w[1] * direction[0]
    dist = math.sqrt(cx * cx + cy * cy + cz * cz) / nd
    return dist <= _AXIS_ORIGIN_EPS_MM


def _check_kinematics(plan: dict[str, Any], inventory_path: str) -> list[str]:
    """Cross-check kinematics entries against parts and inventory dof descriptors.

    Each entry's `moving_union` must reference an existing union id. When the entry
    names a `block`, it must exist and carry a `dof`, and -- the joint contract -- the
    declared joint `type` and axis must be satisfied by the block's dof: the type must
    match, and the block's block-coordinate dof axis (pushed through the moving union's
    placement) must match the plan's assembled-frame axis (revolute coaxial, prismatic
    parallel). The range arm of the contract is the separate numeric range check in
    `kinematic_check`. Spherical joints are not contract-checked. A block-less entry (no
    `block`) is out of the contract's scope by construction: its axis and range are
    author-declared with no block `dof` to compare against, so only the `moving_union`
    check applies. Entries nest via `children` into a tree; every entry is checked the
    same way regardless of nesting depth.
    """
    kinematics = plan.get("kinematics", [])
    if not kinematics:
        return []

    from blocks.validate import get_block
    from placement import transform_direction, transform_point
    from units import iter_kinematics_entries, iter_unions

    union_part = {uid: part for part, uid, _plate in iter_unions(plan)}
    errors = []
    for entry in iter_kinematics_entries(kinematics):
        jid = entry.get("joint_id", "(unknown)")
        ref = entry["moving_union"]
        if ref not in union_part:
            errors.append(f"Kinematics '{jid}': moving_union '{ref}' is not a union id")
        block_name = entry.get("block")
        if block_name is None:
            continue  # block-less: axis is author-declared, nothing to contract-check
        block = get_block(block_name, inventory_path)
        if block is None:
            errors.append(f"Kinematics '{jid}': unknown block '{block_name}' (not in inventory)")
            continue
        dof = block.get("dof")
        if dof is None:
            errors.append(f"Kinematics '{jid}': block '{block_name}' has no 'dof' descriptor")
            continue

        # ---- contract: type arm ----
        jtype, dtype = entry.get("type"), dof.get("type")
        if jtype != dtype:
            errors.append(
                f"Kinematics '{jid}': joint type '{jtype}' does not match block "
                f"'{block_name}' dof.type '{dtype}'"
            )
            continue
        # Spherical (and any non single-axis) joint is parked: no axis contract yet.
        if dtype not in ("revolute", "prismatic"):
            continue

        # ---- contract: axis arm (compared in the assembled frame, after placement) ----
        part = union_part.get(ref)
        if part is None:  # moving_union already flagged above
            continue
        placement = part.get("placement")
        if placement is None:
            # The part author supplies `placement` during the build phase (see
            # assembled-pose-handback); on a Phase 2 run it is not there yet, and
            # treating absence as identity here would silently compare the wrong
            # frame. Deferred to check_deferred_axis_arms as a non-fatal advisory;
            # authoritative only on the pre-export re-validation.
            continue
        block_dir = transform_direction(dof["direction"], placement)
        wish_dir = _WISH_AXIS_VEC[entry["axis_dir"]]
        if not _parallel(block_dir, wish_dir):
            errors.append(
                f"Kinematics '{jid}': joint axis_dir '{entry['axis_dir']}' is not parallel to "
                f"block '{block_name}' dof axis after placement"
            )
        elif dtype == "revolute":
            block_origin = transform_point(dof["origin"], placement)
            if not _point_on_line(entry["axis_origin_mm"], block_origin, block_dir):
                errors.append(
                    f"Kinematics '{jid}': revolute joint is not coaxial -- axis_origin_mm "
                    f"{entry['axis_origin_mm']} is off block '{block_name}' dof axis line"
                )

    return errors


def _check_single_joint(
    joint: dict[str, Any], part_ids: set[str], inventory_path: str
) -> tuple[tuple[str, str] | None, list[str]]:
    """Validate one `joints[]` entry. Return (edge, errors); edge is None if invalid.

    `edge` is the (part_a, part_b) pair to add to the mate graph, only when both
    parts are declared and distinct.
    """
    from blocks.validate import get_block

    errors: list[str] = []
    jid = joint.get("joint_id", "(unknown)")
    block_name = joint["block"]
    block = get_block(block_name, inventory_path)
    if block is None:
        errors.append(f"Joint '{jid}': unknown block '{block_name}' (not in inventory)")
        return None, errors
    emits = block.get("emits")
    if not emits:
        errors.append(
            f"Joint '{jid}': block '{block_name}' has no 'emits' descriptor and cannot back a joint"
        )
        return None, errors

    members = joint["members"]
    member_ids = [m["member"] for m in members]
    part_refs = [m["part"] for m in members]

    for mid in member_ids:
        if mid not in emits:
            errors.append(
                f"Joint '{jid}': member '{mid}' is not one of block '{block_name}' emits {emits}"
            )
    if all(mid in emits for mid in member_ids) and len(set(member_ids)) < len(member_ids):
        errors.append(
            f"Joint '{jid}': the two members must reference distinct emits ids, got {member_ids}"
        )

    for p in part_refs:
        if p not in part_ids:
            errors.append(f"Joint '{jid}': part '{p}' is not a declared part id")

    if part_refs[0] == part_refs[1]:
        errors.append(
            f"Joint '{jid}': both members reference the same part '{part_refs[0]}'; "
            "a same-part matched pair uses the part's own 'unions' array, not a "
            "'joints' entry"
        )
        return None, errors

    if part_refs[0] in part_ids and part_refs[1] in part_ids:
        return (part_refs[0], part_refs[1]), errors
    return None, errors


def _bfs_mate_tree(
    root_part: str, adjacency: dict[str, list[str]]
) -> tuple[dict[str, str | None], set[str]]:
    """BFS the undirected mate graph from `root_part`.

    Tracks each node's parent so the edge back to where we came from isn't
    mistaken for a cycle. Returns (parent, conflicting) -- `conflicting` holds
    parts reachable via more than one mate path.
    """
    parent: dict[str, str | None] = {root_part: None}
    order = [root_part]
    conflicting: set[str] = set()
    i = 0
    while i < len(order):
        cur = order[i]
        i += 1
        for nxt in adjacency.get(cur, []):
            if nxt == parent.get(cur):
                continue
            if nxt in parent:
                conflicting.add(nxt)
                continue
            parent[nxt] = cur
            order.append(nxt)
    return parent, conflicting


def _check_joints(plan: dict[str, Any], inventory_path: str) -> list[str]:
    """Cross-check `joints` entries and validate the mate graph is a single tree.

    Each entry's `members` must reference the block's declared `emits` ids (two
    distinct ones) and two distinct existing part ids. The mate graph (parts as
    nodes, each `joints` entry an edge) must form a single tree rooted at
    `root_part`: every part named in some `joints` entry must be reachable via
    exactly one path (a second path is a conflicting mate path -- closed loops are
    out of scope, the same tree-only boundary as the `kinematics` tree), and no
    such part other than `root_part` itself may also declare its own `placement`
    (double-anchored).
    """
    joints = plan.get("joints", [])
    if not joints:
        return []

    errors: list[str] = []
    part_ids = {p["id"] for p in plan.get("parts", [])}
    parts_by_id = {p["id"]: p for p in plan.get("parts", [])}
    root_part = plan.get("root_part")

    adjacency: dict[str, list[str]] = {}
    graph_parts: set[str] = set()

    for joint in joints:
        edge, joint_errors = _check_single_joint(joint, part_ids, inventory_path)
        errors.extend(joint_errors)
        if edge is not None:
            a, b = edge
            adjacency.setdefault(a, []).append(b)
            adjacency.setdefault(b, []).append(a)
            graph_parts.add(a)
            graph_parts.add(b)

    if not graph_parts:
        return errors

    if root_part is None:
        errors.append("root_part is required when 'joints' is non-empty")
        return errors
    if root_part not in part_ids:
        errors.append(f"root_part '{root_part}' is not a declared part id")
        return errors

    parent, conflicting = _bfs_mate_tree(root_part, adjacency)

    for p in sorted(conflicting):
        errors.append(
            f"Part '{p}' is reachable via more than one mate path (conflicting mate path)"
        )

    unanchored = sorted(graph_parts - set(parent) - conflicting)
    for p in unanchored:
        errors.append(f"Part '{p}' is unanchored: not reachable from root_part '{root_part}'")

    for p in parent:
        if p == root_part:
            continue
        if parts_by_id.get(p, {}).get("placement"):
            errors.append(
                f"Part '{p}' is double-anchored: reachable via the mate chain but also "
                "declares its own placement"
            )

    return errors


def _check_request_log(plan: dict[str, Any]) -> list[str]:
    """When present, `request_log` must hold exactly one `initial` entry, first in
    the array. Draft-7 has no minContains/maxContains, so this is checked here
    instead of in the schema (see request-log design.md, Decision 2)."""
    log = plan.get("request_log")
    if not log:
        return []
    initial_idxs = [i for i, entry in enumerate(log) if entry.get("kind") == "initial"]
    if len(initial_idxs) != 1:
        return [f"request_log must contain exactly one 'initial' entry, found {len(initial_idxs)}"]
    if initial_idxs[0] != 0:
        return ["request_log's 'initial' entry must be first"]
    return []


def check_deferred_axis_arms(
    plan: dict[str, Any], inventory_path: str = _INVENTORY_PATH
) -> list[str]:
    """Advisory: kinematics entries whose axis-arm contract check was deferred.

    `_check_kinematics` skips the axis-arm comparison for any entry whose moving
    union's part carries no `placement` yet (the part author supplies it during the
    build phase, see `assembled-pose-handback` design D5). This reports which entries
    that affected, as a non-fatal advisory alongside `check_block_thinness` -- it does
    not distinguish "author has not run yet" from "author chose the assembled frame",
    since absence means identity either way; the pre-export re-validation is what
    makes the axis arm authoritative again.
    """
    kinematics = plan.get("kinematics", [])
    if not kinematics:
        return []

    from blocks.validate import get_block
    from units import iter_kinematics_entries, iter_unions

    union_part = {uid: part for part, uid, _plate in iter_unions(plan)}
    findings: list[str] = []
    for entry in iter_kinematics_entries(kinematics):
        jid = entry.get("joint_id", "(unknown)")
        block_name = entry.get("block")
        if block_name is None:
            continue  # block-less: no dof to compare, nothing deferred
        block = get_block(block_name, inventory_path)
        if block is None:
            continue  # unknown block already flagged as an error
        dof = block.get("dof")
        if dof is None or entry.get("type") != dof.get("type"):
            continue  # missing dof / type mismatch already flagged as an error
        if dof.get("type") not in ("revolute", "prismatic"):
            continue  # no axis contract for this type
        moving_union = entry.get("moving_union")
        part = union_part.get(moving_union) if moving_union is not None else None
        if part is not None and part.get("placement") is None:
            findings.append(
                f"Kinematics '{jid}': axis arm deferred -- moving_union "
                f"'{moving_union}' (part '{part.get('id')}') carries no "
                "placement yet; authoritative only on the pre-export re-validation"
            )

    return findings


def check_block_thinness(plan: dict[str, Any]) -> list[str]:
    """Flag blocks whose smallest declared extent is below the wall minimum.

    Script-level thin-interface check: runs on the plan before any code or mesh,
    with full attribution to the part, block, and axis. Returns advisory findings
    (not hard validation errors). Blocks without declared `extents_mm` are skipped.
    """
    findings: list[str] = []
    wall_min = plan.get("constraints", {}).get("wall_min_mm")
    if not wall_min:
        return findings

    for part in plan.get("parts", []):
        pid = part.get("id", "(unknown)")
        for block in part.get("blocks_needed", []):
            if not isinstance(block, dict):
                continue
            extents = block.get("extents_mm")
            if not extents:
                continue
            smallest = min(extents)
            if smallest < wall_min:
                axis = ["x", "y", "z"][extents.index(smallest)]
                findings.append(
                    f"Part '{pid}' block '{block.get('name')}': {axis}-extent "
                    f"{smallest} mm is below wall_min {wall_min} mm; increase this "
                    f"block dimension or the part will have an unprintable thin wall"
                )

    return findings


def main():
    parser = argparse.ArgumentParser(description="Validate BUILD_PLAN.json")
    parser.add_argument("plan", help="Path to BUILD_PLAN.json")
    parser.add_argument(
        "--inventory", default=_INVENTORY_PATH, help="Path to blocks/inventory.json"
    )
    parser.add_argument(
        "--archetypes", default=_ARCHETYPES_PATH, help="Path to templates/archetypes.json"
    )
    args = parser.parse_args()

    errors = validate_plan(args.plan, args.inventory, args.archetypes)
    if errors:
        print(f"BUILD_PLAN validation FAILED ({len(errors)} error(s)):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    plan = _load_json(args.plan)
    n_parts = len(plan.get("parts", []))
    print(f"BUILD_PLAN OK — {n_parts} part(s), schema_version={plan.get('schema_version')}")

    findings = check_block_thinness(plan)
    if findings:
        print(f"\nThin-block findings ({len(findings)}):")
        for f in findings:
            print(f"  - {f}")

    deferred = check_deferred_axis_arms(plan, args.inventory)
    if deferred:
        print(f"\nDeferred axis-arm findings ({len(deferred)}):")
        for f in deferred:
            print(f"  - {f}")


if __name__ == "__main__":
    main()
