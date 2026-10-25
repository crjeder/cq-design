## Context

`_section_cuts(result, extra_sections, cross_sections)` in `src/render_preview.py` returns the extra-section cuts if there are any, else the bbox-center cuts if `--cross-sections` is set. `section_select.select_sections(shape, max_cuts, reserved)` already treats features that reserved cuts show as covered, and drops candidates within 0.5 mm of a reserved cut.

## Goals / Non-Goals

**Goals:** opt-in geometry-driven cuts, at most 3 cuts total, no new failure modes.

**Non-Goals:** changing `select_sections` heuristics; changing the `--detail` section path; changing how render_prompt ranks plan `--extra-section` cuts.

## Decisions

- **Slot fill:** `select_sections(shape, max_cuts=3 - len(extra), reserved=extra)`, skipped when there are already 3 or more extra cuts. The selector is greedy, so asking for fewer cuts gives the same result as asking for 3 and truncating.
- **Shape for multi-union results:** `render_preview` merges the unions with `Workplane.add`, so `.val()` would see only the first union. The selector runs on `Compound.makeCompound(result.vals())` so every union's bores are seen.
- **Implies `--cross-sections`:** so the bbox fallback works when no cut is selected, without callers having to pass two flags.
- **Auto cut file names:** `<stem>_section_<axis>_<pos>mm.png`, the same as extra-section cuts. They are positioned cuts, not center cuts.
- **Error policy:** any exception from import or selection prints `WARNING: --auto-sections failed: ...` and is treated as "nothing selected".

## Risks / Trade-offs

- Each preview now spends extra time walking the faces; for builder-sized parts this is small next to the rendering time.
