# cq-design

## Trigger

Activate when the user asks to design, model, or generate a 3D-printable part. Trigger phrases: "3D print", "STL", "CadQuery", "enclosure", "bracket", "mount", "case", "holder", "box", "lid", "stand", "print me a", "design a part", "make a part for".

Also activate on these explicit slash commands:

| Command | Action |
|---------|--------|
| `/cq-design` | Full pipeline (phases 1-4) |
| `/plan` | Planning only (phases 1-2, stop after BUILD_PLAN.json is approved) |
| `/deliver <script.py>` | Export STL and 3MF for an existing script |
| `/render <script.py>` | Render a multi-view preview PNG for an existing script |

### Slash command dispatch

Read the first token of the user's message to determine which command was invoked, then jump to the corresponding section below. For `/cq-design` (or natural-language triggers), run the full pipeline starting at Phase 1.

## Overview

This skill generates parametric 3D-printable CadQuery models via a four-phase pipeline:

1. **Planning** - gather requirements, produce and validate `BUILD_PLAN.json`
2. **Part loop** - you write each part script inline, validate geometry, retry on failure
3. **Model export** - if multiple parts all succeed, assemble them declaratively from each part's `placement` via `model_export.py`
4. **Quality gate** - DFM checks, in-process trimesh geometry + overhang analysis (no slicer required), print recipe

## Prerequisites

Python 3.10-3.12 (CadQuery has no wheels for 3.13+), with the venv activated:

```bash
python3.12 -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Before running any skill commands, establish `SKILL_DIR` — the absolute path to the
directory containing this SKILL.md file. All `src/` scripts must be invoked via
`$SKILL_DIR/src/...` so they resolve correctly regardless of where you call them from.

```bash
# macOS / Linux
SKILL_DIR="$(cd "$(dirname "$BASH_SOURCE")" && pwd)"

# Windows (PowerShell)
$SKILL_DIR = Split-Path -Parent (Resolve-Path $PSCommandPath)

# Windows (cmd / any shell, using Python)
for /f "delims=" %i in ('python -c "import pathlib, sys; print(pathlib.Path(sys.argv[1]).parent.resolve())" "%~f0"') do set SKILL_DIR=%i
```

Generated output files (`BUILD_PLAN.json`, `build/`, exports) are always written to
the directory you called the skill from (your current working directory) — not to
`$SKILL_DIR`.

### Permission bootstrap (first use per directory)

The pipeline issues many `uv run`, `python`, `uv sync`, file-copy, `WebSearch`, and
`WebFetch` commands. To avoid a permission prompt for each one, seed the working
directory's `.claude/settings.local.json` with the patterns these commands need, once
per directory. Do this immediately after establishing `SKILL_DIR` and before Phase 1.

First check whether this directory was already seeded, then merge if not:

```bash
# --check exits 0 if already seeded, 1 if not
if ! python "$SKILL_DIR/src/init_permissions.py" --check .; then
    python "$SKILL_DIR/src/init_permissions.py" .
