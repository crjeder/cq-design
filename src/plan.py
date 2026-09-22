#!/usr/bin/env python3
"""Read, validate, and write back BUILD_PLAN.json.

    python3 plan.py validate BUILD_PLAN.json
    python3 plan.py validate BUILD_PLAN.json --inventory blocks/inventory.json
    python3 plan.py summary BUILD_PLAN.json
    python3 plan.py import-params <part_script.py> --part <id> [--plan BUILD_PLAN.json] [--write]

`validate` checks the plan against its schema and cross-checks block names
(exit 0 valid, 1 invalid). `summary` renders the Phase 2 plan-summary checkpoint
tables as Markdown. `import-params` reconciles a hand-edited part script's
PARAMETERS block back into the plan -- a dry-run diff by default; `--write`
re-validates the updated plan against the schema before persisting, refusing to
write an invalid plan.

Exit codes: 0 success, 1 on validation/parse/reconcile error.
"""

import argparse
import ast
import copy
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
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

_COMPASS_WORD_RE = re.compile(r"\b(north|south|east|west)\b", re.IGNORECASE)
_HINGE_WORD_RE = re.compile(r"\b(hinge|pivot|fold|articulat)", re.IGNORECASE)

# Canonical load-bearing trigger set for `engineering_rationale` (see the
# `engineering-rationale` spec): a part using one of these blocks or archetypes takes
# the full object form regardless of whether it also declares `load`. Single source of
# truth -- src/render_prompt.py and prompts/audit.md use it via _is_load_bearing.
# Names verified against blocks/inventory.json and templates/archetypes.json.
_LOAD_BEARING_BLOCKS = {
    "snap_hook_clip",
    "screw_boss",
    "pcb_standoff",
    "living_hinge",
    "dovetail_groove",
    "dovetail_tongue",
    "dovetail_corner_joint",
}
_LOAD_BEARING_ARCHETYPES = {
    "hook",
    "clip",
    "l-bracket-gusset",
}


def _hint_for_error(err: jsonschema.exceptions.ValidationError) -> str:
    """Extra guidance for a known-legacy additional-property error, else ''."""
    path = list(err.absolute_path)
    if err.validator == "pattern" and path[-1:] == ["name"] and "interfaces" in path:
        return (
            " (interface names must be normalized snake_case: lowercase, with "
            "spaces and hyphens replaced by underscores, e.g. 'inner_lip')"
        )
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
    errors.extend(_check_interface_names(plan))
    errors.extend(_check_placements(plan))
    errors.extend(_check_nonzero_dir(plan, "load"))
    errors.extend(_check_nonzero_dir(plan, "show_face"))
    errors.extend(_check_kinematics(plan, inventory_path))
    errors.extend(_check_joints(plan, inventory_path))
    errors.extend(_check_request_log(plan))
    errors.extend(_check_intent_reconciled(plan))

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


def _check_interface_names(plan: dict[str, Any]) -> list[str]:
    """Interface `name` values must be unique within a part; unnamed interfaces are
    skipped. Unlike `_check_unions` (model-wide -- union ids share one namespace for
    files and 3MF objects), this scope is per-part: callout badges are rendered one
    part at a time, so a duplicate only creates ambiguity within that part's legend.
    The same name on two different parts is fine -- the part id disambiguates them."""
    errors = []
    for part in plan.get("parts", []):
        pid = part.get("id", "(unknown)")
        seen: set[str] = set()
        for interface in part.get("interfaces", []):
            name = interface.get("name")
            if name is None:
                continue
            if name in seen:
                errors.append(f"Part '{pid}': interface name '{name}' is declared more than once")
            seen.add(name)
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


