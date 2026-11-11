## Why

Named features are rarely inspectable: `--detail` is manual-only (TODO.md "Preview proactive
detail renders"), the detail camera is fixed so back/bottom features are hidden, there is no
marker in detail or section images, the cut axis for an interface is guessed from its wall
(slicing a hole across instead of along its axis), and `section_select` finds only
axis-aligned cylinders, so shelves and enclosures get no meaningful whole-part cut.
Depends on `preview-section-readability` (cap colour, edges, visibility test).

## What Changes

- New `feature_frame.py`: for an interface with `position_mm`, derive from the built solid
  the feature bounding box, dominant face normal and depth (solid-derived; no schema change).
- Per-feature preview: camera along the feature normal, framed on the bbox, marker on the
  feature; a section through the feature axis (containing the normal) when the feature has
  depth (hole, slot, pocket, boss), skipped for flat features.
- Whole-part section selection by slice analysis (inner-loop count, void area, area change
  between neighbouring slices) in addition to `section_select` bore/boss cuts.
- One 2 x 2 preview sheet per part holds at most 4 tiles, chosen by relevance: features the
  user named in a prompt, changed by a user request or answered via ask_user rank first
  (request_log kinds `clarification`, `correction`, explicit mention), then remaining
  features by size, then whole-part sections. Full-size per-tile files are still written.
- `validate_args` emits the selection flags; the builder runs the command unchanged.

## Capabilities

### New Capabilities
- `feature-preview-frames`: solid-derived feature bbox/normal/depth, per-feature views with marker and section, relevance-ranked 2 x 2 sheet capped at 4.

### Modified Capabilities
- `preview-cross-sections`: whole-part sections chosen by slice analysis; interface cut axis from the feature frame instead of the wall guess.

## Impact

- New `src/feature_frame.py`, section scorer next to `src/section_select.py`,
  `src/preview.py` (marker in detail/section renders, 2 x 2 sheet), `src/render_preview.py`
  (new `--feature` / `--sheet` flags), `src/render_prompt.py` (`validate_args`, relevance
  ranking reusing `section_cuts`' request_log ranking), `prompts/builder.md`,
  `reference/scripts.md`, `FILES.md`, tests.
- `run_cadquery_model.py` forwards the new flags; existing JSON contract keys unchanged.
