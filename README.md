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

## Files

```
SKILL.md                    # skill definition and workflow phases
CLAUDE.md                   # development guidance for the pipeline scripts
src/build_plan_schema.json  # JSON Schema draft-7 for BUILD_PLAN.json
pyproject.toml              # dependencies and project metadata (uv)

src/
  run_cadquery_model.py     # subprocess wrapper: runs a .py model, validates geometry, emits JSON
  run_model_shim.py         # runpy shim that auto-exports `result` to STL
  quality_gate.py           # DFM + in-process trimesh geometry/overhang analysis (no slicer required), fix rounds, print recipe
  plan_validate.py          # validates BUILD_PLAN.json against schema and block inventory
  measure_stl.py            # geometry feature extractor for reference STLs (trimesh + numpy)
  preview.py                # headless multi-view PNG renderer (CadQuery tessellation + matplotlib)
  render_preview.py         # subprocess entry point for preview.py
  mesh_io.py                # STL loader with watertightness validation (trimesh + numpy only)

  blocks/
    __init__.py             # re-exports all blocks
    primitives.py           # fillet_box, hollow_box
    fasteners.py            # screw_boss, pcb_standoff, snap hooks, alignment pins
    connectors.py           # port_cutout, cable_slot, vent_grid
    hardware.py             # cq_warehouse-backed fastener geometry
    joints.py               # dovetail groove and tongue for sliding joints
    validate.py             # inventory loader and validator
    inventory.json          # machine-readable block descriptors
    inventory_schema.json   # JSON Schema for inventory.json

  exporters/
    __init__.py             # run_exporters(script, formats, output_dir)
    stl.py  step.py  threemf.py  obj.py  iges.py  scad.py

prompts/
  planning.md               # planning phase prompt (outputs BUILD_PLAN.json)
  part.md                   # per-part code generation prompt
  assembly.md               # assembly phase prompt

tests/
  test_run_wrapper.py       # integration tests for the subprocess wrapper
  test_blocks.py            # block geometry tests
  test_exporters.py         # exporter tests
  test_preview.py           # preview.py / render_preview.py tests
  test_thin_interfaces.py   # thin-wall detection tests
  test_plan_validate.py     # schema validation tests -- fast, no CadQuery
  test_mesh_io.py           # mesh loader tests
  test_cq_warehouse_integration.py
  test_stl_to_3mf.py
```

## Prior art

Related projects surveyed for ideas. The "Relevant to" column notes what each one
informs in this skill; "high"/"medium"/"low" rates how directly its ideas apply.

| Project | What it is | Relevant to | Ideas worth adapting |
|---------|-----------|-------------|----------------------|
| [thereprocase/cad-skill](https://github.com/thereprocase/cad-skill) | Claude Code CadQuery skill with a phased checkpoint pipeline and DFM checks | high | Dimensioned cross-section rendering at critical features; `cq_debug_helpers.py` catching silent boolean failures / workplane drift; dual-layer (construction-time + post-export) validation |
| [vericontext/cadgate](https://github.com/vericontext/cadgate) | Quality gate / PR reviewer for AI-generated CadQuery / build123d | high | Differential geometry comparison (volume / bbox / wall-thickness delta vs base); optional LLM-judge intent match (geometry vs description); per-class exit codes for CI gating; sticky PR comments with 6-view renders |
| [jmwright/cadquery-llm-skill](https://github.com/jmwright/cadquery-llm-skill) | Maintainer-authored skill teaching LLMs idiomatic CadQuery | high | BRep-vs-CSG mindset, selector cheat sheet, anti-patterns; grep-friendly local doc snapshot -- upgrade material for `reference/` and `prompts/part.md` |
| [ChristophSchranz/Tweaker-3](https://github.com/ChristophSchranz/Tweaker-3) | Auto-rotation optimizer for 3D print orientation | high | Progressive overhang penalty (severity exponent `OV_H`); area-cumulation candidate generation; a build-height / volume minimization objective -- all for `print_orientation.py` and `mesh_io.overhang_metrics` |
| [CadQuery/cadquery-contrib mcp-server](https://github.com/CadQuery/cadquery-contrib/tree/master/mcp-server) | Official CadQuery MCP server (render / inspect / get_parameters / export) | medium | `get_parameters` style extraction of customizable script params for a parametric re-run UX (this skill avoids MCP by design) |
| [rishigundakaram/cad-query-workspace](https://github.com/rishigundakaram/cad-query-workspace) | MCP-driven conversational CadQuery workspace | low | Searchable API-docs layer + few-shot examples folder (this skill's `reference/` already covers it); validates the inline-vs-MCP choice |
| [rundiwu/DeepCAD](https://github.com/rundiwu/DeepCAD) | ML model representing CAD as sketch+extrude command sequences | low | Chamfer distance as a mesh-vs-reference similarity metric for golden-mesh regression tests (skip the ML pipeline) |
| [CodeGraphContext/CodeGraphContext](https://github.com/CodeGraphContext/CodeGraphContext) | Code knowledge-graph MCP server / CLI | low | Repo navigation and impact analysis during development; not part of the CAD pipeline |
| [Aryo-Zare/cq](https://github.com/Aryo-Zare/cq) | Early-stage single-part CadQuery example | low | Nothing actionable (one file, no docs) |

## License

The skill and scripts are licensed under the [PolyForm Noncommercial License 1.0.0](LICENSE). Free to use, modify, and distribute for noncommercial purposes.
