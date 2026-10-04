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
the skill delivered) and recomputes orientations otherwise. While building it prints `[k/N] <step> <id>` progress
lines to stdout (orientation, loading, stl, plate; each phase counted separately). Override the defaults
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

## Command-line reference

Claude calls these scripts during the pipeline; you can also run them by hand with
`uv run python <skill-dir>/src/<script>.py ...`. Every script supports `-h`/`--help`.
Required options are marked **(req)**. Exit codes and JSON output shapes are in
[`reference/scripts.md`](reference/scripts.md).

### Installers (`install.sh` / `install.ps1`)

| Option | Effect |
|---|---|
| `--link` / `-Link` | Symlink the repo instead of copying |
| `--uninstall` / `-Uninstall` | Remove the installed skill |
| `--dest <dir>` / `-Dest <dir>` | Install to another skills directory (or set `CLAUDE_SKILLS_DIR`) |

### Build and run

**`run_cadquery_model.py <script>`** runs a part script, validates the geometry, and emits the JSON contract.

| Option | Default | Effect |
|---|---|---|
| `--preview` | off | Render a multi-view preview PNG |
| `--views {iso,multi}` | `multi` | Preview layout |
| `--preview-dir DIR` | next to script | Preview output directory (needs `--preview`) |
| `--cross-sections` | off | Render cross-sections as separate files (needs `--preview`) |
| `--extra-section AXIS=MM` | none | Extra cross-section, e.g. `x=50`; repeatable |
| `--detail SPEC` | none | High-resolution detail view, `name=<feature>;center=x,y,z;size=<mm>[;section=<axis>=<pos>]`; repeatable |
| `--callout SPEC` | none | Numbered badge for a feature, `name=<feature>;center=x,y,z`; repeatable |
| `--unlocated-name NAME` | none | Legend entry for a feature with no known position; repeatable |
| `--strict` | off | Fail if an STL is not watertight or none was produced |
| `--timeout SEC` | 180 | Model run timeout |
| `--expected-dims W,D,H` | none | Expected bounding box in mm |
| `--dim-tolerance MM` | 1.0 | Tolerance for `--expected-dims` |
| `--wall-min MM` | 0 | Minimum wall thickness for the DFM check (0 skips it) |
| `--line-width MM` | 0.42 | Extrusion line width for the brittle thin-wall threshold |
| `--density G/CM3` | 1.24 | Filament density for the weight estimate (PLA) |
| `--material NAME` | `PLA` | Material label in the preview footer |
| `--deliver` | off | Run the exporters and populate `stl`/`stls` |
| `--formats LIST` | `stl` | Comma-separated formats for `--deliver` |
| `--output-dir DIR` | next to script | Output directory for `--deliver` |
| `--print-rotate FILE` | none | `print_orientation.py` JSON; sets the print pose for `blocks.print_up()` |
| `--attempts-log FILE` | none | Append this run's attempt record to an `attempts.jsonl` |
| `--model NAME` | none | Model name stored in the attempt record |

#### Export formats and STEP output

`--deliver --formats LIST` writes one file per format. Supported keys: `stl`, `step`, `3mf`, `obj`, `iges`, `scad`.

```bash
uv run python src/run_cadquery_model.py part.py --deliver --formats stl,step --output-dir out
```

- STEP is the exact B-rep (not a mesh), meant for editing in Fusion 360, FreeCAD and similar CAD tools. It is written as `<name>.step`.
- `<name>` is the script stem, or the union id for each union of a multi-union part (one file per union; keep-out zones are never exported).
- Files go to `--output-dir` (default: next to the script) and the JSON lists only the STL (`stls`) and 3MF (`threemfs`) paths; STEP files are on disk but not reported there.
- `build.py` / `model_export.py` always write `model.3mf` and STLs; add `--formats step` (also `obj`, `iges`, `scad`) to also write `<union-id>.step` per union, in the assembled pose, next to the STLs.
- `fem_check.py` takes a part's exported STEP file as its positional input.

**`render_preview.py`** (preview subprocess) takes `--script` **(req)**, `--output` **(req)**, `--views`, `--title`, `--subtitle`, `--density`, `--material`, `--cross-sections`, `--extra-section`, `--detail`, `--callout`, `--unlocated-name` with the same meaning as above. `preview.py --help-note` prints a usage note.

