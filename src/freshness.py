#!/usr/bin/env python3
"""Provenance stamp: hash a part script, compare a recorded stamp against it.

A generated artifact (an orientation result, an exported STL) is only as current as the
part script that produced it. The stamp is a SHA-256 hex digest of the script's file
contents -- not mtime, which is noisy across checkouts, copies, and editors. Two carriers
build on the same primitive: an orientation result gains one `source_script_hash` key
(free-form, see `print_orientation.py`); the model export writes a dedicated sidecar
manifest (`write_manifest`/`read_manifest`) since an STL has no field of its own to stamp.

Stdlib only, no CadQuery import, so every consumer (including `plan_validate`-adjacent
tooling) can import it cheaply.
"""

import hashlib
import json
import os
from datetime import datetime, timezone

MANIFEST_FILENAME = "export_manifest.json"


def script_hash(script_path: str) -> str:
    """SHA-256 hex digest of a part script's file contents -- the provenance key."""
    with open(script_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def is_stale(stamped_hash: str | None, script_path: str) -> bool:
    """True when `stamped_hash` no longer matches the current hash of `script_path`.

    `stamped_hash` is None when the artifact carries no provenance stamp at all (produced
    before this mechanism existed, or without opting in) -- that is "unknown", not a known
    mismatch, so it returns False rather than flagging staleness.
    """
    if stamped_hash is None:
        return False
    return stamped_hash != script_hash(script_path)


def write_manifest(
    stl_dir: str,
    union_scripts: dict[str, tuple[str, str]],
    keep_out_scripts: dict[str, tuple[str, str]] | None = None,
    print_rotates: dict[str, list] | None = None,
) -> str:
    """Write the export manifest into `stl_dir`; return its path.

    `union_scripts` maps union id -> (part_id, script_path). `keep_out_scripts` maps
    "<part_id>::<zone_name>" -> (part_id, script_path), matching `export_model`'s
    `keep_out_stls` key convention. Each entry records the script's provenance stamp.
    """
    rotates = print_rotates or {}
    manifest = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "unions": {
            uid: {
                "part_id": pid,
                "script_part": os.path.splitext(os.path.basename(path))[0],
                "source_script_hash": script_hash(path),
                **({"print_rotate": rotates[uid]} if uid in rotates else {}),
            }
            for uid, (pid, path) in union_scripts.items()
        },
        "keep_out_zones": {
            key: {"part_id": pid, "source_script_hash": script_hash(path)}
            for key, (pid, path) in (keep_out_scripts or {}).items()
        },
    }
    path = os.path.join(stl_dir, MANIFEST_FILENAME)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    return path


def read_manifest(stl_dir: str) -> dict | None:
    """Read the export manifest from `stl_dir`, or None when it does not exist."""
    path = os.path.join(stl_dir, MANIFEST_FILENAME)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def script_stem(manifest_section: dict, uid: str, part_id: str | None) -> str:
    """Script stem behind a union: a `copy_of` part's manifest entry names its source
    script; otherwise (or with no entry) the owning part id."""
    return manifest_section.get(uid, {}).get("script_part") or str(part_id)


def stale_ids(manifest_section: dict, ids_to_scripts: dict[str, str]) -> set[str]:
    """Ids from `ids_to_scripts` (id -> current source script path) whose manifest entry
    is stale. `manifest_section` is a manifest's `"unions"` or `"keep_out_zones"` dict. An
    id absent from the manifest section is skipped (no provenance recorded for it, so
    nothing to compare -- distinct from a recorded-but-mismatching stamp)."""
    stale: set[str] = set()
    for entry_id, script_path in ids_to_scripts.items():
        entry = manifest_section.get(entry_id)
        if entry is None:
            continue
        if is_stale(entry.get("source_script_hash"), script_path):
            stale.add(entry_id)
    return stale


def pose_stale_ids(manifest_section: dict, rotates: dict[str, list | None]) -> set[str]:
    """Union ids whose export was finished under a different print pose than `rotates`
    (id -> the currently accepted `rotate`). An entry with no recorded `print_rotate` (the
    export ran without a finishing pose) is not judged, matching `is_stale`'s "unknown"."""
    return {
        uid
        for uid, rotate in rotates.items()
        if (entry := manifest_section.get(uid)) is not None
        and "print_rotate" in entry
        and entry["print_rotate"] != rotate
    }