fi
```

```powershell
# Windows (PowerShell)
python "$SKILL_DIR/src/init_permissions.py" --check .
if ($LASTEXITCODE -ne 0) { python "$SKILL_DIR/src/init_permissions.py" . }
```

The merge is additive and idempotent: it creates `.claude/settings.local.json` if
absent, appends only missing patterns to `permissions.allow`, and never removes,
reorders, or duplicates existing entries or other settings keys. On a truly fresh
directory the very first invocation of `init_permissions.py` itself may prompt once;
that single approval seeds everything else.

**Explicit init:** if the user asks to "init permissions" (or to re-seed after updating
the skill), run `python "$SKILL_DIR/src/init_permissions.py" .` unconditionally (skip the
`--check`) so any newly added patterns are merged in.

**Fallback when the helper cannot run:** if `init_permissions.py` is unavailable or its
first run is declined, read `$SKILL_DIR/src/skill_permissions.json` and merge its `allow`
array into `.claude/settings.local.json` yourself with the Read/Write tools (same
additive, dedup, order-preserving merge — do not drop existing entries or other keys).

Known gaps: arbitrary manufacturer `WebFetch` domains and browser MCP tools (whose
server name is environment-dependent) are not in the seeded set and may still prompt.

---

## Phase 1: Requirements gathering

Collect the following before generating the plan. Ask if any are missing:

- What the part is for and its primary function
- Key dimensions, or a real-world product/PCB to look up
- Printer model (e.g. Bambu P1S, Prusa MK4, Ender 3)
- Material: PLA | PETG | ABS | ASA | TPU (default PLA)
- Nozzle diameter: 0.2 | 0.4 | 0.6 | 0.8 mm (default 0.4)
- Fit type for any mating surfaces (press, snap, sliding, loose)

**Never guess dimensions for real-world products** (phones, PCBs, connectors, screens). Search for the exact spec first. Cross-reference at least two sources. Use -1 as a placeholder if a dimension cannot be verified, then ask the user before finalizing the plan.

### Dimension lookup with Playwright

When a real product is mentioned, use the Playwright MCP to fetch its spec page before writing a single dimension into the plan.

**Workflow:**

1. Navigate to the manufacturer spec page or a reliable secondary source:
   - Phones / tablets: manufacturer product page, then GSMArena as a cross-check
   - PCBs / SBCs: official documentation or schematic PDF
   - Connectors / ICs: manufacturer datasheet (Mouser, DigiKey, or vendor site)
   - General hardware: iFixit teardown, or search `"<product name> dimensions mm filetype:pdf"`
   - **Proprietary mechanical interfaces** (appliance bowl adapters, twist-lock mounts, bayonet couplings, vacuum ports, tool chucks, coffee machine portafilters, etc.): manufacturer documentation almost never covers these. Use this search sequence:
     1. Web search: `"<product name>" adapter OR compatible STL 3D print dimensions mm` -- catches forum posts, Reddit threads, and blog teardowns that state measured values.
     2. Search Thingiverse: `thingiverse.com/search?q=<product+name>+adapter` -- also try `compatible`, `plate`, `replacement`.
     3. Search Printables: `printables.com/search/models?q=<product+name>+adapter`
     4. Search MakerWorld: `makerworld.com/en/search/models?keyword=<product+name>`
     5. Open the most-downloaded matching model on each platform. Read the full description and all comments -- community designers routinely state the key dimensions they measured.
     6. If a parametric source (OpenSCAD, FreeCAD, CadQuery) is linked, navigate to it and read the parameter block for exact values.
     7. If only an STL download is available and no dimensions are stated, download the file and run `python "$SKILL_DIR/src/measure_stl.py" <path>` to extract bounding box, layer heights, and cylinder diameters automatically. Record those values in `planning_notes`.
     8. Cross-check two sources (or two found models) before committing any dimension.
2. Call `browser_snapshot` (or `browser_take_screenshot` if the page is image-heavy) to extract the spec table.
3. Record the dimensions. Repeat for the second source and confirm they agree within 0.5 mm.
4. If sources conflict or a dimension is absent, set it to `-1` and ask the user.

**Tool usage pattern:**

```
web_search        →  "<product> adapter STL dimensions mm"
browser_navigate  →  thingiverse / printables / makerworld search results
browser_snapshot  →  read model description and comments
[if STL only]     →  download STL, run: python "$SKILL_DIR/src/measure_stl.py" reference.stl
browser_navigate  →  manufacturer spec URL (for non-proprietary dims)
browser_snapshot  →  read dimension values from accessibility tree
```

**Downloading an STL for measurement:**

```bash
python -c "import urllib.request; urllib.request.urlretrieve('<direct-stl-url>', 'reference.stl')"
python "$SKILL_DIR/src/measure_stl.py" reference.stl
```

The output JSON contains `bounding_box_mm`, `flat_faces` (Z heights and radii of each horizontal layer), and `cylinders` (boss/hole diameter, height, and Z position). Use these as the primary dimension source when no stated values are available.

Use `browser_take_screenshot` only when the spec is in an image or the snapshot returns no useful text. Prefer `browser_snapshot` - it is faster and more token-efficient.

**Lookup narration:** Before each lookup, output a one-line status naming what is being looked up and which source is being consulted (e.g., "Looking up Bosch MUM9 bowl dimensions on bosch-home.com..."). After each lookup, report the value found and the source URL (e.g., "Found bowl diameter: 220 mm -- bosch-home.com/en/product/...").

---

## Dimension validation checkpoint

After all dimension lookups are complete and **before generating `BUILD_PLAN.json`**, present a summary table of every looked-up dimension:

| Item | Value (mm) | Source | Status |
|------|-----------|--------|--------|
| Example: iPhone 15 Pro width | 70.6 | apple.com/... | confirmed |

**Status values:**
- `confirmed` -- found in two sources that agree within 0.5 mm
- `single-source` -- found in only one source
- `conflict` -- two sources disagree; show both values
- `missing` -- could not be found; value is `-1`

**Do not generate `BUILD_PLAN.json` until the user has explicitly approved or corrected the table.** If the user corrects a value (e.g., "the depth is 8.5, not 8.0"), record the correction and use the corrected value in the plan. If any rows are `missing` or `conflict`, ask the user for the correct value before continuing.

Skip this checkpoint entirely if no real-world dimension lookups were performed (i.e., all dimensions were provided directly by the user).

---

## Phase 2: Planning

**Prerequisite:** The dimension validation checkpoint must be approved before this phase begins. If user-corrected values were provided during the checkpoint, use those values -- not the originally looked-up values -- when populating `BUILD_PLAN.json`.

Build the planning prompt from the template in `prompts/planning.md`. Substitute three placeholders:

| Placeholder | Source |
|-------------|--------|
| `{{USER_REQUEST}}` | User's full description of the part |
| `{{BLOCK_INVENTORY}}` | Condensed name + use lines from `src/blocks/inventory.json` |
| `{{FDM_GUIDELINES}}` | Sections tagged `always` from `reference/FDM 3D Print Design Guidelines.md` |

Follow the planning prompt instructions to produce `BUILD_PLAN.json`. The plan must conform to `src/build_plan_schema.json`.

Write the plan to disk, then validate:

```python
import json
with open("BUILD_PLAN.json", "w", encoding="utf-8") as f:
    json.dump(plan, f, indent=2)