def _parse_ts(value: str) -> datetime:
    """Parse an ISO-8601 timestamp (trailing `Z` allowed on Python 3.10); naive means UTC."""
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _check_intent_reconciled(plan: dict[str, Any]) -> list[str]:
    """Fail when a clarification/correction entry is newer than `intent_ts` (or the stamp
    is absent while such entries exist): `intent` was not reconciled against the log."""
    entries = [e for e in plan.get("request_log") or [] if e.get("kind") != "initial"]
    if not entries:
        return []
    fix = (
        "rewrite `intent` if the design changed, then set `intent_ts` "
        "(request_log_search.py add --reconciled)"
    )
    stamp = plan.get("intent_ts")
    try:
        cutoff = _parse_ts(stamp) if stamp is not None else None
    except ValueError:
        return [f"intent_ts {stamp!r} is not an ISO-8601 timestamp"]
    errors = []
    stale = []
    for e in entries:
        try:
            ts = _parse_ts(e["ts"])
        except ValueError:
            errors.append(f"request_log entry ts {e['ts']!r} is not an ISO-8601 timestamp")
            continue
        if cutoff is None or ts > cutoff:
            stale.append(f"[{e['kind']} {e['ts']}] {e['text'][:60]}")
    if stale:
        errors.append(
            f"intent not reconciled with request_log ({len(stale)} entr"
            f"{'y' if len(stale) == 1 else 'ies'} newer than intent_ts={stamp}): "
            + "; ".join(stale)
            + f" -- {fix}"
        )
    return errors


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


def _linked_part_pairs(plan: dict[str, Any]) -> set[frozenset[str]]:
    return {
        frozenset(m.get("part") for m in joint.get("members", []))
        for joint in plan.get("joints", [])
    }


# Relative tolerance for comparing two interfaces' diameter_mm in the positional
# coincidence check (D4). Small and multiplicative, unlike the fixed-mm position tolerance.
_DIAMETER_REL_TOL = 0.05


def _positional_round_interfaces(
    plan: dict[str, Any],
) -> list[tuple[str, tuple[float, float, float], float]]:
    """(part_id, assembled-frame position, diameter_mm) for every interface carrying both
    `position_mm` and `diameter_mm`, transformed through its part's `placement` (D4)."""
    from placement import transform_point

    out = []
    for part in plan.get("parts", []):
        pid = part.get("id", "(unknown)")
        placement = part.get("placement")
        for interface in part.get("interfaces", []):
            if "position_mm" not in interface or "diameter_mm" not in interface:
                continue
            pos = transform_point(interface["position_mm"], placement)
            out.append((pid, pos, float(interface["diameter_mm"])))
    return out


def _check_positional_shared_interfaces(plan: dict[str, Any]) -> list[str]:
    """Advisory: two parts' round interfaces coincide in the assembled frame (position
    within `feature_presence_check`'s `_POS_TOL_MM`, diameter within a small relative
    tolerance) with no `joints` entry linking the two parts. Additive to the named-
    interface check above -- independent of whether `name` matches, is null, or differs.
    """
    import math

    from feature_presence_check import _POS_TOL_MM

    entries = _positional_round_interfaces(plan)
    linked = _linked_part_pairs(plan)

    findings: list[str] = []
    seen_pairs: set[frozenset[str]] = set()
    for i, (pid_a, pos_a, dia_a) in enumerate(entries):
        for pid_b, pos_b, dia_b in entries[i + 1 :]:
            if pid_a == pid_b:
                continue
            pair = frozenset((pid_a, pid_b))
            if pair in linked or pair in seen_pairs:
                continue
            dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(pos_a, pos_b, strict=True)))
            if dist > _POS_TOL_MM:
                continue
            if abs(dia_a - dia_b) / max(dia_a, dia_b) > _DIAMETER_REL_TOL:
                continue
            seen_pairs.add(pair)
            findings.append(
                f"Parts '{pid_a}' and '{pid_b}' each declare a round interface "
                f"(~{dia_a:.2f} mm) at coincident assembled-frame positions with no "
                "joints entry linking them; a shared vocabulary word for two genuinely "
                "independent features is legitimate, but a shared physical mate belongs "
                "in `joints` so its value has a single source and the mated part's pose "
                "is derived (mate_chain.py)"
            )

    return findings


