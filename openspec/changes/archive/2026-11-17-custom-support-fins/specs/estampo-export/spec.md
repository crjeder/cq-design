## ADDED Requirements

### Requirement: Parts carrying fin unions disable slicer supports
When a part's plan contains a `sacrificial: true` fin union, the estampo export SHALL
write `enable_support = false` for that part, because the support is designed into the
STL.

#### Scenario: Fins present
- **WHEN** a part has a sacrificial fin union
- **THEN** its estampo entry has `enable_support = false`

#### Scenario: No fins
- **WHEN** a part has no sacrificial union
- **THEN** the existing `enable_support` derivation is unchanged