```

```bash
python "$SKILL_DIR/src/plan_validate.py" BUILD_PLAN.json
```

If the write fails (e.g. the working directory is not writable), surface the error and ask the user to confirm or change the working directory before continuing.

Display a human-readable Markdown summary of the validated plan (do not show raw JSON in chat) and confirm the write path using the absolute path:

> Written to: `/absolute/path/to/BUILD_PLAN.json`

(Use `os.path.abspath("BUILD_PLAN.json")` or `Path("BUILD_PLAN.json").resolve()` to obtain the absolute path before displaying it.)

The summary must include:

**Printer / Material**

| Printer | Material | Nozzle |
|---------|----------|--------|
| `<printer>` | `<material>` | `<nozzle_mm>` mm |

**Parts**

| # | ID | Description | W x D x H (mm) | Orientation | Load | Blocks |
|---|-----|-------------|----------------|-------------|------|--------|
| 1 | ... | ... | ... x ... x ... | ... | ... | ... |

(The `Load` column shows each part's `load.dir` hint, or `inferred` when the part omits
it — it drives print-orientation strength scoring.)

**Print optimization**

State the plan-level `optimize_for` (`strength` default, `min_support`, or
`visual_quality`) and call out any part that overrides it. For `visual_quality`, note each
part's `show_face.dir` (or `inferred`). This is the objective the print-orientation step
uses.

**Interfaces** (omit section if no part has any interfaces)

| Part | Type | Connector | Wall | Position (mm) |
|------|------|-----------|------|---------------|
| ... | ... | ... | ... | ... |

**Constraints**

| Wall min | Overhang max | Dim tolerance |
|----------|-------------|---------------|
| `<wall_min_mm>` mm | `<overhang_max_deg>` deg | `<dimension_tolerance_mm>` mm |

After displaying the summary, wait for the user to approve or request edits. If the user edits `BUILD_PLAN.json` on disk before confirming, re-validate from disk before proceeding to Phase 3.

---

## Phase 3: Build

Execute the part loop inline. You are the orchestrator.

### Setup

Read into context (once, before the loop):

- `BUILD_PLAN.json` — the validated plan
- `$SKILL_DIR/src/blocks/inventory.json` — block metadata (module, function, params)
- `$SKILL_DIR/prompts/part.md` — part prompt template
- `$SKILL_DIR/reference/CadQuery Pattern Reference.md` — full contents for `{{CQ_REFERENCE}}`
- `$SKILL_DIR/reference/FDM 3D Print Design Guidelines.md` — tag-filtered sections for `{{FDM_GUIDELINES}}`
- `$SKILL_DIR/reference/Visual Review Checklist.md` — the visual self-review checklist applied in Step 4

Create the `build/` directory in your current working directory.

### Build mode (per part)

Decide per part whether to build **autonomously** (the single-shot Part loop below) or
**progressively** (staged, with user checkpoints — see Progressive build).

**Complexity gate (default):** build progressively when the part has **at least one
`interfaces` entry** OR `len(part["blocks_needed"]) >= 3`; otherwise build autonomously.
The threshold (`3`) is tunable — adjust it here from field experience.

**User override:** if the user asks to build progressively (e.g. "show me each step",
"checkpoint as you go") or autonomously (e.g. "just build it", "no checkpoints"), honor
that for the part or the whole run regardless of the gate. Absent an override, the gate decides.

### Part loop

For each part in `plan["parts"]`, in order, attempt up to **3 times**:

**Step 1 — Render the part prompt**

Read `$SKILL_DIR/prompts/part.md` and substitute every placeholder:

| Placeholder | Value |
|-------------|-------|
| `{{PART_ID}}` | `part["id"]` |
| `{{PART_DESCRIPTION}}` | `part["description"]` |
| `{{W_MM}}` | `part["dimensions"]["w_mm"]` |
| `{{D_MM}}` | `part["dimensions"]["d_mm"]` |
| `{{H_MM}}` | `part["dimensions"]["h_mm"]` |
| `{{INTERFACES}}` | `part["interfaces"]` as JSON, or `(none)` |
| `{{BLOCK_SPECS}}` | For each block in `part["blocks_needed"]`: look up in inventory, format as `- **name** — use\n  params: k (v), ...`; `(none — use raw CadQuery primitives)` if list is empty |
| `{{WALL_MIN_MM}}` | `plan["constraints"]["wall_min_mm"]` |
| `{{OVERHANG_MAX_DEG}}` | `plan["constraints"]["overhang_max_deg"]` |
| `{{MATERIAL}}` | `plan["material"]` |
| `{{NOZZLE_MM}}` | `plan["nozzle_mm"]` |
| `{{CQ_REFERENCE}}` | Full contents of `CadQuery Pattern Reference.md` |
| `{{FDM_GUIDELINES}}` | Sections from `FDM 3D Print Design Guidelines.md` whose `applies_to` tag includes any block in `blocks_needed`, plus all sections tagged `always` |

**Step 2 — Write the part script**

Write `build/<part_id>.py`. The script must open with import lines for every block in `blocks_needed` — look up `module` and `function` from the inventory:

```python
from blocks.primitives import fillet_box    # example
from blocks.fasteners import screw_boss     # example
```

Then a `PARAMETERS` block, then the geometry, then `result = ...`. See generated-script rules below.

**Multi-union parts.** When the part declares a `unions` array in `BUILD_PLAN.json` (one script
that builds several rigid bodies in one coordinate frame, e.g. both leaves of a print-in-place
hinge), set `result` to a **dict** mapping each declared union id to its `Workplane` --
`result = {"leaf_a": <wp>, "leaf_b": <wp>}` -- with keys exactly the declared union ids. Each
union is then exported, posed, and kinematically/clearance checked as a distinct body. A part
without a `unions` array keeps the single `result = <wp>` form (one union, id = part id).

On retry attempts: review the error types and hints from the previous attempt, apply targeted fixes. Do not start over blindly — you have full planning context.

**Step 3 — Validate**

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/run_cadquery_model.py" \
    build/<part_id>.py \
    --expected-dims <w_mm>,<d_mm>,<h_mm> \
    --dim-tolerance <dimension_tolerance_mm> \
    --wall-min <wall_min_mm> \
    --preview \
    --cross-sections
```

