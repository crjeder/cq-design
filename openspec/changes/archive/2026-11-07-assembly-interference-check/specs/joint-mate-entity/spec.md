## ADDED Requirements

### Requirement: A joint member may name the union it fuses into
Each `joints[].members[]` entry SHALL accept an optional `union` (a union id belonging to the member's `part`). When absent it SHALL resolve to the part's only union. Plan validation SHALL reject an entry that omits `union` when its part declares more than one union, and an entry whose `union` is not one of that part's unions.

#### Scenario: Multi-union part without union is rejected
- **WHEN** a member's part declares two unions and the member omits `union`
- **THEN** plan validation fails, reporting the member must name a union

#### Scenario: Unknown union is rejected
- **WHEN** a member names `union: "ghost"` not declared by its part
- **THEN** plan validation fails, reporting the union is not in that part

#### Scenario: Single-union part needs no union
- **WHEN** a member's part has one union and `union` is omitted
- **THEN** the member resolves to that union