**`section_select.py <script>`** picks section planes through bore/boss axes: `--max N` (default 3), `--reserve AXIS=MM` (repeatable).

**`build_template.py`** (copied to `build/build.py`): `--plan` (default `<root>/BUILD_PLAN.json`), `--parts-dir` (default script dir), `--out` (default root; `model.3mf`), `--stl-out` (default `<root>/stl`), `--orientations` (default `orientations.json` in `--parts-dir`), `--formats` (comma-separated extra per-union formats: `step`, `obj`, `iges`, `scad`; default none).

**`model_export.py`**: `--plan` **(req)**, `--parts-dir` **(req)**, `--out` **(req)**, `--stl-out` (default: `--out`), `--orientations FILE` (part id to orientation JSON; deliverables are written in these poses), `--formats` (as for `build.py`).

**`export_standalone.py`**: `--parts-dir` (default `build`), `--out` (default `standalone`), `--parameters` (default `parameters.py`).

**`bundle_project.py [dir]`** and **`init_permissions.py [dir]`**: `dir` defaults to the current directory. `init_permissions.py --check` exits 0 if init already ran, 1 otherwise, and changes nothing.

### Quality gate and checks

**`quality_gate.py`**: `--script` **(req)**, `--plan` **(req)**, `--stl FILE`, `--model-3mf FILE`, `--stl-dir DIR` (default: next to `--script`), `--orientation FILE` (a `print_orientation.py` result), `--attempts-log FILE` (default `attempts.jsonl` next to `--script`), `--fix` (invoke `claude` to fix errors; default is report-only).

**`plan.py`** subcommands:

| Subcommand | Options |
|---|---|
| `validate <plan>` | `--inventory FILE`, `--archetypes FILE`, `--require-rationale` (engineering_rationale findings become errors; use at the Phase 3 pre-export run) |
| `summary <plan>` | none |
| `import-params <script>` | `--part ID` **(req)**, `--plan FILE` (default `BUILD_PLAN.json`), `--write` (persist the reconciled plan) |

**`script_lint.py <script>`**: AST pre-flight lint, no options.

**`edge_treatment_check.py`**: `--script` **(req)**, `--orientations FILE` (omit to classify in the authored frame).
**`feature_presence_check.py`**: `--script` **(req)**.
**`gridfinity_check.py`**: `--script` **(req)**, `--kind {auto,bin,baseplate}` (default `auto`), `--cells COLSxROWS` (default: read from the footprint).

**Whole-model checks** `kinematic_check.py`, `plate_clearance_check.py`, `keep_out_check.py` share `--plan` **(req)**, `--stl-dir` **(req)**, `--parts-dir` (detects STLs stale relative to their scripts; omit to skip). `kinematic_check.py` adds `--penetration-tol-mm3` (default 0.1) and `--inventory FILE`.

**`minimal_cutout_search.py <script>`**: `--param NAME` **(req)**, `--plan` **(req)**, `--part` **(req)**, `--joint-id` **(req)**, `--stl-dir` **(req)**, `--lo` **(req)** (bound that must still collide), `--hi` **(req)** (bound that must already clear), `--tolerance-mm` (0.1), `--margin-mm` (0.2), `--apply` (write the value back into the script).

### Orientation and advisors

**`print_orientation.py <stl>`**:

| Option | Default | Effect |
|---|---|---|
| `--overhang-max-deg` | 45 | Overhang angle above which support is needed |
| `--bridge-max-mm` | built-in | Longest span treated as a bridge |
| `--load x,y,z` | none | Principal load direction in the authored frame |
| `--load-type` | `tension` | `tension`, `bending`, `shear`, or `compression` |
| `--optimize-for` | `strength` | `strength`, `min_support`, `visual_quality`, `min_build_height`, or `min_print_time` |
| `--show-face x,y,z` | inferred | Cosmetic surface normal |
| `--source-script FILE` | none | Stamp the result with the script's provenance hash |
| `--fem-stress FILE` | none | `fem_check.py` result; strength = `1 - fi_p99` when status is `ok` |
| `--speed-model FILE` | none | `toolpath_speed.py --emit-candidates` result; enables `min_print_time` ordering |

