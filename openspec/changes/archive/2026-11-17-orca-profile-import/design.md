## Context

`profile.json` is seeded from `src/profile.default.json` and edited by hand
(`printer_profile_validate.py --set`). Orca-family slicers (OrcaSlicer, Snapmaker Orca,
Bambu Studio) already hold most of these values as JSON presets:

- System presets: `<data_dir>/system/<vendor>/{machine,process,filament}/*.json`
- User presets: `<data_dir>/user/<user_id>/{machine,process,filament}/*.json`
- Every preset may carry `inherits: "<parent name>"`; user presets are deltas (a user
  filament on the dev machine held 4 keys). Values are strings or lists of strings
  (`"5%"`, `["0.4","0.4","0.4","0.4"]`).
- `<data_dir>/<App>.conf` begins with a JSON object whose `presets.machine` is the
  currently selected printer (verified on Snapmaker Orca 2.4); the selected process and
  filaments were `null` there, so they cannot be relied on.

Verified on the dev machine: the U1 machine chain is 4 files deep, a user process 5 deep,
a user filament 5 deep (crossing into `system/OrcaFilamentLibrary`).

## Goals / Non-Goals

**Goals:**
- Fill Orca-sourced `profile.json` fields with no hand-copying.
- Keep the profile usable without Orca (CI, evals, shared projects).
- Detect drift between the snapshot and the Orca presets.
- Pick a process preset by print purpose and say why; allow override.

**Non-Goals:**
- PrusaSlicer / SuperSlicer `.ini` bundles, Cura.
- Calibration values (fit clearance, tolerance, bridge length, hole compensation): no
  Orca source exists.
