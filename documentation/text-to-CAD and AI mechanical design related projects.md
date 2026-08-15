### partially related

- https://github.com/libfive/libfive
    "libfive is a software library and set of tools for solid modeling, especially suited for parametric and procedural design. It is infrastructure for generative design, mass customization, and domain-specific CAD tools."
- https://github.com/leap71/LEAP71_ShapeKernel
- https://github.com/fogleman/sdf
- https://github.com/mkeeter/fidget
- https://github.com/Text-to-CadQuery/Text-to-CadQuery
- https://samxuxiang.github.io/skexgen/
- https://github.com/rundiwu/DeepCAD
- https://github.com/philinhphan/cad-agent (drawing to cad)
- https://www.tootalltoby.com/practice/ (CAD practice)
- https://github.com/buckster123/Cadre-RS
- https://github.com/varun29ankuS/Roshera-CAD
| https://arxiv.org/html/2401.06561v1 | intent signals
| https://snorkel.ai/blog/is-intent-analysis-the-key-to-unlocking-more-accurate-llm-question-answering/ | intent signals
| https://docs.cognigy.com/ai/platform-features/nlu/external/intent-reranking | intent signals
| https://medium.com/data-science-collective/intent-driven-natural-language-interface-a-hybrid-llm-intent-classification-approach-e1d96ad6f35d | intent signals |
| https://intentanalysis.ai/ 
| https://mediatum.ub.tum.de/doc/1735613/lzs01scxrh9m12brkxpb03r1l.2402.02136.pdf | LLM data strategies for intent recognition involve using large language models (LLMs) and specialized data techniques to identify what users mean when they interact with AI systems, like chatbots or search tools. |
| https://github.com/mariyahendriksen/awesome-intent-analysis | intent signals |
| https://github.com/alphadl/SafeLLM_with_IntentionAnalysis | intent signals |
| (https://github.com/nyaniv/StepForge) | dataset? |


### **Key Takeaways for Your Own Text-to-CAD LLM Skill**

- **Multi-agent architectures** (e.g., CADSmith, ai-cad-labs/ai-cad, jabarkle/CADSmith) are the most robust, using validation, vision, and iterative refinement.
- **Deterministic intent preservation** (IntentForge, LunaiCAD) is critical for editable, maintainable CAD.
- **Browser-native/WASM** (CADAM, vespo92/AI-CAD, drogertieni/text-to-cad-studio) is a strong trend for accessibility.
- **DFM/DFA and manufacturability checks** (Anvilate, ai-cad-labs/ai-cad, cprakash64/CAD-Maker) are essential for real-world engineering.
- **Graph-based or structured decomposition** (Graph-CAD, Text-to-CadQuery) helps handle complex, hierarchical logic.
- **End-to-end pipelines** (vasparshin/text-to-3d-print, earthtojake/text-to-cad) with verification and slicing are valuable for print-ready output.

**Recommendation:** Focus on adopting **multi-agent validation loops**, **deterministic intent preservation**, and **manufacturability checks** for a production-ready skill. Browser-native/WASM and structured decomposition are also high-impact areas.

### Key Technical Trends

* **Agentic CAD execution:** Repositories increasingly use AI coding agents (such as Claude Code or Codex) paired with programmatic CAD kernels (build123d, OpenCASCADE, OpenSCAD, Replicad) to evaluate, measure, and fix geometries deterministically.
* **Direct-to-Print Slicing:** Modern tools like `earthtojake/text-to-cad` include G-code slicing capabilities directly in the agent pipeline for seamless FDM 3D printing workflows.

### early stage (watch)
- https://github.com/workarvindrajaraman-cmyk/AI-text-to-CAD-engine
- https://github.com/Anie0205/Text-to-CAD-using-Gemini

### not related
- https://github.com/brdsmth/cadsmith
- https://github.com/xuebiyixia/text_to-cad (empty)
- https://github.com/jangjun7091/Vibe_Layout
