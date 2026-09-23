## Context

TODO.md "Bill of non-printed materials" asked to decide between a BOM derived from
`blocks_needed` plus manual additions, and a fully hand-authored top-level `bom`. Reading
the schema settles it: `parts[].blocks_needed` items are a block name or `{name,
extents_mm}` -- no screw size, no insert spec, no instance count. Those live only in the
part scripts' calls (`heat_set_boss(size="M3-0.5-6", ...)` in a loop). The plan alone cannot
derive a single BOM row.

## Goals / Non-Goals

**Goals:**
- One place in the plan naming everything the user must supply, with quantities.
- A forgotten row for an obvious hardware block is visible at validate time.
- The user sees the list at the Phase 2 checkpoint and in the delivery / README.

**Non-Goals:**
- Deriving rows from part scripts (runtime call recording in `blocks/`). Revisit if
  hand-authored rows prove unreliable in evals.
- Purchase links, prices, supplier part numbers.
- Checking that `spec`/`qty` match the script's actual calls.

## Decisions

- **Hand-authored top-level `bom` + inventory-driven advisory.** Planner writes rows; a
  `supplied_hardware` marker on inventory blocks drives a "part uses X but no bom row lists
  it" advisory. Alternative (derived rows) rejected above: needs block-call instrumentation
  in every hardware block plus a run-time aggregation step, for data the planner already
  has when it picks the block.
- **Top-level, not per-part.** One M3 screw spec is often shared across parts; a row lists
  its consuming `parts`. Per-part arrays would duplicate rows and need merging at render.
- **Marker lives in `inventory.json`**, not a hardcoded set in `plan.py`: block metadata
  already has one source, and new hardware blocks get the check by setting one field.
- **Advisory, not error.** A part can legitimately use a `screw_boss` whose screw is listed
  under a sibling part's row (e.g. the lid part owns the screw). Unknown part ids in a row
  are a hard error -- that is always a typo.
- **README section is instruction-driven**, like the rest of `README.md` (Claude writes it
  from the plan in Phase 4); no new renderer.

Initial `supplied_hardware` values:

| Block | supplied_hardware |
|---|---|
| screw_boss | self-tapping screw |
| pcb_standoff | PCB mounting screw |
| heat_set_boss | heat-set threaded insert + machine screw |
| hex_nut_trap | hex nut + machine screw |
| counterbore_hole | socket head cap screw |
| countersink_hole | countersunk screw |
| pin_hinge | 1.75 mm filament pin |

`servo_spline`, `dowel_bore`, `ball_socket` are left unmarked: their mate is a user device
or is normally printed.

## Risks / Trade-offs

- [Planner omits a non-block item (glue, magnet in a plain pocket)] -> no marker can catch
  it; the planner rule names these categories explicitly and the Phase 2 table shows the
  user what is (and is not) listed.
- [`qty` drifts from the script after a correction] -> `qty` is optional; the delivery
  report reads the plan as last reconciled. Accepted.