Parse the JSON result. Blocking error types: `non_manifold_edge`, `non_watertight`, `dimension_mismatch`, `occ_exception`.

**Step 4 — Decide**

Handle geometry errors first, then the visual self-review. A part is done only
when geometry validation passes AND the visual self-review confirms intent.

1. **Geometry errors present** AND attempt < 3 → fix the script (step 2), re-validate (step 3). The render is unreliable when geometry failed, so skip the visual review for this attempt.
2. **`success: true` AND no blocking errors** → run the **visual self-review**: examine the preview PNG against every item in `reference/Visual Review Checklist.md` (shape match, feature completeness, feature placement, proportions, connected geometry, flat bed face, orientation), judged against this part's entry in `BUILD_PLAN.json`.
   - **All checklist items pass** → part done. Record `geometry.bbox`. Display the preview PNG. Advance to next part.
   - **Any item fails** AND attempt < 3 → record a `visual_mismatch` finding naming the failed item(s) and the discrepancy, then fix the script (step 2) with a targeted edit driven by that description and re-validate (step 3).
3. **Attempt 3 exhausted** with remaining geometry errors or an unresolved `visual_mismatch` → summarize the remaining errors and any visual mismatch to the user. Ask conversationally: provide a hint, accept the part as-is, or skip this part.

### Progressive build

Used for a part the Build mode gate (or the user) routed to progressive. Instead of
producing the finished part in one shot, construct it in three ordered stages, pausing
for the user between each. Do not disappear and return with a finished part — show
progress at each stage.

**Stages:** `base shape` → `features` → `finishing`

- **base shape** — outer shell / overall body, no features yet
- **features** — boolean cutouts, bosses, ports, slots, vents, and every `interfaces` entry
- **finishing** — fillets, chamfers, and final cleanup

For each stage, in order:

1. **Author the stage** — write the current `build/<part_id>.py` reflecting everything through this stage (reuse Step 2 authoring rules).
2. **Validate** — run Step 3 (`run_cadquery_model.py --preview --cross-sections`). Fix any geometry errors (the same retry handling as Step 4 item 1) **before** showing the checkpoint, so the user always reviews a geometrically valid stage.
3. **Visual self-review** — apply `reference/Visual Review Checklist.md` scoped to the features expected through this stage (e.g. don't fault a missing port at the base-shape stage). Resolve any `visual_mismatch` before the checkpoint.
4. **Checkpoint** — display the staged preview PNG and a one-line summary of what this stage added, then wait. The user can:
   - **Approve** → advance to the next stage (or complete the part if this was `finishing`).
   - **Request a change** → re-author this stage with the feedback, re-validate (2), re-review (3), present the checkpoint again.
   - **Skip remaining** → finish the rest of the part with the autonomous Part loop; show no further checkpoints for this part.

**Completion bar:** a progressively built part is done only when its final geometry
satisfies the plan dimensions within tolerance AND passes the **full** visual self-review —
the same bar as the autonomous path. Progressive build does not lower the criteria.

### Print-orientation optimization

After every union passes the part loop, choose how each one sits on the bed before
exporting. The objective is **user-selectable** via the plan's `optimize_for` field (a
plan-level default with optional per-part override; defaults to `strength`):

- **`strength`** (default): keep the part's load in the layer plane (FDM is weakest across
  layer lines, build Z), then least support as the tiebreaker.
- **`min_support`**: minimize support material first, strength as the tiebreaker. For jigs,
  drafts, and parts where print time/cleanup matters more than load capacity.
- **`visual_quality`**: best surface appearance first, strength then support as tiebreakers.
  Penalizes gentle inclines (surfaces sloped under 45 deg, which stair-step visibly) and
  rewards orienting the part's cosmetic surface (`show_face`) face-down against the smooth
  bed. For display pieces.

When the user states a priority ("optimize for looks", "minimize supports"), it should
already be recorded as `optimize_for` in `BUILD_PLAN.json` during planning; honor it here.

