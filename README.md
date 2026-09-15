# CAD Skill for Claude Code

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill for generating parametric 3D-printable models using [CadQuery](https://cadquery.readthedocs.io/). Describe a physical object, and Claude will write a parametric script, export STL, render previews, and iterate with you until it's right.


## Usage

Once installed, the skill activates in two ways inside Claude Code:

- **Auto-trigger.** Describe a part you want to print ("design a wall mount for an Arduino Uno", "I need a snap-fit lid for this box") and Claude picks up the skill from its trigger keywords (3D print, STL, CadQuery, enclosure, bracket, and so on).
- **Explicit slash command.** Type `/cq-design` to invoke it directly, useful when your request does not contain the obvious keywords.

Claude will then walk you through requirements, build the model in phases (base shape, features, finish), and deliver an STL plus a rendered preview.

The first time the skill runs in a working directory it seeds that directory's
`.claude/settings.local.json` with the permission patterns its pipeline commands need
(the `uv run`/`python`/`uv sync` calls, build-file copies, and dimension-lookup web
searches), so you are not prompted for each step. The merge is additive and only happens
once per directory; ask Claude to "init permissions" to re-seed after updating the skill.

## Setup

Install [uv](https://docs.astral.sh/uv/), then run the installer from the repo
root. It copies the skill into the Claude Code personal skills directory
(`~/.claude/skills/cq-design/`) and provisions its Python environment:

```bash
# macOS / Linux
./install.sh

# Windows (PowerShell)
./install.ps1
```

Options:

- `--link` / `-Link` symlinks the repo instead of copying, so your edits are
  picked up live (useful for development).
- `--uninstall` / `-Uninstall` removes the installed skill.
- `--dest <dir>` / `-Dest <dir>` (or the `CLAUDE_SKILLS_DIR` environment
  variable) installs to a different skills directory.

`uv` must be on your PATH; the installer stops with the install URL if it is
not. Python 3.12 is managed automatically. CadQuery requires Python 3.10-3.12;
uv enforces this constraint and downloads the right Python version if needed.

To work in the repo directly without installing, just run `uv sync`.

## Checking what's installed

A copy install can silently go stale -- edits to this repo don't reach
`~/.claude/skills/cq-design/` until you re-run the installer. Check what's
actually there:

```bash
python ~/.claude/skills/cq-design/src/skill_version.py
```

It reports the commit that was copied (or, for a `--link`/`-Link` install,
the live commit of the linked repo -- always current by construction). Pass
`--compare <path-to-this-repo>` to diff the installed commit against the
repo's current `HEAD`:

```bash
python ~/.claude/skills/cq-design/src/skill_version.py --compare .
```

Exits non-zero when the installed copy isn't confirmed up to date, so it
also works as a quick check in a script.

## Regenerating the 3MF / STL files

When the skill finishes it turns your working directory into a self-contained
[uv](https://docs.astral.sh/uv/) project: a `pyproject.toml`, `.python-version`, and
committed `uv.lock` at the root, plus a `build/` directory holding the per-part scripts,
`build.py`, `BUILD_PLAN.json`, `orientations.json` (when orientations were accepted), and
the bundled build tooling (`exporters/`, `blocks/`, `model_export.py`, and friends).
Everything needed to rebuild the model lives here -- the skill does not have to be
installed.

To rebuild the model files after hand-editing a part script, sync the environment once
and run `build.py` with uv instead of re-invoking the skill:

```bash
uv sync
uv run python build/build.py
```

`uv sync` downloads a compatible Python (3.10-3.12) and installs the pinned dependencies
(CadQuery, trimesh, ...); later runs reuse the synced `.venv`. The build regenerates
everything with each object in its print orientation and writes, to the output directory:

- `model.3mf` -- one named object per union, with plate metadata
- `<union-id>.stl` -- one assembled-pose STL per union
- `plate_<n>.stl` -- one fused STL per multi-union plate

`build.py` reuses `build/orientations.json` when present (so the plates match what
the skill delivered) and recomputes orientations otherwise. Override the defaults
when your layout differs:

```bash
uv run python build/build.py --plan BUILD_PLAN.json --parts-dir build --out build
```

## Regenerating the project with a fresh session

Alongside the model files, delivery writes `REGENERATE.md` at the project root: a
self-contained prompt that rebuilds the *design* from scratch, as opposed to `build.py`,
which rebuilds the *geometry* from the scripts you already have. Paste it into a new
session -- a better model, a newer version of this skill, a different skill -- when you
want the design re-derived rather than re-exported.

It carries what the plan's structured fields cannot be re-narrated from memory: the
approved intent (what is being built, in resolved terms), the verbatim request history
including every correction, `parameters.py` inlined whole so the measured real-world
numbers and their provenance travel along, the print target, and the previous parts and
joints -- labelled reference, so the new session is free to decompose the request
differently. Images cannot be inlined; the prompt lists the `sketches/` paths and asks you
to re-attach those files.

The skill rewrites the file on every delivery, so it always reflects the latest
corrections. To re-export it by hand after editing `BUILD_PLAN.json` (the script is
stdlib-only -- no `uv sync` needed):

```bash
python <skill-dir>/src/regen_prompt.py --plan BUILD_PLAN.json --out REGENERATE.md
```

Omit `--out` to print it to stdout.

## Files

```
SKILL.md                    # skill definition and workflow phases
CLAUDE.md                   # development guidance for the pipeline scripts
src/build_plan_schema.json  # JSON Schema draft-7 for BUILD_PLAN.json
src/printer_profile_schema.json      # JSON Schema draft-7 for printer_profile.json
src/printer_profile.default.json     # default printer_profile.json seeded into a fresh directory
pyproject.toml              # dependencies and project metadata (uv)

src/
  run_cadquery_model.py     # subprocess wrapper: runs a .py model, validates geometry, emits JSON
  run_model_shim.py         # runpy shim that auto-exports `result` to STL
  quality_gate.py           # DFM + in-process trimesh geometry/overhang analysis (no slicer required), fix rounds, print recipe
  plan_validate.py          # validates BUILD_PLAN.json against schema and block inventory
  printer_profile_validate.py # validates printer_profile.json and writes back field overrides
  measure_stl.py            # geometry feature extractor for reference STLs (trimesh + numpy)
  preview.py                # headless multi-view PNG renderer (CadQuery tessellation + matplotlib)
  render_preview.py         # subprocess entry point for preview.py
  mesh_io.py                # STL loader with watertightness validation (trimesh + numpy only)
  placement.py              # assembled-frame placement helper (cq Workplane + trimesh matrix)
  mate_chain.py             # derived pose along a `joints` mate chain from root_part
  units.py                  # part -> unions / keep-out-zone expansion shared by export/validate/checks
  model_export.py           # model-level export: named multi-object 3MF + per-union/plate/keep-out STL
  kinematic_check.py        # whole-model range-of-motion sweep (trimesh + python-fcl)
  plate_clearance_check.py  # whole-model co-plated union clearance check
  keep_out_check.py         # whole-model keep-out-zone check (trimesh + python-fcl)
  print_orientation.py      # auto-rotation optimizer for print orientation
  build_template.py         # build.py template copied into build/ to regenerate plates
  regen_prompt.py           # exports REGENERATE.md: a fresh-session prompt to re-derive the design
  cq_compat.py              # CadQuery/cq_warehouse compatibility shims
  init_permissions.py       # seeds .claude/settings.local.json with pipeline permissions
  skill_permissions.json    # permission patterns seeded by init_permissions.py
  skill_version.py          # reports/compares the installed commit -- see "Checking what's installed"

  project_template/
    pyproject.toml          # scaffolded into the working directory as a self-contained uv project
    .python-version         # pinned Python version for the scaffolded project

  blocks/
    __init__.py             # re-exports all blocks flat (import via `from blocks import <name>`)
    primitives.py           # fillet_box, hollow_box
    fasteners.py            # screw_boss, pcb_standoff, snap hooks, alignment pins
    connectors.py           # port_cutout, cable_slot, vent_grid, teardrop bore/post
    hardware.py             # cq_warehouse-backed fastener geometry (heat-set, screws, nuts, traps)
    joints.py               # dovetail, finger, mortise/tenon, dowel, ball, hinge, living-hinge, shadow-gap
    validate.py             # inventory loader and validator
    inventory.json          # machine-readable block descriptors
    inventory_schema.json   # JSON Schema for inventory.json

  exporters/
    __init__.py             # run_exporters(script, formats, output_dir)
    stl.py  step.py  threemf.py  threemf_multi.py  obj.py  iges.py  scad.py

prompts/
  planning.md               # planning phase prompt (outputs BUILD_PLAN.json)
  part.md                   # per-part code generation prompt

tests/
  test_run_wrapper.py       # integration tests for the subprocess wrapper
  test_blocks.py            # block geometry tests
  test_block_imports.py     # flat block-import contract (every inventory block flat-importable; no runtime injection)
  test_exporters.py         # exporter tests
  test_preview.py           # preview.py / render_preview.py tests
  test_thin_interfaces.py   # thin-wall detection tests
  test_plan_validate.py     # schema validation tests -- fast, no CadQuery
  test_mesh_io.py           # mesh loader tests
  test_placement.py         # placement helper tests
  test_units.py             # part -> unions / keep-out-zone expansion tests
  test_model_export.py      # model-level export tests
  test_mate_chain.py        # derived mate-chain pose tests
  test_kinematic_check.py   # kinematic sweep tests
  test_plate_clearance_check.py
  test_keep_out_check.py    # keep-out-zone check tests
  test_print_orientation.py
  test_printer_profile_validate.py
  test_build_script.py
  test_gate_plan_validation.py
  test_quality_gate.py
  test_init_permissions.py
  test_cq_compat.py
  test_hardware_lazy_import.py
  test_cq_warehouse_integration.py
  test_stl_to_3mf.py
```

## Related projects
Projects surveyed for ideas -- see [`info/related_projects.md`](documentation/related_projects.md).
Adoption status/tracking lives in `TODO.md`.

## Part Libraries
Libraries which could be usefull are in [`Block_Sources.md`](documentation/Block_Sources.md)

## Software Bill of Materials
Third-party dependencies and credit for code/ideas adapted from other
projects -- see [`SBOM.md`](documentation/SBOM.md).

## License

The skill and scripts are licensed under the [PolyForm Noncommercial License 1.0.0](LICENSE). Free to use, modify, and distribute for noncommercial purposes.
