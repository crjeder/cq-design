# Phase 1: Requirements gathering

Collect the following before generating the plan. Ask if any are missing:

- What the part is for and its primary function
- Key dimensions, or a real-world product/PCB to look up
- Printer model, material, nozzle diameter, and DFM constraints (wall_min_mm,
  overhang_max_deg, dimension_tolerance_mm) -- read from `printer_profile.json` when it
  validates; only ask for a field the profile doesn't supply or that fails validation. If the
  user states a different value for this model without calling it a one-time exception, write
  that field back into `printer_profile.json` as the new project default (see Phase 2) and
  tell the user the default changed.
- Fit type for any mating surfaces (press, snap, sliding, loose)

**Never guess dimensions for real-world products** (phones, PCBs, connectors, screens). Search for the exact spec first. Cross-reference at least two sources. Use -1 as a placeholder if a dimension cannot be verified, then ask the user before finalizing the plan.

## Topology clarification

Some requests describe a 3D shape in words with more than one plausible reading — a
"recessed pit" vs. a raised rim, a taper that could be wide-at-top or wide-at-bottom, a
bare dimension with no stated reference ("the base is 6.5mm high" — of the whole part,
or of one internal feature?), a feature that could sit on top of vs. inside another. A
wrong dimension is a parameter edit; a wrong topology is a full rebuild of every part
built on that assumption — so resolve shape ambiguity before spending any effort on
size.

If the request contains topology ambiguity, do not guess and proceed. Illustrate your
reading of the shape and ask the user to confirm or correct it before generating
`BUILD_PLAN.json`:

- If a diagram/visualization tool is available in this session, render a small labeled
  2D cross-section.
- Otherwise, draw an ASCII cross-section directly in the chat message — a few lines
  showing the profile, labeled with which dimension is which.

Pair the sketch with a direct either/or question naming both readings, e.g. "Is this
the pit recessed *into* the top face, 6.5mm deep, or a rim standing *proud* of it?" —
not an open-ended "does this look right?" Wait for the user's confirmation before
continuing to dimension lookups or the plan.

## Dimension lookup with Playwright

When a real product is mentioned, run the lookup workflow below in a **research agent**
before writing a single dimension into the plan.

**Gate: only spawn the research agent when a real-world lookup is actually needed** — a
real product, PCB, or connector is named and its dimensions are not already fully known
from the user or `printer_profile.json`. A request with no external product reference
(pure user-stated dimensions) never spawns this agent — skip straight to the checkpoint
below with an empty table, or skip the checkpoint entirely per its own rule.

**Research agent.** Spawn one agent whose task is the full lookup workflow below (web
search, spec pages, community model pages, STL download + `measure_stl.py`) for every
dimension this request needs looked up. Model override: session default — this role does
not carry the topology/rebuild cost that justifies the planner's strong-model override.
The agent has no user channel: it never asks the user anything and never presents the
checkpoint. It returns exactly two things as its final message:

- The dimension validation table (Item / Value / Source / Status — the same shape as the
  Dimension validation checkpoint table below).
- The list of source URLs it consulted.

Everything else the lookup workflow touches — page snapshots, screenshots, downloaded
STLs, intermediate search results — stays inside the agent; main receives only the table
and the sources. Main then runs the Dimension validation checkpoint below exactly as
written, using the returned table.

**Workflow (followed by the research agent):**

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

**Lookup narration:** Before each lookup, note internally what is being looked up and which source is being consulted (e.g., "Looking up Bosch MUM9 bowl dimensions on bosch-home.com..."). After each lookup, note the value found and the source URL (e.g., "Found bowl diameter: 220 mm -- bosch-home.com/en/product/..."). This narration lives inside the research agent's own reasoning — it has no user channel, so none of it reaches the user directly; the user-visible summary is the Dimension validation checkpoint table main presents after the agent returns.

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
