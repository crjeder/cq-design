# Phase 1: Requirements gathering

**Sourcing search vs. dimension lookup:** Phase 0 (`skill/phase0_sourcing.md`) already
runs a full-model search — "does a usable model already exist for this request" —
before Phase 1 starts. The "Dimension lookup with Playwright" workflow below answers a
narrower question — "what are the exact dimensions of a named real-world product or
component" — and is not a repeat of Phase 0's search. **No second sweep:** if Phase 0
ran and fell through to Phase 1 (rung 5, nothing usable), reuse its search results
already in context instead of re-running the platform searches from scratch; only look
up dimensions genuinely still missing.

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

Once the user confirms, append one line to `build/journal.md` (see `skill/resume.md`):

```
- phase1/topology_confirmed: <one-line restatement of the confirmed reading>
```

Skip this line when the request had no topology ambiguity (nothing was asked).

## Dimension lookup with Playwright

When a real product is mentioned, run the lookup workflow below in a **research agent**
before writing a single dimension into the plan.

**Gate: only spawn the research agent when a real-world lookup is actually needed** — a
real product, PCB, or connector is named and its dimensions are not already fully known
from the user or `printer_profile.json`. A request with no external product reference
(pure user-stated dimensions) never spawns this agent — skip straight to the checkpoint
below with an empty table, or skip the checkpoint entirely per its own rule.

A **Gridfinity** request is dimensioned by the standard, not by a lookup: the grid pitch,
height unit, foot profile, and hole sizes are in `reference/gridfinity.md`, so never
research or guess them. Ask only what the standard cannot supply — how many units, how
tall, and what goes in — and still look up any real object the bin has to hold, whose size
then picks the unit count via `gridfinity_units_for`.

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

## Provenance write, at approval

As soon as the user approves or corrects the table (same turn, before Phase 2 starts),
write `parameters.py` at the project root: one module documenting every real-world
measurement this design is based on -- both what the user stated directly and what came
from web search (the table above). This is durable, human-readable provenance, separate
from each part script's own internal `PARAMETERS` block (resolved/derived geometry
values, not necessarily the raw sourced ones):

```python
"""Sourced real-world measurements this design is based on.

Not imported by the build -- each part script carries its own resolved PARAMETERS
block. This file keeps the underlying real-world numbers and their sources visible
and easy to re-verify or update independent of how a part script used them.
"""

TV_BASE_WIDTH_MM = 385.0   # user-stated
IPHONE_15_PRO_WIDTH_MM = 70.6  # apple.com/iphone-15-pro/specs, confirmed vs. gsmarena.com
USB_C_PORT_MM = (9.0, 3.5)  # USB-IF spec, single-source
```

Include every dimension from the table regardless of its status (note
`single-source`/`conflict`/`missing` in the comment as-is), plus any measurement the
user stated directly that never went through a web lookup. Skip this file only when the
design has no sourced real-world measurements whatsoever. Phase 2
(`skill/phase2_planning.md`) updates this same file later only if planning introduces or
changes a measurement -- it does not write it from scratch.

Then append one line to `build/journal.md` (see `skill/resume.md`):

```
- phase1/dimensions_approved: parameters.py written, <n> dimensions recorded
```

If the checkpoint was skipped entirely (no lookups performed), skip this journal line
too -- Phase 2's plan-approval milestone is the next one recorded.

## Requirements spec write, at approval

Immediately after the provenance write above (same turn), write `REQUIREMENTS.md` at
the project root: the durable, human-readable spec this design is built from. Where
`parameters.py` documents the sourced numbers, this file documents everything else
Phase 1 resolved -- what the part is for, which shape reading was confirmed, what fit
types apply, and which constraints came from a stated exception vs. the printer
profile default. It is the reviewable artifact a user (or a later session) can read to
understand *why* the plan looks the way it does, without replaying the conversation.
Phase 2 does not parse this file -- it reads `BUILD_PLAN.json` -- so nothing about the
build pipeline depends on its exact wording; it exists for human review before
planning commits everything to a schema.

Template:

```markdown
# Requirements: <request title>

## Intent
<what the part is for, its primary function>

## Topology
<confirmed reading of any ambiguous shape, from the topology-clarification step -- or
"No topology ambiguity in this request.">

## Dimensions
<the same table shown at the Dimension validation checkpoint, or "All dimensions
user-stated; no lookups performed.">

## Fit requirements
<mating surface fit types per interface -- press/snap/sliding/loose -- or "No mating
surfaces in this request.">

## Printer & DFM constraints
- Printer: <model>, Material: <material>, Nozzle: <mm>
- wall_min_mm / overhang_max_deg / dimension_tolerance_mm: <values>, noting whether
  each came from `printer_profile.json`'s default or a user-stated one-time exception

## Open questions / assumptions
<anything left as -1, or resolved by assumption rather than explicit confirmation --
or "None.">
```

Include every section even when a given section has nothing to report (use the
placeholder text shown) -- a reader should never have to guess whether a section was
omitted because it was empty or because it was forgotten.

**Skip this file only** when the request had no topology ambiguity, no real-world
dimension lookups, and no stated fit type -- i.e., Phase 1 resolved nothing beyond bare
user-stated numbers already inline in the request. Phase 2
(`skill/phase2_planning.md`) amends this same file later, in place, only if planning
introduces or changes a requirement -- it does not write it from scratch.

Then append one line to `build/journal.md`:

```
- phase1/requirements_written: REQUIREMENTS.md written
```

Skip this journal line whenever the file itself was skipped.
