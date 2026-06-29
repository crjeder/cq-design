# Newer Open-Source & Niche Projects in LLM-Driven CAD, Parametric Tooling, and FDM Printability (2023–2026)

## TL;DR
- The most directly adaptable recent work clusters into three groups: **agentic/diagnostics-first code-CAD wrappers** (cad-khana, FreeCAD-AI, CadQuery-MCP, flowful-ai/cad-skill), **fine-tuned text/image→CadQuery models** (CAD-Coder, Text-to-CadQuery, CAD-Recode, cadrille, CADReasoner), and **printability-aware generative methods** (SEG/ODPO for support reduction, orient-stl, build-orientation optimizers).
- The single most novel idea for an FDM-focused skill is the **closed feedback loop between code-CAD and computed manufacturability diagnostics** — cad-khana's `diagnostics.json` (overhangs, wall thickness, clearances as build-failing assertions) and SEG's **Normalized Support Volume (NSV)** reward are the two reusable primitives worth adapting.
- True FDM-printability optimization is still **largely disconnected from the LLM-CAD layer**: most LLM-CAD tools stop at "valid geometry," while printability work (support minimization, orientation, self-supporting design) lives in separate geometry/diffusion pipelines. Bridging these two is the clearest open opportunity.

## Key Findings
1. **CadQuery and build123d have become the de facto LLM code-CAD targets.** Multiple 2025–2026 research models (CAD-Recode, cadrille, CAD-Coder, Text-to-CadQuery, CADReasoner) all emit CadQuery Python, because pretrained LLMs already excel at Python and the code is interpretable/editable. This is the dominant representation choice and the natural target for a new skill.
2. **The frontier is shifting from one-shot generation to iterative, feedback-driven loops** — both at training time (RL/GRPO with geometric rewards in cadrille and CAD-Coder; ODPO in SEG) and at inference time (CADReasoner's iterative program editing; cad-khana's diagnostics; CADCodeVerify's VLM visual feedback).
3. **MCP (Model Context Protocol) has exploded as the integration layer** for connecting LLMs to CAD engines (FreeCAD, CadQuery, OpenSCAD, AutoCAD, Creo), mostly in 2025–2026. These are lightweight and easy to fork.
4. **FDM printability optimization is mature but siloed.** Strong tools exist for build-orientation and support minimization (orient-stl, genetic-algorithm orientation, SEG support-volume reduction), but they operate on meshes/B-reps and are not wired into LLM design-intent pipelines.
5. **A "diagnostics-first" DFM layer is the missing connective tissue.** cad-khana and Palmetto both compute manufacturability metrics (overhangs, wall thickness, clearances) and feed them back to an agent — this is the most direct analog to the skill's CAD+LLM+FDM intersection.

## Details — Ranked Project List

### Tier 1 — Directly on-target (CAD + LLM + printability/DFM)

**1. cad-khana** — `github.com/cyberchitta/cad-khana`
A Claude Code skill and diagnostics-first build123d wrapper for LLM-driven CAD iteration. You (or an agent) write Python scripts declaring parts/assemblies; the `khana` CLI runs them, exports STL/STEP, and writes a structured `diagnostics.json` reporting interferences, clearances, wall thickness, and overhangs. Assertions (`assert_no_interference`, `assert_clearance`, `assert_min_wall`) become build failures when violated. `khana render` produces PNGs for a multimodal agent. **Novel idea to adapt:** geometric constraints as build-failing assertions + structured JSON diagnostics is exactly the feedback loop an FDM skill needs. Also maintains a landscape map ("60 Alternatives to CAD Khana," May 2026) splitting tools into agent-driven vs. human-directed.

**2. FreeCAD-AI** — `github.com/ghbalf/freecad-ai`
An AI assistant workbench embedded in FreeCAD. Generates models from natural language via 50 structured FreeCAD tool operations (create_primitive, boolean_operation, fillet_edges) wrapped in undo transactions, with a fallback code-generation mode. Has a subprocess sandbox validation step that catches invalid shapes without touching the live document, plus "Fix with AI" self-correction. Supports ~20 LLM providers and project-level `AGENTS.md`/`FREECAD_AI.md` instruction files (e.g., "All parts should have 1mm fillets"). **Novel idea:** pre-validated tool operations + per-project design-rule instruction files; the AGENTS.md pattern could encode FDM rules.

**3. CADReasoner** — `github.com/zhemdi/CADReasoner` (CVPR 2026)
Iterative CAD reverse-engineering with VLMs. Predicts a runnable CadQuery program, renders it, compares against target geometry (multi-view renders + point-cloud), feeds discrepancy back, and refines over several iterations. **Novel idea:** explicit iterative program-editing paradigm with geometric-discrepancy feedback — directly transferable to a "fix this until it's printable" loop.

**4. SEG / Offset Direct Preference Optimization** — arXiv 2511.16434 (no public code found)
"From Prompts to Printable Models: Support-Effective 3D Generation via Offset Direct Preference Optimization," by Chenming Wu, Xiaofan Li, and Chengkai Dai (Axiswise Ltd. / Centre for Perceptual and Interactive Intelligence, Hong Kong; manuscript accepted Feb 18, 2026, for an IEEE journal). Refines a text-to-3D generator (TRELLIS baseline) using ODPO with a dynamic margin proportional to the difference in support volume between samples. Introduces **Normalized Support Volume (NSV)** = support-material volume / model volume as a scale-invariant printability cost, validated against the Cura slicer (Pearson r > 0.85 over 50 Thingi10k models). On the Thingi10k-Val benchmark, SEG reaches NSV 0.176 vs TRELLIS 0.343 (≈48.7% lower) and NSV\* 0.587 vs 1.255 (≈53% lower), with a support-efficient-consistency win/tie rate of 0.870; trained with LoRA on 8× A100, ~50 s per inference, and physically validated on a Bambu Lab A1 FDM printer. **Novel idea:** NSV as a reward/score is the cleanest quantitative printability metric to bolt onto any generative or agentic loop. Note: SEG is a diffusion approach, not LLM/code — its *metric* is the reusable part. The authors claim it is the first framework to refine 3D generative models for support-efficient design.

### Tier 2 — LLM→CadQuery/CAD code models & datasets (research, 2024–2026)

**5. CAD-Recode** — `github.com/filaPro/cad-recode` (Rukhovich et al., University of Luxembourg, ICCV 2025, arXiv 2412.14042)
First LLM-based model to translate point clouds into executable CadQuery Python. Built on Qwen2-1.5B + a single-layer point-cloud projector; trained on 1M procedurally generated CadQuery programs. Per the paper: "Trained solely on a procedurally generated dataset, CAD-Recode significantly outperforms prior methods on DeepCAD and Fusion360 benchmarks, achieving 10× lower Chamfer Distance and over 20% higher IoU." Output code is human-editable and works with GPT-4o for interactive editing. **Adapt:** the procedurally generated 1M-program dataset and the "code as interpretable output" philosophy.

**6. cadrille** — `github.com/col14m/cadrille` (Kolodiazhnyi et al., ICLR 2026, arXiv 2505.22914)
Multimodal (point cloud + images + text) CAD reconstruction outputting CadQuery code, on a Qwen2-VL backbone. Two-stage SFT + online RL (GRPO) with programmatic feedback; per the paper, "we are the first to explore RL fine-tuning of LLMs for CAD tasks demonstrating that online RL algorithms such as Group Relative Preference Optimization (GRPO) outperform offline alternatives." Sets SOTA across multiple benchmarks. **Adapt:** the online-RL-with-programmatic-feedback recipe is a template for rewarding printability.

**7. CAD-Coder (Doris et al., MIT DeCoDE)** — arXiv 2505.14646 (ASME IDETC-CIE 2025)
Open-source vision-language model (LLaVA-1.5 architecture) fine-tuned to output CadQuery code from images. Released the **GenCAD-Code dataset of 163,671 image–code pairs**. Per the paper: "CAD-Coder outperforms state-of-the-art VLM baselines such as GPT-4.5 and Qwen2.5-VL-72B, achieving a 100% valid syntax rate and the highest accuracy in 3D solid similarity" (Qwen2.5-VL-72B's valid-script rate was 94%). (Note: distinct from the similarly named "CAD-Coder: Text-to-CAD with CoT and Geometric Reward," arXiv 2505.19713, which uses SFT + GRPO with a Chamfer-distance reward and is on HuggingFace as `gudo7208/CAD-Coder`.)

**8. Text-to-CadQuery** — `github.com/Text-to-CadQuery` (Xie et al., arXiv 2505.06507)
Augments the Text2CAD dataset with 170,000 CadQuery annotations (generated via Gemini 2.0 Flash) and fine-tunes six open LLMs. Per the paper: "Our best model achieves a top-1 exact match of 69.3%, up from 58.8%, and reduces Chamfer Distance by 48.6%" (with ~85% first-pass execution success). Finetuned models on HuggingFace. **Adapt:** ready-made text→CadQuery training data and finetuned checkpoints.

**9. BlenderLLM** — `github.com/FreedomIntelligence/BlenderLLM` (arXiv 2412.14203)
Qwen2.5-Coder-7B fine-tuned to generate Blender `bpy` scripts via self-improvement; ships the BlendNet dataset and CADBench benchmark. **Adapt:** self-improvement training loop and CADBench evaluation methodology.

**10. STEP-LLM** — `github.com/JasonShiii/STEP-LLM` (arXiv 2601.12641)
Generates CAD STEP models (B-rep) directly from natural language, arguing B-rep better supports downstream manufacturing than kernel-locked command sequences or scripts. **Adapt:** the manufacturing-oriented argument for B-rep output.

**11. Text2CAD-Bench** — arXiv 2605.18430
Benchmark for LLM text-to-parametric-CAD covering advanced features beyond sketch-extrude, evaluating GPT-5.2, Claude-4.5-Sonnet, Gemini-3-Flash, and domain-specific models. **Adapt:** evaluation harness for a new tool. (Related: CADFusion, arXiv 2501.19054, which infuses rendered-visual feedback into LLM text-to-CAD; Seek-CAD, arXiv 2505.17702, a self-refined generative pipeline using local DeepSeek inference.)

### Tier 3 — MCP servers & agent skills (integration layer, 2025–2026)

**12. CadQuery MCP server** — `github.com/rishigundakaram/cadquery-mcp-server` (+ companion `cad-query-workspace`)
MCP server giving Claude full CadQuery support, STL/STEP export, SVG visual feedback, and a `verify_cad_query` validator against natural-language criteria. **Adapt:** verification-against-criteria tool pattern.

**13. flowful-ai/cad-skill** — `github.com/flowful-ai/cad-skill`
A Claude Code skill for generating parametric, 3D-printable CadQuery models — writes a parametric script, exports STL, renders previews, iterates. Closest existing analog to the target skill. Also note **CadQuery LLM Skill** listed in `CadQuery/awesome-cadquery`.

**14. FreeCAD MCP servers (multiple)** — `neka-nat/freecad-mcp`, `bonninr/freecad_mcp`, `contextform/freecad-mcp` (AICopilot workbench), `sandraschi/freecad-mcp` (adds 3D-printing + CFD tools, 46 tools)
Mature ecosystem of MCP bridges to FreeCAD's Python API; the contextform one exposes PartDesign/Part operations (Pad, Revolution, Fillet, Holes, Patterns, Booleans). **Adapt:** structured-operation tool catalogs.

**15. OpenSCAD MCP / TalkCAD / PromptSCAD / CADAM** — `jabberjabberjabber/openscad-mcp`, `format37/openscad-mcp`, `outerreaches/talkcad`, `promptscad.com`, `Adam-CAD/CADAM`
Natural-language→OpenSCAD with live render feedback (base64 PNGs for vision models), STL export, manifold-status checks. TalkCAD is an Electron app with a specs-verification panel and a markdown skills knowledge base. **CADAM** is the open-source web app behind the AdamCAD startup, running OpenSCAD WASM in-browser (the repo had 3,523 GitHub stars as of May 24, 2026); AdamCAD closed a **$4.1M seed round on Oct 31, 2025, led by TQ Ventures** (with 468 Capital, Pioneer, Script Capital, Transpose Platform), per TechCrunch — CEO Zach Dive: "We were getting term sheets over email without any meetings." **Adapt:** render-status (manifold, triangle count, dimensions) surfaced back to the model.

**16. CQAsk / text-2-cad** — `OpenOrion/CQAsk`, `roberto-ceraolo/text-2-cad`
Earlier indie LLM→CadQuery/OpenSCAD generators; text-2-cad notably proposes RAG over OpenSCAD docs and steerable parameter re-generation.

### Tier 4 — Parametric CAD libraries & frameworks (ecosystem, may lack AI)

**17. PartCAD** — `github.com/partcad/partcad` (+ VS Code extension)
"Package manager for things" / digital thread for manufacturable products. Supports CadQuery, build123d, OpenSCAD, and `ai-openscad`/`ai-cadquery`/`ai-build123d` part types that generate geometry from text descriptions + requirements via Google Gemini or OpenAI. Sandboxed rendering for supply-chain security. **Adapt:** the `requirements:` field + AI part-type schema is a clean design-intent→code interface; manufacturing-process metadata.

**18. build123d external-tools ecosystem** — `build123d.readthedocs.io/en/latest/external.html`
Rich ecosystem: MakerRepo (decorators `@artifact`, `@customizable`, `@cached`), Partomatic (standardized parametric models), a dl4to-based **topology-optimization** library for OCP models, Yet Another CAD Viewer, ocp-vscode. **Adapt:** topology-optimization-on-build123d is a printability-adjacent capability.

**19. cq-gridfinity & gridfinity generators** — `github.com/michaelgale/cq-gridfinity`
Parametric CadQuery library for Gridfinity boxes/baseplates with print-aware options ("lite" style for less material/faster printing, bridging-friendly magnet holes, variable wall thickness). The broader Gridfinity ecosystem (gridfinity-rebuilt-openscad, GridPilot AI tray generator, Tracemate photo-to-tray) shows print-in-place/DFM heuristics in practice. **Adapt:** concrete print-friendly parameterizations (lite shells, bridge-over magnet holes).

**20. Zoo (formerly KittyCAD) Text-to-CAD + KCL** — `zoo.dev`, `github.com/KittyCAD/text-to-cad-ui`
Generates editable B-rep (not mesh) from text via the ML-ephant API and open-source KCL language; open-source Text-to-CAD UI (SvelteKit) and Blender add-on. The Zookeeper conversational agent inspects/snapshots/debugs geometry. Largely API-gated but the UI and KCL tooling are open. **Adapt:** B-rep-output emphasis and the agent-inspects-geometry pattern.

### Tier 5 — FDM printability optimization (geometry-level, adaptable metrics)

**21. orient-stl** — `github.com/sameer/orient-stl`
Finds best FDM print orientation for STL files via constrained global nonlinear optimization (DIRECT algorithm). Fast (sub-second). **Adapt:** drop-in orientation scoring.

**22. Build-orientation / support-minimization research** — genetic-algorithm printing-direction optimization (slice count + overhang area weighted fitness, IEEE); connected-components orientation (ScienceDirect); "Part Orientation Fused Shape Optimization" (SSRN 2025, alternating geometry+orientation optimization to minimize supports under minimal shape deviation). **Adapt:** overhang-area + slice-count fitness functions as printability scores.

**23. Self-supporting / support-free generation** — continuous layer-height variation for support-free overhangs (ScienceDirect 2025); topology optimization under overhang constraints; Curvy interactive variable-density support tool (arXiv 2102.10013). **Adapt:** 45°-overhang-threshold and self-supporting redesign heuristics.

**24. Palmetto** — `github.com/connorkapoor/Palmetto`
Web-based CAD workbench for discovering/creating DFM algorithms using LLMs + Attributed Adjacency Graphs. Covers 3D printing (overhang angles, support requirements), CNC, injection molding (wall thickness, draft angles). **Adapt:** LLM-authored DFM rules over a graph representation of the part.

**25. SmartDFM** — `github.com/Vijeyavelan/SmartDFM`
Standalone open-source Python DFM assistant for mechanical parts. **Adapt:** baseline DFM checks.

**26. CADCodeVerify** — `github.com/Kamel773/CAD_Code_Generation` (arXiv 2410.05340)
VLM-based iterative verify-and-improve loop for CAD code: generates validation questions, answers them visually, corrects deviations. With GPT-4, reports a 7.30% reduction in point-cloud distance and a 5.5% improvement in compile rate vs prior work. **Adapt:** auto-generated validation-question feedback.

## Recommendations
1. **Build the skill on CadQuery or build123d output**, not a bespoke DSL — every serious 2025–2026 model and the strongest agent skills converge there, maximizing LLM code priors and editability.
2. **Adopt cad-khana's diagnostics-first architecture as the backbone**: emit a structured `diagnostics.json` with FDM-specific fields and turn them into build-failing assertions. Extend its overhang/wall-thickness checks with: (a) an **NSV-style support-volume score** (from SEG), (b) an **orientation score** (from orient-stl / overhang-area fitness), and (c) bridging/teardrop-hole checks (from Gridfinity practice).
3. **Wire in an iterative repair loop** modeled on CADReasoner/CADCodeVerify: generate → render + compute diagnostics → feed discrepancies back → regenerate, with a hard stop on assertion failures.
4. **Reuse existing training data** (Text-to-CadQuery's 170k annotations, CAD-Recode's 1M procedural programs, CAD-Coder's 163,671-pair GenCAD-Code) if any fine-tuning is contemplated; reuse CADBench/Text2CAD-Bench for evaluation.
5. **Expose the tool via MCP** for client-agnostic adoption, forking the CadQuery-MCP verifier pattern.
6. **Thresholds that would change the plan:** if a tool emerges that *natively* couples LLM code-CAD generation with FDM support/orientation optimization (none exists today), prioritize integrating/forking it over building from scratch. If B-rep manufacturing fidelity becomes critical, pivot output toward STEP-LLM/Zoo-style B-rep.

## Caveats
- **Maturity varies widely.** Research repos (CAD-Recode, cadrille, CADReasoner, SEG) are proofs-of-concept with limited shape complexity (often sketch-extrude-biased datasets like DeepCAD); they are not production CAD.
- **Spatial reasoning remains weak.** Multiple sources (Build Great AI, Hacker News on build123d, AdamCAD reviews) note LLMs frequently produce detached parts, wrong proportions, or non-printable features, especially on complex/organic geometry.
- **Printability and LLM-CAD are still separate worlds.** SEG (the strongest support-reduction result) is a diffusion model, not code-CAD; its NSV metric is reusable but its pipeline is not LLM/code. No identified LLM text/code tool directly minimizes FDM support material at the geometry-generation stage.
- **SEG has no public code** as of this writing and its venue/DOI are not yet confirmed (manuscript indicates IEEE journal acceptance Feb 2026); the support-volume reduction percentages quoted are derived from its reported NSV table values, not stated as headline numbers by the authors.
- **Some "MCP for CAD" listings are thin or vendor-marketing** (aggregator directories). Verify activity/commit history before depending on any single server.
- **Commercial tools excluded per scope** (Fusion 360, SolidWorks, Onshape) except where open layers exist (Zoo/KCL, CADAM/AdamCAD's open web app).