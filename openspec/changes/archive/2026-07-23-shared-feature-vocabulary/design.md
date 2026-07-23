# Design: shared-feature-vocabulary

## Context

The canonical feature vocabulary already exists in `BUILD_PLAN.json` (part ids,
`interfaces[].name`, union ids), and a spatial convention (compass directions) is
documented in USE.md and both prompts. What is missing is (a) the names originating
from the user's own words instead of LLM-coined snake_case, (b) any way for the user to
map names to pixels on the preview tile, and (c) consistency between the compass
convention and the artifacts (`preview.py` labels panels "Front (Y-) / Left (X-) /
Top (Z+)", `preview.py:394-398`).

Existing machinery this builds on:

- `render_preview.py` already parses named `--detail` specs
  (`name=...;center=x,y,z;...`) and threads plan positions via `--extra-section`;
  `run_cadquery_model.py` forwards both (`run_cadquery_model.py:544`).
- Panels are rendered by `_render_cq_view` with known cameras (elev/azim, ortho for the
  three projection panels), so a 3D authored-frame point projects deterministically to
  panel 2D.
- `interfaces[].position_mm` (optional, authored frame) is the position source; the
  plan summary already tables interface names.

## Goals / Non-Goals

**Goals:**

- One vocabulary flowing unchanged: user's request nouns -> plan ids -> preview legend
  -> conversation -> part-script parameters.
- The checkpoint preview doubles as the glossary-ratification artifact: badges + legend
  bind each agreed name to visible geometry, deterministically (no LLM drawing, no
  vision pass).
- Compass terms are the only spatial vocabulary in user-facing prose and on the tile.

**Non-Goals:**

- No naming for undeclared geometry (walls, ribs, base bodies) -- that is the
  intra-part-anchors item (TODO.md:110), a separate decision.
- No dynamic "currently under discussion" filtering: a part's `interfaces` list is
  short, so labeling all declared features is already "only relevant features". Named
  `--detail` views remain the zoom mechanism.
- No plan-schema changes: `interfaces[].name` and `position_mm` already exist and
  suffice.
- No occlusion handling: with three orthographic views nearly every feature is visible
  in at least one panel (user-accepted); badges draw in all three ortho panels.

## Decisions

### D1: Names originate from the user (prompt + skill rule, no tooling)

`prompts/planning.md` gains a naming rule: when the user has named a thing (in the
request or conversation), that word verbatim (lowercased, spaces to underscores)
becomes the part id / interface name. The LLM only coins names for unnamed things and
the plan-summary checkpoint introduces them explicitly ("I'm calling the bottom part
`base`"). Rejected alternative: a rename/aliasing layer mapping user nouns to internal
ids -- two vocabularies with a sync problem, when the plan can simply use the user's
word directly.

### D2: Callouts are drawn inside matplotlib, not post-hoc on the PIL image

Badge positions come from projecting the authored-frame `position_mm` through the
panel's live `Axes3D` (`proj3d.proj_transform` + the axes data transform) before the
figure is rasterized. Rejected alternative: post-hoc PIL drawing on the saved panel
image -- requires re-deriving the data-to-pixel mapping (axis limits, margins) that
matplotlib already owns; fragile against any framing change.

Rendering: a filled circle badge with the number, a thin leader line from badge to the
projected point (badge offset outward from the panel center so leaders point inward),
drawn on the three orthographic panels only. The isometric panel stays clean -- it is
the pictorial read, and a non-ortho projection adds ambiguity for no grounding value.

### D3: CLI shape mirrors `--detail`

`render_preview.py` gains a repeated `--callout "name=<n>;center=x,y,z"` flag reusing
the existing `--detail` spec parser conventions; `run_cadquery_model.py` forwards it
exactly like `extra_sections`. The skill (phase 3 step 4) threads every interface that
declares both `name` and `position_mm` from the plan, in plan order; badge numbers are
assignment order. Interfaces without `position_mm` get no badge; the legend lists them
after the badged entries as "(not located)" so the vocabulary is still complete on the
artifact. Rejected alternative: reading `BUILD_PLAN.json` inside the renderer --
`preview.py` is deliberately plan-agnostic (it renders any script), and the
skill-threads-plan-data pattern already exists for sections.

### D4: Legend is a caption row, not in-panel text

One legend line under the tile (same footer area as the existing bbox/volume caption):
`1 handle   2 cable_slot   3 boss_sw (not located)`. In-panel name text collides with
geometry at small view sizes; numbers stay readable at badge size.

### D5: Panel labels become compass terms derived from the actual camera

The three ortho panel labels change to compass terms naming the viewing station
("Viewed from North/West/above" style), chosen so they are consistent with the axis
mapping in `prompts/planning.md` (North=+Y, East=+X). The current prose is
contradictory (docstring says Front looks -Y; the label says "Front (Y-)"; USE.md's
viewer-facing-North convention implies the user's mental "front" is the South face), so
the labels are fixed empirically: render an asymmetric fixture (distinct marker on the
North face) once during implementation and name each panel by what it provably shows.
The spec delta mandates compass labels + empirical consistency, not specific
elev/azim-to-label pairs. Camera angles themselves do not change -- only labels.

### D6: Conversational rules live in the skill phase docs

Two rules added to the checkpoint prose in `skill/phase2_planning.md` and
`skill/phase3_build.md`:

- Spatial references in user-facing text use compass/up-down terms only;
  left/right/front/back appear only when quoting the user.
- Before acting on an ambiguous or spatial feature reference, restate it as the agreed
  name + badge number and (when not obvious) confirm. This is a prose rule for the main
  session and checkpoint-facing agents; sub-agent prompts already carry the compass
  table.

## Risks / Trade-offs

- [Badge clutter on feature-dense parts] -> interfaces lists are short in practice
  (schema encourages a handful); badges are numbers not names; detail views absorb
  dense clusters. If a part exceeds what fits, later escalation is per-panel badge
  filtering, not v1.
- [Projected badge lands on empty space for a feature inside the body (blind cavity)]
  -> accepted: the leader still points at the true location; section/detail views are
  where internal features are actually reviewed, and those are already named.
- [Panel relabel invalidates habits/tests that grep for "Front"] -> update
  `tests/test_preview.py` and the `cq-preview-rendering` spec in the same change; the
  label strings appear nowhere in machine contracts (JSON keys are unchanged).
- [User nouns collide or are unusable as ids (spaces, duplicates, non-ASCII)] ->
  normalization rule (lowercase, underscores) plus the existing schema uniqueness
  check; on collision the LLM disambiguates with a suffix and says so at the
  checkpoint.
- [`position_mm` optional, so some features are unmarked] -> legend still lists them;
  planning prompt already encourages structured placement, and
  `feature_presence_check`'s recorded feature centers are a future fallback source
  (explicitly deferred).

## Open Questions

- None blocking. The Front-vs-North empirical check (D5) is resolved during
  implementation, not before it.