Run the optimizer once per union, on the union's **authored-frame** STL (the part's own
`result`, before any `placement`), since print orientation is a property of the part, not
of its assembled pose. Export that authored STL first (hidden during the loop), then
optimize with the part's effective mode:

```bash
# authored-frame STL for the part (deliver mode writes it out)
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/run_cadquery_model.py" \
    build/<part_id>.py --deliver --formats stl
# orientation: pass the part's load.dir / show_face.dir when the plan declares them,
# else omit to infer; --optimize-for is the part's effective mode (default strength)
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/print_orientation.py" \
    build/<part_id>.stl --overhang-max-deg <overhang_max_deg> \
    --optimize-for <strength|min_support|visual_quality> [--load x,y,z] [--show-face x,y,z]
```

Each run prints a JSON result: the active `optimize_for`, a `rotate` transform (placement
convention), the `strength_score`, `support_score`, `bed_contact_mm2`, `visual_score` (with
`cosmetic_down` and `gentle_incline_fraction`), the `load_dir` used (with `load_inferred`),
the `show_face` used (with `show_face_inferred`), and a `rationale`.

**The loop:** read the score breakdown and decide.
- **Accept** the recommended orientation when its scores are acceptable for the chosen mode,
  or when no better orientation exists at comparable primary score.
- **Improve** the part when the chosen mode's primary score is poor: make a targeted geometry
  edit to the part script (chamfer a steep overhang or a gentle incline, add a
  print-in-place foot, split a feature), re-validate it (Step 3), and re-run the optimizer.
  Re-scoring on identical input is deterministic, so a changed score reflects the edit.
- Respect the user's mode: `visual_quality` and `min_support` may deliberately accept a
  weaker or higher-support pose. The non-primary scores stay in the result and rationale, so
  if the trade-off looks unacceptable, surface it to the user rather than silently overriding
  the mode.

Collect the accepted orientations into `build/orientations.json` mapping each part id to
its result (`{"<part_id>": {"rotate": [...], ...}}`). This file feeds the model export and
the quality-gate recipe below.

### Model export

The model is assembled declaratively from each part's `placement` — there is no
hand-written fused-assembly script. Run the model export to emit the deliverables. Pass
`--orientations build/orientations.json` so the **deliverable 3MF/STL are written in each
union's recommended print orientation**; the assembled-pose per-union STLs that the
kinematic check consumes are still written from `placement`, unaffected:

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/model_export.py" \
    --plan BUILD_PLAN.json --parts-dir build --out build \
    --orientations build/orientations.json
```

This writes a named-object `model.3mf` (each union a separately named object in its print
orientation, carrying its `plate` metadata), one **assembled-pose** STL per union
(`build/<part_id>.stl`, the kinematic check's input, in `placement` pose), and one fused
STL per plate that holds more than one union (in the plate's print orientation). Run the
export even for a single-part model to get the print-oriented deliverable; omit
`--orientations` to fall back to assembled-pose deliverables.

Then make the working directory a **self-contained uv project** so the user can
regenerate the plates on any machine with uv, without the skill installed. Three steps:

1. **Drop in the re-runnable build script and bundle the tooling.** Copy
   `$SKILL_DIR/src/build_template.py` verbatim to `build/build.py` (no placeholder
   substitution), then copy the build tooling it imports into `build/` so it sits on
   `build.py`'s own `sys.path`: the modules `mesh_io.py`, `model_export.py`,
   `print_orientation.py`, `placement.py`, `units.py` and the packages `exporters/` and `blocks/`
   (copy the whole directories, including their `*.json` data files). Re-running the skill
   overwrites these with the current `src/` versions.

2. **Scaffold the uv project files** at the working-directory root: copy
   `$SKILL_DIR/src/project_template/pyproject.toml` to `pyproject.toml` and
   `$SKILL_DIR/src/project_template/.python-version` to `.python-version`.

3. **Sync and verify.** Run `uv sync` in the working directory to create `.venv` and
   produce a committed `uv.lock`, then verify the build runs in that environment with
   `uv run python build/build.py`.

```bash
# POSIX
cp "$SKILL_DIR/src/build_template.py" build/build.py
for m in mesh_io.py model_export.py print_orientation.py placement.py units.py; do
    cp "$SKILL_DIR/src/$m" build/
done
cp -r "$SKILL_DIR/src/exporters" "$SKILL_DIR/src/blocks" build/
cp "$SKILL_DIR/src/project_template/pyproject.toml" pyproject.toml
cp "$SKILL_DIR/src/project_template/.python-version" .python-version
uv sync
uv run python build/build.py
```

```powershell
# Windows (PowerShell)
Copy-Item "$SKILL_DIR/src/build_template.py" build/build.py
'mesh_io.py','model_export.py','print_orientation.py','placement.py','units.py' |
    ForEach-Object { Copy-Item "$SKILL_DIR/src/$_" build/ }
