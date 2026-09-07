## ADDED Requirements

### Requirement: An interface name shared by two unlinked parts is reported

`plan_validate.py` SHALL report a plan-validation finding when one
`interfaces[].name` is declared on two or more parts that no `joints` entry links.
Two parts are linked when a single `joints` entry names both of them across its two
`members[].part` values. The finding SHALL name the interface and the parts holding
it, and SHALL point at `joints` / `mate_chain.py` as the derivation route.

The finding is advisory: it SHALL NOT be returned by `validate_plan` and SHALL NOT
make the plan invalid, so it never reaches the quality gate's `plan_invalid` path. It
SHALL be printed by `plan_validate.main()` after the plan passes, alongside the
existing thin-block and deferred-axis-arm findings. Interfaces with no `name` SHALL
be skipped.

#### Scenario: A shared pivot bore is declared twice with no joint
- **WHEN** a plan declares an interface named `pivot_bore` on both `cradle` and
  `plate`, and `joints` contains no entry naming both parts
- **THEN** `plan_validate.main()` prints a finding naming `pivot_bore`, `cradle` and
  `plate`
- **AND** `validate_plan` still returns an empty error list

#### Scenario: The shared feature is routed through a joint
- **WHEN** the same plan adds a `joints` entry whose two members are `cradle` and
  `plate`
- **THEN** no finding is reported for `pivot_bore`

#### Scenario: A name used by one part only
- **WHEN** an interface name appears on exactly one part, or an interface declares no
  `name`
- **THEN** no finding is reported for it

#### Scenario: Three parts share a name, one pair is linked
- **WHEN** `pivot_bore` is declared on `cradle`, `plate` and `strut`, and one
  `joints` entry links `cradle` and `plate`
- **THEN** one finding is reported naming `strut` as the unlinked holder of
  `pivot_bore`
