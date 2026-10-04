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
  plan.py                   # validate / summary / import-params over BUILD_PLAN.json
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
