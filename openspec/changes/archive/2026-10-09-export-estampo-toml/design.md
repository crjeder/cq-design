## Context

`deliverables.write_deliverables` writes 3MF, STL and extra per-union formats from `_REGISTRY`; `build_template.py` passes `--formats` through. `profile.json` already holds `motion.layer_height_mm`, `motion.infill_density` and a `slicer` block (`preferred_format`, `slicer_name`). estampo 0.4.x reads a TOML with `[[parts]]` (file, copies, filament, orient/rotate), `[plate]`, `[slicer]`, `[slicer.orca]` (printer, process, filaments) and `[slicer.orca.overrides]`. Its config reference (docs/config.md) was not read; the keys above come from the README/PyPI page.

## Goals / Non-Goals

**Goals:**
- Emit a committable `estampo.toml` that slices the delivered STLs with the profile's layer height and infill.
- Keep generation pure text so the builder is testable without CadQuery.

**Non-Goals:**
- Plate packing or nesting (estampo's job; the cq-design item was rejected for that reason).
- Running or validating with estampo, pinning profiles, CI slicing.
- Guessing Orca printer/process/filament profile names.
- Engines other than `orca`.

## Decisions

- **Not an exporter-registry entry.** `_REGISTRY` exporters are per-union geometry writers; this file is whole-model text. Add `write_estampo_toml(plan, profile, stl_files, out_dir)` in a new `src/estampo_export.py`, called from `write_deliverables`, which forces `stl` when `estampo` is requested. Registry plugin rejected: wrong signature.
- **Hand-built TOML strings.** Output is flat scalars and arrays of tables; no TOML writer dependency. Tests assert on strings (tomllib is absent on Python 3.10).
- **Overrides are an allowlist** (layer_height, sparse_infill_density today), each emitted only when its source value exists; wall_loops, enable_support and brim_type are valid estampo keys but have no source data. Mirrors the slicer-copilot guardrail pattern in related_projects.md.
- **Profile names via optional `profile.json` `slicer.estampo`** (`engine`, `printer`, `process`, `filaments`); the schema block uses `additionalProperties: false`.
- **`rotate = [0, 0, 0]` on every part**: estampo defaults `orient` to "flat"; `rotate` overrides it, keeping our print pose.
- **No `[plate]` or `[pipeline]` section**, leaving estampo defaults; bed size is not in profile.json.

## Risks / Trade-offs

- estampo config is unstable between minor versions -> header comment naming the targeted version; minimal key set.
- Unread config reference may mean a wrong key name (e.g. the layer height override) -> task 1.1 verifies keys against docs/config.md first.
- Wall loops, support and brim may not exist in the plan -> omit, never default (the spec requires this).

## Open Questions

None. Resolved: the plan has no wall/support/brim data, and copies each have their own union STL.
