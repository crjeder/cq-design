#!/usr/bin/env python3
"""Import OrcaSlicer-family presets (machine, process, filament) into profile.json.

Usage:
    python orca_profile.py discover
    python orca_profile.py import profile.json [--data-dir D] [--machine M] [--process P]
        [--purpose visual|functional|draft] [--filament F ...] [--material PLA]
        [--max-materials N]
    python orca_profile.py select-process profile.json (--purpose P | --process NAME
        [--purpose P]) [--write]
    python orca_profile.py check profile.json

Every subcommand prints one JSON object with `success` and `errors` (each `type`,
`message`, `hint`). Exit codes: 0 success (check: always 0), 1 failure.
"""

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

from printer_profile_validate import write_profile_fields

APPS = {
    "OrcaSlicer": "OrcaSlicer",
    "Snapmaker_Orca": "Snapmaker Orca",
    "BambuStudio": "Bambu Studio",
}
KINDS = ("machine", "process", "filament")
# ponytail: target layer height as a fraction of nozzle diameter; tune per printer if picks feel off
PURPOSE_LAYER_FRACTION = {"visual": 0.40, "functional": 0.50, "draft": 0.70}
PURPOSE_TEXT = {
    "visual": "visual quality",
    "functional": "functional strength",
    "draft": "a fast draft",
}
MATERIALS = ("PLA", "PETG", "ABS", "ASA", "TPU", "PA", "PC")
MATERIAL_ALIASES = {"PA6": "PA", "PA12": "PA", "PAHT": "PA", "PA66": "PA", "PCTG": "PETG"}
NEVER_WRITTEN = (
    "fit_clearance_mm",
    "constraints.wall_min_mm",
    "constraints.dimension_tolerance_mm",
    "constraints.bridge_max_mm",
    "constraints.interface_min_area_mm2",
    "slicer.preferred_format",
)
COMPENSATION_KEYS = ("xy_hole_compensation", "xy_contour_compensation", "elefant_foot_compensation")


class OrcaError(Exception):
    """Typed failure carried into the JSON `errors` list."""

    def __init__(self, type_: str, message: str, hint: str = "", **extra: Any):
        super().__init__(message)
        self.entry = {"type": type_, "message": message, "hint": hint, **extra}


