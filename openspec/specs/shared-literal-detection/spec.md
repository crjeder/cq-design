## Purpose

Advisory detection of an unlinked physical mate between two parts that plan_validate.py
would otherwise miss: a shared `interfaces[].name`, a same-position/same-diameter round
interface pair (regardless of name), or hinge/pivot language on a multi-part plan with
no `joints` entry at all. Each closes a way a shared literal (a pivot Z, a bore diameter)
can re-diverge between two parts' independently-typed declarations.

## Requirements

### Requirement: Shared named interface with no linking joint is flagged
When one `interfaces[].name` is held by two or more parts, and no single
`joints` entry's `members` links every pair of those parts, `plan_validate.py`
SHALL emit one advisory finding (same tier as `check_block_thinness`) naming
the shared interface and the parts that remain unlinked. A `joints` entry
covering one pair narrows the finding to the parts still independently
typed; if every pair is linked, no finding is emitted. Interfaces with
`name: null` are not covered by this requirement (see the positional
requirement below).

#### Scenario: Two parts share a named interface with no joints entry
- **WHEN** two parts each declare an `interfaces[]` entry with
  `name: "pivot"` and the plan has no `joints` entry linking them
- **THEN** `plan_validate.py`'s advisory findings include one naming
  `'pivot'` and both parts

#### Scenario: A joints entry silences the finding
- **WHEN** the same two parts are also both `members` of one `joints` entry
- **THEN** no finding is emitted for `'pivot'`

#### Scenario: Three holders, one joint covers a pair
- **WHEN** three parts share `name: "pivot"` and a `joints` entry links two
  of them
- **THEN** the finding reports only the remaining unlinked part(s), not all
  three

### Requirement: Co-located round interfaces with no linking joint are flagged regardless of name
`plan_validate.py` SHALL also flag two parts that each declare an
`interfaces[]` entry with both `position_mm` and `diameter_mm`, whose
positions coincide within `feature_presence_check`'s existing position
tolerance after each is transformed through its part's `placement` (identity
when absent) into the assembled frame, and whose `diameter_mm` values are
within a small relative tolerance of each other — when no `joints` entry
links the two parts. This applies whether the two interfaces' `name` fields
are both null, both set but different, or one is null and the other set; it
is additive to, not a replacement for, the named-interface requirement
above.

#### Scenario: Unnamed co-located round interfaces are flagged
- **WHEN** two parts each declare a round `interfaces[]` entry with
  `name` absent, the same `diameter_mm` (within tolerance), and
  `position_mm` that, after each part's `placement` transform, land at the
  same assembled-frame point (within tolerance) — and no `joints` entry
  links the two parts
- **THEN** `plan_validate.py`'s advisory findings include one naming both
  parts and noting the coincident round feature

#### Scenario: A joints entry silences the positional finding
- **WHEN** the same two parts are `members` of one `joints` entry
- **THEN** no positional finding is emitted for that pair

#### Scenario: Different diameters are not flagged
- **WHEN** two parts' round interfaces coincide in position but their
  `diameter_mm` values differ by more than the relative tolerance
- **THEN** no positional finding is emitted for that pair

#### Scenario: Different positions are not flagged
- **WHEN** two parts each declare a round interface with the same
  `diameter_mm` but their assembled-frame positions differ by more than the
  position tolerance
- **THEN** no positional finding is emitted for that pair

#### Scenario: Interfaces without position_mm or diameter_mm are skipped
- **WHEN** a part's `interfaces[]` entry lacks `position_mm` or
  `diameter_mm`
- **THEN** it is not considered by this positional check (it may still be
  covered by the named-interface requirement above)

### Requirement: Hinge/pivot intent with no joints is flagged
When a plan has more than one part and its `intent` or any
`request_log[].text` contains a hinge/pivot/fold/articulation word
(word-boundary, case-insensitive match against `hinge`, `pivot`, `fold`, or
`articulat`), and the plan's `joints` field is absent, null, or an empty
array, `plan_validate.py` SHALL emit one advisory finding pointing at the
`joints`/`kinematics` schema fields as the expected route for a shared
mechanical mate.

#### Scenario: Hinge language with no joints entry
- **WHEN** a plan's `intent` is "cradle that folds flat against the plate"
  and `joints` is absent
- **THEN** the advisory findings include one noting hinge/pivot language
  with no `joints` entry

#### Scenario: joints present silences the finding
- **WHEN** the same plan declares a non-empty `joints` array
- **THEN** no hinge-intent finding is emitted

#### Scenario: Single-part plan is exempt
- **WHEN** a plan has exactly one part and its `intent` uses hinge language
- **THEN** no hinge-intent finding is emitted (a `joints` entry links two or
  more parts by definition)