- A build-volume gate check (review item #1); this change only records the volume.
- Per-filament density/strength overrides of `material_properties.json`.
- Writing back into Orca presets.

## Decisions

### D1. One script, four subcommands

`src/orca_profile.py {discover,import,select-process,check}`, JSON on stdout like the
other `src/` tools. `import` and `select-process --write` edit `profile.json` and
re-validate it through `printer_profile_validate`'s existing validator.

### D2. Discovery

Candidate dirs per OS: Windows `%APPDATA%`, macOS `~/Library/Application Support`,
Linux `~/.config`, each joined with `OrcaSlicer`, `Snapmaker_Orca`, `BambuStudio`.
`--data-dir` overrides. A dir counts when it has `system/`. With several found,
`discover` lists them all and `import` requires `--data-dir` (the command prompt asks
the user); with one, it is used. The machine preset is `--machine` or the conf's
`presets.machine`.

Alternative: ask the user to export a bundle from Orca. Rejected: extra manual step, and
the bundle loses the user/system link needed for sync.

### D3. Inheritance resolution

Index every `*.json` under `system/*/<kind>/` and `user/*/<kind>/` (recursive) by its
`name` field; user presets shadow system presets of the same name. Merge child over
parent until `inherits` is empty. A missing parent or a cycle is a typed error naming the
chain so far. The digest is sha256 over the resolved chain files' bytes for machine,
process and every filament, in chain order.

### D4. Field mapping

| profile.json | Orca (resolved) | Rule |
|---|---|---|
| `printer` | machine `printer_model` | fallback machine `name` |
| `nozzle_mm` | machine `nozzle_diameter[0]` | must be in schema enum, else error |
| `max_materials` | `--max-materials N`, else `len(nozzle_diameter)` when > 1 | otherwise unchanged (AMS is not in presets; init asks) |
| `material` | filament[0] `filament_type` | base-type map below |
| `build_volume_mm` | `printable_area` bbox, `printable_height` | x/y = polygon extent |
| `constraints.overhang_max_deg` | process `support_threshold_angle` | `90 - t` when `t > 0`; `t == 0` (auto) leaves the field |
| `constraints.top_bottom_layers` | `min(top_shell_layers, bottom_shell_layers)` | min = thinnest skin for FEM |
| `motion.layer_height_mm` | `layer_height` | |
| `motion.line_width_mm` | `outer_wall_line_width`, fallback `line_width` | `"N%"` = N/100 x nozzle |
| `motion.infill_density` | `sparse_infill_density` | `"15%"` -> 0.15 |
| `motion.accel_mm_s2` | `outer_wall_acceleration[0]`, fallback `default_acceleration[0]` | 0 means "use default" |
| `motion.v_cruise_mm_s` | `min(outer_wall_speed[0], mvs / (layer_height x line_width))` | `mvs` = filament `filament_max_volumetric_speed[0]` |
| `motion.min_layer_time_s` | filament[0] `slow_down_layer_time[0]` | |
| `motion.junction_deviation_mm` | machine `machine_max_junction_deviation[0]` if > 0; else Klipper: `scv^2 x (sqrt(2)-1) / accel` with `scv = machine_max_jerk_x[0]` | none derivable -> omit the whole `motion` block (advisor skips, per existing spec) |
| `slicer.slicer_name` | data dir app name | |
| `slicer.estampo.{printer,process,filaments}` | preset names | |

Base-type map for `material`: strip a `-CF`/`-GF`/`+`/`-HS`-style suffix and match the
schema enum (`PLA`, `PETG`, `ABS`, `ASA`, `TPU`, `PA`; `PA6`/`PA12`/`PAHT` -> `PA`; `PCTG`
-> `PETG`). Unmapped (e.g. `PVA`, `CoPE`) is a typed `unmapped_material` error with the raw
type; the command asks the user and passes `--material`.

Fields the import never writes: `fit_clearance_mm`, `constraints.wall_min_mm`,
`constraints.dimension_tolerance_mm`, `constraints.bridge_max_mm`,
`constraints.interface_min_area_mm2`, `slicer.preferred_format`.

`import` also reports (does not store) slicer-side compensation that would double up
with model-side compensation: `xy_hole_compensation`, `xy_contour_compensation`,
`elefant_foot_compensation`, `filament_shrink` != 100%.

### D5. The `orca` block (hybrid)

```json
"orca": {
  "app": "Snapmaker_Orca",
  "data_dir": "C:/Users/.../Snapmaker_Orca",
  "machine": "Snapmaker U1 (0.4 nozzle)",
  "process": "0.16mm Standard @Snapmaker U1 (0.4 nozzle)",
  "process_purpose": "visual",
  "filaments": ["Jayo PETG"],
  "processes": [
    {"name": "0.16mm Standard @Snapmaker U1 (0.4 nozzle)", "layer_height_mm": 0.16,
     "wall_loops": 2, "infill_density": 0.15, "user": false}
  ],
  "digest": "sha256:..."
}
```

`processes` lists every process preset compatible with the machine (D6), resolved, so the
planner (which receives the whole profile in its prompt) can choose from it. Other
consumers keep reading the plain fields. `check`
re-resolves and compares the digest: `fresh`, `stale` (lists changed fields), or
`unavailable` (data dir or a preset missing; not an error, the snapshot still works).

Alternative: names only, resolve at every use. Rejected: every tool would need Orca on
the machine. Alternative: snapshot only. Rejected: no drift detection.

### D6. Process selection

Candidates are process presets whose resolved `compatible_printers` contains the machine
name; an empty list counts as compatible only for user presets. Target layer height per
purpose as a fraction of nozzle diameter:

| purpose | target | tie-break |
|---|---|---|
| `visual` | 0.40 x nozzle | more `wall_loops` |
| `functional` | 0.50 x nozzle | more `wall_loops` |
| `draft` | 0.70 x nozzle | larger layer |

Pick the candidate with the smallest `|layer_height - target|`; then the tie-break; then a
user preset over a system preset; then a name containing "Standard" (on the U1, "0.20mm
High Quality" otherwise beat "0.20mm Standard" alphabetically at a third of the speed);
then name order. The reason string names the preset,
layer height and purpose. `--process "<name>"` bypasses the ranking; with `--purpose` it
records that purpose (planner choice), without it records `user` and the reason says
"chosen by user". The fractions are module constants (calibration knob).

Selection writes the process-derived fields (D4 rows from process, plus `motion` fields
whose formula uses the process) and `orca.process` / `orca.process_purpose`. This is the
existing "per-model overrides persist as the project default" behavior.

Where it runs: init ranks with `functional` (Orca's own selection is not reliably in
the conf). In Phase 2 the planner judges the request's purpose and picks a preset from
`orca.processes` (it can weigh walls and infill against the part's load, which a
layer-height rank cannot), recording it as a planning note
`PROCESS: <name> | <purpose> | <why>`. Unless `orca.process_purpose` is `user`, the main
session applies a differing choice with `select-process --process "<name>" --purpose <p>
--write` and shows the reason line in the plan summary. The user overrides at plan
approval by naming a preset (applied without `--purpose`).

Alternative: rank only, no planner choice. Rejected: the rank sees layer height only.

### D7. Commands

- `/cq-design:init`: if `profile.json` was seeded in this run and `discover` finds an
  install, run `import` (machine from conf, first compatible filament the user
  confirms or the machine's default filament, purpose `functional`) and show the summary
  including the process reason line and any compensation warnings. When the machine has
  one nozzle, init asks how many filament slots an AMS/MMU gives and passes
  `--max-materials N`. Idempotent: a pre-existing profile is left alone.
- `/cq-design:sync-profile [--machine M] [--process P] [--filament F ...]`: run
  `import` against the recorded names (or the given ones), print each changed field
  old -> new, write.
- `/cq-design:status`: add `orca_profile.py check` output.

## Risks / Trade-offs

- [Orca key names change between versions] -> Missing keys fall back as in D4 or leave
  the field untouched and list it under `skipped` in the JSON; tests pin a fixture tree.
- [Klipper SCV -> junction deviation formula is approximate] -> Applied only when no
  `machine_max_junction_deviation`; the derivation is named in the import output. Verify
  the formula against Klipper docs during implementation.
- [Filament choice is ambiguous: no reliable "selected filament"] -> Init asks the user
  to pick from the compatible filaments it lists, defaulting to the first one.
- [Import overwrites hand-edited Orca-sourced fields] -> Init imports only into a
  profile it just seeded; sync prints old -> new for every field before writing.
- [Paths contain the user's home dir] -> Stored only in local `profile.json`, never sent
  anywhere; `profile.json` is not part of `lib/` bundles.

## Migration Plan

Additive. Existing profiles validate unchanged and are never auto-imported (init imports
only into a profile it seeded in the same run). Users opt in with `/cq-design:sync-profile`. Rollback: delete the `orca` block.

## Open Questions

None.
