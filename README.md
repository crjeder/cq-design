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
  cq_compat.py              # CadQuery/cq_warehouse compatibility shims
  init_permissions.py       # seeds .claude/settings.local.json with pipeline permissions
  skill_permissions.json    # permission patterns seeded by init_permissions.py

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

## Prior art

Related projects surveyed for ideas, sorted by relevance. The "Relevance" column
rates how directly each one's ideas apply to this skill: "high"/"medium"/"low".

| Project | What it is | Relevance | Ideas worth adapting |
|---------|-----------|-------------|----------------------|
| [thereprocase/cad-skill](https://github.com/thereprocase/cad-skill) | Claude Code CadQuery skill with a phased checkpoint pipeline and DFM checks | high | Dimensioned cross-section rendering at critical features; `cq_debug_helpers.py` catching silent boolean failures / workplane drift; dual-layer (construction-time + post-export) validation |
| [vericontext/cadgate](https://github.com/vericontext/cadgate) | Quality gate / PR reviewer for AI-generated CadQuery / build123d | high | Differential geometry comparison (volume / bbox / wall-thickness delta vs base); optional LLM-judge intent match (geometry vs description); per-class exit codes for CI gating; sticky PR comments with 6-view renders |
| [jmwright/cadquery-llm-skill](https://github.com/jmwright/cadquery-llm-skill) | Maintainer-authored skill teaching LLMs idiomatic CadQuery | high | BRep-vs-CSG mindset, selector cheat sheet, anti-patterns; grep-friendly local doc snapshot -- upgrade material for `reference/` and `prompts/part.md` |
| [ChristophSchranz/Tweaker-3](https://github.com/ChristophSchranz/Tweaker-3) | Auto-rotation optimizer for 3D print orientation | high | Progressive overhang penalty (severity exponent `OV_H`); area-cumulation candidate generation; a build-height / volume minimization objective -- all for `print_orientation.py` and `mesh_io.overhang_metrics` |
| [Text-to-CadQuery (arXiv 2505.06507 + code)](https://github.com/Text-to-CadQuery) | Research generating CadQuery code directly (not command sequences); ~170k text->CadQuery pairs, finetuned 124M-7B models | high | Chamfer distance as mesh-vs-reference regression metric; render-then-VLM-judge eval (Gemini visual assessment); validates this skill's direct-CadQuery-codegen design over intermediate B-rep command sequences |
| [cyberchitta/cad-khana](https://github.com/cyberchitta/cad-khana) | build123d CLI / agent skill with a diagnostics-first (not vision-first) loop | high | Assertions-as-constraints that fail the build when geometry is out of spec; `diagnostics.json` of interferences / clearances / wall thickness / overhangs (parallels `quality_gate` + `measure_stl`); HLR orthographic line-art drawings for shape questions renders can't answer |
| [jacksonferrigno/cad-llm](https://github.com/jacksonferrigno/cad-llm) | Local desktop app: NL -> CadQuery code -> 3D preview / STEP, Qwen 4B via MLX, sandbox-and-self-correct loop | high | Explicit exploratory-prompt vs build-prompt routing (clarify/options vs straight to code), mirroring this skill's planning -> part loop; sandbox-execute-read-error-retry loop; on-device model option |
| [Rahix/FusedFilamentDesign](https://github.com/Rahix/FusedFilamentDesign) | FreeCAD PartDesign addon of parametric FDM design-for-printing features | high | Concrete printable-feature blocks and DFM rules: teardrop horizontal holes, counterbore/roof bridges for overhang-free holes, thread-forming ribs, zip-tie channels, auto-fillet on vertical edges -- upgrade material for `blocks/` and the DFM gate |
| [partcad/partcad](https://github.com/partcad/partcad) | Package manager for hardware / manufacturable products across CAD kernels (CadQuery, build123d, OpenSCAD), YAML assembly format, BOM, AI-assisted workflows | high | Package-manager framing for reusable, versioned part definitions with declared metadata (parallels `blocks/inventory.json`); YAML assembly format tracking BOM and part relationships across CAD kernels; caching rendered models to speed iteration |
| [r3c0nshade/CADForge](https://github.com/r3c0nshade/CADForge) | Prompt-to-CAD web app: multi-provider LLM (Claude / GPT / GLM / NVIDIA / Ollama) writes CadQuery, sandboxed execution, Three.js preview, STEP/STL/OBJ/DXF export | high | Automatic error-feedback self-correction pass on generation failure (parallels this skill's part loop); per-part version history across iterative edits; provider-agnostic LLM backend design |
| [CadQuery/cadquery-contrib mcp-server](https://github.com/CadQuery/cadquery-contrib/tree/master/mcp-server) | Official CadQuery MCP server (render / inspect / get_parameters / export) | medium | `get_parameters` style extraction of customizable script params for a parametric re-run UX (this skill avoids MCP by design) |
| [earthtojake/text-to-cad](https://github.com/earthtojake/text-to-cad) (forks: [cedrickchee](https://github.com/cedrickchee/text-to-cad), [costrict mirror](https://github.com/costrict-plugins-repo/earthtojake-text-to-cad-cad); web wrapper [CodeEagle/text-to-cad-web](https://github.com/CodeEagle/text-to-cad-web)) | build123d agent-skills library (CAD + URDF + G-code + DXF skills) for Claude / Codex | medium | Skill decomposition into CAD / slicing / URDF / DXF sub-skills; multi-format export pipeline (STEP / 3MF / GLB) beyond STL |
| [rawwerks/VibeCAD](https://github.com/rawwerks/VibeCAD) | build123d skills library plus render-glb and gltf-transform plugins | medium | IoU / Dice / precision-recall mesh metrics for AI-output regression; `bd_warehouse` fasteners and `gggears` parametric gears (parallel to `blocks/hardware`) |
| [lwidm/cq_gears](https://github.com/lwidm/cq_gears) | Parametric involute spur/helical gear generator for CadQuery (exact analytical curve equations, no boolean approximation) | medium | Fills the gap in `blocks/` for gear geometry; upstream declares no license, so it's referenced as a downloadable external resource in `planning_notes` rather than pinned or vendored |
| [outerreaches/talkcad](https://github.com/outerreaches/talkcad) | Conversational OpenSCAD Electron app with orchestrator/builder/researcher agents | medium | Spec tracking with explicit/inferred/default values plus per-spec verification status; web research for real-world dimensions; vision-based verification of rendered models |
| [lightoshadow/text-to-openscad](https://github.com/lightoshadow/text-to-openscad) | Claude Code plugin: plan -> write `.scad` -> render -> iterate up to N rounds | medium | Manifold genus / facet stats as a geometry sanity check; color-coded multi-part renders to spot clipping and gaps; standard multi-view grid (iso/top/front/right) |
| [rohittp0/ClaudeCAD](https://github.com/rohittp0/ClaudeCAD) | Claude Code + OpenSCAD plugin, Interview -> Design -> Code -> Validate -> Export | medium | `admesh` mesh-integrity validation as an export-time gate; explicit interview phase before modeling |
| [levkropp/ClawSCAD](https://github.com/levkropp/ClawSCAD) | Electron app gluing OpenSCAD + Claude Code via an OpenSCAD MCP subprocess | medium | Checkpoint branching (immutable model tree, revert + branch alternatives); auto error-feedback loop from render failures |
| [Masoudjafaripour/Vibe_CADing](https://github.com/Masoudjafaripour/Vibe_CADing) | Multi-agent generative pipeline: Planner / Retriever / Generator / Critic | medium | Critic with manufacturability heuristics (symmetry, center-of-mass, structural validity); RAG retrieval of CAD examples to ground generation |
| [OpenOrion/CQAsk](https://github.com/OpenOrion/CQAsk) (fork [alexmao1024/CQAsk-Pro](https://github.com/alexmao1024/CQAsk)) | CadQuery chat web app (React + Python + OpenAI) | medium | Chat-driven iterate UX; validates inline CadQuery codegen with STL/STEP export straight from the UI |
| [ankurhanda/claude-cad](https://github.com/ankurhanda/claude-cad) | build123d models built from image-derived construction prompts | medium | Image -> structured construction-prompt intermediary (vs direct image->CAD); named multi-part assembly modeling (42- and 74-part examples) |
| [fa-mc/vibe-cading](https://github.com/fa-mc/vibe-cading) | AI-friendly parametric CadQuery component library | medium | Reusable AI-oriented CadQuery component set, a direct parallel to this skill's `blocks/` |
| [ConAcademy/WeaselToonCadova](https://github.com/ConAcademy/WeaselToonCadova) | Experiment: Claude generates Cadova (Swift CSG) code from reference images, exports 3MF | medium | Automated visual self-correction loop (render 3MF -> PNG via `f3d`, analyze, fix, re-render); image-reference-driven modeling (Cadova/Swift itself not applicable) |
| [AkBKukU/scad-HirthJoint](https://github.com/AkBKukU/scad-HirthJoint) | Parametric Hirth face-spline coupling in OpenSCAD | medium | A Hirth coupling block extending `blocks/joints`; quarter-tooth rotation offset so mating halves self-align |
| [raybellis/hingefold](https://github.com/raybellis/hingefold) | Print-in-place latching fold/living-hinge joints for OpenSCAD | medium | A print-in-place latching fold-hinge block; print-in-place joints are exactly what `kinematic_check` already sweeps without special-casing |
| [CameronBrooks11/panel-cube-joints](https://github.com/CameronBrooks11/panel-cube-joints) | Parametric panel / cube joinery in OpenSCAD (base shell, connectors, cube cluster) | medium | Parametric panel-connector blocks for box / enclosure assemblies |
| [Rahix/FreeCAD-Macros](https://github.com/Rahix/FreeCAD-Macros) | FreeCAD macros generating parametric FDM geometry (same author as FusedFilamentDesign) | medium | Overhanging-counterbore and rib-forming-thread generators; a macro that exports parametric part variants |
| [RareSense/Nova3D](https://github.com/RareSense/Nova3D) | Code-native 3D asset gen: text/image -> executable Blender Python -> structured GLB with named parts, assembly tree, joint pivots | medium | "Program is the source of truth, mesh is the compiled output" principle (matches this skill); exporting named, separately addressable parts plus assembly hierarchy and joint pivots, paralleling the named-object 3MF + `kinematics` design |
| [BaLaurent/ClawdCAD](https://github.com/BaLaurent/ClawdCAD) | Electron app: Claude Agent SDK + OpenSCAD, offline-first, git-native | medium | Dual compile (STL + OFF) to carry per-face color for visual diffing; git-native model history with temporal 3D preview/diff (compare to ClawSCAD's checkpoint branching) |
| [WKJBryan/cadquery-library](https://github.com/WKJBryan/cadquery-library) | CadQuery fine-tuning dataset: 2600+ parametric 3D part examples | medium | Large corpus of parametric CadQuery examples usable as few-shot references or golden-mesh regression fixtures (parallels the Text-to-CadQuery dataset) |
| [intuitia/CadQuery-Project](https://github.com/intuitia/CadQuery-Project) | LEGO / CaDA / COBI-compatible building-block part designs in CadQuery | medium | Reusable, domain-specific parametric block library (LEGO-style connectors), a direct parallel to this skill's `blocks/` |
| [WyNo22/IA2CAD](https://github.com/WyNo22/IA2CAD) | FastAPI + GPT-4o-mini NL-to-CadQuery assistant with clarifying-question wizard and live Three.js/STL preview | medium | Structured-JSON spec intermediary between NL prompt and CadQuery code; clarifying questions asked before modeling begins (parallels talkcad's spec tracking) |
| [rishigundakaram/cad-query-workspace](https://github.com/rishigundakaram/cad-query-workspace) | MCP-driven conversational CadQuery workspace | low | Searchable API-docs layer + few-shot examples folder (this skill's `reference/` already covers it); validates the inline-vs-MCP choice |
| [rundiwu/DeepCAD](https://github.com/rundiwu/DeepCAD) | ML model representing CAD as sketch+extrude command sequences | low | Chamfer distance as a mesh-vs-reference similarity metric for golden-mesh regression tests (skip the ML pipeline) |
| [CodeGraphContext/CodeGraphContext](https://github.com/CodeGraphContext/CodeGraphContext) | Code knowledge-graph MCP server / CLI | low | Repo navigation and impact analysis during development; not part of the CAD pipeline |
| [Aryo-Zare/cq](https://github.com/Aryo-Zare/cq) | Early-stage single-part CadQuery example | low | Nothing actionable (one file, no docs) |
| [welch52553-byte/Vibe-Cading](https://github.com/welch52553-byte/Vibe-Cading) | OpenSCAD-wasm + Three.js viewer where you click faces to name them | low | Face-naming JSON annotations giving the model stable geometric references for edits |
| [SadilKhan/Text2CAD](https://github.com/SadilKhan/Text2CAD) | NeurIPS 2024 transformer generating B-rep sketch+extrude sequences from text | low | Beginner-to-expert multi-level prompt annotations for prompt design; dataset for eval (skip the ML pipeline) |
| [yas1nsyed/CADomatic](https://github.com/yas1nsyed/CADomatic) | FreeCAD parametric Python script generation via Gemini | low | Planned VLM image-similarity feedback loop; parametric editable-script output (FreeCAD API differs from CadQuery) |
| [rystm01/text-to-cad](https://github.com/rystm01/text-to-cad) | Plain NL -> OpenSCAD web app | low | Minimal; basic NL-to-code round-trip only |
| [niklasmh/ClaudeCAD](https://github.com/niklasmh/ClaudeCAD) | Web multimodal (sketch / text / voice) 3D-print assistant | low | Normal maps to aid the model's spatial understanding; draw-on-model feedback for refinement |
| [lauvww/VibeCading](https://github.com/lauvww/VibeCading) | Local AI workbench driving SolidWorks via structured CAD operations | low | Backend-agnostic CAD-operation abstraction (proprietary backend, not applicable here) |
| [ierror/synaps-cad](https://github.com/ierror/synaps-cad) | Rust OpenSCAD IDE (Bevy / csgrs / genai) with AI chat | low | IDE-level concerns; nothing actionable for a code-gen skill |
| [AnCode666/multiCAD-mcp](https://github.com/AnCode666/multiCAD-mcp) | MCP server controlling AutoCAD / ZWCAD / GstarCAD / BricsCAD via COM | low | Consolidating many commands into a few "unified" tools to cut token overhead (this skill avoids MCP by design) |
| [materializr-cad/materializr](https://github.com/materializr-cad/materializr) | Manual OpenCASCADE (B-rep) parametric CAD app for makers, C++/ImGui, not AI-driven | low | Validation-first operations that refuse to execute on bad geometry (parallels this skill's gate); otherwise GUI-app concerns |
| [PenTest-duck/VibeCAD](https://github.com/PenTest-duck/VibeCAD) | HackHarvard 2025 "Cursor for CAD": sketch + voice + gesture -> OpenSCAD | low | Multimodal inputs (sketch-to-3D, voice editing) as a front-end idea; not core to a code-gen pipeline |
| [prashanthbestha480-stack/VibeCAD](https://github.com/prashanthbestha480-stack/VibeCAD) | FastAPI + Three.js + Claude Sonnet 4.5 NL-to-model with a custom (non-CadQuery) representation | low | Minimal; reinforces the case for a real code-CAD kernel over a bespoke representation |
| [AkytharPandaaa/PandaAidedDesign](https://github.com/AkytharPandaaa/PandaAidedDesign) | Collection of parametric OpenSCAD print models (cable-tie brackets, etc.) | low | Example parametric part patterns; not a tool or library |
| [Rahix/FreeCAD-addons](https://github.com/Rahix/FreeCAD-addons) | Curated directory of community FreeCAD plugins | low | Nothing actionable (plugin index, no 3D-print or AI focus) |
| [theosib/FreeCAD-MCP-Server](https://github.com/theosib/FreeCAD-MCP-Server) | FreeCAD MCP server exposing live document state (topology, sketch DOF, recompute diffs, viewport PNG) | low | Before/after recompute diffs to track what a change actually did (parallels cadgate's differential comparison); sketch-constraint DOF/conflict analysis -- MCP/FreeCAD-specific |
| [blwfish/freecad-mcp](https://github.com/blwfish/freecad-mcp) | FreeCAD MCP server (32 tools) framed as a "thinking partner", multi-instance via UUID sockets | low | Integrated diagnostics that turn cryptic FreeCAD report-view errors into structured agent context (echoes this skill's typed `errors`) -- otherwise MCP/FreeCAD-specific |
| [mehsenazizi/mecagent-test-Mehsen-AZIZI](https://github.com/mehsenazizi/mecagent-test-Mehsen-AZIZI) | Take-home test solution: image -> CadQuery via CLIP + GPT-2, syntax + IOU evaluation, CPU-only | low | IOU-based eval metric (already covered by the VibeCAD entry); otherwise a scoped take-home exercise with no reusable tooling |
| [yacine-baghli/im2D2code3D](https://github.com/yacine-baghli/im2D2code3D) | 7-hour hackathon exercise: best-effort 2D-image -> CadQuery code generator | low | Minimal; time-boxed exercise with no reusable tooling beyond validating the image->CadQuery-code framing |

## License

The skill and scripts are licensed under the [PolyForm Noncommercial License 1.0.0](LICENSE). Free to use, modify, and distribute for noncommercial purposes.