Copy-Item "$SKILL_DIR/src/exporters","$SKILL_DIR/src/blocks" build/ -Recurse
Copy-Item "$SKILL_DIR/src/project_template/pyproject.toml" pyproject.toml
Copy-Item "$SKILL_DIR/src/project_template/.python-version" .python-version
uv sync
uv run python build/build.py
```

This gives the user a self-contained project where `uv run python build/build.py`
regenerates every plate with its object in print orientation after a manual part edit,
without re-invoking the skill. It reuses `build/orientations.json` when present (so the
plates match the ones just delivered) and recomputes orientations otherwise.

### Quality gate

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/quality_gate.py" \
    --script build/<part_id>.py --plan BUILD_PLAN.json \
    --orientation build/<part_id>.orientation.json
```

DFM, geometry, and overhang are per-rigid-body concerns, so the gate runs on each
union's own part script: run it once per union for a multi-part model. Pass the union's
own orientation result (one object split out of `build/orientations.json`) via
`--orientation` so the emitted print recipe's `orientation` field carries the computed
rotation and rationale instead of the default `flat_bottom_down`. The whole-model
kinematic check runs once over the per-union assembled STLs produced by the model export.

Parse `build/quality_gate.json` and proceed to Phase 4.

The gate runs entirely in-process (trimesh + numpy geometry and overhang analysis); it needs no slicer or MCP. Real slicer-based printability validation (e.g. the orca-check MCP) is optional and external, not part of the gate.

If the plan has a `kinematics` array, the gate also runs the **kinematic range check** (`src/kinematic_check.py`) once, after the geometry checks. The sweep is whole-model, so it needs **every union's assembled STL** present in the gate's STL directory as `<part_id>.stl`. Produce these with the **model export** (`src/model_export.py`), which applies each part's `placement` and writes one assembled STL per union (plus the named-object `model.3mf` and any fused-per-plate STL). The stage degrades to a `check_skipped` warning when a union STL or the `python-fcl`/`scipy` backend is missing. See **Kinematic validation** below.

Whenever any plate carries more than one union (print-in-place), the gate also runs the **plate-clearance check** (`src/plate_clearance_check.py`) once, over the same assembled per-union STLs. For every co-plated union pair it measures the minimum surface-to-surface gap and flags any pair within one layer height (`nozzle_mm * 0.5`) as a `plate_clearance` **error** -- those unions fuse on the bed. The gate runs this automatically (no separate command); it degrades to a `check_skipped` warning when trimesh or the `python-fcl` backend is missing. Measuring on the assembled STLs is valid because a plate fuses as a rigid cluster, so its print-orientation rotation preserves the pairwise gaps.

The `build/` directory is in your current working directory (the directory you called the skill from), not inside `$SKILL_DIR`.

---

## Phase 4: Deliver

Report to the user:

1. **Status** - which parts passed, which had remaining warnings or errors
2. **Preview images** - display any `.png` files from `build/`
3. **Print recipe** - show `print_recipe` from `build/quality_gate.json`
4. **Output files** - list the STL / 3MF files in `build/`, and note that the working
   directory is a self-contained uv project (committed `uv.lock`): the user regenerates
   the plates in print orientation with `uv run python build/build.py`, no skill re-invoke

If the quality gate failed, summarize the remaining errors and offer to fix the script manually or re-run the gate with `--no-fix` to get a clean report.

---

---

## /plan command

Run phases 1 and 2 only (requirements gathering + BUILD_PLAN.json generation). Stop after the user approves the plan. Do not start the build.

This is useful when the user wants to review and tweak the plan before committing to a full build run.

---

## /deliver command

Export STL and 3MF for an existing CadQuery script. The script must assign its final geometry to a top-level variable named `result`.

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/run_cadquery_model.py" \
    <script.py> --deliver --formats stl,3mf
```

Parse the JSON result and report:
- Path to the STL file (`result["stl"]`)
- Path to the 3MF file (`result["threemf"]`)
- Geometry summary: bounding box, volume, weight
- Any errors from `result["errors"]`

If `result["success"]` is false, show the errors and stop.

---

## /render command

Render a multi-view preview PNG for an existing CadQuery script.

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/run_cadquery_model.py" \
    <script.py> --preview
```

Parse the JSON result and display the preview image at `result["preview"]`. Report any errors.

---

## Block library

Select blocks in `blocks_needed` during planning. When generating part scripts, write `from blocks.<module> import <function>` at the top based on the inventory (see generated-script rules).

### Primitives (`src/blocks/primitives.py`)

| Block | Use |
|-------|-----|
| `fillet_box` | Rectangular solid with filleted vertical edges. Outer shell for enclosures and bases. |
| `hollow_box` | Open-top hollow body via boolean subtraction. Electronics cases, trays, bins. |

### Fasteners (`src/blocks/fasteners.py`)

| Block | Use |
|-------|-----|
| `screw_boss` | Solid cylinder boss with through-hole for M2-M4 self-tapping screws. |
| `pcb_standoff` | Hollow cylindrical standoff for PCB mounting (M2 / M2.5 / M3). |
| `snap_hook_clip` | Cantilever snap-fit hook clip for lid-to-body connections. Union onto lid inner wall. |
| `snap_socket_receiver` | Slot to subtract from a wall to receive `snap_hook_clip`. |
| `alignment_pin` | Tapered cylinder pin for press-fit part registration. |
| `alignment_socket` | Receiving hole for `alignment_pin`. Use `clearance=0.2` for loose, `0.05` for press. |

### Connectors (`src/blocks/connectors.py`)