def check_shared_interfaces(plan: dict[str, Any]) -> list[str]:
    """Advisory: one `interfaces[].name` held by parts no `joints` entry links, or two
    parts' round interfaces coincide in the assembled frame with no `joints` entry.

    Two parts naming one feature with the same agreed vocabulary word are declaring
    one physical mate. Routed through `joints`, the pair's numbers live once in
    `joints[].params` and the second part's pose is derived by `mate_chain.py`;
    declared as two `interfaces[]` entries instead, they are two independently typed
    literals that agree only by convention -- the C5 cradle/plate `PIVOT_Z`, which
    re-diverged every correction round (see TODO.md). Advisory, not an error: a
    shared vocabulary word for two genuinely independent features is legitimate.
    Unnamed interfaces are skipped by the named-match branch below, but still covered
    by the positional branch (D4) when they carry `position_mm`/`diameter_mm`.
    """
    holders: dict[str, list[str]] = {}
    for part in plan.get("parts", []):
        pid = part.get("id", "(unknown)")
        for interface in part.get("interfaces", []):
            name = interface.get("name")
            if name is not None and pid not in holders.setdefault(name, []):
                holders[name].append(pid)

    linked = _linked_part_pairs(plan)

    findings: list[str] = []
    for name, parts in holders.items():
        if len(parts) < 2:
            continue
        # Parts this name links to no other holder of it. With a joint covering one
        # pair, only the remaining holders are still independently typed.
        unlinked = [
            pid
            for pid in parts
            if not any(frozenset((pid, other)) in linked for other in parts if other != pid)
        ]
        if not unlinked:
            continue
        reported = parts if len(unlinked) == len(parts) else unlinked
        findings.append(
            f"Interface '{name}' is declared on {', '.join(repr(p) for p in reported)} "
            "with no joints entry linking them; a shared mate belongs in `joints` so "
            "its value has a single source and the mated part's pose is derived "
            "(mate_chain.py), instead of the same literal being typed into each part"
        )

    findings.extend(_check_positional_shared_interfaces(plan))
    return findings


def _plan_texts(plan: dict[str, Any], *, include_planning_notes: bool) -> list[str]:
    """intent, optionally planning_notes, and every request_log[].text -- the text pool
    the compass-usage and hinge-intent keyword scans (D2, D5) search."""
    texts = []
    if plan.get("intent"):
        texts.append(plan["intent"])
    if include_planning_notes and plan.get("planning_notes"):
        texts.append(plan["planning_notes"])
    for entry in plan.get("request_log") or []:
        if entry.get("text"):
            texts.append(entry["text"])
    return texts


def check_coordinate_frame_usage(plan: dict[str, Any]) -> list[str]:
    """Advisory: compass language used in `intent`/`planning_notes`/`request_log` with no
    recorded `coordinate_frame` (see coordinate-frame spec). A cheap keyword scan, not an
    LLM classification -- false positives just mean an unnecessary reminder.
    """
    if plan.get("coordinate_frame"):
        return []
    texts = _plan_texts(plan, include_planning_notes=True)
    if not any(_COMPASS_WORD_RE.search(t) for t in texts):
        return []
    return [
        "Plan uses compass language (north/south/east/west) in intent/planning_notes/"
        "request_log but declares no `coordinate_frame`; record one so every reader "
        "resolves 'East' etc. the same way (see prompts/planning.md's Coordinate "
        "vocabulary table for the standard binding)."
    ]


def check_hinge_intent_without_joints(plan: dict[str, Any]) -> list[str]:
    """Advisory: hinge/pivot/fold language in `intent`/`request_log` on a multi-part plan
    with no `joints` entry (see shared-literal-detection spec, D5).
    """
    parts = plan.get("parts", [])
    if len(parts) <= 1:
        return []
    if plan.get("joints"):
        return []
    texts = _plan_texts(plan, include_planning_notes=False)
    if not any(_HINGE_WORD_RE.search(t) for t in texts):
        return []
    return [
        "Plan's intent/request_log uses hinge/pivot/fold/articulation language but "
        "declares no `joints` entry linking the moving parts; route a shared mechanical "
        "mate through `joints`/`kinematics` (see prompts/planning.md rule 7)."
    ]


def _is_load_bearing(part: dict[str, Any]) -> bool:
    """True if `part` meets the engineering-rationale trigger: a declared `load`, or a
    block/archetype in the canonical load-bearing set."""
    if part.get("load"):
        return True
    if part.get("archetype") in _LOAD_BEARING_ARCHETYPES:
        return True
    for block in part.get("blocks_needed", []):
        name = block if isinstance(block, str) else block.get("name")
        if name in _LOAD_BEARING_BLOCKS:
            return True
    return False


