## Why

A finished cq-design model stops at STL/3MF; the user then re-enters layer height, infill, wall count and brim in a slicer by hand. [estampo](https://github.com/estampo/estampo) (Apache-2.0, beta) is a TOML-driven wrapper around OrcaSlicer/CuraEngine that reproduces a slice from a committed config. Emitting an `estampo.toml` is a cheap way to deliver the "calculate and export slicer parameters" backlog item (TODO.md) without bundling a slicer or reopening the rejected plate-nesting item (estampo packs plates itself).

## What Changes

- Add an `estampo` delivery format: `build.py --formats estampo` writes `estampo.toml` next to the other deliverables.
- `[[parts]]` is generated from the plan: one entry per union STL (or per plate STL for multi-union plates), `copies` from the plan's copy count, `orient` omitted because STLs are already written in print pose.
- `[slicer.<engine>.overrides]` is generated from `profile.json` (`layer_height_mm`, `infill_density`, nozzle) and from per-part plan data where it exists (wall loops, support, brim).
- Printer/process/filament profile names are NOT guessed; they are written as commented placeholders unless `profile.json` `slicer` block supplies them.
- No dependency on estampo at runtime; the file is plain TOML text and is never validated by running estampo.

## Capabilities

### New Capabilities
- `estampo-export`: generation of `estampo.toml` from BUILD_PLAN.json and profile.json.

### Modified Capabilities
- `build-script`: the selectable `--formats` keys gain `estampo`.

## Impact

- `src/deliverables.py` (format registry and writer), `src/build_template.py` (format flag passthrough), `src/profile.default.json` and `src/printer_profile_schema.json` (optional `slicer.estampo` keys: engine, printer, process, filament).
- New tests in `tests/` (fast, no CadQuery for the TOML builder).
- `documentation/related_projects.md` estampo row updated to point at this change; TODO.md slicer-parameters item partially covered.
- Risk: estampo config format is documented as unstable between minor versions and its config reference was not fully read; target the 0.4.x keys and pin the version in the design.
