# Related projects

Projects surveyed for ideas relevant to this skill. Task tracking lives in `TODO.md`
(the ten most valuable open ideas are its "Top 10" items); every other open idea is
listed under [Open ideas](#open-ideas), with its background in [Details](#details).

**Rating** = how much the project is worth to this skill: `High` (directly adoptable or
already shaped the pipeline), `Medium-High`, `Medium` (a concrete transferable idea),
`Low-Medium`, `Low` (little to take), `None` (not applicable).

## Projects

| Project | What it is | Rating | Ideas worth adapting / status |
|---------|-----------|--------|-------------------------------|
| [thereprocase/cad-skill](https://github.com/thereprocase/cad-skill) | Claude Code CadQuery skill with a phased checkpoint pipeline and DFM checks | High | Dimensioned cross-section rendering at critical features -> `preview.py`'s `--cross-sections`; `cq_debug_helpers.py` catching silent boolean failures / workplane drift -> `cq_verify.py`'s `verify_boolean`/`check_workplane`; dual-layer (construction-time + post-export) validation -> `cq_verify.py` + `quality_gate.py` |
| [vericontext/cadgate](https://github.com/vericontext/cadgate) | Quality gate / PR reviewer for AI-generated CadQuery / build123d | Medium-High | Differential geometry comparison (volume / bbox / wall-thickness delta vs the previous attempt) -- `quality_gate.py` judges each attempt in isolation and has no notion of a baseline, so a regression between attempts is invisible today; per-class exit codes for CI gating. LLM-judge intent match is only partly covered by the implementation audit -- the auditor judges the render against `BUILD_PLAN.json`, never against `request_log`, so a plan that misread the request passes the bar (see `intent_recognition.md`) |
| [jmwright/cadquery-llm-skill](https://github.com/jmwright/cadquery-llm-skill) | Maintainer-authored skill teaching LLMs idiomatic CadQuery | High | Anti-patterns integrated as `reference/CadQuery Anti-Patterns.md` (kernel / stateful-context / API-mechanic tiers) + fluent recipes folded into the pattern reference (change `add-cadquery-anti-patterns`); Free Function API content excluded (pipeline is fluent-only) |
| [ChristophSchranz/Tweaker-3](https://github.com/ChristophSchranz/Tweaker-3) | Auto-rotation optimizer for 3D print orientation | High | All three ideas landed in `print_orientation.py`: progressive overhang penalty (severity exponent), area-cumulation candidate generation (`_area_cumulation_normals`), build-height minimization (the `min_build_height` optimize mode) |
| [Text-to-CadQuery (arXiv 2505.06507 + code)](https://github.com/Text-to-CadQuery) | Research generating CadQuery code directly (not command sequences); ~170k text->CadQuery pairs, finetuned 124M-7B models | High | Chamfer distance as mesh-vs-reference regression metric -> `evals/run_evals.py`'s `chamfer_mm`; render-then-judge eval -> the part loop's visual review + implementation audit; the direct-codegen-over-B-rep-command-sequences finding validates this skill's design retrospectively (nothing left to adopt) |
| [cyberchitta/cad-khana](https://github.com/cyberchitta/cad-khana) | build123d CLI / agent skill with a diagnostics-first (not vision-first) loop | Medium-High | Assertions-as-constraints -> `cq_verify.py`; `diagnostics.json` of interferences / clearances / wall thickness / overhangs -> `quality_gate.py`'s structured report + the kinematic/clearance/keep-out stages. Still open: HLR line-art drawings for shape questions renders can't answer -- `preview.py` renders orthographic *tessellation*, not hidden-line-removal edges |
| [jacksonferrigno/cad-llm](https://github.com/jacksonferrigno/cad-llm) | Local desktop app: NL -> CadQuery code -> 3D preview / STEP, Qwen 4B via MLX, sandbox-and-self-correct loop | Low | Exploratory-vs-build prompt routing and the sandbox-execute-read-error-retry loop are what Phase 2 -> the part loop already do; only the on-device-model option is unadopted, and it conflicts with the Claude-5 routing in `CLAUDE5_CONVERSION_PLAN.md` |
| [outerreaches/talkcad](https://github.com/outerreaches/talkcad) | Conversational OpenSCAD Electron app with orchestrator/builder/researcher agents | Medium | Spec tracking with explicit/inferred/default values plus per-spec verification status; web research for real-world dimensions; vision-based verification of rendered models |
| [Rahix/FusedFilamentDesign](https://github.com/Rahix/FusedFilamentDesign) | FreeCAD PartDesign addon of parametric FDM design-for-printing features | Medium-High | Teardrop horizontal holes -> `blocks/connectors.py`'s `teardrop_bore`/`teardrop_post`; counterbore for overhang-free holes -> `blocks/fasteners.py`'s `counterbore_hole`; vertical-edge fillet rule -> enforced (advisory) by `edge_treatment_check.py`. Still open: thread-forming ribs, zip-tie channels -- neither exists in `blocks/inventory.json` |
| [partcad/partcad](https://github.com/partcad/partcad) | Package manager for hardware / manufacturable products across CAD kernels (CadQuery, build123d, OpenSCAD), YAML assembly format, BOM, AI-assisted workflows | Low-Medium | Package-manager framing for reusable, versioned part definitions with declared metadata (parallels `blocks/inventory.json`); YAML assembly format tracking BOM and part relationships across CAD kernels; caching rendered models to speed iteration |
| [r3c0nshade/CADForge](https://github.com/r3c0nshade/CADForge) | Prompt-to-CAD web app: multi-provider LLM (Claude / GPT / GLM / NVIDIA / Ollama) writes CadQuery, sandboxed execution, Three.js preview, STEP/STL/OBJ/DXF export | Low-Medium | Still open: per-part version history across iterative edits (`build/attempts.jsonl` records attempts but keeps no script snapshots). Provider-agnostic backend is out of scope for a Claude Code skill |
| [w1ne/kernelCAD-web](https://github.com/w1ne/kernelCAD-web) | Agent-native CAD: design brief -> editable `.kcad.ts` -> evaluated model -> deterministic validation (OpenCASCADE via Replicad) | Low-Medium | "Editable source is truth" and deterministic-validation-before-visual are already the pipeline (`script_lint` -> wrapper -> gate, then review). Still open: importing vendor STEP geometry for real hardware instead of parametric primitives -- see the B-Rep Part Libraries table below, which `blocks/hardware.py` does not yet draw on |
| [pzfreo/build123d-mcp](https://github.com/pzfreo/build123d-mcp) | MCP server letting an assistant build a build123d part incrementally with render/measure/validate after every step ("eyes for the AI") | Low-Medium | The reported CADGenBench jump (36%->46%) from per-step visual+measured feedback validates this skill's existing render+validate loop but adds nothing to adopt; the `install_skill` workflow-order scaffold is the prescriptive pattern de-emphasized post-C2 |
| [CadQuery/cadquery-contrib mcp-server](https://github.com/CadQuery/cadquery-contrib/tree/master/mcp-server) | Official CadQuery MCP server (render / inspect / get_parameters / export) | Medium | `get_parameters` style extraction of customizable script params for a parametric re-run UX (this skill avoids MCP by design) |
| [mikekuniavsky/mcp-cadquery-server-public](https://github.com/mikekuniavsky/mcp-cadquery-server-public) | MCP server executing CadQuery in sandboxed subprocesses, exporting 3MF/PNG/GLB via cloud storage | Medium | AST-based allowlist validation before executing generated code (safer than bare `exec`); export-format selection by result type (`cq.Assembly` -> GLB for per-part color, `cq.Workplane` -> 3MF), parallel to this skill's `dict[str, Workplane]` union-splitting |
| [Kevoyuan/AgentSCAD](https://github.com/Kevoyuan/AgentSCAD) | NL -> validated OpenSCAD artifacts, cost-conscious progressive pipeline (generate once, validate deterministically, repair only on failure) | Medium | Repair-only-on-failure -> `quality_gate.py` defaults `allow_fix=False` (IMPROVEMENT_PLAN item 10); parsing assignments into editable parameters -> `import_params.py`'s `PARAMETERS` reconciliation |
| [deGravity/aidl](https://github.com/deGravity/aidl) | Research DSL (AI Design Language) standardizing CAD construction into a hierarchical Structure/Geometry/Constraint tree for more reliable LLM generation | Low | Semantic dot-notation auto-naming of every generated entity for clearer error feedback; designing for iterative *appending* to a construction tree rather than editing existing statements, relevant if `part.md` prompts move toward incremental edits |
| [Hiram31/CADialogue](https://github.com/Hiram31/CADialogue) | Research: multimodal (text/voice/image) conversational assistant driving FreeCAD via generated Python macros | Low-Medium | Macro caching with vector-similarity retrieval of previously-confirmed designs (reported 85x speedup vs regenerating from scratch) -- a pattern for caching known-good part scripts by description similarity |
| [BenCaunt/SynthCAD](https://github.com/BenCaunt/SynthCAD) | Framework wrapping build123d with CLIs/registries/export tooling, packaged as reusable "skills" for coding agents (Codex etc.) | Low | PR-integrated interactive CAD diff viewer so an agent (or reviewer) can inspect its own geometry changes inline; scoped CI that fans framework changes across sibling projects while containing project-local ones |
| [Svetlana-DAO-LLC/cad-agent](https://github.com/Svetlana-DAO-LLC/cad-agent) | Containerized build123d rendering server: agent sends commands, gets back PNG/STL/STEP/3MF, decides next step | Low-Medium | Technical/blueprint-style 2D dimensioned-drawing renders alongside 3D views, distinct from this skill's multi-view PNG preview |
| [testingacount2026-ui/cadx-local](https://github.com/testingacount2026-ui/cadx-local) | Local Ollama + CadQuery + Flask web app for NL -> CadQuery, no cloud dependency | Low | Auto-computed volume/surface-area/bbox property panel alongside the generated model, echoing `measure_stl.py`'s feature extraction but surfaced directly in the iterate UX |
| [earthtojake/text-to-cad](https://github.com/earthtojake/text-to-cad) (forks: [cedrickchee](https://github.com/cedrickchee/text-to-cad), [costrict mirror](https://github.com/costrict-plugins-repo/earthtojake-text-to-cad-cad); web wrapper [CodeEagle/text-to-cad-web](https://github.com/CodeEagle/text-to-cad-web)) | build123d agent-skills library (CAD + URDF + G-code + DXF skills) for Claude / Codex | Medium | Skill decomposition into CAD / slicing / URDF / DXF sub-skills; multi-format export pipeline (STEP / 3MF / GLB) beyond STL |
| [rawwerks/VibeCAD](https://github.com/rawwerks/VibeCAD) | build123d skills library plus render-glb and gltf-transform plugins | Medium | IoU / Dice / precision-recall mesh metrics for AI-output regression; `bd_warehouse` fasteners and `gggears` parametric gears (parallel to `blocks/hardware`) |
| [lwidm/cq_gears](https://github.com/lwidm/cq_gears) | Parametric involute spur/helical gear generator for CadQuery (exact analytical curve equations, no boolean approximation) | Medium | Fills the gap in `blocks/` for gear geometry; upstream declares no license, so it's referenced as a downloadable external resource in `planning_notes` rather than pinned or vendored |
| [lightoshadow/text-to-openscad](https://github.com/lightoshadow/text-to-openscad) | Claude Code plugin: plan -> write `.scad` -> render -> iterate up to N rounds | Low-Medium | Manifold genus / facet stats as a geometry sanity check; color-coded multi-part renders to spot clipping and gaps; standard multi-view grid (iso/top/front/right) |
| [rohittp0/ClaudeCAD](https://github.com/rohittp0/ClaudeCAD) | Claude Code + OpenSCAD plugin, Interview -> Design -> Code -> Validate -> Export | Medium | `admesh` mesh-integrity validation as an export-time gate; explicit interview phase before modeling |
| [levkropp/ClawSCAD](https://github.com/levkropp/ClawSCAD) | Electron app gluing OpenSCAD + Claude Code via an OpenSCAD MCP subprocess | Low-Medium | Checkpoint branching (immutable model tree, revert + branch alternatives); auto error-feedback loop from render failures |
| [Masoudjafaripour/Vibe_CADing](https://github.com/Masoudjafaripour/Vibe_CADing) | Multi-agent generative pipeline: Planner / Retriever / Generator / Critic | Low-Medium | Critic with manufacturability heuristics (symmetry, center-of-mass, structural validity); RAG retrieval of CAD examples to ground generation |
| [OpenOrion/CQAsk](https://github.com/OpenOrion/CQAsk) (fork [alexmao1024/CQAsk-Pro](https://github.com/alexmao1024/CQAsk)) | CadQuery chat web app (React + Python + OpenAI) | Low | Chat-driven iterate UX; validates inline CadQuery codegen with STL/STEP export straight from the UI |
| [ankurhanda/claude-cad](https://github.com/ankurhanda/claude-cad) | build123d models built from image-derived construction prompts | Low | Image -> structured construction-prompt intermediary (vs direct image->CAD); named multi-part assembly modeling (42- and 74-part examples) |
| [fa-mc/vibe-cading](https://github.com/fa-mc/vibe-cading) | AI-friendly parametric CadQuery component library | Medium | Reusable AI-oriented CadQuery component set, a direct parallel to this skill's `blocks/` |
| [ConAcademy/WeaselToonCadova](https://github.com/ConAcademy/WeaselToonCadova) | Experiment: Claude generates Cadova (Swift CSG) code from reference images, exports 3MF | Low | Automated visual self-correction loop (render 3MF -> PNG via `f3d`, analyze, fix, re-render); image-reference-driven modeling (Cadova/Swift itself not applicable) |
| [AkBKukU/scad-HirthJoint](https://github.com/AkBKukU/scad-HirthJoint) | Parametric Hirth face-spline coupling in OpenSCAD | Low-Medium | A Hirth coupling block extending `blocks/joints`; quarter-tooth rotation offset so mating halves self-align |
| [raybellis/hingefold](https://github.com/raybellis/hingefold) | Print-in-place latching fold/living-hinge joints for OpenSCAD | Medium | A print-in-place latching fold-hinge block; print-in-place joints are exactly what `kinematic_check` already sweeps without special-casing |
| [CameronBrooks11/panel-cube-joints](https://github.com/CameronBrooks11/panel-cube-joints) | Parametric panel / cube joinery in OpenSCAD (base shell, connectors, cube cluster) | Medium | Parametric panel-connector blocks for box / enclosure assemblies |
| [Rahix/FreeCAD-Macros](https://github.com/Rahix/FreeCAD-Macros) | FreeCAD macros generating parametric FDM geometry (same author as FusedFilamentDesign) | Medium | Overhanging-counterbore and rib-forming-thread generators; a macro that exports parametric part variants |
| [RareSense/Nova3D](https://github.com/RareSense/Nova3D) | Code-native 3D asset gen: text/image -> executable Blender Python -> structured GLB with named parts, assembly tree, joint pivots | Low-Medium | "Program is the source of truth, mesh is the compiled output" principle (matches this skill); exporting named, separately addressable parts plus assembly hierarchy and joint pivots, paralleling the named-object 3MF + `kinematics` design |
| [BaLaurent/ClawdCAD](https://github.com/BaLaurent/ClawdCAD) | Electron app: Claude Agent SDK + OpenSCAD, offline-first, git-native | Low | Dual compile (STL + OFF) to carry per-face color for visual diffing; git-native model history with temporal 3D preview/diff (compare to ClawSCAD's checkpoint branching) |
| [WKJBryan/cadquery-library](https://github.com/WKJBryan/cadquery-library) | CadQuery fine-tuning dataset: 2600+ parametric 3D part examples | High | Large corpus of parametric CadQuery examples usable as few-shot references or golden-mesh regression fixtures (parallels the Text-to-CadQuery dataset) |
| [intuitia/CadQuery-Project](https://github.com/intuitia/CadQuery-Project) | LEGO / CaDA / COBI-compatible building-block part designs in CadQuery | Low-Medium | Reusable, domain-specific parametric block library (LEGO-style connectors), a direct parallel to this skill's `blocks/` |
| [WyNo22/IA2CAD](https://github.com/WyNo22/IA2CAD) | FastAPI + GPT-4o-mini NL-to-CadQuery assistant with clarifying-question wizard and live Three.js/STL preview | Low-Medium | Structured-JSON spec intermediary between NL prompt and CadQuery code; clarifying questions asked before modeling begins (parallels talkcad's spec tracking) |
| [rishigundakaram/cad-query-workspace](https://github.com/rishigundakaram/cad-query-workspace) | MCP-driven conversational CadQuery workspace | Low | Searchable API-docs layer + few-shot examples folder (this skill's `reference/` already covers it); validates the inline-vs-MCP choice |
| [rundiwu/DeepCAD](https://github.com/rundiwu/DeepCAD) | ML model representing CAD as sketch+extrude command sequences | Low | Its one applicable idea, Chamfer distance for golden-mesh regression, is in `evals/run_evals.py`; the ML pipeline was never applicable |
| [CodeGraphContext/CodeGraphContext](https://github.com/CodeGraphContext/CodeGraphContext) | Code knowledge-graph MCP server / CLI | None | Repo navigation and impact analysis during development; not part of the CAD pipeline |
| [Aryo-Zare/cq](https://github.com/Aryo-Zare/cq) | Early-stage single-part CadQuery example | None | Nothing actionable (one file, no docs) |
| [welch52553-byte/Vibe-Cading](https://github.com/welch52553-byte/Vibe-Cading) | OpenSCAD-wasm + Three.js viewer where you click faces to name them | Low-Medium | Face-naming JSON annotations giving the model stable geometric references for edits |
| [SadilKhan/Text2CAD](https://github.com/SadilKhan/Text2CAD) | NeurIPS 2024 transformer generating B-rep sketch+extrude sequences from text | Medium | Beginner-to-expert multi-level prompt annotations for prompt design; dataset for eval (skip the ML pipeline) |
| [yas1nsyed/CADomatic](https://github.com/yas1nsyed/CADomatic) | FreeCAD parametric Python script generation via Gemini | Low | Planned VLM image-similarity feedback loop; parametric editable-script output (FreeCAD API differs from CadQuery) |
| [rystm01/text-to-cad](https://github.com/rystm01/text-to-cad) | Plain NL -> OpenSCAD web app | None | Minimal; basic NL-to-code round-trip only |
| [niklasmh/ClaudeCAD](https://github.com/niklasmh/ClaudeCAD) | Web multimodal (sketch / text / voice) 3D-print assistant | Low | Normal maps to aid the model's spatial understanding; draw-on-model feedback for refinement |
| [lauvww/VibeCading](https://github.com/lauvww/VibeCading) | Local AI workbench driving SolidWorks via structured CAD operations | None | Backend-agnostic CAD-operation abstraction (proprietary backend, not applicable here) |
| [ierror/synaps-cad](https://github.com/ierror/synaps-cad) | Rust OpenSCAD IDE (Bevy / csgrs / genai) with AI chat | None | IDE-level concerns; nothing actionable for a code-gen skill |
| [AnCode666/multiCAD-mcp](https://github.com/AnCode666/multiCAD-mcp) | MCP server controlling AutoCAD / ZWCAD / GstarCAD / BricsCAD via COM | Low | Consolidating many commands into a few "unified" tools to cut token overhead (this skill avoids MCP by design) |
| [materializr-cad/materializr](https://github.com/materializr-cad/materializr) | Manual OpenCASCADE (B-rep) parametric CAD app for makers, C++/ImGui, not AI-driven | Low | Validation-first operations that refuse to execute on bad geometry (parallels this skill's gate); otherwise GUI-app concerns |
| [PenTest-duck/VibeCAD](https://github.com/PenTest-duck/VibeCAD) | HackHarvard 2025 "Cursor for CAD": sketch + voice + gesture -> OpenSCAD | Low | Multimodal inputs (sketch-to-3D, voice editing) as a front-end idea; not core to a code-gen pipeline |
| [prashanthbestha480-stack/VibeCAD](https://github.com/prashanthbestha480-stack/VibeCAD) | FastAPI + Three.js + Claude Sonnet 4.5 NL-to-model with a custom (non-CadQuery) representation | None | Minimal; reinforces the case for a real code-CAD kernel over a bespoke representation |
| [AkytharPandaaa/PandaAidedDesign](https://github.com/AkytharPandaaa/PandaAidedDesign) | Collection of parametric OpenSCAD print models (cable-tie brackets, etc.) | Low | Example parametric part patterns; not a tool or library |
| [Rahix/FreeCAD-addons](https://github.com/Rahix/FreeCAD-addons) | Curated directory of community FreeCAD plugins | None | Nothing actionable (plugin index, no 3D-print or AI focus) |
| [theosib/FreeCAD-MCP-Server](https://github.com/theosib/FreeCAD-MCP-Server) | FreeCAD MCP server exposing live document state (topology, sketch DOF, recompute diffs, viewport PNG) | Low-Medium | Before/after recompute diffs to track what a change actually did (parallels cadgate's differential comparison); sketch-constraint DOF/conflict analysis -- MCP/FreeCAD-specific |
| [blwfish/freecad-mcp](https://github.com/blwfish/freecad-mcp) | FreeCAD MCP server (32 tools) framed as a "thinking partner", multi-instance via UUID sockets | Low | Integrated diagnostics that turn cryptic FreeCAD report-view errors into structured agent context (echoes this skill's typed `errors`) -- otherwise MCP/FreeCAD-specific |
| [mehsenazizi/mecagent-test-Mehsen-AZIZI](https://github.com/mehsenazizi/mecagent-test-Mehsen-AZIZI) | Take-home test solution: image -> CadQuery via CLIP + GPT-2, syntax + IOU evaluation, CPU-only | Low | IOU-based eval metric (already covered by the VibeCAD entry); otherwise a scoped take-home exercise with no reusable tooling |
| [thereprocase/novel-cad-skill](https://github.com/thereprocase/novel-cad-skill) | Redesign of thereprocase/cad-skill swapping CadQuery for build123d (`ARCHITECTURE.md`): context-manager scoping, attribute selectors, STEP-as-checkpoint between phases, Manifold3d topology validation, a programmatic `gate_enforcer.py` state machine, and a build123d->CadQuery->OpenSCAD fallback router | Low-Medium | Revisit if this skill ever migrates off CadQuery: STEP-as-checkpoint to cut context bloat between phases, Manifold3d validation as a topology check beyond watertightness, and the executable-gate pattern (`.gate.json`) over doc-only checkpoints |
| [yacine-baghli/im2D2code3D](https://github.com/yacine-baghli/im2D2code3D) | 7-hour hackathon exercise: best-effort 2D-image -> CadQuery code generator | Low | Minimal; time-boxed exercise with no reusable tooling beyond validating the image->CadQuery-code framing |
| Proprietary-CAD MCP ecosystem (surveyed via [cyberchitta.cc/cad-llm-tools](https://www.cyberchitta.cc/articles/cad-llm-tools.html): dozens of MCP servers for Fusion 360, SolidWorks, Rhino/Grasshopper, Onshape, AutoCAD, SketchUp, Blender) | Human-directed MCP bridges exposing a proprietary CAD app's native API/COM interface to an AI client | None | None targets a code-CAD kernel this skill can adopt; they confirm the human-directed-MCP-bridge pattern is well covered elsewhere and reinforce (with rishigundakaram/cad-query-workspace, CadQuery/cadquery-contrib mcp-server, multiCAD-mcp above) that this skill's inline, MCP-free design is the deliberate outlier |
| [Zoo Text-to-CAD Machine](https://zoo.dev/zookeeper) | Native B-Rep mechanical output, open ML pipeline. | Low | CadQuery/OCC already emits native B-Rep; the training pipeline isn't reusable by an inline Claude Code skill. Nothing concretely adoptable |
| [CADAM (by AdamCAD)](https://github.com/Adam-CAD/CADAM) | Local-first, UI web app with live parametric sliders. | Low | Live parametric sliders need a GUI this CLI-driven skill doesn't have; duplicate entry, see the more detailed `Adam-CAD/CADAM` row below |
| [Text2CAD (DFKI / NeurIPS)](https://www.dfki.de/web/forschung/projekte-publikationen/publikation/15570) | Autoregressive transformer trained on multi-level CAD specs. | Low | Research training pipeline with no reusable tooling; the multi-level-spec idea duplicates the `SadilKhan/Text2CAD` row above |
| [CAD/CAE Copilot & Multi-Agent-CAD](https://github.com/armpro24-blip/cad-cae-copilot) | Self-correcting agent loops with finite-element validation. | Medium | FEA/structural validation is a genuine gap here (no stress check exists); the self-correcting loop itself duplicates the existing part loop |
| [IntentForge / CadSmith](https://arxiv.org/html/2603.26512v1) | Deterministic verification and self-repairing execution. | Low | Deterministic-verify-then-repair is already this skill's model (`script_lint` -> wrapper -> `quality_gate.py`); duplicates two later rows on the same research thread |
| [Anvilate](https://github.com/clay-good/anvilate) | Mechanical engineer assistant with DFM and structural checks. | Medium | DFM overlaps heavily with `quality_gate.py`/`edge_treatment_check.py`, but structural (stress) checks are a genuine gap |
| [Kerf (Vulos Engineering)](https://github.com/vul-os/kerf) | Offline-first, chat-driven CAD suite powered by OpenCASCADE. | Low | Same OCC kernel as CadQuery, but the description names no concrete mechanism beyond "offline chat CAD" |
| [microsoft/TRELLIS](https://github.com/microsoft/TRELLIS) | State-of-the-art foundational model for Text/Image to high-quality 3D asset generation using structured geometry reasoning. | None | Organic mesh-asset generation, not parametric mechanical CAD; not applicable to a code-CAD kernel |
| [earthtojake/text-to-cad](https://github.com/earthtojake/text-to-cad) | Agent skills library and harness for LLM/Agent-driven CAD generation, local visual inspection, slicing, and FDM printer automation. | Medium | Duplicate -- same project assessed in detail above (skill decomposition + multi-format export row) |
| [EESJGong/Graph-CAD](https://github.com/EESJGong/Graph-CAD) | Geometry-aware graph representations for LLM-driven text-to-CAD generation using Blender and Python scripting. | Low-Medium | Graph decomposition of part hierarchy is conceptually interesting but Blender/mesh-oriented; doesn't port directly to a parametric-kernel pattern |
| [FishWoWater/Open3DStudio](https://github.com/FishWoWater/Open3DStudio) | Self-hosted local 3DAIGC workspace with mesh generation, auto-rigging, and text-to-3D. | None | Organic asset/character pipeline (rigging, mesh gen), not mechanical parametric CAD |
| [vespo92/AI-CAD](https://github.com/vespo92/AI-CAD) | Open-source web-based AI/LLM workbench converting natural language into parametric 3D CAD geometry (OpenCASCADE WASM engine). | Low | Web-wrapper-around-OCC pattern already covered above (`kernelCAD-web`, Kerf); nothing distinct called out |
| [Adam-CAD/CADAM](https://github.com/Adam-CAD/CADAM) | Browser-based open-source text-to-CAD tool using Anthropic/LLMs to generate parametric OpenSCAD scripts compiled via WebAssembly. | Low | Browser/WASM OpenSCAD generation duplicates the pattern already covered by `lightoshadow/text-to-openscad` above; also a duplicate entry of the `CADAM` row above |
| [SadilKhan/NURBGen](https://github.com/SadilKhan/NURBGen) | LLM-driven high-fidelity text-to-CAD generation using NURBS modeling pipelines. | Low | NURBS/freeform-surface fidelity targets organic shapes; this skill's parts are box/bracket/enclosure primitives, not freeform surfaces |
| [Gustavo-Paris/3dprint-generator](https://www.google.com/search?q=https://github.com/Gustavo-Paris/3dprint-generator) | Self-hostable natural language chat pipeline turning prompts directly into printable 3D models and slicer-ready files. | Low | Self-hostable chat-to-print pipeline, but no technical detail beyond that; nothing concrete to adopt |
| [jabarkle/CADSmith](https://github.com/jabarkle/CADSmith) | Multi-agent CAD generation with programmatic geometric validation, vision-language model judging, and iterative refinement. | Medium | Architecture closely parallels this skill's own pipeline (programmatic validation + VLM judging + iteration); worth a direct comparison for divergent techniques, but nothing distinctly new stated |
| [JonFermin/cadsmith](https://github.com/JonFermin/cadsmith) | Claude Code skill suite for parametric 3D models (build123d/CadQuery) with interactive Three.js previews. | Medium | Interactive WebGL previews are a genuine gap versus this skill's static matplotlib previews; direct Claude-Code/CadQuery analog worth watching |
| [pranjalbhatia710/cadsmith](https://github.com/pranjalbhatia710/cadsmith) | Self-correcting text-to-CAD agent built on CadQuery, executes code, measures geometry, and loops until validation passes. | Low | Validates this skill's own execute-measure-validate loop design but describes nothing beyond it |
| [jzjzzzzzzz/IntentForge](https://github.com/jzjzzzzzzz/IntentForge) | Deterministic CAD intent pipeline, editable model state, structured artifacts, and validation reports. | Low-Medium | Overlaps with `BUILD_PLAN.json` + `quality_gate.py`'s structured reports; duplicate of the same "IntentForge" concept as the row above and the `Text2CAD (MLYengineering)` row below |
| [monicapserrano/text_to_cad](https://github.com/monicapserrano/text_to_cad) | Self-trained AI model for decoding primitive shapes and parameters from text, generates FreeCAD files. | None | Stale, primitives-only, custom (non-LLM) model |
| [sidbalasubramanian007/Aipex-Lab-Research](https://github.com/sidbalasubramanian007/Aipex-Lab-Research) | Benchmarking text-to-CAD models (Zero-To-CAD-Qwen3-VL-2B vs. Qwen3.5-2B), prompt rewriting, and feedback loops. | Low | Benchmark methodology, not reusable tooling; a distant cousin of `evals/run_evals.py`'s scoring approach at best |
| [Text-to-CadQuery/Text-to-CadQuery](https://github.com/Text-to-CadQuery/Text-to-CadQuery) | Data annotation, model training, inference, and evaluation pipelines for CadQuery-based text-to-CAD. | High | Duplicate -- same project assessed in detail in the `Text-to-CadQuery (arXiv 2505.06507 + code)` row above |
| [vasparshin/text-to-3d-print](https://github.com/vasparshin/text-to-3d-print) | End-to-end pipeline: Zoo Agent API for CAD, geometric verification, slicing, and pre-flight checks for 3D printers. | Medium | Actually invoking a slicer for pre-flight checks (vs. this skill's DFM heuristics) is a genuine capability gap; the Zoo Agent CAD backend itself isn't portable |
| [cprakash64/CAD-Maker (LunaiCAD)](https://github.com/cprakash64/CAD-Maker) | Plain-English CAD studio with structured intent, trusted local CAD generators, manufacturability feedback, and export-ready STL/STEP. | Low | Structured intent and manufacturability feedback duplicate `BUILD_PLAN.json`/`quality_gate.py`; no new mechanism described |
| [KnuckKnuck0123/naturalcad](https://github.com/KnuckKnuck0123/naturalcad) | Conversational CAD platform for prompt-to-parametric models, iterative refinement, and STEP/GLB/STL export with build123d. | Low | Generic conversational/iterative pattern already covered by `talkcad` and `cad-khana` above |
| [drogertieni/text-to-cad-studio](https://github.com/drogertieni/text-to-cad-studio) | Browser-native parametric CAD: natural language → build123d → Pyodide (WASM) → STEP/DXF, with click-to-edit features. | Low-Medium | In-browser Pyodide execution is a distinct technical approach, but this skill already executes CadQuery directly via subprocess; not portable, click-to-edit is a GUI feature |
| [Anie0205/Text-to-CAD-using-Gemini](https://github.com/Anie0205/Text-to-CAD-using-Gemini) | Lightweight full-stack system using Google Gemini to generate OpenSCAD/CATScript, with Three.js preview and STL export. | Low | Minimal, limited to OpenSCAD, no depth beyond basic NL-to-code |
| [ai-cad-labs/ai-cad](https://github.com/ai-cad-labs/ai-cad) | Multi-agent mechanical CAD harness: agents plan, write CadQuery, render, critique, repair, and validate with DFM/DFA rules. | Medium | Architecture is nearly identical to this skill's own phased pipeline (plan/write/render/critique/repair + DFM); worth comparing for divergent DFM/DFA rule coverage |
| [ai-cad-labs/ai-cad-pydanticai](https://github.com/ai-cad-labs/ai-cad-pydanticai) | PydanticAI-based multi-agent CAD design system with vision feedback loops and DFM/DFA rulebooks. | Medium | Externalizing DFM/DFA checks into versioned, data-driven "rulebooks" (vs. this skill's code-embedded checks) is a genuinely adoptable structural idea |
| [nludd25/text-to-cad](https://github.com/nludd25/text-to-cad) | Skills library for CAD, robotics, and hardware design agents, with benchmarks and local review tools. | Low | Generic grab-bag description; "local review tools" is too vague to extract a concrete idea |
| [andreyka/forma-ai-service](https://github.com/andreyka/forma-ai-service) | Multi-Agent System, build123d, PyVista Visual Feedback Loop, RAG, STEP/STL Export. | Low | PyVista is a marginal alternative to this skill's matplotlib/trimesh preview stack; RAG-grounded generation is generic and already implicit in the `reference/` folder |
| [outerreaches/talkcad](https://github.com/outerreaches/talkcad) | OpenSCAD Agent, Real-Time WebGL Preview, Web Search Integration, Design Rule Skills. | Medium | Duplicate -- same project assessed in detail in the `outerreaches/talkcad` row above |
| [reetm09/agentic3d](https://github.com/reetm09/agentic3d) | AutoGen Framework, OpenSCAD, VLM Screenshot Evaluation, Modality-Switching Loop. | Low-Medium | "modality-switching" (code-gen vs. vision-driven iteration chosen per task) is an interesting framing but underspecified here |
| [Pan-Chera/Multi-Agent-CAD](https://github.com/Pan-Chera/Multi-Agent-CAD) | Multi-Body Interlocking, Print-in-Place Constraints, Clearance Gap Tuning. | Medium | Squarely overlaps `kinematic_check.py`/`plate_clearance_check.py`/`minimal_cutout_search.py`; same problem domain even without a detailed new mechanism |
| [flowful-ai/cad-skill](https://github.com/flowful-ai/cad-skill) | Claude Code / Agent Skill, CadQuery, Parametric Enclosures, FDM Design Rules. | Medium | Closest direct analog to this exact skill (same stack: Claude Code + CadQuery + FDM rules); worth periodic diffing, though no specific new mechanism is named |
| [Text2CAD](https://github.com/MLYengineering/Text2CAD) | Contract‑Driven, Agentic CAD Generation with Deterministic Execution | Medium-High | READMEd in full: a concrete 7-stage pipeline (Planner/Implementation/Validation/Repair/Execution/Evaluation/Learning agents over FreeCAD) built on the same "LLMs reason, deterministic tools decide" philosophy as this skill. The Repair Agent's rule-bound, non-rewrite patches and the Learning Agent's cross-attempt failure aggregation are genuinely adoptable refinements to `quality_gate.py`'s fix loop, which today just re-prompts `claude -p` rather than applying scoped patches or learning across attempts |
| https://yotown.com/ | A 3D + AI Ecosystem for the Physical World. Yo.Town 3D reconnects real life and the virtual world through spatial computing, AI, multimedia, and advanced 3D printing. We turn abstract digital ideas into tangible, gravity-aware 3D experiences. | None | Marketing page, no code repository, nothing to evaluate |
| [CadAgent](https://github.com/SSSSSia/CadAgent) | An LLM Agent-powered FreeCAD workbench that generates and modifies 3D mechanical models through natural language descriptions. | High | Several concretely adoptable, non-duplicate ideas: **Token Budget Management** (directly relevant to this skill's context-heavy part loop), **Smart Clarification Policy** (auto-assume reasonable defaults instead of always stopping to ask), and **Undo/Rollback via automatic snapshots** (a simpler cousin of the checkpoint-branching idea from ClawSCAD/ClawdCAD above); Progressive Context Injection is also worth a look for `part.md` prompt sizing |
| [cad-agent](https://github.com/pranjalbhatia710/cad-agent) | tiny local CLI for standard parts (no llm?) | Low | READMEd in full: confirmed no LLM integration (only a roadmap item); it's a deterministic "typed part spec -> OpenSCAD" compiler for a handful of primitives (mounting plates, hollow boxes). The "CAD primitive compiler" framing is reasonable but minor, and already implicit in this skill's `blocks/` library |
| https://github.com/PranavChahal/sphaire-web | Geometry validation and FDM, SLA, or CNC-oriented DFM checks, Color, metallic/roughness, image textures, and optional AI materials | Medium | READMEd in full: a browser CAD app (OpenCascade/Replicad WASM + Babylon.js) that decouples AI generation from geometry creation by routing text-to-CAD requests down a *parametric* path (CadQuery/Replicad-equivalent, for mechanical parts) or an *organic* mesh-gen path -- that request-triage pattern is a genuinely useful idea for Phase 0/2 sourcing triage. DFM-for-FDM/SLA/CNC and "code is the source of truth" duplicate what this skill already does; material/texture rendering is out of scope |
| https://github.com/abpyu/text-to-cad-local-chat | multimodal model routing, spatial relationship constraints from images, multi-turn code inheritance, and incremental modifications | Medium | READMEd in full, confirms the concrete value: "subsequent conversations inherit the previous model code, enabling continuous adjustment of dimensions, positions, directions and structures" -- exactly the incremental-edit pattern `part.md` currently lacks (a revision request effectively regenerates the whole script); a local vision model deriving spatial relationships from reference images ties to Phase 0 sourcing from photos |
| https://github.com/aarohkandy/ai-cad | planner-first | Low-Medium | READMEd in full: a plan-then-compile-then-execute CadQuery pipeline where the planner states its assumptions about missing dimensions explicitly, paralleling `BUILD_PLAN.json`/`request_log`; a deterministic rule-based planner fallback for when no LLM is available isn't relevant to a Claude-only skill, and the README itself admits the CadQuery execution path is still a stub ("has never met a real CadQuery"), limited to 5 shape families |
| https://github.com/natgluons/AI-Fusion360-Godot-Design | tune objects using Bayesian optimization | Medium | READMEd in full, confirms a concrete, transferable technique: a `scikit-optimize` "black-box tuning" loop that samples design parameters, simulates/scores each candidate, and iterates without needing an explicit performance model -- directly applicable to auto-tuning a part's dimensions against an objective (mass, clearance, print time) in this skill; the Fusion 360/Godot backend itself isn't portable |
| https://github.com/ReverseZoom2151/harnesscad | Soundness, not completeness. CAD operations are verified before the kernel runs them | High | READMEd in full and substantive: pre-kernel verification with named diagnostics (e.g. catching "fillet radius exceeds half the smallest extent" symbolically *before* the OCC call, instead of after a boolean failure) is a real gap versus `script_lint.py`'s AST-level (geometry-unaware) pre-flight lint; its "measured gate" (certify only when independent measurement predicates pass) already matches this skill's philosophy and could sharpen it. Cross-checking against 13 independent kernels is overkill for a single-kernel (CadQuery) skill and not worth adopting wholesale |
| https://github.com/OzAILabs/Claude-To-Print | multi-color | High | READMEd in full: a close, substantive analog (a Claude Code skill using build123d instead of CadQuery, with a staged design-brief -> parametric-script -> deterministic-export -> mesh-QA -> visual-feedback pipeline nearly identical to this skill's own). Concretely adoptable: **multi-color/multi-material 3MF export** via `lib3mf`, splitting a part into named color regions and exporting a pre-colored 3MF for AMS-style multi-filament printers -- a genuine capability gap in `threemf_multi.py`, which currently tracks named unions/plates but not per-region color |
| https://github.com/natgluons/CAD-modeling-app | GUI (or point-and-click) interactions | Low | READMEd in full: this repo is effectively a fork/mirror of Zoo's (KittyCAD) `modeling-app`. GUI point-and-click and code editing both mutate the same underlying KCL code representation, rendered via a remote GPU geometry-engine service over WebSockets. "Code representation is the single source of truth even for GUI actions" validates this skill's own design but adds nothing new; the hosted-rendering-service dependency is the opposite of this skill's offline, subprocess-based approach |
| https://github.com/SmartAI/Chamfer | benchmarks | Medium-High | READMEd in full: not a distance metric but a lean TypeScript CLI agent (multi-provider LLM, build123d/Fusion backends) that validates output with an objective "geometry-kernel oracle" grading exported STEP files, and reports large efficiency gains over Claude-Code-style agents on identical prompts (5.9x cheaper, 3.2x faster, 6.3x fewer tool calls). Worth studying specifically for cutting this skill's own tool-call/round-trip overhead in the part loop, not just for its benchmark methodology |
| https://github.com/SpatiaOS/Procedura | MIT agentic system: text prompt -> editable parametric OpenSCAD program of named parts joined by typed mates; render, critique, patch loop | Medium | Mating-feature library (pegs, sockets, bolt patterns, snaps), compile-check before accepting a program, trajectory logging. OpenSCAD only, no printability checks |
| https://github.com/gizmuf/voice-to-3d-print | Pulsai 3D: AGPL AI-first parametric CAD (build123d); chat / voice / images -> editable models and print files | Medium | Revision records (source, parameters, mesh hash) and the rule that a failed build never replaces the last valid model (see the undo/rollback idea). AGPL: patterns only |
| https://github.com/SpatiaOS/P3D-Bench | Benchmark: can multimodal LLMs write parametric 3D programs (CadQuery output); scores executability, geometric fidelity, topology, part structure | Medium | Metric set and staged infer-compile-score pipeline for `evals/`; code MIT, dataset non-commercial |
| bernhard-42/jupyter-cadquery | Jupyter viewer for CadQuery | None | Evaluated and rejected in the TODO skill-improvement list: no viewer in this pipeline |
| https://github.com/filaPro/cad-recode | ICCV 2025: point cloud -> CadQuery code; models and datasets on Hugging Face | Medium | Source for the reverse-engineer-mesh backlog item and a CadQuery corpus; check LICENSE.md before reuse |
| https://github.com/JBpeople/ai-cadquery | MIT FastAPI + React web app: natural language -> CadQuery -> STL / STEP / .py export | Low | Sample prompts for printable parts (brackets, gears) as eval requests; nothing else beyond the existing part loop |
| https://github.com/Mr-Though/cadquery-skills | Claude Code / OpenCode skills for CadQuery 2.8.0 with a platform-neutral `core/` (system prompt, style guide, API cheatsheet, patterns, examples) | Medium | Diff its `core/` references against `reference/CadQuery Pattern Reference.md` for missing API coverage; no printing constraints |
| https://github.com/danwahl/cadqueryeval | Inspect AI benchmark: 25 CadQuery part descriptions run in a Docker sandbox, STL graded against reference geometry | Medium-High | Mesh gates (every edge shared by exactly two faces, single component, bbox, volume, Chamfer + Hausdorff), merge near-duplicate vertices before checks, seed RNG, rescore stored logs without model calls, accept alternate references; the 25 tasks as extra eval cases |
| https://get-quot3d.com/technology | Instant quoting with a purpose-built slicing engine (commercial, no code) | Low | Nothing actionable |
| https://multipart3d.com/ | Splits large parts (name-only entry, not read) | Low-Medium | Auto-split for parts larger than the bed; relates to the backlog item on covering more of the print workflow |
| https://pypi.org/project/estampo/ | Reproducible slicer settings (PyPI page failed to load, not read) | Low-Medium | Possible input to calculating and exporting slicer parameters; unverified |
| https://github.com/pfrankov/slicer-copilot | Node CLI: an LLM proposes slicer-setting changes for a Bambu `.3mf` project, geometry untouched | Medium | Guardrail pattern (model may only touch an allowlisted parameter set, per-change rationale, dry-run preview); fits the backlog item on calculating and exporting slicer parameters |
| https://deepwiki.com/jarczakpawel/OrcaStudio/3-core-slicing-engine-(libslic3r) | Wiki of the libslic3r core slicing engine | Low-Medium | Reference if support volume is ever computed with a real slicer instead of the overhang model (see NSV score) |
| https://github.com/VinukaThejana/slicer_rs | Rust API for print cost | Low | Nothing beyond the cost calculators below |
| https://github.com/GladiusSlicer/GladiusSlicer | Rust slicer, old | Low | Nothing |
| https://github.com/khushiyant/kerf | Open IR for mesh -> G-code with `kerf verify` / `kerf diff` (`pykerf.verify_gcode` returns JSON); planar only, resolution-bounded | Medium | G-code verification for the G-code simulator backlog item: check a sliced print deposits the expected material, compare slicers |
| https://github.com/Ultimaker/CuraEngine | Cura slicing engine (AGPL) | Low-Medium | Optional external for real print time / support volume; never bundled |
| https://github.com/prusa3d/PrusaSlicer | PrusaSlicer (AGPL) | Low-Medium | Optional external for real print time / support volume; never bundled |
| https://github.com/jkga/3dpcalc | 3D print cost calculator | Low | Cost formula reference only |
| https://github.com/Gluhy/3d-print-pricer | 3D print cost calculator | Low | Cost formula reference only |
| https://github.com/VishalPatra/3dprintcostcalculator | 3D print cost calculator | Low | Cost formula reference only |
| https://github.com/AndreasReitberger/3D-Print-Cost-Calculator | 3D print cost calculator | Low | Cost formula reference only |
| https://github.com/pyrech/gcode-estimator | G-code print time / cost estimator | Low-Medium | Candidate estimator for the G-code simulator item next to `klipper_estimator`; not evaluated |
| https://create.slant3d.com/ | Building-blocks style configurator example | Low | Not evaluated |
| https://completecalculators.com/calculators/3d-printing/infill-weight-strength-calculator | Infill weight / strength calculator | Low | Formula reference for the weight estimate in the G-code simulator item |
| https://github.com/JustinSDK/cqMore | Adds more fundamental API to CadQuery (JustinSDK) | Medium | Candidate helper / block source; see Details: cqMore and cqterrain |
| [medicationforall/cadqueryhelper](https://github.com/medicationforall/cadqueryhelper) | Small CadQuery primitive helpers (25 stars, active) | Low-Medium | Open: borrow individual functions for `blocks/` (reimplement) -- [details](#cadqueryhelper) |
| [medicationforall/cqterrain](https://github.com/medicationforall/cqterrain) | CadQuery terrain/tabletop generators; rated High usability in `Block_Sources.md` | Medium | Open: block candidates -- [details](#cqterrain) |
| [BOSL2](https://github.com/BelfrySCAD/BOSL2) / [NopSCADlib](https://github.com/nophead/NopSCADlib) / [MCAD](https://github.com/openscad/MCAD) | OpenSCAD libraries | Low-Medium | Reference only (formulas, standard-part sizes); BOSL2 attachment concept -> [BOSL2-style anchors](../TODO.md#bosl2-style-anchors). No import possible |
| [cqparts/cqparts](https://github.com/cqparts/cqparts) | CadQuery parts/assembly wrapper framework, unmaintained since 2020 | Low | Not adopted: assembly abstraction conflicts with the direct-Workplane block pattern -- [details](#cqparts-not-adopted) |
| [michaelgale/cq-gridfinity](https://github.com/michaelgale/cq-gridfinity) | Pure-CadQuery Gridfinity generator | High | Done: reimplemented as `blocks/gridfinity.py` |
| [sameer/orient-stl](https://github.com/sameer/orient-stl) | FDM orientation search via DIRECT global optimization | Medium | Open: overhang-area + slice-count fitness as a cross-check score in `print_orientation.py` -- [details](#orientation-scoring-orient-stl) |
| CADReasoner (CVPR 2026) / CADCodeVerify ([arXiv 2410.05340](https://arxiv.org/abs/2410.05340)) | Render -> auto-generated validation questions -> regenerate loop | Medium | Open: feed preview renders + check questions into the gate's correction prompts -- [details](#iterative-visual-feedback-repair) |
| FreeCAD-AI | LLM FreeCAD agent with per-project design-rule file (`AGENTS.md`) | Medium | Open: per-project FDM design-rule file consumed by the gate -- [details](#diagnostics-as-assertions) |
| [ProCAD](https://arxiv.org/abs/2602.03045) | Clarify-then-generate for text-to-CadQuery | Medium-High | Ask ONLY when necessary; question budget and skip escape hatch -- see Details: spec audit ambiguity categories |
| [LLM4CAD-Editor](https://arxiv.org/abs/2606.20607) | Edit-intent taxonomy for CAD editing | Low-Medium | Functional / operation / parameter intent levels; already mirrored by typed `request_log` entries |
| [CADDesigner](https://arxiv.org/abs/2508.01031) | Requirement-analysis stage before CAD generation | Low-Medium | Prior art for Phase 1 requirements capture (`REQUIREMENTS.md` already shipped) |
| [SEG / ODPO](https://arxiv.org/abs/2511.16434) | Self-supporting shape generation; defines the Normalized Support Volume score | Medium | NSV = support volume / model volume as a scale-invariant orientation and gate score; model itself has no public code -- see Details: NSV score |
| [rishigundakaram/cadquery-mcp-server](https://github.com/rishigundakaram/cadquery-mcp-server) | CadQuery MCP server with `verify_cad_query` (geometry vs natural-language criteria) | Low-Medium | LLM intent-match verifier; overlaps the cadgate-style item -- see Details: verify-against-criteria tool |

## Open ideas

Open items carried over from the former TODO "Related ideas" section. Items in
**bold** became TODO "Top 10" items. Everything else is kept here with its
background in [Details](#details); promote one to TODO.md when it is picked up.

**Parametric CAD libraries**
- `vibe-cading` -- [details](#vibe-cading)
- `cadqueryhelper` -- [details](#cadqueryhelper)
- `cqMore` and `cqterrain` -- [details](#cqterrain)
- `partcad/partcad` -- [details](#partcad)

**Print orientation (Tweaker-3)** -- the table row says all three ideas landed in
`print_orientation.py`; these two boxes were never ticked in TODO. Verify and close:
- area-cumulation candidate generation as a fallback/supplement
- `min_build_height` / volume-minimization mode

**Independent changes**
- cadgate-style gate checks -- [details](#cadgate-style-gate-checks); the differential half is **TODO Top 10 #7**
- `get_parameters`: extract customizable params from a script for parametric re-runs -- [details](#get_parameters)

**Benchmark corpora for `evals/`**
- SadilKhan/Text2CAD (blocked on a DeepCAD-sketch->CadQuery converter) -- [details](#text2cad)
- Metric: executability / syntax pass rate -- [details](#metric-executability-pass-rate)
- Metric: volumetric IoU / Dice (alongside `chamfer_mm`) -- [details](#metric-volumetric-iou)
- Metric: prompt-difficulty stratification -- [details](#metric-prompt-difficulty)
- Metric: efficiency -- superseded by **TODO Top 10 #1**
- Not adopted: SmartAI/Chamfer's STEP geometry-kernel-oracle validity check (overlaps `cq_verify.py` / `script_lint.py`)

**From market research**
- Diagnostics-as-assertions -- [details](#diagnostics-as-assertions); the design-rule-file half is **TODO Top 10 #9**
- Normalized Support Volume (NSV) score -- [details](#nsv-score)
- Orientation scoring (orient-stl) as a cross-check -- [details](#orientation-scoring-orient-stl)
- Iterative visual-feedback repair loop (CADReasoner, CADCodeVerify) -- [details](#iterative-visual-feedback-repair)
- Verify-against-criteria tool (CadQuery-MCP) -- covered by the cadgate-style item

**From intent-recognition research**
- Spec audit with named ambiguity categories -- [details](#spec-audit-ambiguity-categories)
- Under-specified eval cases -- **TODO Top 10 #10** ([details](#under-specified-eval-cases))

**From the SmartAI/Chamfer efficiency study** ([study](#smartaichamfer-study))
- Per-attempt efficiency telemetry -- **TODO Top 10 #1**
- Failure-mode mining -> environment-facts block -- **TODO Top 10 #4**
- Fold verification into the build call -- [details](#fold-verification-into-build-call)
- One reconciliation pass, from measured values -- **TODO Top 10 #6**
- Render economy (agent self-inspection renders only) -- [details](#render-economy)
- Output-token economy -- folded into **TODO Top 10 #6**
- Assumption pinning -- **TODO Top 10 #5**
- Warm kernel process (needs measurement first) -- [details](#warm-kernel-process)
- Context-surface audit -- [details](#context-surface-audit)
- Eval method: held-out set, pre-registered bars -- [details](#eval-method-held-out-set)

**From high-rated entries**
- CadAgent: token budget management for the part loop -- [details](#cadagent-token-budget-management)
- CadAgent: smart clarification policy -- folded into **TODO Top 10 #5**
- CadAgent: undo/rollback via automatic snapshots -- [details](#cadagent-undorollback-snapshots)
- harnesscad: pre-kernel geometry-aware verification -- **TODO Top 10 #2**
- Text2CAD (MLYengineering): repair patches + cross-attempt learning -- **TODO Top 10 #3**
- Claude-To-Print multi-color 3MF -- **TODO Top 10 #8**

## Details

### Integration strategies
Integration strategy per item avoids the native-vs-MCP false binary.
Options, by how much they preserve upstream updates while staying
self-contained and inline (no MCP):
- **reimplement** -- own code; no upstream updates; on-design.
- **pinned dep** -- declare as a uv git/pip dep, call from a thin `src/`
  adapter; updates via `uv lock --upgrade-package` (same as the existing
  `cq-warehouse` dep); self-contained via the committed lock.
- **vendored snapshot** -- copy source into the repo with license + recorded
  upstream SHA + a documented refresh procedure; manual updates.
- **optional external** -- native by default, use the external tool if
  present, degrade with a warning otherwise (same pattern as
  `kinematic_check.py` without `python-fcl`); off the critical path.

### Gear geometry
lwidm/cq_gears -- strategy: optional external -- DONE. Parametric involute
spur/helical gear generator for CadQuery. Fails the license test for pinned
dep / vendored snapshot: upstream declares no license (`license: null`), and
this project is PolyForm Noncommercial, so bundling isn't safe. No gate
check applies either (nothing is installed or called natively to degrade),
so the integration point is the planning prompt: rule 13 in
`prompts/planning.md` tells the LLM to note in `planning_notes` and point to
the repo as a downloadable resource when a design needs gears, instead of
inventing gear geometry from scratch. Also added to the README Prior-art
table.

### Parametric CAD library survey
GitHub survey of reusable OpenSCAD/CadQuery/build123d model libraries (2026-07),
rated for usability as `src/blocks/` additions. Full ratings table in
session history; summary below. Confirms `cq_warehouse` (already a pinned
dep) is the strongest direct-reuse candidate; everything else is
reference-only or needs hand-porting.

#### cq-gridfinity
michaelgale/cq-gridfinity, 200 stars, active -- strategy: reimplement
(blocks) -- pure CadQuery, narrow domain. Teardrop/bridged-hole DFM pattern
already tracked under [Print-friendly parameterizations](#print-friendly-parameterizations);
no separate action beyond that item.

#### vibe-cading
fa-mc/vibe-cading, 5 stars, active -- strategy: reimplement (blocks) --
CadQuery + LLM-agent-oriented typed-parameter part classes (screws, gears,
joints, bearings, heat-set inserts, hinges, standoffs); closest
philosophical match to this skill's block pattern. Low stars/immature --
cherry-pick specific parts as reference when adding new blocks, not a
dependency.

#### cadqueryhelper
medicationforall/cadqueryhelper, 25 stars, active -- strategy: reimplement
(blocks) -- small CadQuery primitive helpers, borrow individual functions if
needed.

#### OpenSCAD libraries (reference only)
BOSL2 (BelfrySCAD/BOSL2, 2252 stars, very active), NopSCADlib
(nophead/NopSCADlib, 1602 stars), MCAD (openscad/MCAD, 681 stars) --
OpenSCAD, not Python; no direct import possible. Reference only for
formulas/dimensions (threading, gears, standard-part sizes) when a new block
needs a formula `cq_warehouse` doesn't cover. No action.

#### bd_warehouse (reference only)
gumyr/bd_warehouse, 96 stars, active -- build123d, not CadQuery; the
actively-maintained successor to `cq_warehouse` with broader
fastener/thread/gear/pipe coverage. Reference only (hand-port on demand)
since the kernel wrapper API doesn't match. No action.

#### cqparts (not adopted)
cqparts/cqparts, 148 stars, unmaintained since 2020 -- wrapper framework,
assembly abstraction conflicts with this skill's direct-Workplane block
pattern. Not adopted.

#### cqterrain
https://github.com/medicationforall/cqterrain: `documentation/Block_Sources.md`, rated High usability

#### partcad
`partcad/partcad` (`documentation/related_projects.md`) -- package manager
for hardware/manufacturable products across CAD kernels (CadQuery,
build123d, OpenSCAD). Adoptable: package-manager framing for versioned part
definitions with declared metadata (parallels `blocks/inventory.json`), YAML
assembly format tracking BOM/part relationships, caching rendered models to
speed iteration. Not evaluated for adoption strategy yet (reimplement /
pinned dep / reference-only).

### Print orientation Tweaker-3
One change -- strategy: reimplement. Clean-room native port of the
orientation formulas. Tweaker-3 is GPL-3.0 and this project is PolyForm
Noncommercial; bundling (pinned dep / vendored snapshot) is
license-incompatible, so we reimplement the algorithm (formulas are not
copyrightable) and do NOT copy the GPL code or its verbatim tuned constants
-- derive our own. Touches `print_orientation.py` + `mesh_io.overhang_metrics`,
tested via `test_print_orientation.py`.

### CadQuery authoring guidance
jmwright/cadquery-llm-skill, one change -- strategy: vendored snapshot.
Doc-only; vendoring a doc snapshot is the upstream-recommended usage, so no
design conflict. Record the upstream SHA and refresh periodically. Upgrades
`reference/` and `prompts/part.md`.

Done (change `add-cadquery-anti-patterns`): anti-patterns integrated as
`reference/CadQuery Anti-Patterns.md` (kernel / stateful-context /
API-mechanic tiers, always-injected) plus fluent recipes folded into the
pattern reference and three contradictions reconciled. Free Function API
(`cadquery.func`) content deliberately excluded -- this pipeline is
fluent-only.

### OCC deepcopy crash
`debug/occ-error.md`: rotating certain B-rep solids (seen in
`build/plate.py`, an axle bore spanning an open slot, or a pure-45-deg
pocket ceiling with no flat cap) crashes inside cq_warehouse's
deepcopy-based `Shape.copy()` -> OCC `BinTools` serialization round-trip
(`Standard_Failure: BinTools_SurfaceSet::ReadGeometry: UnExpected
BRep_PointRepresentation = 42`, sometimes flaky). **Fixed** (see DONE.md); original
leads kept for history: replace cq_warehouse's deepcopy copy
with OCC's native `BRepBuilderAPI_Copy`; or make `write_assembly.py` rotate
the trimesh (mesh-based) for print-oriented 3MF objects instead of the
B-rep, sidestepping the deepcopy path entirely (the kinematic-check STLs
already do this).

### cadgate-style gate checks
Strategy: optional external (off the critical path; gate runs natively,
cadgate augments when present). Differential geometry (volume/bbox/wall
delta vs base) reimplemented in `quality_gate.py`; the LLM intent-match is
the part that justifies the optional external path.

### get_parameters
Extract customizable params from a script for parametric re-runs
(CadQuery/cadquery-contrib mcp-server) -- strategy: reimplement (tiny).

### Chamfer-distance metric
DeepCAD evaluation metric: Chamfer distance for golden-mesh regression tests
-- strategy: reimplement (trimesh already computes it). Done: `chamfer_mm`
in `evals/run_evals.py`, matched to golden parts via
`scipy.optimize.linear_sum_assignment` over shape descriptors. See the
[benchmark corpora survey](#benchmark-corpora-survey) for what should feed
it.

### Benchmark corpora survey
`documentation/related_projects.md` text-to-CAD datasets. Of the ~119
surveyed projects, five are actual prompt-to-result *corpora* (not just
technique ideas) that could seed `evals/cases/`. Rated for adoption as a
benchmark below.

#### Text-to-CadQuery corpus
arXiv 2505.06507; rows "Text-to-CadQuery (arXiv 2505.06507 + code)" and
duplicate "Text-to-CadQuery/Text-to-CadQuery" -- **High**. ~170k
text->CadQuery code pairs, native CadQuery format, zero conversion cost --
runs through `run_cadquery_model.py` unmodified. Already the origin of the
`chamfer_mm` idea. Gap: nobody has sampled a subset into `evals/cases/` yet.
Strategy: reimplement a small corpus-import script that filters the 170k
down to this skill's domain (enclosures/brackets/plates/adapters -- not
organic/decorative shapes), executes each script to produce `golden/*.stl`,
and writes `request.md` from the pair's description.

#### WKJBryan/cadquery-library
**High, complementary**. 2600+ native CadQuery examples, hand-curated (vs.
Text-to-CadQuery's auto-generated 170k) -- better signal-to-noise for a
small eval corpus, less coverage. Same import strategy as above; adopt in
full given the smaller size.

#### Text2CAD
SadilKhan/Text2CAD + duplicate Text2CAD (DFKI / NeurIPS) -- **Medium**. Real
multi-level (beginner->expert) text-difficulty annotations that this skill's
own corpus lacks, but the paired geometry is DeepCAD sketch-extrude JSON,
not CadQuery -- needs a converter that doesn't exist today (closest analog,
`convert_build123d.py`, targets a different kernel). Worth the
prompt-difficulty tiers even if the geometry pairs are skipped; blocked on
the converter.

#### DeepCAD (no action)
rundiwu/DeepCAD -- **Low**. Same non-CadQuery format problem as Text2CAD,
without even the text pairing -- it's the substrate Text2CAD is built on,
not independently useful. No action beyond what Text2CAD covers.

#### mecagent-test (no action)
mehsenazizi/mecagent-test-Mehsen-AZIZI -- **Low**. Take-home-exercise scope,
too small to be a corpus; its IOU eval idea duplicates rawwerks/VibeCAD's
(already noted there). No action.

#### Metrics to add
Alongside the existing first-shot pass rate / attempts-to-pass /
`chamfer_mm` / cost-per-part in `evals/run_evals.py`, in priority order:

##### Metric executability pass rate
Fraction of a corpus's scripts that run without error on attempt 1. This is
the metric the Text-to-CadQuery paper itself reports, so it's the natural
apples-to-apples number when citing that corpus. Strategy: reimplement (the
wrapper's `success`/`errors` fields already carry this per attempt; just
aggregate).

##### Metric volumetric IoU
(rawwerks/VibeCAD row) -- add alongside `chamfer_mm`, not instead of it:
Chamfer averages surface distance and can look fine when a small protrusion
or hole is simply missing, which IoU catches directly. Strategy: reimplement
via `trimesh.boolean` intersection/union on the same centered, matched mesh
pairs `run_evals.py` already produces.

##### Metric prompt difficulty
Prompt-difficulty stratification (SadilKhan/Text2CAD's beginner->expert
tiers) -- bucket eval cases by description complexity and report pass
rate/chamfer per tier instead of one flat scorecard, so degradation on terse
vs. detailed requests is visible. Depends on the [Text2CAD](#text2cad) corpus
item above (or hand-tagging the existing/new cases).

##### Metric efficiency
Tool-calls / iterations / wall-clock per case (SmartAI/Chamfer row,
sidbalasubramanian007/Aipex-Lab-Research row) -- `attempts-to-pass` already
exists in `run_evals.py`; add raw tool-call count and wall-clock alongside
cost/part so loop-efficiency regressions (not just correctness regressions)
show up in the scorecard. Superseded/expanded by
[Efficiency telemetry](#efficiency-telemetry) below.

Explicitly not adopted: SmartAI/Chamfer's STEP geometry-kernel-oracle
validity check overlaps what `cq_verify.py`/`script_lint.py` already do at
construction time, so it wouldn't add a new failure class here.

### Market research survey
`documentation/market_research.md`: recent LLM-CAD / parametric /
FDM-printability projects surveyed 2023-2026. The central finding: LLM-CAD
tools stop at "valid geometry" while printability work (support,
orientation, self-supporting design) lives in separate pipelines -- bridging
them inline is this skill's clearest opening. Items below are the reusable
primitives, not whole-tool adoptions.

#### Diagnostics-as-assertions
cad-khana, FreeCAD-AI -- one change -- strategy: reimplement. cad-khana
(`github.com/cyberchitta/cad-khana`) is a Claude Code skill / build123d
wrapper that emits a structured `diagnostics.json` (overhangs, wall
thickness, clearances, interferences) and turns geometric constraints into
build-failing assertions (`assert_min_wall`, `assert_clearance`,
`assert_no_interference`). This is the closest analog to our gate; extends
`quality_gate.py`.
- geometric constraints as build-failing assertions feeding the structured
  `{source, severity, type, message, hint}` contract the gate already emits
- per-project FDM design-rule file (FreeCAD-AI's `AGENTS.md`/`FREECAD_AI.md`
  pattern, e.g. "min wall 1.2mm, all edges >=0.8mm fillet") consumed by the gate

#### NSV score
Normalized Support Volume score (SEG / ODPO, arXiv 2511.16434) -- one change
-- strategy: reimplement. NSV = support-material volume / model volume: a
scale-invariant printability cost (validated against Cura, Pearson r > 0.85
on 50 Thingi10k models). SEG itself is a diffusion model with no public
code; only the *metric* is reusable. Pairs with the Tweaker-3
print-orientation work ([details](#print-orientation-tweaker-3)) (NSV scores
a given orientation).
- NSV as a quantitative gate score / orientation-selection objective in
  `print_orientation.py` (support volume from the overhang+bed-projection model)

#### Orientation scoring orient-stl
Folds into the Tweaker-3 change -- strategy: reimplement.
`github.com/sameer/orient-stl` finds best FDM orientation via DIRECT global
optimization (sub-second). Overlaps the existing Tweaker-3 item; the
overhang-area + slice-count fitness from the build-orientation research
(genetic-algorithm, connected-components, "Part Orientation Fused Shape
Optimization") is the reusable scoring function.
- overhang-area + slice-count fitness as an alternative/cross-check
  candidate score alongside the Tweaker-3 formulas

#### Iterative visual-feedback repair
CADReasoner, CADCodeVerify -- one change -- strategy: reimplement.
CADReasoner (CVPR 2026) and CADCodeVerify (arXiv 2410.05340) close a render
-> diff -> regenerate loop: render the part, auto-generate validation
questions, answer them against the render, feed discrepancies back. We
already render previews (`preview.py`) and run a bounded `claude -p` fix
loop in the gate; this adds the visual-discrepancy signal to that loop.
- feed multi-view preview renders + auto-generated check questions into the
  gate's correction prompts (currently text-only DFM/geometry findings)

#### Print-friendly parameterizations
cq-gridfinity / Gridfinity practice -- strategy: reimplement (blocks).
`github.com/michaelgale/cq-gridfinity` and the wider Gridfinity ecosystem
encode concrete DFM heuristics: "lite" thin shells for less material,
bridge-over (teardrop) magnet/screw holes, variable wall thickness.
Block-library additions, not a gate change.
- teardrop / bridged horizontal holes in `blocks/connectors.py` +
  `blocks/fasteners.py` so bosses and ports stay self-supporting

#### Verify-against-criteria tool
CadQuery-MCP `verify_cad_query` -- strategy: optional external.
`github.com/rishigundakaram/cadquery-mcp-server` exposes a `verify_cad_query`
validator that checks geometry against natural-language criteria. The LLM
intent-match overlaps the [cadgate-style item](#cadgate-style-gate-checks);
same optional-external rationale (native gate runs without it, augments when
present).

### Intent-recognition survey
`documentation/intent_recognition.md`, surveyed 2026-08, split into three
capabilities: **elicitation** (detect an under-specified request and ask),
**scope classification** (what kind of change is asked for, and what may it
touch), **preservation** (does the delivered geometry still satisfy the
user's own words). The skill does elicitation narrowly (topology +
dimensions, Phase 1 only), records intent well (`request_log`), does no
scope classification, and audits every part against the PLAN rather than the
request -- so a plan that misread the request passes every gate. Items
ordered by value/cost; item 1 is the precondition that makes 2 and 3 cheap.
Prior art: ProCAD (arXiv 2602.03045) clarify-then-generate for
text-to-CadQuery, LLM4CAD-Editor (arXiv 2606.20607) functional/operation/
parameter intent levels, CADDesigner (arXiv 2508.01031) requirement-analysis
stage.

Freeze status (`Feature freeze for V1.0`, 12.08.2026): items 1 and 3 target
logged, reproduced failures (the C5 cradle ping-pong; the audit being blind
to the request) and are arguably defect fixes; 2, 4 and 5 were slated as
features for the next version. **Update 2026-08-29:** item 4 was pulled
forward into V1 anyway (see [Canonical intent restatement](#canonical-intent-restatement))
-- the capture half was cheap (a docs-only Phase 1 addition, no schema or
script change) and closes a real gap in what ships. 2 and 5 remain deferred
to the next version; not decided here.

#### Typed request_log entries
DONE -- `openspec/changes/archive/2026-09-01-typed-request-log/`. `level`
(`functional` | `operation` | `parameter`) and `targets` (part ids + named
features/parameters) are optional fields on `request_log` entries
(`src/build_plan_schema.json`, `openspec/specs/request-log/`), settable via
`log.py request add --level --target` and filterable via `log.py request
search --level --target` (`src/log.py`). `render_prompt.py`'s
`section_cuts` re-keys the Step 3 extra-section tiering off `targets` when
present, falling back to the keyword match only for untyped legacy entries.

The routing rule the label exists for (a `parameter`-level entry may not
silently change a sibling part's independently-typed constant -- the C5 cradle
failure class) is a `quality_gate.py` warning via
`openspec/changes/parameter-entry-routing-check/` (`log.py request add
--snapshot-scripts` baseline + `routing_violation`). It is advisory: promotion to
blocking needs eval evidence.
#### Spec audit ambiguity categories
One change -- strategy: reimplement (ProCAD). Generalize Phase 1's topology-
clarification rule (shape ambiguity only) into an audit over a fixed
category list, and re-run it on mid-build corrections, where ambiguity is
most expensive because parts already exist. ProCAD's contribution is asking
ONLY when necessary -- a rule that fires on every request is worse than
today's; the question budget and the skip-entirely escape hatch (as the
dimension checkpoint already has) are load-bearing. Category-named prompting
beats a bare "ask if unsure" (arXiv 2504.12113).
- categories: topology (exists), missing dimension, conflicting constraint,
  unstated reference frame (the C5 compass-language defect), unstated
  fit/load, part-vs-assembly scope
- one question per ambiguity under a hard budget, keeping the existing named
  either/or discipline -- extends `skill/phase1_requirements.md`, no new phase
- re-audit a mid-build correction before acting on it
  (`skill/phase3_build.md` correction handling)

#### Request-relative acceptance
DONE -- `openspec/changes/archive/2026-09-01-request-relative-acceptance/`.
Both the autonomous implementation audit and the progressive inline
self-review now carry a "Request conformance" question class (group 3 in
`prompts/audit.md`): the approved `intent` (falling back to the
`request_log` `initial` entry) plus every entry scoped to the part via
typed `targets` or a keyword match (`render_prompt.py`'s `scoped_request`),
fed to the reviewer as `REQUEST_TEXT`. A `no` there is `severity: advisory`
-- it does not fail the review or consume a retry -- unless the same
discrepancy also fails a group 1/2 (plan-conformance/universal) question, in
which case it is `severity: blocking` with the request text cited as
supporting evidence. The no-script rule is unchanged: the auditor still
never receives the part script. Promotion of advisory findings to blocking
by default remains eval-gated and has not been done -- that is item 5,
[Under-specified eval cases](#under-specified-eval-cases).

#### Canonical intent restatement
DONE 2026-08-29 -- strategy: reimplement. Merges two standing items ("intent
based prompt reformulation", "regenerate the whole project from scratch with
a new LLM session"): a frame-explicit, user-confirmed restatement of what is
being built, carried forward and updated as corrections land. Also the
natural input to [Request-relative acceptance](#request-relative-acceptance)
and the structural fix for compass-language defects -- restatement forces
the reference frame to be written down instead of assumed.

Shipped as `REQUIREMENTS.md`, a project-root artifact beside `parameters.py`
(resolving the "where it lives" question in favor of a sibling file, not a
plan field): intent, confirmed topology reading, dimensions, fit
requirements, resolved DFM constraints, and open questions/assumptions.
`skill/phase1_requirements.md` writes it at the same checkpoint as
`parameters.py`; `skill/phase2_planning.md` amends it in place if planning
introduces or changes a requirement (bounded role, `planning_notes`-style
current-state-only -- not a changelog). See
`openspec/changes/capture-requirements-spec/` for the proposal and spec
delta.

Deliberately deferred (see that change's `design.md`): no quality-gate
presence check yet (mirrors how `parameters.py`'s own gate check shipped as
a separate follow-up change after the convention existed), and it is not
yet wired into [Request-relative acceptance](#request-relative-acceptance)
or the reference-frame check the compass-language defect needs -- those
still require the auditor to actually read and check against this file,
which is the remaining work under [Intent as invariant](../TODO.md#intent-as-invariant).

#### Under-specified eval cases
One change -- strategy: reimplement (gating cost). Every case in
`evals/cases/` is well-specified, so none of the above can regress and the
existing scorecard cannot see it. This is the gate on the whole idea, not an
afterthought.
- cases whose `request.md` is deliberately under-specified in each named
  category, scored on whether the right question was asked
- well-specified controls scored on NOT asking -- without them the metric
  rewards asking about everything
- `evals/run_evals.py` scoring + `tests/test_eval_corpus.py`

### SmartAI/Chamfer study
github.com/SmartAI/Chamfer @ a8f1c59, read 2026-08. Chamfer is a TypeScript
CAD agent over a build123d MCP server. Its `benchmarks/` directory is the
interesting part: a four-arm head-to-head (Chamfer v0/v1, Claude Code,
Codex) on a held-out set, same model, same MCP server binary for every arm,
graded by a geometry oracle on the exported STEP. Result: equal correctness
at **5.9x lower cost and 3.2x lower wall-clock than Claude Code** -- 6.5 vs
9.2 agent turns, 2,232 vs 9,849 output tokens, ~53k vs ~433k context tokens
read per run.

The gain is explicitly NOT model, kernel, or a cleverer algorithm. Their own
decomposition (`benchmarks/analysis/v0-weaknesses.md`, 21 graded runs):
**~46% of cost is output tokens** (on the hardest case 55% of those are
hidden reasoning), ~33% cache write, ~21% cache read; latency splits ~68%
LLM / ~32% tool. So the levers are (a) how much context is read per turn,
(b) how many output tokens are emitted, (c) how many tool round-trips happen
at all -- in that order. Verification was measured to be **cheap** (~15% of
cost) and is not a lever.

Negative results from the same study, worth as much as the positives -- do
not repeat them:
- **Global thinking=low**: <20% cost saving, dropped checks on two cases.
  Rejected.
- **"Complexity-scaled" verification** (skip the reconciliation pass on
  simple parts): worse on cost AND correctness than not doing it -- one case
  collapsed to 8/15 with an over-claim. Recorded lesson: "verification is
  not overhead to scale away; on interacting-feature parts it is the
  cheapest part of the run."
- Their pattern card (23 mined idioms) was bundled with the two changes
  above, so its own effect is **unmeasured** -- treat it as untested, not as
  proven.
- Standing method rule they adopted after drifting: one intervention at a
  time, each traced to a weakness observed in real run transcripts,
  pre-registered metric movement per change.

Items below are ordered by value/cost. Item 1 is the precondition: none of
the rest can be shown to work without it. (Their STEP geometry-kernel oracle
stays not-adopted, per the [Benchmark corpora survey](#benchmark-corpora-survey)
above -- `cq_verify.py`/`script_lint.py` already cover that failure class.)

#### Efficiency telemetry
One change -- strategy: reimplement. `build/attempts.jsonl` records
`prompt_chars` and `model` and nothing about what the attempt actually cost.
Chamfer's entire analysis is a decomposition our log cannot produce. This
supersedes and fills in [Metric: efficiency](#metric-efficiency) above (raw
tool-call count + wall-clock); the split below is what made their table
actionable.
- `telemetry.py`: optional `tokens` (`in`/`out`/`cache_read`/`cache_write`),
  `cost_usd`, `wall_ms`, `llm_ms` vs `tool_ms`, `tool_calls`,
  `failed_tool_calls` -- all OPTIONAL, existing logs must stay valid
  (`tests/test_telemetry.py`)
- per-tool table: calls, mean duration, result payload size (chars/image
  tokens) -- their finding was that one tool (`render_view`) was 11.5% of
  suite wall for zero model changes, which is invisible without
  payload/duration per tool
- failed-call retry cost: time from a failed call to the next successful
  attempt (they measured ~6% of suite wall lost to 15 failed calls across
  52% of runs)
- `evals/run_evals.py`: aggregate the above into the scorecard next to
  `first-shot rate` / `attempts-to-pass` / `chamfer_mm`, so a loop-efficiency
  regression is visible without correctness moving

#### Failure-mode mining
One change -- strategy: reimplement. Their single biggest robustness win was
four sentences of environment facts in the system prompt, each traced to a
counted failure (missing `from build123d import *`; calling MCP tool names
inside the sandbox; blocked builtins; wrong `expected` schema). That killed
11 of 15 failed tool calls. Our equivalent facts (what the wrapper injects
on `PYTHONPATH`, that `result` may be a `dict[str, Workplane]`, what
`--deliver` changes about STL paths, which `cq_verify` helpers exist) are
spread across `prompts/part.md` and `skill/phase3_build.md`.
- mine `error_types` frequencies out of accumulated `build/attempts.jsonl`
  logs and rank them -- interventions must be evidence-led, not guessed
- a short "facts about the run environment" block at the top of
  `prompts/part.md`, one line per counted failure class, replacing scattered
  prose
- check each mined class against `script_lint.py` first: anything the
  linter can catch deterministically should NOT become a prompt line

#### Fold verification into build call
One change -- strategy: reimplement. Chamfer's `execute` auto-echoes
volume/bbox/face count, and `find_holes(part)`/`measure(obj)` are callable
**inside** the sandbox -- so the measured hole inventory comes back with the
build, not from a separate round-trip. On the pulley case that was 4 tool
calls vs Claude Code's 9 turns for the same verified part.
`run_cadquery_model.py` already returns `geometry` this way; the per-part
checks are still separate processes, each paying a fresh OCC import.
- emit the measured interface/feature inventory (what
  `feature_presence_check.py` asserts) inside the wrapper's existing JSON
  contract, as an additive key -- one subprocess produces build + measured
  evidence
- same for `edge_treatment_check.py`'s classify pass where it needs the
  same shape
- keep the standalone CLIs (build-frame reruns, tests); the JSON key is the
  fast path

#### One reconciliation pass
One change -- strategy: reimplement. Their v1 rule: verify with measured
evidence in ONE pass -- check every requested dimension, hole count AND
diameter, feature position **from measured coordinates, not from the
variables you set**, then stop; no further rounds unless a mismatch
appears; never claim correctness while a discrepancy is open. Two findings
behind it: positions were recited from input constants in 21/21 runs
(nothing numeric ever checked them), and open-ended self-verification
bloated cost by 21% with no correctness gain.
- a single-pass reconciliation rule in `skill/phase3_build.md`, explicitly
  bounded ("do not loop extra verification rounds unless a mismatch appears")
- "measured, not recited": a part's self-report must quote wrapper/check
  output, never restate its own `PARAMETERS` block
- "no completion claim while a discrepancy is open" as an explicit gate line

#### Render economy
One change -- strategy: reimplement (scoped). Their F5: 18 mandatory
renders, 5.8s and ~1,150 image tokens each, and **zero** model changes ever
followed one -- the largest clean saving they found. Not transferable
wholesale: our previews also feed user checkpoints and the visual-review
agent, which is a real signal, not a ritual. The rule applies only to
agent-internal self-inspection renders.
- make the autonomous part agent's own re-render conditional: render when
  the part has features a bbox/interface inventory cannot confirm, skip when
  it repeats what the measured checks already proved -- user-facing
  checkpoint renders stay mandatory
- count renders and their token cost per part in the
  [efficiency telemetry](#efficiency-telemetry) first; demote nothing until
  the count is measured here rather than borrowed

#### Output-token economy
One change -- strategy: reimplement. Output tokens are ~46% of cost and
dominate serial decode time; Claude Code's 4.4x output ratio maps almost
directly onto the 3.2x wall-clock gap. Their fix is one prompt line: the
final message is assumptions (if any) + one summary line, no
feature-by-feature recap -- the reconciliation pass already proved the
features.
- bound the per-part completion report in `prompts/part.md` /
  `skill/phase3_build.md` (the recap duplicates the plan and the check
  output)
- measure it as its own change -- it is the one v1-eff ingredient not
  implicated in that arm's correctness regression, but it was never
  measured alone either

#### Assumption pinning
One change -- strategy: reimplement. Zero assumption statements in 21/21
runs, while structurally divergent readings shipped silently (bearing bore
along X in two reps, along Y in the third, same prompt). Their v1 line: if a
dimension or placement is underdetermined, choose the standard engineering
reading and state it in one line before building. This is the same defect
class as the C5 compass-language and reference-frame items at the top of
this file, and it is far cheaper than the elicitation machinery in the
intent-recognition section -- it does not ask the user anything, it just
makes the coin-flip reviewable.
- one-line assumption statement before building, wherever a
  frame/axis/facing/datum is underdetermined -- `prompts/part.md` and the
  Phase 3 correction path
- land it as a `request_log` entry so the assumption survives the session
  (ties into [Typed request_log entries](#typed-request_log-entries) above)

#### Warm kernel process
One change -- strategy: reimplement -- needs measurement first. Chamfer
keeps one MCP server alive per conversation (`lifecycle: "keep-alive"`), so
the kernel is imported once and a failed step is fixed by re-running only
the failing snippet. Every `run_cadquery_model.py` invocation pays a fresh
interpreter + OCC import. Their tool timings put `execute` at 1.3s against
`inspect_part` at 2.1s and `render_view` at 5.8s, so process startup is a
real fraction of tool time, and tool time was ~32% of wall.
- measure first: cold OCC import cost per attempt vs. total attempt wall
  ([efficiency telemetry](#efficiency-telemetry))
- only if it pays: a keep-alive worker that re-executes the whole script in
  a warm interpreter -- NOT incremental session state. A fresh namespace per
  run is a correctness property here (the script file is the deliverable
  and must stand alone); their "re-run only the failing snippet" habit
  trades that away and is not adopted
- the same warm process should serve the trimesh/fcl whole-model checks,
  which pay their own import cost per invocation

#### Context-surface audit
Folds into the [context-creep restructure](../TODO.md#context-creep-restructure)
above. Their 8x context gap came from tool schemas and general scaffolding
read every turn: 6 curated tools and a one-screen system prompt vs 59 tool
schemas. Our analog is not tool schemas but phase documents and reference
files -- `skill/phase3_build.md` alone is ~1,090 lines, and
`reference/scripts.md` indexes ~30 scripts of which any one part uses a
handful. This is evidence for the standing context-creep restructure item,
with a measurement attached rather than a feeling.
- measure context tokens read per phase per part
  ([efficiency telemetry](#efficiency-telemetry)) before choosing between
  the three restructure options already listed under `Tasks for next version`
- per-phase curated script/reference subsets, so a part loop does not carry
  the planning and export surface

#### Eval method held-out set
One change -- strategy: reimplement. Every case in `evals/cases/` is public
and readable during skill iteration, so the scorecard cannot distinguish
"the skill got better" from "the skill got tuned to these cases". Chamfer's
protocol: a public dev set for iteration, a git-ignored private test set
read exactly once after a freeze commit, N=3 repetitions, and the success
bar written down BEFORE tuning (theirs: v1 > v0 on correctness, else >= 25%
cost/latency improvement at equal correctness). They then reported honestly
that v1 met neither bar.
- a git-ignored `evals/private/` test set with the same case schema, never
  read during skill development, run at release freezes
- N repetitions per case with per-case variance in the scorecard -- their
  whole "structural divergence" finding came from comparing reps of one
  prompt
- over-claim as a scored metric: the run claims completion while the
  quality gate has open findings (their `detectOverClaim` is a five-line
  check over the final message plus the grade -- we have both)
- write the pass bar into the release checklist before the tuning round,
  not after

### CadAgent token budget management
CadAgent (github.com/SSSSSia/CadAgent), rated **High** in
`documentation/related_projects.md` -- an LLM-agent-powered FreeCAD
workbench. Its token-budget management tracks how much context an agent
turn is about to consume and trims/summarizes proactively, rather than
reacting after hitting a limit. Directly relevant to this skill's
context-heavy part loop (`prompts/part.md`, `skill/phase3_build.md`) --
overlaps the standing [context creep restructure](../TODO.md#context-creep-restructure)
item. CadAgent's Progressive Context Injection (loading reference/script
content incrementally rather than all at once) is the same idea and should
fold into that restructure decision rather than tracked separately.

### CadAgent smart clarification policy
CadAgent, same row. Instead of always stopping to ask when a parameter is
underspecified, auto-assume a reasonable default and state the assumption,
escalating to a question only past some ambiguity threshold. Overlaps
[Spec audit ambiguity categories](#spec-audit-ambiguity-categories) and
[Assumption pinning](#assumption-pinning) -- CadAgent's contribution is the
policy for WHEN to assume vs. ask, which neither of those items currently
decides.

### CadAgent undo/rollback snapshots
CadAgent, same row. Automatic snapshots before each agent-driven edit,
restorable on request -- a simpler cousin of the checkpoint-branching idea
from ClawSCAD/ClawdCAD (`documentation/related_projects.md` rows). Scope
for this skill: snapshot a part script (and its `BUILD_PLAN.json` entry)
before an LLM-initiated correction round, so a bad autonomous edit can be
reverted without re-running the whole part loop. Lighter-weight than full
branching -- no alternate-timeline UI, just "restore last known-good".

### harnesscad pre-kernel verification
ReverseZoom2151/harnesscad, rated **High**. Verifies CAD operations
symbolically before the kernel runs them -- e.g. catching "fillet radius
exceeds half the smallest extent" from the operation's own parameters,
instead of after OCC throws a boolean-failure error. `script_lint.py` is
AST-level and geometry-unaware (it can't relate a fillet radius to an edge
length without evaluating expressions), so this is a genuine gap between
lint and runtime. harnesscad's "measured gate" (certify only when
independent measurement predicates pass) also matches and could sharpen
`cq_verify.py`'s existing assertions. Cross-checking against 13 independent
kernels is explicitly not worth adopting for a single-kernel skill.
- add named, parameter-level pre-flight predicates (fillet/chamfer radius
  vs. edge length, boss diameter vs. wall thickness, etc.) that run before
  the boolean op itself, not just before the whole script -- `cq_verify.py`
  or a new sibling helper

### Text2CAD MLYengineering repair and learning
MLYengineering/Text2CAD, rated **Medium-High**. A 7-stage
Planner/Implementation/Validation/Repair/Execution/Evaluation/Learning
pipeline over FreeCAD, built on the same "LLMs reason, deterministic tools
decide" philosophy as this skill. Two adoptable refinements to
`quality_gate.py`'s fix loop, which today just re-prompts `claude -p` with
the current error list:
- Repair Agent: rule-bound, non-rewrite patches -- constrain the fix prompt
  to emit a scoped diff/patch against the specific failing construct
  instead of license to rewrite the whole script, cutting regression risk
  from unrelated changes
- Learning Agent: cross-attempt failure aggregation -- feed the fix prompt
  a summary of what already failed on prior attempts for this part (today
  each `claude -p` fix call sees only the current error, not the attempt
  history already sitting in `build/attempts.jsonl`), so repeated fixes
  don't re-try the same wrong correction