| Block | Use |
|-------|-----|
| `port_cutout` | Rectangular port opening: USB-C (9x3.5 mm), USB-A (12x6 mm), barrel jack, HDMI, etc. Add 0.3-0.5 mm clearance. |
| `cable_slot` | Elongated slot for cable routing, strain relief, wire management. |
| `vent_grid` | Regular grid of ventilation slots. Subtract from a wall or lid face. |

### Joints (`src/blocks/joints.py`)

| Block | Use |
|-------|-----|
| `dovetail_groove` | Dovetail slot cut into a body top edge for a sliding lid. Subtract from the body. |
| `dovetail_tongue` | Sliding lid panel that mates with `dovetail_groove`. The tongue IS the lid. |

---

## Kinematic validation

For an assembly whose parts are meant to move relative to each other (a hinge that
folds, a slide that travels, a ball joint that articulates), declare the required
range of motion so the quality gate can verify the parts actually clear that range
without binding. The check is **multi-part only** (it compares separate part STLs):
single-body print-in-place hinges (`pin_hinge`, print-in-place `hinge_leaf`) declare
a revolute `dof` for their nominal motion but are not swept while fused into one body.
The `living_hinge` flexure is a true exception - it has no axle, so it carries no `dof`.

Two pieces declare the motion:

**1. Inventory `dof`** (intrinsic to the joint block, already set in `inventory.json`):

```json
"dof": {"type": "revolute", "axis": "Y", "mechanical_limit": [0, 180], "unit": "deg"}
```

`type` is `revolute` | `prismatic` | `spherical`; `unit` is `deg` (revolute/spherical)
or `mm` (prismatic). `mechanical_limit` is the block's *nominal* full range -- a
sanity bound only. The collision sweep is authoritative for what the printed
instance actually achieves.

**2. Plan `kinematics`** (the range THIS design requires) -- a top-level array in
`BUILD_PLAN.json`:

```json
"kinematics": [{
  "joint_id": "phone_hinge",
  "moving_union": "arm",
  "block": "hinge_leaf",
  "axis_origin_mm": [0, 0, 4],
  "axis_dir": "Y",
  "type": "revolute",
  "required_range": [0, 90],
  "lo_inclusive": true,
  "hi_inclusive": true,
  "unit": "deg",
  "step": 5
}]
```

`axis_origin_mm` + `axis_dir` give the assembled-frame joint axis (you declare it; it
is not inferred). `moving_union` is the part that moves; **the fixed set is every
other union in the model**, so the sweep is whole-model and catches in-context binding
(a lid blocked by the body, not just the hinge in isolation). `required_range` is the
arc the design depends on, **relative to the union's authored pose (zero)**; it may be
negative or straddle zero (e.g. `[-30, 90]`), and `lo_inclusive`/`hi_inclusive`
(default `true`) mark whether each bound must be cleared. `plan_validate.py` checks
`moving_union` exists, the block exists and carries a `dof`, and `unit` matches the
block `dof.unit`.

The gate then performs two checks per joint: (1) `required_range` within the block's
`mechanical_limit` -> `range_exceeds_limit` on failure (no mesh loaded); (2) a
collision sweep of the moving union against every other union, each added as a
separately named collision object -> `motion_collision` carrying the binding value
and the `colliding_union` so the design loop knows what to fix. A print-in-place
joint (several unions on one plate) is swept the same way -- no special case. Designed
surface contact at the joint is tolerated (small penetration tolerance); only real
interference binds. The check reads the assembled per-union STLs from the model export
(see **Model export** / `model_export.py`).

---

## DFM constraints

Enforce in planning and during code review:

| Constraint | Value |
|------------|-------|
| Wall thickness | 1.2 mm minimum (3 perimeters at 0.4 mm nozzle); 2.0 mm recommended for load-bearing or structural walls |
| Overhang limit | 45 degrees maximum without supports |
| Bridge span | 20 mm reliable without supports; up to ~50 mm only with good part cooling |
| Print bed face | Z = 0; use `centered=(True, True, False)` on `.box()` |
| Boolean overlap | Inner bodies must extend 0.01+ mm past outer boundary |

**Clearance defaults by fit type:**

| Fit type | Default |
|----------|---------|
| press_fit | 0.0 mm |
| snap_fit | 0.15 mm |
| sliding | 0.25 mm |
| loose / cover | 0.5 mm |

---

## Coordinate system

All directional references in prompts, plans, and interfaces use:

| Direction | Axis | Notes |
|-----------|------|-------|
| North | +Y | |
| East | +X | |
| South | -Y | |
| West | -X | |
| Up | +Z | |
| Down | -Z | Print bed face, always Z = 0 |

---

## Generated script rules

Every CadQuery script the pipeline produces must:

- Begin with `from blocks.<module> import <function>` for each block in `blocks_needed` (look up `module` and `function` from `src/blocks/inventory.json`)
- Define all dimensions in a `PARAMETERS` block at the top (no magic numbers)
- Assign the final geometry to a top-level variable named `result`
- Not call `cq.exporters.export()` (the wrapper handles export)

---

## Error handling reference

