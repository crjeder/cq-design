## MODIFIED Requirements

### Requirement: Cross-section views are written as separate files through declared positions

When cross-section rendering is enabled, the renderer SHALL write each cross-section as
a **separate PNG file**, not append it to the multi-view tile. Each section SHALL be
cut through a declared feature or union position supplied by the caller (from
`BUILD_PLAN.json` interfaces/unions). The part-authoring procedure (`skill/
phase3_build.md`) SHALL supply one such position for **every** named+positioned
`interfaces[]` entry selected by the ranking and cap described in the "Section
positions are ranked by request_log priority" requirement below -- not only when the
author judges it necessary. When a part has zero named+positioned interfaces, the
renderer SHALL fall back to the three bounding-box-center cuts (Section X, Section Y,
Section Z). The separate section paths SHALL be returned in `previews[1:]` (the
default tile stays `previews[0]`).

#### Scenario: Section written through a declared junction

- **WHEN** the caller supplies a union-junction position and requests cross-sections
- **THEN** a separate section PNG cut through that position is written and its path
  appears in `previews[1:]`, and the default `previews[0]` tile is unchanged

#### Scenario: Fallback to center cuts only when no named positions exist

- **WHEN** cross-sections are requested for a part with no named+positioned
  `interfaces[]` entries
- **THEN** three separate section files are written for the bounding-box-center X, Y,
  and Z cuts

#### Scenario: Named interfaces suppress the center-cut fallback

- **WHEN** cross-sections are requested for a part that declares at least one
  named+positioned `interfaces[]` entry
- **THEN** the renderer receives declared `--extra-section` positions for that part (per
  the ranking/cap requirement below) instead of falling back to bbox-center cuts

#### Scenario: Boolean cut failure degrades gracefully

- **WHEN** a cross-section Boolean cut raises an OCC exception
- **THEN** that section file is skipped with a warning to stderr and the remaining
  sections and the default tile are produced normally

### Requirement: Section positions are ranked by request_log priority and capped

The part-authoring procedure SHALL select which named+positioned `interfaces[]`
entries become `--extra-section` cuts by tier, most specific first: (1) entries whose
`name` matches a `request_log` entry with `kind: clarification`; (2) entries matching
a `kind: correction` entry; (3) all remaining named+positioned entries. Matching SHALL
use `request_log_search.py BUILD_PLAN.json --query "<name>"` (case-insensitive
substring against `request_log.text`). Within a tier, entries matching a `request_log`
entry SHALL be ordered by that entry's array position descending (most recent first);
unmatched tier-3 entries SHALL keep plan declaration order. The selected list SHALL be
capped at 3 entries, filling tiers in order (tier 1 entries first, then tier 2, then
tier 3, stopping once 3 are selected). Each selected entry's cut axis SHALL be the axis
normal to its declared `wall` field when present, else the axis of `position_mm`'s
largest-magnitude component relative to the part bounding-box center.

#### Scenario: Clarification-flagged feature outranks a correction-flagged one

- **WHEN** a part has one named interface matched by a `kind: clarification`
  `request_log` entry and another matched by a `kind: correction` entry
- **THEN** the clarification-matched interface's position is selected first

#### Scenario: Cap stops selection at 3 even with more candidates

- **WHEN** a part declares 5 named+positioned interfaces, all matching `request_log`
  entries
- **THEN** exactly 3 `--extra-section` positions are supplied, the 3 highest-priority
  by tier and then recency

#### Scenario: Unmatched interfaces fill remaining budget in plan order

- **WHEN** a part has 1 clarification-matched interface and 4 unmatched named+
  positioned interfaces, with a cap of 3
- **THEN** the clarification-matched interface plus the first 2 unmatched interfaces
  in plan declaration order are selected

#### Scenario: Axis chosen from declared wall when present

- **WHEN** a selected interface declares `wall: "+x"` and a `position_mm`
- **THEN** the `--extra-section` cut uses the x axis at that position's x coordinate

#### Scenario: Axis falls back to largest-magnitude position component

- **WHEN** a selected interface has no `wall` field and its `position_mm` relative to
  the part bbox center has its largest-magnitude component on the z axis
- **THEN** the `--extra-section` cut uses the z axis at that position's z coordinate
