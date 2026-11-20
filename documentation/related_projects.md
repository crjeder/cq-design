# Related projects

Projects surveyed for ideas relevant to this skill. Task tracking lives in `TODO.md`
(the ten most valuable open ideas are its "Top 10" items); every other open idea is
marked **Open** in the table below, with background in [Details](#details).

**Rating** = how much the project is worth to this skill: `High` (directly adoptable or
already shaped the pipeline), `Medium-High`, `Medium` (a concrete transferable idea),
`Low-Medium`, `Low` (little to take), `None` (not applicable).

## Projects

| Project | What it is | Rating | Ideas worth adapting / status |
|---------|-----------|--------|-------------------------------|
| [thereprocase/cad-skill](https://github.com/thereprocase/cad-skill) | Claude Code CadQuery skill with a phased checkpoint pipeline and DFM checks | High | Dimensioned cross-section rendering at critical features -> `preview.py`'s `--cross-sections`; `cq_debug_helpers.py` catching silent boolean failures / workplane drift -> `cq_verify.py`'s `verify_boolean`/`check_workplane`; dual-layer (construction-time + post-export) validation -> `cq_verify.py` + `quality_gate.py` |
| [vericontext/cadgate](https://github.com/vericontext/cadgate) | Quality gate / PR reviewer for AI-generated CadQuery / build123d | Medium-High | Differential geometry comparison (volume / bbox / wall-thickness delta vs the previous attempt) -- `quality_gate.py` judges each attempt in isolation and has no notion of a baseline, so a regression between attempts is invisible today; per-class exit codes for CI gating. LLM-judge intent match is only partly covered by the implementation audit -- the auditor judges the render against `BUILD_PLAN.json`, never against `request_log`, so a plan that misread the request passes the bar (see `intent_recognition.md`) **Open:** differential geometry stage = TODO Top 10 #7; optional-external LLM intent-match ([details](#cadgate-style-gate-checks)). |
| [jmwright/cadquery-llm-skill](https://github.com/jmwright/cadquery-llm-skill) | Maintainer-authored skill teaching LLMs idiomatic CadQuery | High | Anti-patterns integrated as `reference/CadQuery Anti-Patterns.md` (kernel / stateful-context / API-mechanic tiers) + fluent recipes folded into the pattern reference (change `add-cadquery-anti-patterns`); Free Function API content excluded (pipeline is fluent-only) |
| [ChristophSchranz/Tweaker-3](https://github.com/ChristophSchranz/Tweaker-3) | Auto-rotation optimizer for 3D print orientation | High | All three ideas landed in `print_orientation.py`: progressive overhang penalty (severity exponent), area-cumulation candidate generation (`_area_cumulation_normals`), build-height minimization (the `min_build_height` optimize mode) **Open (verify and close):** area-cumulation fallback and `min_build_height` mode were never ticked in TODO although this row says they landed. |
| [Text-to-CadQuery (arXiv 2505.06507 + code)](https://github.com/Text-to-CadQuery) | Research generating CadQuery code directly (not command sequences); ~170k text->CadQuery pairs, finetuned 124M-7B models | High | Chamfer distance as mesh-vs-reference regression metric -> `evals/run_evals.py`'s `chamfer_mm`; render-then-judge eval -> the part loop's visual review + implementation audit; the direct-codegen-over-B-rep-command-sequences finding validates this skill's design retrospectively (nothing left to adopt) **Open:** metric - executability / syntax pass rate on attempt 1, aggregated from wrapper `success`/`errors` ([details](#metric-executability-pass-rate)). |
| [cyberchitta/cad-khana](https://github.com/cyberchitta/cad-khana) | build123d CLI / agent skill with a diagnostics-first (not vision-first) loop | Medium-High | Assertions-as-constraints -> `cq_verify.py`; `diagnostics.json` of interferences / clearances / wall thickness / overhangs -> `quality_gate.py`'s structured report + the kinematic/clearance/keep-out stages. Still open: HLR line-art drawings for shape questions renders can't answer -- `preview.py` renders orthographic *tessellation*, not hidden-line-removal edges **Open:** design-rule-file / assertions = TODO Top 10 #9 ([details](#diagnostics-as-assertions)). |
| [jacksonferrigno/cad-llm](https://github.com/jacksonferrigno/cad-llm) | Local desktop app: NL -> CadQuery code -> 3D preview / STEP, Qwen 4B via MLX, sandbox-and-self-correct loop | Low | Exploratory-vs-build prompt routing and the sandbox-execute-read-error-retry loop are what Phase 2 -> the part loop already do; only the on-device-model option is unadopted, and it conflicts with the Claude-5 routing in `CLAUDE5_CONVERSION_PLAN.md` |
| [outerreaches/talkcad](https://github.com/outerreaches/talkcad) | Conversational OpenSCAD Electron app with orchestrator/builder/researcher agents | Medium | Spec tracking with explicit/inferred/default values plus per-spec verification status; web research for real-world dimensions; vision-based verification of rendered models |
| [Rahix/FusedFilamentDesign](https://github.com/Rahix/FusedFilamentDesign) | FreeCAD PartDesign addon of parametric FDM design-for-printing features | Medium-High | Teardrop horizontal holes -> `blocks/connectors.py`'s `teardrop_bore`/`teardrop_post`; counterbore for overhang-free holes -> `blocks/fasteners.py`'s `counterbore_hole`; vertical-edge fillet rule -> enforced (advisory) by `edge_treatment_check.py`. Still open: thread-forming ribs, zip-tie channels -- neither exists in `blocks/inventory.json` |
| [partcad/partcad](https://github.com/partcad/partcad) | Package manager for hardware / manufacturable products across CAD kernels (CadQuery, build123d, OpenSCAD), YAML assembly format, BOM, AI-assisted workflows | Low-Medium | Package-manager framing for reusable, versioned part definitions with declared metadata (parallels `blocks/inventory.json`); YAML assembly format tracking BOM and part relationships across CAD kernels; caching rendered models to speed iteration **Open:** adoption strategy not evaluated (reimplement / pinned dep / reference) ([details](#partcad)). |
| [r3c0nshade/CADForge](https://github.com/r3c0nshade/CADForge) | Prompt-to-CAD web app: multi-provider LLM (Claude / GPT / GLM / NVIDIA / Ollama) writes CadQuery, sandboxed execution, Three.js preview, STEP/STL/OBJ/DXF export | Low-Medium | Still open: per-part version history across iterative edits (`build/attempts.jsonl` records attempts but keeps no script snapshots). Provider-agnostic backend is out of scope for a Claude Code skill |
| [w1ne/kernelCAD-web](https://github.com/w1ne/kernelCAD-web) | Agent-native CAD: design brief -> editable `.kcad.ts` -> evaluated model -> deterministic validation (OpenCASCADE via Replicad) | Low-Medium | "Editable source is truth" and deterministic-validation-before-visual are already the pipeline (`script_lint` -> wrapper -> gate, then review). Still open: importing vendor STEP geometry for real hardware instead of parametric primitives -- see the B-Rep Part Libraries table below, which `blocks/hardware.py` does not yet draw on |
| [pzfreo/build123d-mcp](https://github.com/pzfreo/build123d-mcp) | MCP server letting an assistant build a build123d part incrementally with render/measure/validate after every step ("eyes for the AI") | Low-Medium | The reported CADGenBench jump (36%->46%) from per-step visual+measured feedback validates this skill's existing render+validate loop but adds nothing to adopt; the `install_skill` workflow-order scaffold is the prescriptive pattern de-emphasized post-C2 |
| [pzfreo/augura](https://github.com/pzfreo/augura) | Pre-alpha (0.1.x) build123d BREP printability analyser: overhangs/bridges, axis-pose orientation ranking, tip-over, bed-fit, brim risk, min vertical feature, wall thickness; emits an estampo.toml fragment; Apache-2.0 | Medium | Mostly already covered, often better (bridges, orientation, tip-over, thin walls). Ported: brim/lift-risk advisory, sub-layer vertical step vs `layer_height_mm`, per-part `enable_support`/`brim_type` in the estampo export ([crjeder/cq-design#255](https://github.com/crjeder/cq-design/pull/255)). **Open:** bed-fit vs build volume (needs bed dims in `profile.json`) -- [details](#augura-printability-checks) |
| [CadQuery/cadquery-contrib mcp-server](https://github.com/CadQuery/cadquery-contrib/tree/master/mcp-server) | Official CadQuery MCP server (render / inspect / get_parameters / export) | Medium | `get_parameters` style extraction of customizable script params for a parametric re-run UX (this skill avoids MCP by design) **Open:** `get_parameters` - extract customizable params from a script for parametric re-runs ([details](#get_parameters)). |
| [mikekuniavsky/mcp-cadquery-server-public](https://github.com/mikekuniavsky/mcp-cadquery-server-public) | MCP server executing CadQuery in sandboxed subprocesses, exporting 3MF/PNG/GLB via cloud storage | Medium | AST-based allowlist validation before executing generated code (safer than bare `exec`); export-format selection by result type (`cq.Assembly` -> GLB for per-part color, `cq.Workplane` -> 3MF), parallel to this skill's `dict[str, Workplane]` union-splitting |
| [Kevoyuan/AgentSCAD](https://github.com/Kevoyuan/AgentSCAD) | NL -> validated OpenSCAD artifacts, cost-conscious progressive pipeline (generate once, validate deterministically, repair only on failure) | Medium | Repair-only-on-failure -> `quality_gate.py` defaults `allow_fix=False` (IMPROVEMENT_PLAN item 10); parsing assignments into editable parameters -> `import_params.py`'s `PARAMETERS` reconciliation |
| [deGravity/aidl](https://github.com/deGravity/aidl) | Research DSL (AI Design Language) standardizing CAD construction into a hierarchical Structure/Geometry/Constraint tree for more reliable LLM generation | Low | Semantic dot-notation auto-naming of every generated entity for clearer error feedback; designing for iterative *appending* to a construction tree rather than editing existing statements, relevant if `part.md` prompts move toward incremental edits |
| [Hiram31/CADialogue](https://github.com/Hiram31/CADialogue) | Research: multimodal (text/voice/image) conversational assistant driving FreeCAD via generated Python macros | Low-Medium | Macro caching with vector-similarity retrieval of previously-confirmed designs (reported 85x speedup vs regenerating from scratch) -- a pattern for caching known-good part scripts by description similarity |
| [BenCaunt/SynthCAD](https://github.com/BenCaunt/SynthCAD) | Framework wrapping build123d with CLIs/registries/export tooling, packaged as reusable "skills" for coding agents (Codex etc.) | Low | PR-integrated interactive CAD diff viewer so an agent (or reviewer) can inspect its own geometry changes inline; scoped CI that fans framework changes across sibling projects while containing project-local ones |
| [Svetlana-DAO-LLC/cad-agent](https://github.com/Svetlana-DAO-LLC/cad-agent) | Containerized build123d rendering server: agent sends commands, gets back PNG/STL/STEP/3MF, decides next step | Low-Medium | Technical/blueprint-style 2D dimensioned-drawing renders alongside 3D views, distinct from this skill's multi-view PNG preview |
| [testingacount2026-ui/cadx-local](https://github.com/testingacount2026-ui/cadx-local) | Local Ollama + CadQuery + Flask web app for NL -> CadQuery, no cloud dependency | Low | Auto-computed volume/surface-area/bbox property panel alongside the generated model, echoing `measure_stl.py`'s feature extraction but surfaced directly in the iterate UX |
| [earthtojake/text-to-cad](https://github.com/earthtojake/text-to-cad) (forks: [cedrickchee](https://github.com/cedrickchee/text-to-cad), [costrict mirror](https://github.com/costrict-plugins-repo/earthtojake-text-to-cad-cad); web wrapper [CodeEagle/text-to-cad-web](https://github.com/CodeEagle/text-to-cad-web)) | build123d agent-skills library (CAD + URDF + G-code + DXF skills) for Claude / Codex | Medium | Skill decomposition into CAD / slicing / URDF / DXF sub-skills; multi-format export pipeline (STEP / 3MF / GLB) beyond STL |
| [rawwerks/VibeCAD](https://github.com/rawwerks/VibeCAD) | build123d skills library plus render-glb and gltf-transform plugins | Medium | IoU / Dice / precision-recall mesh metrics for AI-output regression; `bd_warehouse` fasteners and `gggears` parametric gears (parallel to `blocks/hardware`) **Open:** metric - volumetric IoU / Dice next to `chamfer_mm` via `trimesh.boolean` ([details](#metric-volumetric-iou)). |
| [lwidm/cq_gears](https://github.com/lwidm/cq_gears) | Parametric involute spur/helical gear generator for CadQuery (exact analytical curve equations, no boolean approximation) | Medium | Fills the gap in `blocks/` for gear geometry; upstream declares no license, so it's referenced as a downloadable external resource in `planning_notes` rather than pinned or vendored |
| [lightoshadow/text-to-openscad](https://github.com/lightoshadow/text-to-openscad) | Claude Code plugin: plan -> write `.scad` -> render -> iterate up to N rounds | Low-Medium | Manifold genus / facet stats as a geometry sanity check; color-coded multi-part renders to spot clipping and gaps; standard multi-view grid (iso/top/front/right) |
| [rohittp0/ClaudeCAD](https://github.com/rohittp0/ClaudeCAD) | Claude Code + OpenSCAD plugin, Interview -> Design -> Code -> Validate -> Export | Medium | `admesh` mesh-integrity validation as an export-time gate; explicit interview phase before modeling |
| [levkropp/ClawSCAD](https://github.com/levkropp/ClawSCAD) | Electron app gluing OpenSCAD + Claude Code via an OpenSCAD MCP subprocess | Low-Medium | Checkpoint branching (immutable model tree, revert + branch alternatives); auto error-feedback loop from render failures |
| [Masoudjafaripour/Vibe_CADing](https://github.com/Masoudjafaripour/Vibe_CADing) | Multi-agent generative pipeline: Planner / Retriever / Generator / Critic | Low-Medium | Critic with manufacturability heuristics (symmetry, center-of-mass, structural validity); RAG retrieval of CAD examples to ground generation |
| [OpenOrion/CQAsk](https://github.com/OpenOrion/CQAsk) (fork [alexmao1024/CQAsk-Pro](https://github.com/alexmao1024/CQAsk)) | CadQuery chat web app (React + Python + OpenAI) | Low | Chat-driven iterate UX; validates inline CadQuery codegen with STL/STEP export straight from the UI |
| [ankurhanda/claude-cad](https://github.com/ankurhanda/claude-cad) | build123d models built from image-derived construction prompts | Low | Image -> structured construction-prompt intermediary (vs direct image->CAD); named multi-part assembly modeling (42- and 74-part examples) |
| [fa-mc/vibe-cading](https://github.com/fa-mc/vibe-cading) | AI-friendly parametric CadQuery component library | Medium | Reusable AI-oriented CadQuery component set, a direct parallel to this skill's `blocks/` **Open:** cherry-pick parts as reference when adding blocks, not a dependency ([details](#vibe-cading)). |
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
| [SadilKhan/Text2CAD](https://github.com/SadilKhan/Text2CAD) | NeurIPS 2024 transformer generating B-rep sketch+extrude sequences from text | Medium | Beginner-to-expert multi-level prompt annotations for prompt design; dataset for eval (skip the ML pipeline) **Open:** blocked on a DeepCAD-sketch -> CadQuery converter ([details](#text2cad)); metric - prompt-difficulty tiers ([details](#metric-prompt-difficulty)). |
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
| [Text2CAD](https://github.com/MLYengineering/Text2CAD) | Contract‑Driven, Agentic CAD Generation with Deterministic Execution | Medium-High | READMEd in full: a concrete 7-stage pipeline (Planner/Implementation/Validation/Repair/Execution/Evaluation/Learning agents over FreeCAD) built on the same "LLMs reason, deterministic tools decide" philosophy as this skill. The Repair Agent's rule-bound, non-rewrite patches and the Learning Agent's cross-attempt failure aggregation are genuinely adoptable refinements to `quality_gate.py`'s fix loop, which today just re-prompts `claude -p` rather than applying scoped patches or learning across attempts **Open:** TODO Top 10 #3 ([details](#text2cad-mlyengineering-repair-and-learning)). |
| https://yotown.com/ | A 3D + AI Ecosystem for the Physical World. Yo.Town 3D reconnects real life and the virtual world through spatial computing, AI, multimedia, and advanced 3D printing. We turn abstract digital ideas into tangible, gravity-aware 3D experiences. | None | Marketing page, no code repository, nothing to evaluate |
| [CadAgent](https://github.com/SSSSSia/CadAgent) | An LLM Agent-powered FreeCAD workbench that generates and modifies 3D mechanical models through natural language descriptions. | High | Several concretely adoptable, non-duplicate ideas: **Token Budget Management** (directly relevant to this skill's context-heavy part loop), **Smart Clarification Policy** (auto-assume reasonable defaults instead of always stopping to ask), and **Undo/Rollback via automatic snapshots** (a simpler cousin of the checkpoint-branching idea from ClawSCAD/ClawdCAD above); Progressive Context Injection is also worth a look for `part.md` prompt sizing **Open:** token budget management ([details](#cadagent-token-budget-management)); undo/rollback snapshots ([details](#cadagent-undorollback-snapshots)); smart clarification policy = TODO Top 10 #5. |
| [cad-agent](https://github.com/pranjalbhatia710/cad-agent) | tiny local CLI for standard parts (no llm?) | Low | READMEd in full: confirmed no LLM integration (only a roadmap item); it's a deterministic "typed part spec -> OpenSCAD" compiler for a handful of primitives (mounting plates, hollow boxes). The "CAD primitive compiler" framing is reasonable but minor, and already implicit in this skill's `blocks/` library |
| https://github.com/PranavChahal/sphaire-web | Geometry validation and FDM, SLA, or CNC-oriented DFM checks, Color, metallic/roughness, image textures, and optional AI materials | Medium | READMEd in full: a browser CAD app (OpenCascade/Replicad WASM + Babylon.js) that decouples AI generation from geometry creation by routing text-to-CAD requests down a *parametric* path (CadQuery/Replicad-equivalent, for mechanical parts) or an *organic* mesh-gen path -- that request-triage pattern is a genuinely useful idea for Phase 0/2 sourcing triage. DFM-for-FDM/SLA/CNC and "code is the source of truth" duplicate what this skill already does; material/texture rendering is out of scope |
| https://github.com/abpyu/text-to-cad-local-chat | multimodal model routing, spatial relationship constraints from images, multi-turn code inheritance, and incremental modifications | Medium | READMEd in full, confirms the concrete value: "subsequent conversations inherit the previous model code, enabling continuous adjustment of dimensions, positions, directions and structures" -- exactly the incremental-edit pattern `part.md` currently lacks (a revision request effectively regenerates the whole script); a local vision model deriving spatial relationships from reference images ties to Phase 0 sourcing from photos |
| https://github.com/aarohkandy/ai-cad | planner-first | Low-Medium | READMEd in full: a plan-then-compile-then-execute CadQuery pipeline where the planner states its assumptions about missing dimensions explicitly, paralleling `BUILD_PLAN.json`/`request_log`; a deterministic rule-based planner fallback for when no LLM is available isn't relevant to a Claude-only skill, and the README itself admits the CadQuery execution path is still a stub ("has never met a real CadQuery"), limited to 5 shape families |
| https://github.com/natgluons/AI-Fusion360-Godot-Design | tune objects using Bayesian optimization | Medium | READMEd in full, confirms a concrete, transferable technique: a `scikit-optimize` "black-box tuning" loop that samples design parameters, simulates/scores each candidate, and iterates without needing an explicit performance model -- directly applicable to auto-tuning a part's dimensions against an objective (mass, clearance, print time) in this skill; the Fusion 360/Godot backend itself isn't portable |
| https://github.com/ReverseZoom2151/harnesscad | Soundness, not completeness. CAD operations are verified before the kernel runs them | High | READMEd in full and substantive: pre-kernel verification with named diagnostics (e.g. catching "fillet radius exceeds half the smallest extent" symbolically *before* the OCC call, instead of after a boolean failure) is a real gap versus `script_lint.py`'s AST-level (geometry-unaware) pre-flight lint; its "measured gate" (certify only when independent measurement predicates pass) already matches this skill's philosophy and could sharpen it. Cross-checking against 13 independent kernels is overkill for a single-kernel (CadQuery) skill and not worth adopting wholesale **Open:** TODO Top 10 #2 ([details](#harnesscad-pre-kernel-verification)). |
| https://github.com/OzAILabs/Claude-To-Print | multi-color | High | READMEd in full: a close, substantive analog (a Claude Code skill using build123d instead of CadQuery, with a staged design-brief -> parametric-script -> deterministic-export -> mesh-QA -> visual-feedback pipeline nearly identical to this skill's own). Concretely adoptable: **multi-color/multi-material 3MF export** via `lib3mf`, splitting a part into named color regions and exporting a pre-colored 3MF for AMS-style multi-filament printers -- a genuine capability gap in `threemf_multi.py`, which currently tracks named unions/plates but not per-region color **Open:** TODO Top 10 #8 ([details](todo-import-export.md#multi-color-material-support-claude-to-print)). |
| https://github.com/natgluons/CAD-modeling-app | GUI (or point-and-click) interactions | Low | READMEd in full: this repo is effectively a fork/mirror of Zoo's (KittyCAD) `modeling-app`. GUI point-and-click and code editing both mutate the same underlying KCL code representation, rendered via a remote GPU geometry-engine service over WebSockets. "Code representation is the single source of truth even for GUI actions" validates this skill's own design but adds nothing new; the hosted-rendering-service dependency is the opposite of this skill's offline, subprocess-based approach |
| https://github.com/SmartAI/Chamfer | benchmarks | Medium-High | READMEd in full: not a distance metric but a lean TypeScript CLI agent (multi-provider LLM, build123d/Fusion backends) that validates output with an objective "geometry-kernel oracle" grading exported STEP files, and reports large efficiency gains over Claude-Code-style agents on identical prompts (5.9x cheaper, 3.2x faster, 6.3x fewer tool calls). Worth studying specifically for cutting this skill's own tool-call/round-trip overhead in the part loop, not just for its benchmark methodology **Open:** telemetry = TODO Top 10 #1; failure-mode mining #4; reconciliation pass and output-token economy #6; assumption pinning #5; also fold verification into the build call ([details](#fold-verification-into-build-call)), render economy ([details](#render-economy)), warm kernel process ([details](#warm-kernel-process)), context-surface audit ([details](#context-surface-audit)), held-out eval method ([details](#eval-method-held-out-set)). Not adopted: STEP kernel-oracle check (overlaps `cq_verify.py` / `script_lint.py`). |
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
| https://github.com/estampo/estampo (also [PyPI](https://pypi.org/project/estampo/)) | Build system for reproducible prints: one TOML (parts, slicer overrides, printer targets) drives OrcaSlicer/CuraEngine CLIs; bin-packs plates, pins slicer profiles and Docker image, CI action; Apache-2.0, beta (0.4.5), takes STL/STEP/3MF | Low-Medium | Downstream consumer of our output, not a competitor. Implemented as `--formats estampo` (openspec change `export-estampo-toml`); pin-the-profile pattern still open. Its `validate` checks setting names only, no geometry or print safety, so nothing for the quality gate |
| https://github.com/pfrankov/slicer-copilot | Node CLI: an LLM proposes slicer-setting changes for a Bambu `.3mf` project, geometry untouched | Medium | Guardrail pattern (model may only touch an allowlisted parameter set, per-change rationale, dry-run preview); fits the backlog item on calculating and exporting slicer parameters |
| https://deepwiki.com/jarczakpawel/OrcaStudio/3-core-slicing-engine-(libslic3r) | Wiki of the libslic3r core slicing engine | Low-Medium | Reference if support volume is ever computed with a real slicer instead of the overhang model (see NSV score) |
| https://github.com/VinukaThejana/slicer_rs | Rust API for print cost | Low | Nothing beyond the cost calculators below |
| https://github.com/GladiusSlicer/GladiusSlicer | Rust slicer, old | Low | Nothing |
| https://github.com/khushiyant/kerf | Open IR for mesh -> G-code with `kerf verify` / `kerf diff` (`pykerf.verify_gcode` returns JSON); planar only, resolution-bounded | Medium | G-code verification for the G-code simulator backlog item: check a sliced print deposits the expected material, compare slicers |
| https://github.com/Ultimaker/CuraEngine | Cura slicing engine (AGPL) | Low-Medium | Optional external for real print time / support volume; never bundled |
| https://github.com/prusa3d/PrusaSlicer | PrusaSlicer (AGPL) | Low-Medium | Optional external for real print time / support volume; never bundled |
| https://github.com/Snapmaker/OrcaSlicer | Snapmaker's OrcaSlicer fork for the U1: same engine, adds Snapmaker profiles, LAN/WAN device control, extra paint modes, Full Spectrum layer-alternating color mixing (beta); reported ~4000 commits behind upstream (July 2026) | Low | Not needed for headless G-code: upstream Orca 2.4.0 emits U1 motion settings and 2.4.1 adds U1 nozzle profiles. Bump estampo's Orca pin to >= 2.4.1 for U1. Unverified: whether its tool-change / prime-tower G-code differs from upstream |
| https://github.com/steenfeldt/mica-slicer | Rust FFF slicer, AGPL-3.0, alpha: `mica` CLI + GUI with byte-identical G-code, reads PrusaSlicer INI and Orca JSON profiles, validated against PrusaSlicer 2.9.6 / Snapmaker Orca incl. U1 (4 tools), Marlin 2 / Klipper output, MCP server | Medium | Best fit for "same input, same output" philosophy; candidate second estampo backend once out of alpha. README warns it may damage printers; single maintainer |
| https://github.com/slicerx-oss/slicerx | Rust slicer/CAD core (not a fork, uses Orca/Prusa setting names), Apache-2.0, pre-alpha (started September 2026): `sx` CLI, C ABI, MCP server, variable-width walls, adaptive layers | Low | Too early; revisit if it matures (permissive license is the draw) |
| https://github.com/oozebot/preFlight | PrusaSlicer fork with a rewritten engine ("Luminary"), AGPL-3.0, GUI-focused, imports Prusa/Super/Orca bundles; no CLI documented | Low | Nothing for a headless pipeline |
| https://github.com/ThymeKeeper/fable-slicer | Rust FFF slicer, AGPL-3.0, CLI + egui GUI, Klipper only, 3 printer profiles, toolchanger without purge tower | Low | Hobby scope; nothing to adopt |
| https://github.com/telecos/lib3mf_rust/tree/main/tools/slicer | lib3mf crate sample: 3MF -> per-layer PNG cross-sections, no G-code, MIT | Low | Not a slicer for FFF |
| https://dragonfruit-slicer.com/docs/dev/slicing-engine/ | Rust resin (MSLA) slicer, AGPL-3.0: .ctb/.goo/.nanodlp output | None | Wrong process (resin) |
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
| [BOSL2](https://github.com/BelfrySCAD/BOSL2) / [NopSCADlib](https://github.com/nophead/NopSCADlib) / [MCAD](https://github.com/openscad/MCAD) | OpenSCAD libraries | Low-Medium | Reference only (formulas, standard-part sizes); BOSL2 attachment concept -> [BOSL2-style anchors](todo-joints.md#bosl2-style-anchors). No import possible |
| [cqparts/cqparts](https://github.com/cqparts/cqparts) | CadQuery parts/assembly wrapper framework, unmaintained since 2020 | Low | Not adopted: assembly abstraction conflicts with the direct-Workplane block pattern -- [details](#cqparts-not-adopted) |
| [michaelgale/cq-gridfinity](https://github.com/michaelgale/cq-gridfinity) | Pure-CadQuery Gridfinity generator | High | Done: reimplemented as `blocks/gridfinity.py` |
| [sameer/orient-stl](https://github.com/sameer/orient-stl) | FDM orientation search via DIRECT global optimization | Medium | Open: overhang-area + slice-count fitness as a cross-check score in `print_orientation.py` -- [details](#orientation-scoring-orient-stl) |
| CADReasoner (CVPR 2026) / CADCodeVerify ([arXiv 2410.05340](https://arxiv.org/abs/2410.05340)) | Render -> auto-generated validation questions -> regenerate loop | Medium | Open: feed preview renders + check questions into the gate's correction prompts -- [details](#iterative-visual-feedback-repair) |
| FreeCAD-AI | LLM FreeCAD agent with per-project design-rule file (`AGENTS.md`) | Medium | Open: per-project FDM design-rule file consumed by the gate -- [details](#diagnostics-as-assertions) TODO Top 10 #9. |
| [ProCAD](https://arxiv.org/abs/2602.03045) | Clarify-then-generate for text-to-CadQuery | Medium-High | Ask ONLY when necessary; question budget and skip escape hatch -- see Details: spec audit ambiguity categories **Open:** spec audit with named ambiguity categories ([details](#spec-audit-ambiguity-categories)); eval cases = TODO Top 10 #10 ([details](#under-specified-eval-cases)). |
| [LLM4CAD-Editor](https://arxiv.org/abs/2606.20607) | Edit-intent taxonomy for CAD editing | Low-Medium | Functional / operation / parameter intent levels; already mirrored by typed `request_log` entries |
| [CADDesigner](https://arxiv.org/abs/2508.01031) | Requirement-analysis stage before CAD generation | Low-Medium | Prior art for Phase 1 requirements capture (`REQUIREMENTS.md` already shipped) |
| [SEG / ODPO](https://arxiv.org/abs/2511.16434) | Self-supporting shape generation; defines the Normalized Support Volume score | Medium | NSV = support volume / model volume as a scale-invariant orientation and gate score; model itself has no public code -- see Details: NSV score **Open:** NSV score as gate / orientation objective ([details](#nsv-score)). |
| [rishigundakaram/cadquery-mcp-server](https://github.com/rishigundakaram/cadquery-mcp-server) | CadQuery MCP server with `verify_cad_query` (geometry vs natural-language criteria) | Low-Medium | LLM intent-match verifier; overlaps the cadgate-style item -- see Details: verify-against-criteria tool |
| [aguera](https://github.com/pzfreo/augura) | Misspelled duplicate of `pzfreo/augura` | Medium | Duplicate -- assessed in the `pzfreo/augura` row above |
| [Quiddity](https://github.com/pzfreo/quiddity) | Deterministic geometry-only feature recognition for STEP / B-Rep (holes, counterbores, bosses, slots, pockets, ribs, fillets, chamfers, patterns) on build123d/OCP; JSON records, placement-independent local frames; Apache-2.0, 0.x | Medium | Read the README: a measured check that the built solid actually has the planned features (hole count / diameter, counterbore depth, slot width) vs `BUILD_PLAN.json`, which `cq_verify.py` / `measure_stl.py` cannot report today; also the recognition half of importing vendor STEP (see `kernelCAD-web`). Pulls in build123d next to CadQuery (same OCP), so optional external at most |
| [wormgear.studio](https://wormgear.studio/) ([pzfreo/worm-gear-3d](https://github.com/pzfreo/worm-gear-3d)) | Browser (Pyodide) + `pip install wormgear` CLI generating cylindrical / globoid worm gear pairs (DIN 3975 profiles, virtual hobbing, keyways, DD-cuts) to STEP/3MF/STL from a `design.json` | Low-Medium | Read the site: worm gears are a gap next to `cq_gears` (spur/helical only); the JSON -> STEP CLI fits the same "downloadable external resource in `planning_notes`" route. License not stated on the site, check the repo before more than that |
| [forgent3d/forgent3d-desktop](https://github.com/forgent3d/forgent3d-desktop) | MIT desktop viewer that a coding agent (Claude Code / Codex) runs alongside: build123d `part.py` + `params.json` packages under an `asm.xml`, Three.js preview via MJCF, optional MuJoCo joint simulation | Low-Medium | Read the README: viewer-only materials/colors kept in `params.json` apart from geometry; MuJoCo simulation of joints as a stronger cousin of `kinematic_check.py`'s sweep. The rest (desktop GUI, screenshot + bbox checks) is already this skill's loop |
| [ForgeCAD/forgecad-public-kit](https://github.com/ForgeCAD/forgecad-public-kit) | Public kit for the hosted ForgeCAD product (forgecad.io): JS/TS code-CAD by agents, exporting simulation assets (OpenUSD / MJCF / URDF / STEP); MIT, 3 commits | Low | Read the README: almost no detail (no kernel, validation or agent mechanism described); robotics-sim export targets are outside a print-focused skill |
| [amagine-ai/Amagine3D](https://github.com/amagine-ai/Amagine3D) | Apache-2.0 build123d system (6.3k stars): product description + reference images + key dimensions -> printable hardware enclosure built around its internal components, editable source, STEP/STL/3MF | High | Read the README: component-first layout (mounts and interfaces before the shell), one "semantic scene" per generation recording parts / features / interfaces / materials, covers / hinges / latches developed together with assembly clearances and print tolerances, collision checks along a defined motion path. Closest high-traction match to Phase 2 and multi-part assemblies; compare its scene record against `BUILD_PLAN.json` |
| [jdilla1277/agentcad](https://github.com/jdilla1277/agentcad) | Apache-2.0 CAD CLI + MCP for coding agents (build123d default, CadQuery compatibility mode); execution, STEP / mesh export, render, metrics, validation, diffing; skill via `npx skills add jdilla1277/agentcad-skill` | Medium-High | Read the README: strict JSON on stdout, progress on stderr; published CADGenBench gains (48% higher CAD score, 2.5x valid outputs vs direct build123d with GPT-5 Nano; 80/81 valid in a later run). Best published evidence for the tool-boundary design; a head-to-head via `cadgenbench_run.py` is possible |
| [wzyn20051216/solidworks-automation-skill](https://github.com/wzyn20051216/solidworks-automation-skill) | MIT skill + MCP toolkit (1.5k stars) driving SolidWorks from Codex / Claude / Cursor with result verification | Low-Medium | Read the README: SolidWorks-only, code not usable. Transferable: "tool success is not task success" (dimension read-back after rebuild) and a per-subskill maturity status (`verified` / `stable` / `pilot`) that could label `blocks/inventory.json` entries |
| [heyixuan2/bambu-studio-ai](https://github.com/heyixuan2/bambu-studio-ai) | MIT agent skill for Bambu Lab printing: find models (MakerWorld / Printables), generate or design them, open in Bambu Studio, monitor the print; featured in Bambu Lab's official skill showcase | Medium | Read the README: routes precision parts to exact parametric modeling and decorative parts to AI mesh generation (the sphaire-web triage idea, proven in use); end-to-end to printer monitoring, beyond this skill's delivery boundary |
| [neka-nat/freecad-mcp](https://github.com/neka-nat/freecad-mcp) | MIT FreeCAD MCP server (3.1k stars, most-starred CAD MCP): create / edit models, run Python, inspect documents, FEM | Low | Read the README: battle-tested, but the human-directed MCP-bridge pattern this skill avoids by design; nothing to adopt |
| [Shpigford/nurb](https://github.com/Shpigford/nurb) | Agentic CAD app for 3D printing on OCCT B-rep (616 stars, license unclear): describe, live viewer with sliders, print checks, 3MF | High | Read the README: 13 printability rules with findings pinned to the faces they fired on; print time / grams from the user's own OrcaSlicer or Bambu Studio; 3MF with check-justified print settings embedded (brim when corners will lift); voxel stress simulation quoting breaking load against layer adhesion; measured "reference cards" (phone scan) the AI may not guess, with two-way deviation reports. Check the license before more than patterns |
| [kerryshi/cad-agent](https://github.com/kerryshi/cad-agent) | MIT, parked: English -> frozen pydantic spec -> CadQuery -> spec-derived verification -> OrcaSlicer slice check -> Bambu P2S print; 13-task benchmark, 80 tests | Medium-High | Read the README: the codegen agent never writes its own checks; every assertion derives from the frozen spec, and each gate ships "refuse-first" sabotaged parts (thin walls, missing posts) that the owning check must reject -- mutation testing for `quality_gate.py`. Benchmark: schema-constrained local 8B extracts specs perfectly, codegen needs a frontier model |
| [Anthonyhangprinter/maker-agent](https://github.com/Anthonyhangprinter/maker-agent) | MIT fully-local build123d agent (observe-edit loop, deterministic gate, multimodal critic) on one 24 GB GPU; v1.0 is a findings release | Medium-High | Read the README: "measure, don't claim" with negative results kept. Best-of-3 first-turn sampling doubled acceptance (5/22 -> 10/22) and cut suite time 42%; removing the planning brief helped a small model; gate vs blind human review 9/11 after adding interference checks; QLoRA fine-tune no gain. Inputs for TODO Top 10 #1 / #4 |
| [ReshefElisha/jarvis-onshape-mcp](https://github.com/ReshefElisha/jarvis-onshape-mcp) | Claude Code plugin driving Onshape: structured "truth" on every mutation, multi-view renders, vision-decomposition skill, drawing OCR | Medium | Read the README: per-feature geometric delta (bbox / part count / mass) before any render; `vision-decompose` zoom-and-describe pass on a reference image before building (benchmarked in `RESEARCH.md`); Tesseract OCR of drawing callouts; `compare_to_reference` composite. Relevant to Phase 0 sourcing from photos / drawings; Onshape backend not portable |
| [benmfzen/inanimatus](https://github.com/benmfzen/inanimatus) | MIT method docs + CadQuery Claude Code skill + two worked examples with geometry tests and CI | Medium | Read the README: "images are not a spec" (vision for intent, explicit numbers for geometry); shapes specified as dimensioned profiles on Z-planes joined by lofts; distilled from failed projects |
| [Kai-Jungsthoefel/SOMA](https://github.com/Kai-Jungsthoefel/SOMA) | GPL-3.0 desktop app: any CLI agent (Claude Code / Codex / Gemini CLI) writes CadQuery, SOMA rebuilds and shows it; bundles Python, CadQuery, Git, CalculiX | Medium | Read the README: agent-agnostic `soma build` / `analyze` / `render` CLI plus a project `AGENTS.md`; git commit per version; bundled CalculiX for FEA (the structural-check gap). GPL: patterns only |
| [andreahaku/openscad_claude_skill](https://github.com/andreahaku/openscad_claude_skill) | Claude Code OpenSCAD skill: design, preview, iterate, reconstruct from STL, export | Medium | Read the README: quick mode (guess, then list assumptions back; cf. TODO Top 10 #5); modify mode editing an existing STL by booleans; clearances from one measured printer profile; STL -> parametric reconstruction via SVG profiling + SDF optimization with IoU scoring. No license: patterns only |
| [filippofinke/cad-studio](https://github.com/filippofinke/cad-studio) | MIT native macOS studio: Claude Code / Codex + build123d, live viewer, sliders, version history | Low-Medium | Read the README: per-frame collision checks during a physics animation (cousin of `kinematic_check.py`), ISO first-angle technical drawings as multi-page PDF, oriented print-plate `plate.3mf` |
| [gAmUssA/cadquery-skills](https://github.com/gAmUssA/cadquery-skills) | MIT Codex / Claude Code CadQuery skills (planner, codegen, assembly constraints, export, versioning), adapted from shdaifat/cadquery-cad-vscode | Low-Medium | Read the README: planner uses confidence-driven assumptions instead of question loops (TODO Top 10 #5); git design-versioning skill (tagging prints) |
| [almightyshui/Mechanical-AI-Skill](https://github.com/almightyshui/Mechanical-AI-Skill) | MIT engineering-review skill over uploaded STEP assemblies (CAD / FEA / DFM / DFA review, reports) | Low | Read the README: review layer, not generation; nothing concrete beyond the existing implementation audit |
| [dashs20/CRAP](https://github.com/dashs20/CRAP) | build123d cycloidal reducer generator: solver-derived dimensions, full-turn collision check, toleranced STEP / STL | Low-Medium | Read the README: block-source reference for cycloidal drives next to `cq_gears`; no license, so reference only |
| [phillipthelen/awesome-build123d](https://github.com/phillipthelen/awesome-build123d) | CC0 curated list of build123d code and resources | Low | Discovery source for further block candidates and projects |
| G-code viewers and checkers (12 surveyed) | Human review step after headless slicing, ranked by whether they flag dangerous G-code | Medium | **Open:** GcodeGuard `scan` as the safety gate plus the PrusaSlicer G-code Viewer (layer slider and legend, like Orca's Preview tab) for the human reviewer ([details](#g-code-review-after-headless-slicing)) |
| https://github.com/fangzhengfelix9461/Text2CAD-GC | MIT pilot benchmark + RL toolkit: per-seam G0/G1/G2 geometric-continuity analyzer (OCC) over 90 analytic two-surface STEPs, layered reward for PPO/GRPO | Low | Read the README: targets NURBS seam continuity that Chamfer / watertight metrics miss; this skill's box/bracket parts rarely have freeform seams, and the RL side is not applicable |
| https://github.com/shivamrajput-py/Archgen-Text2CAD | Architecture docs for a proprietary 9-agent text -> FreeCAD script system (hybrid RAG, cross-iteration memory, auto 2D drawing, physics report, per-axis quality score) | Low | Read the README: "the production codebase is proprietary", only docs; cross-iteration memory echoes the Text2CAD (MLYengineering) Learning Agent row above |
| https://github.com/WaterXiao-git/text2cad-parametric | Chinese task text -> structured hard constraints (`taskspec.py`) -> one dedicated parametric builder per task (40 builders + generic fallback), Shapely 2D + manifold3d booleans, FDM printability (support-free, stable base) designed in at modeling time | Low-Medium | Read the README: competition-style hand-written builders, not LLM codegen; the "merge boolean tags with numeric limits like 'height at most 90 mm' into hard constraints" step parallels `request_log`. No license |
| https://github.com/CY-HYUN/text2cad-verifier | MIT study: Claude writes CadQuery for the public Text2CAD-Bench preview (Message Batches API); execution verifier (AST allow-list, `BRepCheck`, volume > 0) + size verifier; measures whether one round of verifier feedback fixes failures | Medium | Read the README: expected bounding box is derived from the text itself, accepted only when two independent readings of the two dataset descriptions agree within 2% / 0.5 mm, then compared with axes sorted -- a cheap, reference-free size check for `evals/` and for under-specified eval cases (TODO Top 10 #10); per-part demo page |
| https://github.com/nohope88/text2cad | Autonomous daily trend -> product pipeline: scans X/HN, proposes 3D-printable products in parallel lanes, blind judges search Amazon/Etsy/Printables to reject anything that already exists, then emits print-ready STEP/STL per part | Low-Medium | Read the README: product ideation is out of scope; transferable bits are blind parallel judging with URL evidence and a `taste.md` / lessons file learned from human rejects. No license |
| https://github.com/jeet18101999/text2cad ([templates](https://github.com/jeet18101999/text2cad/tree/main/text2cad)) | MIT Windows desktop app: local Ollama (qwen3-coder 30B / qwen2.5-coder 7B by hardware) -> CadQuery -> STEP/STL; tested part templates usable without AI, parameter panel | Low-Medium | Read the README and `templates.py`: eight tested CadQuery templates (rectangular plate, L-bracket, flange, stepped shaft, involute spur gear, enclosure, structural section u/angle/t/I, standoff) each with a `describe()` that renders the params back as a canonical text description -- template -> description pairs are a ready source of eval cases with known ground truth; the templates themselves add little over `blocks/` |
| https://github.com/Red-Owl/text2cad | Proof of concept: Grok fills a 1024^3 voxel space to make a printable OBJ | None | Read the README: voxel output, no parametric CAD; nothing to adopt |
| https://github.com/sameerreddy789/Text2Cad | Unattributed copy (not a GitHub fork) of `earthtojake/text-to-cad` (same skill folders, SKILL.md provenance still points upstream) | None | Duplicate of the `earthtojake/text-to-cad` row above. Note: upstream now also has `dfam-check` (fact-only mesh measurement tool, verdicts left to the workflow), `dfm` and `engineering-drawing` skills -- worth a re-read when that row is revisited |
| https://github.com/Bur3d-crack/Text2CAD | 2024 PyTorch skeleton: text -> point cloud model, point cloud -> CadQuery conversion still a TODO | None | Read the README: untrained skeleton; point clouds as the intermediate add nothing for a code-gen skill |
| https://github.com/yinchangguwang/Text2CAD | 2025 OpenAI script (`text2cad.py`, vedo viewer); `zhanx` branch is "Prompt2CAD", a Flask app with a `json_to_stl_converter.py` and committed generated STLs | None | Checked both branches: LLM emits a JSON shape description converted straight to STL, no CAD kernel or validation; nothing to adopt |
| https://github.com/6532123a/Efficient-Text2CAD- | 2024 placeholder repo | None | README is a single line; nothing to evaluate |
| https://github.com/annguyenphanhuu/text2cad | Dockerized text -> FreeCAD service for industrial sheet-metal parts (plates, tubes, bends, enclosures / coffrets) with example spec files | Low | Read the repo tree: `FreeCadUtil` function library per part family plus a `GeometryAnalyzer`; domain (sheet metal, French industrial enclosures) is outside FDM printing. No license |
| https://github.com/tengfeizhang666/text2cad-rag | Derivative of giuliano-t/openAI-to-freeCAD-workflow: pluggable local LLM, Chroma + BGE reranker RAG over a few-shot cookbook, FreeCAD headless run, trimesh validity check (closed, consistent winding, volume > 0) | Low | Read the README: RAG over examples and a trimesh sanity check, both already covered (`reference/`, wrapper `watertight`) |
| https://github.com/Principle-of-Procrastination/text2cad | SOLIDWORKS 2026 C# add-in MVP: server proposes an `ExecutionPlan` (versioned DSL), local client validates strictly, previews, user confirms, bridge creates native features | Low | Read the README: proprietary-CAD bridge; the validate-preview-confirm-execute plan DSL mirrors `BUILD_PLAN.json` approval, nothing new |
| [burr](https://crates.io/crates/burr) | | |
| [mesh2cad](https://github.com/emirmrkaljevic/mesh2cad) | transforms STL to CadQuery. MCP available | | 
| [Obico](https://github.com/TheSpaghettiDetective/obico-server) | smart 3D printing platform | |
| [TheSpaghettiDetective](https://github.com/TheSpaghettiDetective/OctoPrint-TheSpaghettiDetective) | detecting print errors while printing - physical world feedback? | |
| [Strecs3D](https://github.com/tomohiron907/Strecs3D) |  preprocessing software that generates optimized infill for 3D printing based on structural analysis | |
| [EFFECT OF INFILL PARAMETERS](https://www.revistadyna.com/Articulos/Ficha.aspx?IdMenu=33094c58-1bb5-4163-8382-a0d0942862d2&Cod=9674) | Infill / Strengh relation | |
| [3MF spec](https://3mf.io/spec/) | | |
| https://completecalculators.com/calculators/3d-printing/infill-weight-strength-calculator | infill strength calculator | | 
| https://3dprintcalcs.uk/ | calculators | |

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
which is the remaining work under [Intent as invariant](todo-intent.md#intent-as-invariant).

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
- keep the standalone CLIs (print-pose reruns, tests); the JSON key is the
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
Folds into the [context-creep restructure](todo-context-cost.md#context-creep-restructure)
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
overlaps the standing [context creep restructure](todo-context-cost.md#context-creep-restructure)
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

### augura printability checks
pzfreo/augura, rated **Medium**. Reads the exact BREP (build123d over OCC) instead
of a mesh; `cadquery_adapter.py` shows a CadQuery solid can be shared with build123d
via its `TopoDS_Shape` with no copy. About 1.8k lines, pre-alpha.

Already covered by this skill, usually more thoroughly:
- bridges: augura takes the span as the smaller in-plane bounding-box extent (a
  diagonal slot reads too wide) and requires a descending wall on every edge;
  `mesh_io._is_bridge` measures per-side anchored coverage
- orientation: augura ranks only the 6 axis poses by overhang area;
  `print_orientation.py` enumerates hull facets and has strength/speed modes
- tip-over: same COM-in-support-polygon test as `print_orientation._stability_metrics`
- thin walls: augura ray-samples face centres (+3x3 UV grid on faces > 100 mm2) and
  can miss thin spots; `run_cadquery_model.py`'s local-thickness check is exhaustive
  and separates XY-thin from Z-thin regions

Ported in crjeder/cq-design#255 (advisory only, never blocking):
- brim/lift risk: bed-contact area < 50 mm2 or height / sqrt(contact) > 6
- minimum vertical feature: smallest gap between horizontal face planes below the
  profile's layer height
- estampo export: per-part `enable_support` and `brim_type`

Open:
- bed-fit vs build volume -- `profile.json` has no bed dimensions; add them and
  flag (or rank down, as augura does) poses that overflow

Not adopted: an exact-BREP analysis path. Exact overhang angles would mean a
build123d dependency and a second analysis pipeline for little practical gain over
the mesh path; depending on augura itself is premature while it is pre-alpha.

### G-code review after headless slicing

Goal: a human review step for G-code from a headless slicer. The deciding feature is
flagging G-code that can harm the printer or people nearby, judged on the file alone
(firmware protections such as MAXTEMP and software endstops are out of scope). Surveyed
2026-11-16 from each README; nothing was installed or run.

Rows not marked *added* were the candidates given; rows marked *added* were found by
searching GitHub for G-code viewers, linters, validators and safety checkers. The
review step needs two things: a danger check, and a Preview-style view for the human
(3D toolpaths with a layer slider and a legend, as in Orca's Preview tab). The
"Preview-style view" column records the second; no project offers both.

| Rank | Project | Kind | Danger flagging | Preview-style view | Fit for a headless pipeline | Notes |
|---|---|---|---|---|---|---|
| 1 | [Ri4dH/GcodeGuard](https://github.com/Ri4dH/GcodeGuard) *added* | Checker (Python, MIT) | Best: 21 rules. Over-temperature incl. PTFE limit, heaters left on while idle, cold extrusion, moves out of bounds after `M211 S0`/`G92`, steppers off mid-print, persistent firmware changes (`M500`, `M502`, `SAVE_CONFIG`, SD auto-run files), host shell macros, sabotage (flow cut, temperature drop, skipped layers) | None | `gcodeguard scan --profile <yaml>` exits 2 on a block, SARIF output, `simulate` shows what would physically happen | Per-printer YAML profile with a macro allowlist. Reports 0 blocks on 15 real Prusa/Orca/Cura files. Very new (0 stars, one maintainer): pin a commit |
| 2 | PrusaSlicer G-code Viewer (standalone app shipped with [PrusaSlicer](https://github.com/prusa3d/PrusaSlicer)) *added* | Desktop viewer (AGPL) | None | Yes, the closest match: layer and move sliders, legend by feature type, speed, flow, fan, temperature and more | GUI only; the reviewer opens the file by hand | Same viewer family as Orca's Preview tab (shared `GCodeProcessor` lineage) and the most popular option. Run as a separate app, so AGPL is no concern |
| 3 | [keivanmalhani/gcode-lint](https://github.com/keivanmalhani/gcode-lint) *added* | Checker (Python, stdlib only, MIT) | Partial: temperature range, cold extrusion, build volume; the other 9 of its 12 rules are print quality | None | `--json`, `--fail-on high`, exit codes 0/1/2, printer presets or `--bed WxHxD` | Reads Prusa/Cura/Orca/Bambu headers. Fallback if GcodeGuard does not hold up |
| 4 | [2nugu/gcode-inspector](https://github.com/2nugu/gcode-inspector) | Analyzer with a browser UI (Rust, MIT) | None built in. Its checks are print quality (overhangs, motion planner, extrusion anomalies), but the `Detector` API is made for custom checks; the README example is a nozzle-temperature limit | No. `--serve` shows a findings list next to a G-code text editor (click a finding to jump to its line); `--html` gives a per-layer profile and a 2D bed map of findings. No 3D toolpaths, layer slider or legend | One binary, streams the file, self-contained `--html` report | Optional on top of rank 1 + 2 for jumping from a finding to its line. Its quality checks skip start/end G-code (`;TYPE:Custom`), where dangerous commands sit, so custom detectors must not inherit that exclusion |
| 5 | [sevagjb/PrintView3D](https://github.com/sevagjb/PrintView3D) | Desktop viewer (Python, MIT) | None for G-code. Its "Check" covers meshes (overhangs, thin walls, non-manifold edges) | Yes: layer slider, "show only this layer", toolpaths coloured by feature type | GUI only | Good general viewer (STL/3MF/STEP/G-code, opens files in the slicer); alternative to rank 2 |
| 6 | [remcoder/gcode-preview](https://github.com/remcoder/gcode-preview) *added* | three.js viewer library (TypeScript, MIT, 204 stars) | None | Partly: 3D rendering is built in, the slider and legend are our own code | Embeddable in an HTML review page next to a checker report; streaming, arcs, `;WIDTH:`/`;HEIGHT:` support | Use this instead of rank 2 if the review page should be our own |
| 7 | [twixinator/GCode-Sentinel](https://github.com/twixinator/GCode-Sentinel) *added* | Checker + optimizer (Rust, Apache-2.0) | Weak: out-of-bounds moves, negative coordinates, abnormal retractions; no temperature or firmware checks | None | `--check-only`, JSON report, non-zero exit | JSON schema unstable (0.x). Its optimizer rewrites the file; use check-only |
| 8 | [hudbrog/gCodeViewer](https://github.com/hudbrog/gCodeViewer) (gcode.ws) | Web viewer + analyzer (JS, 443 stars) | None | Yes: layer slider, 2D/3D views, per-layer stats | Docker image or online; manual | Most popular of the candidates; old codebase, license marked NOASSERTION |
| 9 | [Gren-95/gcode-viewer](https://github.com/Gren-95/gcode-viewer) | Desktop viewer (Rust, GPL-3.0) | None (counts tool changes and `M600` pauses) | Yes: top and bottom layer sliders, play button, colour by height, speed, layer, feature type or filament | GUI only, Linux + Vulkan | Nice renderer, but Linux only |
| 10 | [TetherMotion/GCodeFlow](https://github.com/TetherMotion/GCodeFlow) | CNC/printer path viewer + editor (Rust/C++) | None; `verify` only checks expected end positions and point counts | Partly: 3D paths coloured by move type, speed or Z; no layer slider | CLI exists (`verify --format json`) | No license, 0 stars, CNC-oriented: not usable |
| 11 | [rahuling/layerlens](https://github.com/rahuling/layerlens) | Desktop viewer (Rust, MIT) | None planned | Planned (layer slider, colours by feature) | Windows GUI only | "Nothing to download yet" per its README |
| 12 | [PuddingPengChen/G-codeViewer](https://github.com/PuddingPengChen/G-codeViewer) | Desktop viewer (C++) | None | Unknown | None | Last push 2015, one-line README, no license |

Recommendation: run GcodeGuard `scan` as the blocking gate on every sliced file (a
per-printer profile with the start/end macros allowlisted), then the human reviews the
GcodeGuard findings and the file in the PrusaSlicer G-code Viewer, which gives the same
layer slider and legend as Orca's Preview tab. gcode-inspector is optional on top, for
jumping from a finding to its line; a danger rule GcodeGuard lacks can go into a
gcode-inspector `Detector`. GcodeGuard is brand new with one maintainer: pin a commit
and recheck it on the real Orca output for each target printer before relying on it.
