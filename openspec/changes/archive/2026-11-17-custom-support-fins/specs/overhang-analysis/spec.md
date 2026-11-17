## ADDED Requirements

### Requirement: Sacrificial fin unions are excluded from part findings
The gate SHALL skip unions flagged `sacrificial: true` when evaluating
`overhang_exceeded`, `sliver_fin`, thin-region and brim findings, and SHALL emit one
`designed_support` `info` issue giving the fin count and total fin volume. The part
unions SHALL still be analyzed in full.

#### Scenario: Fin gap not flagged
- **WHEN** a plan has a part union and a `sacrificial` fin union with a 0.2 mm standoff
- **THEN** no `sliver_fin` or thin-region finding names the fin union

#### Scenario: Designed support reported
- **WHEN** at least one sacrificial union exists
- **THEN** the report contains exactly one `designed_support` info issue

#### Scenario: Part overhang still reported
- **WHEN** the part union has an overhang above the limit that no fin covers
- **THEN** `overhang_exceeded` is still emitted for the part union
