# Phase 1: Requirements gathering

**Sourcing search vs. dimension lookup:** Phase 0 (`skill/phase0_sourcing.md`) already
runs a full-model search — "does a usable model already exist for this request" —
before Phase 1 starts. The "Dimension lookup" step below answers a
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

This confirm stays a separate, earlier round -- it gates which dimensions are worth
looking up at all, so it cannot be folded into the Phase 1 exit checkpoint below. The
exit checkpoint is the *second* stop (and the last); it does not re-ask topology.

## Ask vs. assume

Phase 1 must not leave an ambiguity unresolved when guessing it wrong would cost a
rebuild. It may leave one resolved by a stated assumption when guessing it wrong costs
only a parameter edit. This is the same cost axis as "a wrong dimension is a parameter
edit; a wrong topology is a full rebuild" above, and the same axis as the `request_log`
`level` enum:

- **Ask the user** when the unknown is `functional` or `operation` level -- whether a
  part exists at all, what a part's overall shape is, how two parts join, which fit type
  a mating surface takes.
- **May assume** when the unknown is `parameter` level -- a dimension or literal with the
  design otherwise fixed. Pick a concrete value, record it in the approved reformulation
  as an explicit assumption ("legs 24 mm to start -- assumed, adjust after a test fit"),
  and let the exit checkpoint be where a wrong assumption is caught.

No dimension may leave Phase 1 as `-1`: a row that could not be sourced is either
resolved with the user or converted to `assumed` with a concrete value the user accepts.

## Dimension lookup

**Gate: only spawn the research agent when a real-world lookup is actually needed** -- a
real product, PCB, or connector is named and its dimensions are not already fully known
from the user or `printer_profile.json`. With no external product reference, skip straight
to the exit checkpoint with an empty table.

A **Gridfinity** request is dimensioned by the standard, not by a lookup: the grid pitch,
height unit, foot profile, and hole sizes are in `reference/gridfinity.md`, so never
research or guess them. Ask only what the standard cannot supply — how many units, how
tall, and what goes in — and still look up any real object the bin has to hold, whose size
then picks the unit count via `gridfinity_units_for`.

**Research agent.** Render `$SKILL_DIR/prompts/research.md`, substituting
`{{LOOKUP_TARGETS}}` (one bullet per item to look up and what it is for),
`{{KNOWN_CONTEXT}}` (user-stated dimensions plus any Phase 0 search results already in
context, as URL + what it gave; `(none)` otherwise) and `{{SKILL_DIR}}`. Spawn one agent
with it on the session default model. It returns the dimension table and its sources;
page snapshots and downloads stay inside the agent. Use the returned table in the exit
checkpoint below and resolve its `conflict`/`missing` rows with the user there.

## Phase 1 exit checkpoint

This is the single gate out of Phase 1. It presents two things **in one message** and
takes **one approval** covering both:

1. A **reformulation of the request** in resolved terms (the content contract is below).
2. The **dimension table** of every looked-up dimension.

Do not present the reformulation and the table as two separate approval rounds.

### The dimension table

| Item | Value (mm) | Source | Status |
|------|-----------|--------|--------|
| Example: iPhone 15 Pro width | 70.6 | apple.com/... | confirmed |

**Status values:**
- `confirmed` -- found in two sources that agree within 0.5 mm
- `single-source` -- found in only one source
- `conflict` -- two sources disagree; show both values
- `assumed` -- no source; a concrete starting value the skill picked per **Ask vs.
  assume** (the reformulation names it as an assumption)
- `missing` -- could not be found; value is `-1`

If no real-world dimension lookups were performed (all dimensions user-stated), the
table may be empty or omitted -- but the reformulation is still presented and approved.

### The reformulation

Write the reformulation as prose. It **must** state:

- what is being built and why;
- the confirmed reading of any shape the request left ambiguous (from the
  topology-clarification step);
- the fit type of every mating surface (press / snap / sliding / loose);
- every assumption Phase 1 made rather than asked about, each with its concrete assumed
  value;
- the repo-relative `sketches/` path of every user-supplied image the design is based on;
- when the user's wording implies a non-standard compass binding (e.g. "East is the
  side the logo faces" not matching the standard East=+X table in
  `prompts/planning.md`), the resolved binding to write into `BUILD_PLAN.json`'s
  `coordinate_frame` -- read any `coordinate_frame` already on the plan (a re-plan)
  before asking again. Omit this when the request used no compass language, or used it
  consistently with the standard table.

It **must not** restate values a structured field already carries in full -- the
dimension table (it lives in `parameters.py` and, later, `parts[].dimensions`), or the
printer / material / nozzle fields.

Worked example:

> Wall-mounted J-hook for a broom handle, printed as a single part. Mounting plate is
> screwed to the wall through two countersunk holes; the hook curls up from the plate's
> lower edge with a retaining lip so the handle cannot lift out. Handle diameter assumed
> 24 mm (no source -- adjust after a test fit). Based on the user's sketch,
> `sketches/broom-hook-2026-09-01T10-00-00Z.jpg`.

### Approval

**Do not generate `BUILD_PLAN.json` until the user has explicitly approved or corrected
the checkpoint.** If the user corrects a dimension ("the depth is 8.5, not 8.0"), use
the corrected value. If the user corrects the reformulation ("the lid snaps on, it
doesn't screw on"), the corrected reading is what gets written to `intent`, and the
correction is appended to `request_log` as a `clarification` entry.

**Approval is not accepted while any row reads `-1` / `missing`.** Resolve such a row to
a sourced value with the user, or convert it to `assumed` with a concrete value the user
accepts, before proceeding.

The approved reformulation text is written **verbatim** to `BUILD_PLAN.json`'s `intent`
by the Phase 2 planner (`prompts/planning.md`). `request_log`'s `initial` entry keeps
the user's original opening wording unchanged -- the resolved reading lives in `intent`,
never in place of the verbatim entry.

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
`single-source`/`conflict`/`assumed`/`missing` in the comment as-is -- an `assumed` row
is recorded with its concrete value exactly as `single-source` and `conflict` are),
plus any measurement the user stated directly that never went through a web lookup.
Skip this file only when the design has no sourced real-world measurements whatsoever.
Phase 2 (`skill/phase2_planning.md`) updates this same file later only if planning
introduces or changes a measurement -- it does not write it from scratch.

Then append one line to `build/journal.md` (see `skill/resume.md`):

```
- phase1/dimensions_approved: parameters.py written, <n> dimensions recorded
```

If the checkpoint was skipped entirely (no lookups performed), skip this journal line
too -- Phase 2's plan-approval milestone is the next one recorded.

## Sketches attached to the opening request

If the user's opening request (or a Phase 1 clarification) attaches an image -- a
hand-drawn sketch, a photo of the object to be fitted, an annotated screenshot -- copy
it into a `sketches/` directory at the project root before the request_log `initial`
entry is written, named `<slug>-<ts>.<ext>` (a short slug from the request text, or
`sketch` if none is obvious; `ts` is the entry's timestamp with `:` replaced by `-`).
The copied repo-relative path goes into that entry's `images` field, and the same path
is named inline in the approved reformulation. This is the same rule
`skill/phase3_build.md` applies to an image attached to a mid-build correction -- it
covers the `initial` entry too.
