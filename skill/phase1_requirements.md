# Phase 1: Requirements gathering

Collect before planning, asking for whatever is missing:

- what the part is for and its primary function;
- key dimensions, or a real-world product/PCB to look up;
- printer, material, nozzle, and constraints (`wall_min_mm`, `overhang_max_deg`,
  `dimension_tolerance_mm`) -- from `profile.json` when it validated; ask only for
  what it lacks. A differing user value that is not a one-time exception becomes the new
  project default in Phase 2's write-back; tell the user;
- the fit type of every mating surface (press, snap, sliding, loose).

**Sketches.** An image attached to the request or a clarification is copied to
`sketches/<slug>-<ts>.<ext>` (`:` in `ts` replaced by `-`) and referenced from that
`request_log` entry's `images` array and from the reformulation.

## Topology clarification

A wrong dimension is a parameter edit; a wrong topology rebuilds every part built on it.
When the request's shape has more than one plausible reading (a recessed pit vs. a raised
rim, which end of a taper is wide, a bare dimension with no stated reference, a feature on
top of vs. inside another), resolve it before any dimension lookup: draw a small labeled
cross-section (a diagram tool if available, else ASCII) and ask a direct either/or
question naming both readings. Wait for the answer, then:
```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/log.py" journal append build/journal.md \
    phase1/topology_confirmed "<confirmed reading>"
```

## Ask vs. assume

Same cost axis as `request_log`'s `level`:

- **Ask** at `functional` / `operation` level: whether a part exists, a part's overall
  shape, how parts join, a fit type.
- **May assume** at `parameter` level: pick a concrete value and name it as an assumption in
  the reformulation ("legs 24 mm -- assumed, adjust after a test fit").

No dimension leaves Phase 1 as `-1`.

## Dimension lookup

Only when a named real product, PCB, or connector has dimensions not already known.
Otherwise go straight to the exit checkpoint.

**Mass.** When a part will carry a real-world object as a structural load (e.g. "holds a
phone", "supports a router"), add that object's mass to the lookup targets alongside its
dimensions. The planner derives the load's `magnitude_n` from it in Phase 2 (for the FEM
stress advisor) -- never invented, and never estimated here; a load whose object's mass
was not looked up simply gets no `magnitude_n`.

**Gridfinity** is dimensioned by the standard (`reference/gridfinity.md`): never look up or
guess grid, height, foot, or hole sizes. Ask for unit count, height, and contents; still look
up any real object the bin holds (its size picks the units via `gridfinity_units_for`).

**Research agent.** Write the lookup targets (one bullet per item and what it is for) to
`build/lookup_targets.md`. When Phase 0 ran, or the user stated dimensions, write that known
context (user values plus the sourcing agent's candidate rows as URL + what it gave) to
`build/known_context.md` -- the research agent does not repeat Phase 0's search. Render:

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/render_prompt.py" research \
    --targets-file build/lookup_targets.md [--known-file build/known_context.md]
```

Spawn one agent with `Read <out> in full and follow it. Working directory: <absolute cwd>.`
on the session default model. It returns a dimension table (status `confirmed`,
`single-source`, `conflict`, `missing`) and sources.

## Exit checkpoint

One message, one approval, covering:

1. **Dimension table** -- the research rows (omit when nothing was looked up), with every
   `conflict`/`missing` row resolved with the user or converted to `assumed` (a concrete
   value the user accepts).
2. **Reformulation** -- prose stating: what is built and why; the confirmed reading of any
   ambiguous shape; every mating fit type; every assumption with its value; the
   `sketches/` path of each image used; and, when the user's compass words imply a
   non-standard binding (e.g. "East is the logo side" meaning -X), the `coordinate_frame`
   to record (check an existing plan's first). Do not restate the dimension table or the
   printer fields.

   > Wall-mounted J-hook for a broom handle, printed as a single part. Mounting plate is
   > screwed to the wall through two countersunk holes; the hook curls up from the plate's
   > lower edge with a retaining lip so the handle cannot lift out. Handle diameter assumed
   > 24 mm (no source -- adjust after a test fit). Based on the user's sketch,
   > `sketches/broom-hook-2026-09-01T10-00-00Z.jpg`.

Do not start Phase 2 until the user approves or corrects it. Corrections replace the
looked-up values; a corrected reading becomes the approved text. The approved reformulation
is copied verbatim into `BUILD_PLAN.json`'s `intent` by the planner; `request_log`'s
`initial` entry keeps the user's original wording. If the log already holds
clarification entries at that point, the planner also sets `intent_ts` to the newest
entry's `ts`; with only an `initial` entry, no stamp is needed.

## At approval

In the same turn, write `parameters.py` at the project root: every real-world measurement
the design rests on (table rows with their status, and user-stated values), one commented
constant each. Skip only when there are none.

```python
"""Sourced real-world measurements this design is based on (not imported by the build)."""

TV_BASE_WIDTH_MM = 385.0   # user-stated
IPHONE_15_PRO_WIDTH_MM = 70.6  # apple.com/iphone-15-pro/specs, confirmed vs. gsmarena.com
```

Then always append the milestone, even when nothing was looked up (resume keys on it).
When `parameters.py` was skipped, use the text `"nothing sourced, no parameters.py"`:
```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/log.py" journal append build/journal.md \
    phase1/dimensions_approved "parameters.py written, <n> dimensions recorded"
```