| Error type | Meaning | Action |
|------------|---------|--------|
| `non_manifold_edge` | Geometry has non-manifold edges | Rebuild booleans; ensure no zero-thickness faces |
| `non_watertight` | Mesh has open holes | Check for unclosed boolean bodies |
| `dimension_mismatch` | Bounding box deviates from plan beyond tolerance | Correct the parameter driving that axis |
| `occ_exception` | OpenCASCADE kernel error | See hint for the specific exception class |
| `thin_wall` | Wall below `wall_min_mm` | Increase wall parameter or reduce cutout size |
| `overhang_exceeded` | Face angle exceeds `overhang_max_deg` | Add chamfers, redesign, or warn user if unavoidable |
| `visual_mismatch` | Render fails a `reference/Visual Review Checklist.md` item (wrong shape, missing/misplaced/mirrored feature, wrong proportions) | Re-examine intent against the plan; fix the responsible parameter or geometry. See Phase 3 Step 4. |

The `visual_mismatch` finding is recorded by Claude during the Phase 3 part loop, not emitted by `run_cadquery_model.py` — the wrapper JSON contract is unchanged and contains no `visual_mismatch` entry. It participates in the same 3-attempt retry budget as the geometry errors above.

After retries are exhausted, summarize the remaining errors to the user and ask conversationally how to proceed (try a different approach, provide a hint, or skip the part).

---

## Hardware dimension reference

Use these tables when choosing parameters for `heat_set_boss`, `counterbore_hole`, `countersink_hole`, and `hex_nut_trap`.

### Heat-set inserts (CNC Kitchen / Hilitchi-style)

| Size | Insert OD (mm) | Insert length (mm) | Boss OD rec. (mm) | Hole dia. for PLA (mm) |
|------|---------------|-------------------|-------------------|------------------------|
| M2   | 3.2           | 4.0               | 6.0               | 3.0                    |
| M2.5 | 3.5           | 4.0               | 6.5               | 3.3                    |
| M3   | 4.6           | 5.7               | 7.5               | 4.4                    |
| M4   | 5.6           | 8.1               | 9.0               | 5.4                    |
| M5   | 6.4           | 9.5               | 10.5              | 6.2                    |

Pass `size='Mx-pitch-length'` to `heat_set_boss` (e.g. `'M3-0.5-6'`). The hole dia. column
is the hole sized for a firm heat-press fit in PLA; PETG may need +0.1 mm.

### Socket head cap screws (ISO 4762 / DIN 912)

For `counterbore_hole(d_screw, d_head, h_head, depth)`:

| Size | d_screw clearance (mm) | d_head (mm) | h_head (mm) |
|------|------------------------|-------------|-------------|
| M2   | 2.4                    | 3.8         | 2.0         |
| M2.5 | 2.9                    | 4.5         | 2.5         |
| M3   | 3.4                    | 5.5         | 3.0         |
| M4   | 4.5                    | 7.0         | 4.0         |
| M5   | 5.5                    | 8.5         | 5.0         |
| M6   | 6.6                    | 10.0        | 6.0         |

### Flat-head screws, 90 deg countersink (DIN 7991 / ISO 10642)

For `countersink_hole(d_screw, d_sink, depth, angle=90)`:

| Size | d_screw clearance (mm) | d_sink (mm) |
|------|------------------------|-------------|
| M3   | 3.2                    | 6.0         |
| M4   | 4.3                    | 8.0         |
| M5   | 5.3                    | 10.0        |
| M6   | 6.4                    | 12.0        |

### Hex nuts (ISO 4032 / DIN 934)

For `hex_nut_trap(nut_flat, nut_h, depth, d_screw=0)`:

| Size | nut_flat (mm) | nut_h (mm) | d_screw clearance (mm) |
|------|--------------|------------|------------------------|
| M2   | 4.0          | 1.6        | 2.4                    |
| M2.5 | 5.0          | 2.0        | 2.9                    |
| M3   | 5.5          | 2.4        | 3.4                    |
| M4   | 7.0          | 3.2        | 4.5                    |
| M5   | 8.0          | 4.7        | 5.5                    |
| M6   | 10.0         | 5.2        | 6.6                    |

Add 0.3-0.5 mm to `nut_flat` for a pocket that doesn't require force-fitting in PLA.

---

## Quick reference: key files

| File | Role |
|------|------|
| `BUILD_PLAN.json` | Generated plan; validate before building |
| `src/build_plan_schema.json` | JSON Schema draft-7 the plan must conform to |
| `src/run_cadquery_model.py` | Geometry validator; emits structured JSON result |
| `src/quality_gate.py` | DFM + geometry gate; emits print recipe |
| `src/plan_validate.py` | Validates BUILD_PLAN.json against schema and inventory |
| `prompts/planning.md` | Planning phase prompt template |
| `prompts/part.md` | Per-part code generation prompt template |
| `src/model_export.py` | Assembles placed unions into model.3mf + per-union/plate STL |
| `src/blocks/inventory.json` | Machine-readable block descriptors |
| `reference/CadQuery Pattern Reference.md` | CadQuery idioms injected into part prompts |
| `reference/FDM 3D Print Design Guidelines.md` | FDM guidelines injected into planning and part prompts |