def check_engineering_rationale(plan: dict[str, Any]) -> list[str]:
    """Check each part's `engineering_rationale` against the load-bearing trigger.

    A triggered part must carry the object form; an untriggered part may carry either
    form; a missing field is always a finding. Advisory by default -- the caller decides
    whether to treat these as errors (see `--require-rationale`).
    """
    findings: list[str] = []
    for part in plan.get("parts", []):
        pid = part.get("id", "(unknown)")
        rationale = part.get("engineering_rationale")
        triggered = _is_load_bearing(part)

        if rationale is None:
            findings.append(
                f"Part '{pid}': missing 'engineering_rationale'"
                + (" (this part is load-bearing)" if triggered else "")
            )
        elif triggered and isinstance(rationale, str):
            findings.append(
                f"Part '{pid}': declares a load or a load-bearing block/archetype but "
                f"'engineering_rationale' is the one-line form -- the full "
                f"load_path/worst_case_stress/check object is required"
            )

    return findings


def check_load_case_anchors(plan: dict[str, Any]) -> list[str]:
    """Check a part's `load.applied_at` / `load.grounded_at` name interfaces that exist
    on that part (see the `fem-stress-advisor` spec). Advisory: a missing/misnamed
    anchor means the FEM advisor skips the part, not that the plan is invalid.
    """
    findings: list[str] = []
    for part in plan.get("parts", []):
        pid = part.get("id", "(unknown)")
        load = part.get("load")
        if not load:
            continue
        names = {i.get("name") for i in part.get("interfaces", []) if i.get("name")}
        applied_at = load.get("applied_at")
        if applied_at is not None and applied_at not in names:
            findings.append(
                f"Part '{pid}': load.applied_at '{applied_at}' does not name an "
                f"interfaces[].name on this part"
            )
        for grounded in load.get("grounded_at", []):
            if grounded not in names:
                findings.append(
                    f"Part '{pid}': load.grounded_at '{grounded}' does not name an "
                    f"interfaces[].name on this part"
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


REVIEW_POLICY_MEANING = {
    "every_stage": "every part shows a profile-stub checkpoint, then one per stage "
    "(base shape, features, finishing)",
    "checkpoints": "every part shows the stub checkpoint; only parts with an interface "
    "or 3+ blocks get per-stage checkpoints",
    "minimal": "no stub and no stage checkpoints",
}


def _cell(value) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _table(header: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(_cell(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def _load(part: dict) -> str:
    load = part.get("load")
    if not load:
        return "(none)"
    text = ",".join(f"{v:g}" for v in load["dir"]) if load.get("dir") else ""
    if load.get("type", "tension") != "tension" or not text:
        text = f"{text} {load.get('type', 'tension')}".strip()
    return text


def _blocks(part: dict) -> str:
    names = [b if isinstance(b, str) else b["name"] for b in part.get("blocks_needed") or []]
    return ", ".join(names) or "(none)"


def _tokens(text: str) -> set[str]:
    """Non-numeric word tokens (numeric suffixes like the '2' in hole_2 disambiguate,
    they don't need to match user wording)."""
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if not t.isdigit()}


def _open_questions(plan: dict) -> list[str]:
    lines = (plan.get("planning_notes") or "").split("\n")
    stripped = [re.sub(r"^[-*+]\s+", "", line.strip()) for line in lines]
    return [line for line in stripped if line.startswith("OPEN:")]


# `LOAD_MASS: <part_id> <mass> <unit> sf=<safety_factor>` in planning_notes, e.g.
# `LOAD_MASS: phone_shelf 187 g sf=2.0` -- same free-text-convention approach as
# `OPEN:`, carrying the mass/safety-factor derivation behind a part's `load.magnitude_n`
# without a schema field for it (the schema already carries the resulting magnitude_n).
_LOAD_MASS_RE = re.compile(
    r"^LOAD_MASS:\s+(?P<part_id>[a-z][a-z0-9_]*)\s+(?P<mass>[\d.]+)\s*(?P<unit>\S+)\s+sf=(?P<sf>[\d.]+)"
)


def _load_mass_notes(plan: dict) -> dict[str, dict[str, str]]:
    lines = (plan.get("planning_notes") or "").split("\n")
    stripped = [re.sub(r"^[-*+]\s+", "", line.strip()) for line in lines]
    notes: dict[str, dict[str, str]] = {}
    for line in stripped:
        m = _LOAD_MASS_RE.match(line)
        if m:
            notes[m.group("part_id")] = {
                "mass": m.group("mass"),
                "unit": m.group("unit"),
                "sf": m.group("sf"),
            }
    return notes


def _load_cases(plan: dict) -> list[list]:
    """One row per part declaring `load.magnitude_n`: the derivation (source mass, unit,
    safety factor) alongside the resulting force and anchors, so the Phase 2 checkpoint
    can catch a wrong mass before Phase 3 runs any FEM solve."""
    mass_notes = _load_mass_notes(plan)
    rows = []
    for p in plan["parts"]:
        load = p.get("load") or {}
        magnitude_n = load.get("magnitude_n")
        if magnitude_n is None:
            continue
        note = mass_notes.get(p["id"], {})
        mass = f"{note['mass']} {note['unit']}" if note else "(unspecified)"
        sf = note.get("sf", "(unspecified)")
        applied = load.get("applied_at") or "(none)"
        applied_dir = load.get("applied_dir")
        if applied_dir:
            applied += " dir=" + ",".join(f"{v:g}" for v in applied_dir)
        grounded = ", ".join(load.get("grounded_at") or []) or "(none)"
        rows.append([p["id"], mass, sf, f"{magnitude_n:g} N", applied, grounded])
    return rows


def _coined_names(plan: dict) -> list[str]:
    log_words: set[str] = set()
    for entry in plan.get("request_log") or []:
        log_words |= _tokens(entry.get("text", ""))
    if not log_words:
        return []
    flagged = []
    for part in plan["parts"]:
        if not _tokens(part["id"]) <= log_words:
            flagged.append(f"`{part['id']}` (part)")
        for i in part.get("interfaces") or []:
            name = i.get("name")
            if name and not _tokens(name) <= log_words:
                flagged.append(f"`{name}` (interface on `{part['id']}`)")
    return flagged


def summarize(plan: dict, plan_path: Path) -> str:
    """Markdown checkpoint tables for a validated plan."""
    parts = plan["parts"]
    out = [f"Written to: `{plan_path.resolve()}`", ""]
    out += [
        "**Printer / Material**",
        "",
        _table(
            ["Printer", "Material", "Nozzle"],
            [[plan.get("printer", ""), plan["material"], f"{plan['nozzle_mm']:g} mm"]],
        ),
        "",
        "**Parts**",
        "",
        _table(
            ["#", "ID", "Description", "W x D x H (mm)", "Load", "Pose", "Blocks", "Archetype"],
            [
                [
                    n,
                    p["id"],
                    p["description"],
                    " x ".join(f"{p['dimensions'][k]:g}" for k in ("w_mm", "d_mm", "h_mm")),
                    _load(p),
                    p.get("pose_intent", "(none)"),
                    _blocks(p),
                    p.get("archetype", "(none)"),
                ]
                for n, p in enumerate(parts, 1)
            ],
        ),
        "",
    ]

    goal = plan.get("optimize_for", "strength")
    line = f"**Print optimization:** `{goal}`"
    overrides = [
        f"`{p['id']}` -> `{p['optimize_for']}`"
        for p in parts
        if p.get("optimize_for", goal) != goal
    ]
    if overrides:
        line += "; overrides: " + ", ".join(overrides)
    faces = [
        f"`{p['id']}` show_face "
        + (",".join(f"{v:g}" for v in p["show_face"]["dir"]) if p.get("show_face") else "inferred")
        for p in parts
        if p.get("optimize_for", goal) == "visual_quality"
    ]
    if faces:
        line += "; " + ", ".join(faces)
    policy = plan.get("review_policy", "every_stage")
    out += [line, "", f"**Review policy:** `{policy}` -- {REVIEW_POLICY_MEANING[policy]}", ""]

    interfaces = [
        [
            p["id"],
            i.get("name") or "",
            i.get("type", ""),
            i.get("connector", ""),
            i.get("wall", ""),
            ",".join(f"{v:g}" for v in i["position_mm"]) if i.get("position_mm") else "",
        ]
        for p in parts
        for i in p.get("interfaces") or []
    ]
    if interfaces:
        out += [
            "**Interfaces**",
            "",
            _table(["Part", "Name", "Type", "Connector", "Wall", "Position (mm)"], interfaces),
            "",
        ]

    load_cases = _load_cases(plan)
    if load_cases:
        headers = [
            "Part",
            "Source mass",
            "Safety factor",
            "magnitude_n",
            "Applied at",
            "Grounded at",
        ]
        out += ["**Load cases**", "", _table(headers, load_cases), ""]

    coined = _coined_names(plan)
    if coined:
        out += ["**Names I chose**", "", *[f"- {c}" for c in coined], ""]

    open_questions = _open_questions(plan)
    if open_questions:
        out += ["**Open questions**", "", *[f"- {q}" for q in open_questions], ""]

    cons = plan["constraints"]
    out += [
        "**Constraints**",
        "",
        _table(
            ["Wall min", "Overhang max", "Dim tolerance"],
            [
                [
                    f"{cons['wall_min_mm']:g} mm",
                    f"{cons['overhang_max_deg']:g} deg",
                    f"{cons['dimension_tolerance_mm']:g} mm",
                ]
            ],
        ),
    ]
    return "\n".join(out)


_DIM_NAME_MAP = {"width": "w_mm", "depth": "d_mm", "height": "h_mm"}

Number = int | float


def parse_parameters(script_path: str) -> dict[str, Any]:
    """Extract module-level numeric-literal assignments from a part script via AST.

    Never imports or executes the script. Accepts a value only when it is an
    int/float (bool excluded) or a tuple/list of such. Returns {} on an unparseable
    file; caller distinguishes via a separate existence/syntax check if needed.
    """
    with open(script_path, encoding="utf-8") as f:
        source = f.read()
    tree = ast.parse(source, filename=script_path)

    params: dict[str, Any] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        name = node.targets[0].id
        try:
            value = ast.literal_eval(node.value)
        except (ValueError, SyntaxError):
            continue
        if _is_numeric(value):
            params[name] = value
    return params


def _is_numeric(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int | float):
        return True
    if isinstance(value, tuple | list):
        return len(value) > 0 and all(_is_numeric(v) for v in value)
    return False


def reconcile(parsed: dict[str, Any], plan: dict[str, Any], part_id: str) -> dict[str, Any]:
    """Diff parsed parameters against a plan part's dimensions.

    Returns {"changed": [...], "unchanged": [...], "unmapped": [...]}. Raises
    KeyError if part_id is not present in plan["parts"] -- caller maps to a
    structured error.
    """
    part = next((p for p in plan.get("parts", []) if p.get("id") == part_id), None)
    if part is None:
        raise KeyError(part_id)

    dimensions = part.get("dimensions", {})
    changed = []
    unchanged = []
    unmapped = []

    for name, value in parsed.items():
        field = _DIM_NAME_MAP.get(name)
        if field is None:
            unmapped.append(name)
            continue
        current = dimensions.get(field)
        if current == value:
            unchanged.append(field)
        else:
            changed.append({"field": field, "from": current, "to": value})

    return {"changed": changed, "unchanged": unchanged, "unmapped": unmapped}


def _apply_changes(
    plan: dict[str, Any], part_id: str, changed: list[dict[str, Any]]
) -> dict[str, Any]:
    """Return a deep copy of plan with `changed` dimension diffs applied to part_id."""
    updated = copy.deepcopy(plan)
    part = next(p for p in updated["parts"] if p["id"] == part_id)
    for entry in changed:
        part["dimensions"][entry["field"]] = entry["to"]
    return updated


def run(script_path: str, part_id: str, plan_path: str, write: bool) -> dict[str, Any]:
    """Run the full import-params flow. Returns the report dict (never raises)."""
    report: dict[str, Any] = {
        "part": part_id,
        "changed": [],
        "unchanged": [],
        "unmapped": [],
        "written": False,
        "errors": [],
    }

    try:
        parsed = parse_parameters(script_path)
    except OSError as e:
        report["errors"].append(f"Cannot read script '{script_path}': {e}")
        return report
    except SyntaxError as e:
        report["errors"].append(f"Cannot parse script '{script_path}' as Python: {e}")
        return report

    try:
        with open(plan_path, encoding="utf-8") as f:
            plan = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        report["errors"].append(f"Cannot load plan '{plan_path}': {e}")
        return report

    try:
        diff = reconcile(parsed, plan, part_id)
    except KeyError:
        report["errors"].append(f"Part '{part_id}' is not present in plan '{plan_path}'")
        return report

    report["changed"] = diff["changed"]
    report["unchanged"] = diff["unchanged"]
    report["unmapped"] = diff["unmapped"]

    if not write or not diff["changed"]:
        return report

    updated_plan = _apply_changes(plan, part_id, diff["changed"])

    fd, tmp_path = tempfile.mkstemp(suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(updated_plan, f)
        validation_errors = validate_plan(tmp_path)
    finally:
        os.remove(tmp_path)

    if validation_errors:
        report["errors"] = validation_errors
        return report

    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(updated_plan, f, indent=2, ensure_ascii=False)
        f.write("\n")
    report["written"] = True
    return report


def _cmd_validate(args: argparse.Namespace) -> int:
    errors = validate_plan(args.plan, args.inventory, args.archetypes)
    if errors:
        print(f"BUILD_PLAN validation FAILED ({len(errors)} error(s)):")
        for e in errors:
            print(f"  - {e}")
        return 1

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

    shared = check_shared_interfaces(plan)
    if shared:
        print(f"\nShared-interface findings ({len(shared)}):")
        for f in shared:
            print(f"  - {f}")

    coordinate_frame = check_coordinate_frame_usage(plan)
    if coordinate_frame:
        print(f"\nCoordinate-frame findings ({len(coordinate_frame)}):")
        for f in coordinate_frame:
            print(f"  - {f}")

    hinge_intent = check_hinge_intent_without_joints(plan)
    if hinge_intent:
        print(f"\nHinge-intent findings ({len(hinge_intent)}):")
        for f in hinge_intent:
            print(f"  - {f}")

    rationale = check_engineering_rationale(plan)
    if rationale:
        label = "error" if args.require_rationale else "advisory"
        print(f"\nEngineering-rationale findings ({len(rationale)}, {label}):")
        for f in rationale:
            print(f"  - {f}")
        if args.require_rationale:
            return 1

    load_anchors = check_load_case_anchors(plan)
    if load_anchors:
        print(f"\nLoad-case anchor findings ({len(load_anchors)}, advisory):")
        for f in load_anchors:
            print(f"  - {f}")
    return 0


def _cmd_summary(args: argparse.Namespace) -> int:
    path = Path(args.plan)
    print(summarize(json.loads(path.read_text(encoding="utf-8")), path))
    return 0


def _cmd_import_params(args: argparse.Namespace) -> int:
    report = run(args.script, args.part, args.plan, args.write)
    print(json.dumps(report, indent=2))
    return 1 if report["errors"] else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    vp = sub.add_parser("validate", help="Validate BUILD_PLAN.json")
    vp.add_argument("plan", help="Path to BUILD_PLAN.json")
    vp.add_argument("--inventory", default=_INVENTORY_PATH, help="Path to blocks/inventory.json")
    vp.add_argument(
        "--archetypes", default=_ARCHETYPES_PATH, help="Path to templates/archetypes.json"
    )
    vp.add_argument(
        "--require-rationale",
        action="store_true",
        help=(
            "Treat engineering_rationale findings as errors (exit 1). Use at the Phase 3 "
            "pre-export run, once every part has been authored; the Phase 2 run omits "
            "this flag since no part has a rationale yet."
        ),
    )
    vp.set_defaults(func=_cmd_validate)

    sp = sub.add_parser("summary", help="Render the Phase 2 checkpoint tables as Markdown")
    sp.add_argument("plan", help="Path to BUILD_PLAN.json")
    sp.set_defaults(func=_cmd_summary)

    ip = sub.add_parser(
        "import-params", help="Reconcile a part script's PARAMETERS block into BUILD_PLAN.json"
    )
    ip.add_argument("script", help="Path to the part .py script")
    ip.add_argument("--part", required=True, help="Part id in the plan")
    ip.add_argument("--plan", default="BUILD_PLAN.json", help="Path to BUILD_PLAN.json")
    ip.add_argument("--write", action="store_true", help="Persist the reconciled plan")
    ip.set_defaults(func=_cmd_import_params)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
