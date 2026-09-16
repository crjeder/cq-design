## ADDED Requirements

### Requirement: Plan summary surfaces open questions from planning_notes

`src/plan_summary.py` SHALL scan `planning_notes` line by line (stripping surrounding
whitespace and a leading `-`, `*`, or `+` bullet marker) and render every line whose
remainder starts with the literal `OPEN:` as a Markdown bullet list under an **Open
questions** heading. The section SHALL be omitted entirely when no line matches, and
SHALL NOT be omitted when `planning_notes` is absent from the check itself -- an absent
`planning_notes` simply yields zero matches.

#### Scenario: Single open question rendered
- **WHEN** `planning_notes` contains a line `OPEN: hinge pin diameter not specified by
  user`
- **THEN** the summary contains an **Open questions** section with that line as a bullet

#### Scenario: Bullet-prefixed OPEN line is recognized
- **WHEN** `planning_notes` contains a line `- OPEN: unclear whether lid is snap or screw
  fit`
- **THEN** the summary's **Open questions** section includes it with the bullet marker
  stripped from the matched text

#### Scenario: No open questions omits the section
- **WHEN** `planning_notes` contains no line starting with `OPEN:` (including when
  `planning_notes` is absent)
- **THEN** the summary contains no **Open questions** heading

#### Scenario: Prose mentioning "open" is not mistaken for the marker
- **WHEN** `planning_notes` contains a line such as "the enclosure stays open on the
  east face"
- **THEN** that line is not included in the **Open questions** section (only a line whose
  remainder starts with the literal token `OPEN:` is matched)

---

### Requirement: Plan summary flags planner-coined names against request_log

`src/plan_summary.py` SHALL check each part `id` and each non-empty
`interfaces[].name` against the words (lowercased, non-alphanumeric-delimited tokens) of
every `request_log[].text` entry. A name whose own tokens are not a subset of that
combined word set SHALL be listed under a **Names I chose** heading, one bullet per
flagged name naming the part and, for an interface, the interface too. The section SHALL
be omitted when `request_log` is absent or empty, or when every part id and interface
name matches.

#### Scenario: Unmatched part id is flagged
- **WHEN** a part has `id: "bracket"` and no `request_log[].text` entry contains the word
  "bracket"
- **THEN** the summary's **Names I chose** section lists `bracket`

#### Scenario: User-named part is not flagged
- **WHEN** a part has `id: "handle"` and some `request_log[].text` entry contains the
  word "handle"
- **THEN** `handle` does not appear in the **Names I chose** section

#### Scenario: Suffix-disambiguated name matches its root word
- **WHEN** an interface has `name: "hole_2"` and a `request_log[].text` entry contains
  the word "hole"
- **THEN** `hole_2` does not appear in the **Names I chose** section (its own word tokens
  `hole` and `2` need only the `hole` token to be present)

#### Scenario: No request_log omits the section
- **WHEN** the plan has no `request_log` field
- **THEN** the summary contains no **Names I chose** heading, regardless of naming
