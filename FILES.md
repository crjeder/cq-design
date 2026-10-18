# File Layout

Repository layout, one line per file. Full per-script contract detail lives in
[reference/scripts.md](reference/scripts.md) (`src/`) and [evals/README.md](evals/README.md) (`evals/`).

```
.
  .claude-plugin/        # plugin.json (skills: ["."]) + marketplace.json; repo root is the plugin root
  commands/              # /cq-design:design plan init update build render status
  src/
    run_cadquery_model.py    # Model runner / DFM wrapper (emits JSON contract)
    run_model_shim.py        # runpy shim that auto-exports `result` to STL
    cq_verify.py             # Construction-time assertions (verify_boolean, verify_feature_bounds, check_workplane, verify_stage, verify_backed)
    quality_gate.py          # DFM + geometry/overhang aggregation, claude -p fixes (model from skill_config.json's models.fix_loop)
    plan.py                  # BUILD_PLAN.json: `validate` (schema + inventory cross-check),
                             # `summary` (Phase 2 checkpoint Markdown tables), `import-params`
                             # (reconcile a part script's PARAMETERS block back into the plan)
    script_lint.py           # AST-based pre-flight lint for a generated part script (stdlib only)
    render_prompt.py         # Renders builder/auditor prompts for one part (Phase 3), and the
                              # planner/research agent prompts (Phase 1/2)
    skill_version.py         # Reports the installed commit (.version.json / symlink target / checkout) and diffs it against a repo
    print_orientation.py     # Computes bed-relative print orientation by minimizing support/overhang cost.
                              # `--speed-model` (toolpath_speed.py) adds a min_print_time mode.
    fem_check.py              # FEM stress advisor (optional `fem` dep group): solves a declared load case,
                              # reports a per-orientation failure index + geometry hint. Never a gate.
    toolpath_speed.py         # Toolpath-speed advisor: corner-sharpness + feature-crowding print-time cost
                              # from an exact CAD-solid section (no slicer, no G-code). Never a gate.
    material_properties.json # Elastic constants + allowables per material (fem_check.py + the injected
                              # Engineering Design Rules.md table; single source for both)
    convert_build123d.py     # Phase 0 sourcing aid: build123d -> CadQuery conversion
    cq_compat.py             # Compatibility shim neutralizing a cq_warehouse shape-copy patch
    init_permissions.py      # Seeds a working directory: .claude/settings.local.json (patterns + hooks), build/stl/preview dirs, default profile.json + skill_config.json
    bundle_project.py        # Copies build.py, lib/ tooling, and the uv project template into a working directory; stamps .bundle_version.json; --check reports staleness
    export_standalone.py     # Minimal per-part deliverable: standalone/ = part scripts + only the helpers they import
    printer_profile_validate.py # profile.json schema validation + field write-back
    kinematic_check.py       # Whole-model range-of-motion sweep (trimesh + fcl)
    minimal_cutout_search.py # Bisects a part-script parameter to the minimal value clearing a kinematics entry
    plate_clearance_check.py # Whole-model co-plated union clearance check (trimesh + fcl)
    keep_out_check.py        # Whole-model keep-out-zone check (trimesh + fcl)
    interference.py          # Shared static interference primitive (trimesh + fcl + manifold3d)
    edge_treatment_check.py  # Per-part chamfer/fillet rule check (apply-time hook + print-pose classify)
    gridfinity_check.py      # Per-part Gridfinity conformance check (grid/height/foot profile/mating; auto-scoped gate stage)
    feature_presence_check.py # Per-part interfaces[] position assertion
    placement.py             # Assembly-pose placement helper (cq + trimesh)
    mate_chain.py            # Derived pose along a `joints` mate chain from root_part
    units.py                 # Part->unions / keep-out-zone expansion (resolve_unions / resolve_keep_out)
    freshness.py              # Provenance stamp: hash a part script, compare/write the export manifest
    write_assembly.py        # Assembly writer: assembled-pose per-union + keep-out-zone STLs + manifest (the checks' input); assemble() poses unions
    deliverables.py          # User-facing files, all in print pose: named 3MF, per-union/plate STL, STEP/OBJ/IGES/SCAD (called by build.py)
    estampo_export.py        # estampo.toml writer for `--formats estampo` (pure text; called by deliverables.py)
    build_template.py        # build.py template copied to build/; writes the preferred (or --formats) model files to out/
    log.py                   # Build-time logs: `attempt` (per-attempt log -> build/attempts.jsonl;
                             # fold_attempts, --hook PostToolUse entry point), `journal` (milestone
                             # log -> build/journal.md, see skill/resume.md), `request` (BUILD_PLAN.json's
                             # request_log: search by keyword/kind/level/target, add a clarification/
                             # correction with an auto-stamped ts)
    session_cost.py          # Session transcript -> billed token cost in build/cost.json (Stop hook)
    model_prices.json        # Editable USD-per-MTok table (session_cost.py, evals/run_evals.py)
    regen_prompt.py          # BUILD_PLAN.json + parameters.py + sketches/ -> REGENERATE.md (Phase 4)
    measure_stl.py           # Geometry feature extractor (trimesh + numpy)
    diff_models.py           # Two-STL diff: volume summary JSON + gray/red/green diff PNG (trimesh + manifold3d)
    preview.py               # CadQuery tessellation + z-buffered preview renderer
    zbuffer.py               # numpy z-buffer rasterizer + orthographic camera (no OpenGL)
    render_preview.py        # Subprocess entry point for preview.py
    section_select.py        # Picks axis-aligned section planes through bore/boss axes (render_preview --auto-sections; standalone CLI)
    mesh_io.py               # Trimesh loader + watertightness validation; lateral_area() feeds toolpath_speed.py;
                             # fold_metrics() finds fin/knife-edge folds for quality_gate's sliver_fin
    build_plan_schema.json   # JSON Schema draft-7 for BUILD_PLAN.json
    printer_profile_schema.json  # JSON Schema draft-7 for profile.json
    profile.default.json # Default profile.json seeded into a fresh directory
    skill_config.default.json # Default skill_config.json (models.planner/part_author/fix_loop) seeded into a fresh directory

    blocks/
      __init__.py            # Re-exports all blocks
      primitives.py          # fillet_box, hollow_box
      fasteners.py           # screw_boss, pcb_standoff, snap hooks, alignment pins
      connectors.py          # port_cutout, cable_slot, vent_grid
      hardware.py            # cq_warehouse-backed fastener geometry
      joints.py              # dovetail_groove / dovetail_tongue sliding joints
      gridfinity.py          # Gridfinity bins, baseplates, feet, socket cutters (42 mm grid standard)
      inventory.json         # Machine-readable block descriptors
      inventory_schema.json  # JSON Schema for inventory.json
      validate.py            # Inventory loader + validator

    exporters/
      __init__.py            # run_exporters(script, formats, output_dir)
      stl.py step.py threemf.py obj.py iges.py scad.py
      threemf_multi.py       # Multi-object 3MF writer (named unions + plate metadata)

  evals/
    cases/<case>/        # request.md, golden BUILD_PLAN.json, golden/*.stl, case.json
    run_evals.py         # Scorecard runner (score-only by default; --generate opt-in; --tags filter)
    generate_goldens.py  # Regenerates the golden STLs
    import_external_corpus.py # Manual: imports a filtered/sampled slice of a local external
                          # text->CadQuery corpus snapshot into evals/cases/
    README.md            # Eval-runner contract (scoring, cost sources, --generate)

  prompts/
    research.md          # Research agent prompt (dimension lookup table)
    planning.md          # Planner agent prompt (outputs BUILD_PLAN.json)
    builder.md           # Builder agent operating instructions + return contract
    part.md              # Per-part specification appended to builder.md
    audit.md             # Fresh-context implementation auditor prompt

  templates/
    archetypes.json         # Machine-readable archetype index (name, file, use, params)
    archetypes_schema.json  # JSON Schema for archetypes.json
    enclosure_body.py, lid_sliding.py, lid_snap.py, lid_screwed.py,
    adapter_ring_flanged.py, l_bracket_gusset.py, plate_boss_pattern.py,
    hook.py, clip.py, stand.py,
    gridfinity_bin.py, gridfinity_baseplate.py   # Known-good, pre-verified whole-part templates,
                                    # one per archetype (builder start points)

  skill/                 # Per-phase SKILL.md detail (phase0-4, resume), read on demand
  reference/             # Injected design references (CadQuery patterns, FDM DFM, hardware_dims, Block_Sources)
  openspec/              # OpenSpec specs and change history

  tests/
    conftest.py                      # Adds src/ to sys.path; CadQuery fixtures
    test_blocks.py                   # Block geometry (CadQuery)
    test_run_wrapper.py              # run_cadquery_model.py JSON contract
    test_exporters.py                # Modular exporters (CadQuery)
    test_preview.py                  # preview.py / render_preview.py
    test_mesh_io.py                  # Trimesh loader
    test_stl_to_3mf.py               # 3MF export path
    test_cq_warehouse_integration.py # cq_warehouse fastener integration
    test_prose_layer.py              # Paths + CLI flags in SKILL.md/commands/skill/prompts exist -- fast, no CadQuery
    test_plan.py                     # Schema validation, Phase 2 summary rendering, parameter
                                     # round-trip -- fast, no CadQuery
    test_freshness.py                # Provenance stamp hash/compare/manifest -- fast, no CadQuery
    test_script_lint.py              # AST pre-flight lint findings + CLI -- fast, no CadQuery
    test_render_prompt.py            # Builder/audit/planning/research prompt rendering -- fast, no CadQuery
    test_skill_version.py            # Version stamping/detection/compare -- fast, no CadQuery
    test_log.py                      # Journal/attempt/request_log helpers + CLI -- fast, no CadQuery
    test_regen_prompt.py             # Regeneration-prompt rendering + CLI -- fast, no CadQuery
    test_run_evals.py                # Eval runner scoring path -- fast, no CadQuery
    test_import_external_corpus.py   # External-corpus importer filter/sampling/golden gen (CadQuery)
    test_eval_corpus.py              # Corpus sanity: plans validate, goldens match dims
    test_printer_profile_validate.py # profile.json schema + write-back -- fast, no CadQuery
    test_edge_treatment_check.py     # Chamfer/fillet rule check (CadQuery)
    test_toolpath_speed.py           # Corner/crowding print-time advisor (CadQuery)
    test_gridfinity.py               # Gridfinity blocks + conformance check (CadQuery)
    test_minimal_cutout_search.py    # Parameter bisection search against a kinematics entry (CadQuery)
    test_sliver_fin.py               # Fin detection on a real part (fixtures/rim_fillet_fins.py.txt) with four zero-thickness fins (CadQuery)
    test_templates.py                # Archetype index validation + per-template lint/geometry
    test_pose_terminology.py         # Retired frame-term guard -- fast, no CadQuery
    fixtures/
```