def _config_root() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def _selected_machine(data_dir: Path) -> str | None:
    conf = data_dir / f"{data_dir.name}.conf"
    if not conf.is_file():
        return None
    try:
        head, _ = json.JSONDecoder().raw_decode(conf.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return (head.get("presets") or {}).get("machine")


def discover(root: Path | None = None) -> list[dict]:
    """List Orca-family data dirs under the OS config root."""
    root = root or _config_root()
    found = []
    for app in APPS:
        d = root / app
        if (d / "system").is_dir():
            found.append({"app": app, "data_dir": d.as_posix(), "machine": _selected_machine(d)})
    return found


def _app_of(data_dir: Path) -> str:
    if data_dir.name not in APPS:
        raise OrcaError(
            "unknown_app",
            f"{data_dir} is not an Orca-family data dir",
            f"Expected one of {list(APPS)}",
        )
    return data_dir.name


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_index(data_dir: Path) -> dict[str, dict[str, tuple[Path, dict, bool]]]:
    """Map kind -> preset name -> (file, raw preset, is_user); user shadows system."""
    index: dict[str, dict[str, tuple[Path, dict, bool]]] = {k: {} for k in KINDS}
    for is_user, top in ((False, "system"), (True, "user")):
        for kind in KINDS:
            for path in sorted(data_dir.glob(f"{top}/*/{kind}/**/*.json")):
                try:
                    raw = _load(path)
                except (OSError, json.JSONDecodeError):
                    continue
                index[kind][raw.get("name", path.stem)] = (path, raw, is_user)
    return index


def resolve(index: dict, kind: str, name: str) -> tuple[dict, list[Path]]:
    """Merge a preset over its `inherits` chain; returns (merged, chain files child-first)."""
    merged: dict = {}
    chain: list[Path] = []
    seen: list[str] = []
    current: str | None = name
    while current:
        if current in seen:
            raise OrcaError(
                "inheritance_cycle", f"{kind} '{name}' inherits in a cycle: {seen + [current]}"
            )
        if current not in index[kind]:
            if not seen:
                raise OrcaError("unknown_preset", f"No {kind} preset named '{name}'")
            raise OrcaError(
                "missing_parent",
                f"{kind} '{seen[-1]}' inherits '{current}', which does not exist",
                chain=seen,
            )
        seen.append(current)
        path, raw, _ = index[kind][current]
        chain.append(path)
        merged = {**raw, **merged}
        current = raw.get("inherits") or None
    return merged, chain


def _first(value: Any) -> Any:
    return value[0] if isinstance(value, list) and value else value


def _num(value: Any, scale: float = 1.0) -> float | None:
    """Orca value (string or list of strings) -> float; 'N%' is N/100 x `scale`."""
    v = _first(value)
    if v is None or v == "":
        return None
    s = str(v).strip()
    if s.endswith("%"):
        return float(s[:-1]) / 100 * scale
    return float(s)


def _base_material(filament_type: str) -> str | None:
    token = filament_type.upper().replace("+", "-").replace(" ", "-").split("-")[0]
    token = MATERIAL_ALIASES.get(token, token)
    return token if token in MATERIALS else None


def _compatible(preset: dict, is_user: bool, machine: str) -> bool:
    printers = preset.get("compatible_printers") or []
    return machine in printers or (not printers and is_user)


def list_processes(index: dict, machine: str) -> tuple[list[dict], list[tuple[str, str]]]:
    """Every instantiable process compatible with `machine`, resolved; plus skip notes."""
    out, skipped = [], []
    for name, (_, raw, is_user) in sorted(index["process"].items()):
        if raw.get("instantiation") == "false":
            continue
        try:
            p, _ = resolve(index, "process", name)
        except OrcaError as e:
            skipped.append((name, e.entry["type"]))
            continue
        lh = _num(p.get("layer_height"))
        if not _compatible(p, is_user, machine) or not lh:
            continue
        out.append(
            {
                "name": name,
                "layer_height_mm": lh,
                "wall_loops": int(_num(p.get("wall_loops")) or 0),
                "infill_density": _num(p.get("sparse_infill_density")) or 0.0,
                "user": is_user,
            }
        )
    return out, skipped


def rank_process(processes: list[dict], purpose: str, nozzle: float) -> dict:
    """Pick the process whose layer height is closest to the purpose target."""
    target = PURPOSE_LAYER_FRACTION[purpose] * nozzle

    def key(p: dict) -> tuple:
        tie = -p["layer_height_mm"] if purpose == "draft" else -p["wall_loops"]
        standard = "standard" in p["name"].lower()
        delta = round(abs(p["layer_height_mm"] - target), 6)
        return (delta, tie, not p["user"], not standard, p["name"])

    return min(processes, key=key)


def reason_line(process: dict, purpose: str) -> str:
    """One-line explanation of the process choice for the user."""
    head = f"{process['name']} (layer {process['layer_height_mm']:g} mm)"
    if purpose == "user":
        return f"{head} chosen by user"
    return f"selected {head} for {PURPOSE_TEXT[purpose]}"


def _junction_deviation(machine: dict, accel: float) -> tuple[float | None, str]:
    jd = _num(machine.get("machine_max_junction_deviation"))
    if jd:
        return jd, "machine_max_junction_deviation"
    scv = _num(machine.get("machine_max_jerk_x"))
    if machine.get("gcode_flavor") == "klipper" and scv:
        # Klipper toolhead._calc_junction_deviation: scv^2 * (sqrt(2) - 1) / accel
        return scv**2 * (math.sqrt(2) - 1) / accel, "klipper square_corner_velocity"
    return None, ""


def _motion(machine: dict, process: dict, filament: dict, nozzle: float) -> tuple[dict | None, str]:
    lh = _num(process.get("layer_height"))
    lw = _num(process.get("outer_wall_line_width"), nozzle) or _num(
        process.get("line_width"), nozzle
    )
    accel = (
        _num(process.get("outer_wall_acceleration"))
        or _num(process.get("default_acceleration"))
        or _num(machine.get("machine_max_acceleration_extruding"))
    )
    speed = _num(process.get("outer_wall_speed"))
    layer_time = _num(filament.get("slow_down_layer_time"))
    infill = _num(process.get("sparse_infill_density"))
    if not (lh and lw and accel and speed and layer_time) or infill is None:
        return (
            None,
            "missing layer height, line width, acceleration, wall speed, infill or layer time",
        )
    jd, source = _junction_deviation(machine, accel)
    if not jd:
        return (
            None,
            "no machine_max_junction_deviation and no Klipper square-corner velocity",
        )
    mvs = _num(filament.get("filament_max_volumetric_speed"))
    if mvs:
        speed = min(speed, mvs / (lh * lw))
    motion = {
        "v_cruise_mm_s": round(speed, 1),
        "accel_mm_s2": accel,
        "junction_deviation_mm": round(jd, 4),
        "min_layer_time_s": layer_time,
        "layer_height_mm": lh,
        "line_width_mm": round(lw, 4),
        "infill_density": round(infill, 4),
    }
    return motion, f"junction deviation from {source}"


def _build_volume(machine: dict) -> dict | None:
    pts = [tuple(float(c) for c in s.split("x")) for s in machine.get("printable_area") or []]
    height = _num(machine.get("printable_height"))
    if not pts or not height:
        return None
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return {"x": round(max(xs) - min(xs), 2), "y": round(max(ys) - min(ys), 2), "z": height}


def _digest(chains: list[list[Path]]) -> str:
    h = hashlib.sha256()
    for chain in chains:
        for path in chain:
            h.update(path.read_bytes())
    return "sha256:" + h.hexdigest()


def _material(filament: dict, override: str | None) -> str:
    if override:
        return override
    raw = str(_first(filament.get("filament_type")) or "")
    base = _base_material(raw)
    if not base:
        raise OrcaError(
            "unmapped_material",
            f"Filament type '{raw}' has no profile material",
            f"Pass --material one of {list(MATERIALS)}",
            raw_type=raw,
        )
    return base


def _compensation(process: dict, filament: dict) -> list[str]:
    warnings = [f"{k} = {_num(process.get(k))}" for k in COMPENSATION_KEYS if _num(process.get(k))]
    for key in ("filament_shrink", "filament_shrinkage_compensation_z"):
        v = _num(filament.get(key))
        if v is not None and abs(v - 1.0) > 1e-9:
            warnings.append(f"{key} = {_first(filament.get(key))}")
    return warnings


def _filament_choices(index: dict, machine: str) -> dict:
    user: list[str] = []
    system: list[str] = []
    for name, (_, raw, is_user) in sorted(index["filament"].items()):
        if raw.get("instantiation") == "false":
            continue
        try:
            f, _ = resolve(index, "filament", name)
        except OrcaError:
            continue
        if _compatible(f, True, machine):
            (user if is_user else system).append(name)
    return {"user": user, "system": system}


def _pick_data_dir(arg: str | None, recorded: dict) -> Path:
    if arg:
        return Path(arg)
    if recorded.get("data_dir"):
        return Path(recorded["data_dir"])
    found = discover()
    if not found:
        raise OrcaError(
            "no_install",
            "No OrcaSlicer, Snapmaker Orca or Bambu Studio data dir found",
            "Pass --data-dir",
        )
    if len(found) > 1:
        raise OrcaError(
            "ambiguous_data_dir",
            "Several Orca-family installs found",
            "Pass --data-dir with one of them",
            candidates=[f["data_dir"] for f in found],
        )
    return Path(found[0]["data_dir"])


def _choose_process(
    processes: list[dict], args: argparse.Namespace, recorded: dict, nozzle: float
) -> tuple[dict, str]:
    by_name = {p["name"]: p for p in processes}
    if args.process:
        if args.process not in by_name:
            raise OrcaError(
                "incompatible_process",
                f"Process '{args.process}' is not a compatible preset for this machine",
                "Pick a name from orca.processes",
            )
        return by_name[args.process], args.purpose or "user"
    if not args.purpose and recorded.get("process") in by_name:
        return by_name[recorded["process"]], recorded["process_purpose"]
    purpose = args.purpose or recorded.get("process_purpose") or "functional"
    purpose = "functional" if purpose == "user" else purpose
    return rank_process(processes, purpose, nozzle), purpose


def compute(profile: dict, args: argparse.Namespace) -> dict:
    """Resolve presets and return the fields to write plus report data (no file I/O)."""
    recorded = profile.get("orca") or {}
    data_dir = _pick_data_dir(args.data_dir, recorded).resolve()
    app = _app_of(data_dir)
    index = build_index(data_dir)
    machine_name = args.machine or recorded.get("machine") or _selected_machine(data_dir)
    if not machine_name:
        raise OrcaError("machine_required", "No machine selected in Orca", "Pass --machine")
    machine, machine_chain = resolve(index, "machine", machine_name)
    nozzles = machine.get("nozzle_diameter") or []
    nozzle = _num(nozzles)
    if not nozzle:
        raise OrcaError("no_nozzle", f"Machine '{machine_name}' has no nozzle_diameter")
    filament_names = args.filament or recorded.get("filaments")
    if not filament_names:
        raise OrcaError(
            "filament_required",
            "Choose a filament preset",
            "Pass --filament <name>",
            choices=_filament_choices(index, machine_name),
        )
    filaments = [resolve(index, "filament", n) for n in filament_names]
    processes, skipped_processes = list_processes(index, machine_name)
    if not processes:
        raise OrcaError("no_process", f"No process preset is compatible with '{machine_name}'")
    chosen, purpose = _choose_process(processes, args, recorded, nozzle)
    process, process_chain = resolve(index, "process", chosen["name"])
    filament = filaments[0][0]

    fields: dict[str, Any] = {
        "printer": machine.get("printer_model") or machine_name,
        "nozzle_mm": nozzle,
        "material": _material(filament, args.material),
    }
    skipped: dict[str, str] = {f"orca.processes: {n}": t for n, t in skipped_processes}
    if args.max_materials:
        fields["max_materials"] = args.max_materials
    elif len(nozzles) > 1:
        fields["max_materials"] = len(nozzles)
    volume = _build_volume(machine)
    if volume:
        fields["build_volume_mm"] = volume
    threshold = _num(process.get("support_threshold_angle"))
    if threshold:
        fields["constraints.overhang_max_deg"] = 90 - threshold
    else:
        skipped["constraints.overhang_max_deg"] = "support_threshold_angle is 0 (auto)"
    top, bottom = _num(process.get("top_shell_layers")), _num(process.get("bottom_shell_layers"))
    if top and bottom:
        fields["constraints.top_bottom_layers"] = int(min(top, bottom))
    motion, note = _motion(machine, process, filament, nozzle)
    if motion:
        fields.update({f"motion.{k}": v for k, v in motion.items()})
    else:
        skipped["motion"] = note
    if "slicer" in profile:
        fields["slicer.slicer_name"] = APPS[app]
        fields["slicer.estampo"] = {
            "printer": machine_name,
            "process": chosen["name"],
            "filaments": filament_names,
        }
    else:
        skipped["slicer"] = "profile has no slicer block (needs preferred_format)"
    fields["orca"] = {
        "app": app,
        "data_dir": data_dir.as_posix(),
        "machine": machine_name,
        "process": chosen["name"],
        "process_purpose": purpose,
        "filaments": filament_names,
        "processes": processes,
        "digest": _digest([machine_chain, process_chain] + [c for _, c in filaments]),
    }
    return {
        "fields": fields,
        "skipped": skipped,
        "notes": [note] if motion else [],
        "compensation_warnings": _compensation(process, filament),
        "process_reason": reason_line(chosen, purpose),
    }


def _get(profile: dict, key: str) -> Any:
    group, _, sub = key.partition(".")
    return (profile.get(group) or {}).get(sub) if sub else profile.get(group)


def changed_fields(profile: dict, fields: dict) -> dict:
    """field -> {old, new} for every field whose value differs from the profile."""
    return {
        k: {"old": _get(profile, k), "new": v}
        for k, v in fields.items()
        if k != "orca" and _get(profile, k) != v
    }


def cmd_import(args: argparse.Namespace) -> dict:
    """Resolve presets and write the mapped fields into profile.json."""
    profile = _load(Path(args.profile))
    result = compute(profile, args)
    fields = result.pop("fields")
    assert not any(k.startswith(NEVER_WRITTEN) for k in fields)
    changed = changed_fields(profile, fields)
    errors = write_profile_fields(args.profile, fields)
    if errors:
        raise OrcaError(
            "invalid_profile", "; ".join(errors), "The imported values failed profile validation"
        )
    return {**result, "written": changed}


def cmd_select(args: argparse.Namespace) -> dict:
    """Choose a process (ranked by purpose, or named) and optionally write it."""
    profile = _load(Path(args.profile))
    if not profile.get("orca"):
        raise OrcaError(
            "not_imported", "profile.json has no orca block", "Run /cq-design:sync-profile first"
        )
    if not args.write:
        result = compute(profile, args)
        return {
            "process": result["fields"]["orca"]["process"],
            "process_reason": result["process_reason"],
        }
    result = cmd_import(args)
    return {"process": _load(Path(args.profile))["orca"]["process"], **result}


def cmd_check(args: argparse.Namespace) -> dict:
    """Compare the recorded Orca snapshot against the presets on disk."""
    profile = _load(Path(args.profile))
    orca = profile.get("orca")
    if not orca:
        return {"state": "not_imported"}
    if not Path(orca["data_dir"]).is_dir():
        return {"state": "unavailable", "reason": f"{orca['data_dir']} not found"}
    try:
        result = compute(profile, argparse.Namespace(**{**_EMPTY, "profile": args.profile}))
    except OrcaError as e:
        return {"state": "unavailable", "reason": e.entry["message"]}
    fields = result["fields"]
    if fields["orca"]["digest"] == orca["digest"]:
        return {"state": "fresh"}
    return {"state": "stale", "changed": changed_fields(profile, fields)}


_EMPTY = {
    "data_dir": None,
    "machine": None,
    "process": None,
    "purpose": None,
    "filament": None,
    "material": None,
    "max_materials": None,
    "write": False,
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import OrcaSlicer-family presets into profile.json"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("discover")
    for name in ("import", "select-process", "check"):
        p = sub.add_parser(name)
        p.add_argument("profile")
        if name == "check":
            continue
        p.add_argument("--data-dir")
        p.add_argument("--machine")
        p.add_argument("--process")
        p.add_argument("--purpose", choices=list(PURPOSE_LAYER_FRACTION))
        p.add_argument("--filament", action="append")
        p.add_argument("--material", choices=list(MATERIALS))
        p.add_argument("--max-materials", type=int)
        p.add_argument("--write", action="store_true")
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.cmd == "select-process" and not (args.purpose or args.process):
        _parser().error("select-process needs --purpose or --process")
    handlers = {
        "discover": lambda a: {"installs": discover()},
        "import": cmd_import,
        "select-process": cmd_select,
        "check": cmd_check,
    }
    try:
        out = {"success": True, "errors": [], **handlers[args.cmd](args)}
        code = 0
    except OrcaError as e:
        out = {"success": False, "errors": [e.entry]}
        code = 0 if args.cmd == "check" else 1
    print(json.dumps(out, indent=2))
    sys.exit(code)


if __name__ == "__main__":
    main()
