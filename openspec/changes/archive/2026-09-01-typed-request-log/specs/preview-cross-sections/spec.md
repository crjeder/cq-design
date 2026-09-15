## MODIFIED Requirements

### Requirement: Section positions are ranked by request_log priority and capped

The part-authoring procedure SHALL select which named+positioned `interfaces[]`
entries become `--extra-section` cuts by tier, most specific first: (1) entries whose
`name` matches a `request_log` entry with `kind: clarification`; (2) entries matching
a `kind: correction` entry; (3) all remaining named+positioned entries. An interface
matches a `request_log` entry when the interface `name` (or `<part>.<name>`) appears
in that entry's `targets` array (case-insensitive); for a `request_log` entry that
carries no `targets`, matching SHALL fall back to
`request_log_search.py BUILD_PLAN.json --query "<name>"` (case-insensitive substring
against `request_log.text`). Within a tier, entries matching a `request_log`
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

#### Scenario: Targets membership matches ahead of a text substring

- **WHEN** an interface `name` appears in a `clarification` entry's `targets`
  array but that word does not appear in the entry's `text`
- **THEN** the interface is treated as matched to that entry (tier 1)

#### Scenario: Untyped entry still matches by text substring

- **WHEN** an interface `name` appears in the `text` of a `correction` entry that
  carries no `targets`
- **THEN** the interface is treated as matched to that entry (tier 2)

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
