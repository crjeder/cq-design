# Context, cost and performance -- details

Tasks: [TODO.md](../TODO.md#5-context-cost-and-performance).

### Context creep restructure

Restructure to combat context creep. Reference: `ARCHITECTURE.md`. Options:
- like openspec: phases are own commands, user interaction at the end
  (change, restart), then start new phase
- python script owns the loop and switches context & models; prompt will be
  split
- use sub-agents / workers for each phase

### Warm kernel worker


`run_cadquery_model.py` starts a fresh subprocess and re-imports CadQuery on every
attempt. build123d-mcp keeps one spawned worker with OCC loaded, SIGKILLs and
respawns it on crash or timeout (their ADR 0002). Keep cq-design's whole-script
runs (reproducible deliverable) but execute them in a persistent worker. Measure
first: if the import is a small share of a typical attempt, drop this item.

### Knowledge domain activation audit

Audited `documentation/Knowledge Domains.md` (an external survey of what a
text-to-CadQuery LLM needs: 3D/B-Rep/CSG spatial reasoning, the fluent
CadQuery API + selectors, mechanical/DFM engineering, NL intent
disambiguation, and a three-part execution/feedback loop -- exception
mapping, geometric validation, visual verification) against what this skill
already injects and enforces. Finding: **already substantially activated**
for every domain except NL intent, which was already the subject of a
separate, deeper survey.

Per domain, what already exists:
- **Spatial reasoning / B-Rep / CSG**: `reference/CadQuery Pattern
  Reference.md` (workplane naming, selector semantics, transforms) +
  `reference/CadQuery Anti-Patterns.md` Tier 1 (kernel-level: booleans, wire
  closure) and Tier 2 (stateful-context: origin drift, `.workplane()` local
  coords) -- injected into `prompts/part.md` as `{{CADQUERY_REFERENCE}}` for
  every part.
- **Fluent API / selectors**: same Pattern Reference file's `## Face & Edge
  Selectors` section -- the doc's own recommended remediation for "selector
  hallucination" ("RAG over CadQuery docs") is exactly what this injection is.
- **Mechanical engineering / DFM**: `reference/FDM 3D Print Design
  Guidelines.md` + `reference/Engineering Design Rules.md`, both injected as
  `{{FDM_GUIDELINES}}`/`{{ENGINEERING_RULES}}` in `prompts/part.md` and
  `prompts/planning.md`; SKILL.md's DFM constraints table duplicates the
  load-bearing numbers for main-session checks.
- **Execution/feedback loop**: `run_cadquery_model.py`'s JSON contract is the
  doc's sketched `execute_cadquery_code`, `quality_gate.py`'s bounded
  `claude -p` fix loop is its self-correction loop, `cq_verify.py` adds
  construction-time assertions the doc only gestures at.
- **Exception/stack-trace mapping**: SKILL.md's `## Error handling
  reference` table maps every OCC exception class the doc names
  (`Standard_ConstructionError`, `BRep_API command not done`,
  `StdFail_NotDone`, `Standard_NullObject`, `Standard_OutOfRange`,
  `Standard_TypeMismatch`) to a typed error + hint -- more granular than the
  doc's sketch.
- **Topological/geometric validation**: `mesh_io.py` watertightness +
  `run_cadquery_model.py`'s `geometry` block (bbox, volume, face count)
  cover this; the multi-union/thin-wall checks go beyond what the doc
  describes.
- **Visual verification**: `preview.py`/`render_preview.py` +
  `reference/Visual Review Checklist.md`, applied at both progressive-build
  and autonomous-audit checkpoints (`skill/phase3_build.md` Step 4).

Remaining gap, the doc's failure-mode-table row "Fillet & Chamfer Crashes --
radius >= adjacent edge length": `prompts/part.md`'s "Fillet/Chamfer Safety"
line states the rule as prose but nothing checks it *before* the OCC call
the way `cq_verify.py` checks *after* a boolean -- already tracked under
[harnesscad pre-kernel verification](related_projects.md#harnesscad-pre-kernel-verification); no
new item needed.

The doc's "Domain-Specific NLP" row (intent disambiguation, hierarchical
decomposition) is the one domain NOT covered by reference-file injection --
Phase 1's topology clarification is narrow (shape ambiguity only). This is
already the subject of a full separate survey; see
[Intent-recognition survey](related_projects.md#intent-recognition-survey) for the five-item
breakdown (typed `request_log`, ambiguity-category audit, request-relative
acceptance, canonical intent restatement, under-specified eval cases) -- no
new item needed here either.

Net: this bullet is closer to DONE than open. What's actually left under it
collapses into the two already-tracked items above; keeping it as a
separate top-level bullet risks double-tracking the same gap under three
names. Recommend closing this bullet at the next TODO pass and letting the
two linked items carry the remaining work.

### Optimisation backlog

4. `kinematic_check.py` sweep: per-pose `mesh.copy()` + `apply_transform`, full-resolution manifold booleans, 8 bisect steps x azimuths, STL reload and `CollisionManager` rebuild per entry. Fix: load/build once, set the fcl transform instead of copying, decimate or bbox-gate the boolean. Gain: high on plans with joints
- [ ] 7. Repeated tessellation per union (3MF at 0.01, STL, shim default, preview per view) and a 0.01 mesh feeding all trimesh analysis. Fix: tessellate once for STL + 3MF, coarser tolerance (~0.02-0.05) for analysis STLs. Gain: medium, compounds with 1, 4, 5, 6
- [ ] 9. `preview.py`: per-triangle Python shading, per-triangle `verts[list(f)]`, re-tessellation per panel/section. Fix: vectorized `np.cross` shading, `verts[faces]`, tessellate once. Gain: medium