**`toolpath_speed.py`**: `--script` **(req)**, `--stl FILE` (posed union STL; omit for authored-frame corner findings only), `--profile FILE` (default `profile.json` next to `--plan`), `--emit-candidates UNION` (per-candidate table for `--speed-model`; needs `--stl`).

**`fem_check.py <step>`**: `--plan` **(req)**, `--part` **(req)**, `--mesh-size MM` **(req)**, no default by design. Needs the `fem` dependency group.

**`printer_profile_validate.py <profile>`**: `--set KEY=VALUE` writes a field back, e.g. `nozzle_mm=0.6`, `constraints.overhang_max_deg=50`; repeatable.

### Measuring and comparing

**`measure_stl.py <stl>`**: `--min-radius MM` (1.0), `--min-area MM2` (5.0), `--thin-max MM` (2.0), `--line-width MM` (0.42).
**`diff_models.py <a> <b>`**: `--png FILE` (diff image), `--tol` (relative volume tolerance for "identical", default 1e-6).

### Prompts, logs, and housekeeping

**`render_prompt.py <kind>`**:

| Kind | Options |
|---|---|
| `builder` | `--plan` **(req)**, `--part` **(req)**, `--out`, `--override {autonomous,staged}`, `--attempts FILE` |
| `audit` | `--plan` **(req)**, `--part` **(req)**, `--out`, `--script` **(req)**, `--previews FILE...` **(req)** |
| `planning` | `--request-file` **(req)**, `--plan`, `--profile` (default `profile.json`), `--out` |
| `research` | `--targets-file` **(req)**, `--known-file`, `--out` |
| `sourcing` | `--request-file` **(req)**, `--out` |

**`log.py`**:

| Command | Arguments and options |
|---|---|
| `--hook` | Read a PostToolUse payload from stdin; append a base attempt record |
| `journal append <journal> <milestone> <text>` | `milestone` is `<phase>/<key>`, e.g. `phase3/part_accepted:lid` |
| `attempt append <file> [json]` | `--field KEY=VALUE` (JSON-parsed, repeatable) |
| `attempt audit-fail` | `--part` **(req)**, `--audit FILE` **(req)**, `--file` (default `build/attempts.jsonl`) |
| `request search <plan>` | `--query`, `--kind {initial,clarification,correction}`, `--level {functional,operation,parameter}`, `--target` |
| `request add <plan>` | `--kind {clarification,correction}` **(req)**, `--text` **(req)**, `--level`, `--target` (repeatable), `--reconciled`, `--snapshot-scripts DIR` |

**`session_cost.py`**: `--hook` (read the hook payload from stdin; update `./build/cost.json`), or `--transcript FILE`, `--out FILE`, `--session-id ID` (non-hook mode).
**`regen_prompt.py`**: `--plan` (default `BUILD_PLAN.json`), `--out` (default stdout).
**`skill_version.py`**: `--compare REPO`, `--json`.
**`convert_build123d.py`**: `--mapping` (print the build123d to CadQuery table as JSON), `--smoke-check FILE` (run a converted script through the wrapper).
**`blocks/validate.py`**: `--search KEYWORD` (find blocks mentioning a keyword).

## Files

```
SKILL.md                    # skill definition and workflow phases
CLAUDE.md                   # development guidance for the pipeline scripts
src/build_plan_schema.json  # JSON Schema draft-7 for BUILD_PLAN.json
src/printer_profile_schema.json      # JSON Schema draft-7 for profile.json
src/profile.default.json     # default profile.json seeded into a fresh directory
pyproject.toml              # dependencies and project metadata (uv)

src/
  run_cadquery_model.py     # subprocess wrapper: runs a .py model, validates geometry, emits JSON
  run_model_shim.py         # runpy shim that auto-exports `result` to STL
  quality_gate.py           # DFM + in-process trimesh geometry/overhang analysis (no slicer required), fix rounds, print recipe
  plan.py                   # validate / summary / import-params over BUILD_PLAN.json
  printer_profile_validate.py # validates profile.json and writes back field overrides
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
  test_plan.py              # plan validate/summary/import-params tests -- fast, no CadQuery
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
