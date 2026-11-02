# part-materials Specification

## Purpose
TBD - created by archiving change multi-material-planning. Update Purpose after archive.
## Requirements
### Requirement: Per-body material and color
A part and each `unions[]` entry SHALL accept optional `material` and `color` (`#RRGGBB`).
Each resolves union, then part, then plan-level `material`; color falls back to a color
derived from the resolved material.

#### Scenario: Union overrides part
- **WHEN** a part sets `material` PLA and one union sets `material` TPU
- **THEN** that union resolves to TPU and the other unions to PLA

#### Scenario: Single-material plan unchanged
- **WHEN** no part or union sets `material` or `color`
- **THEN** the plan validates, resolves every body to the plan material, and exports byte-identically to before

### Requirement: Material boundaries are non-sticky and silent
The system SHALL NOT raise an error or warning because bodies of different materials touch
or overlap, and SHALL NOT assume adhesion across such a boundary.

#### Scenario: Support material touches body
- **WHEN** a PVA union touches a PLA union
- **THEN** validation and the quality gate report nothing about that contact

### Requirement: Filament slot assignment
The system SHALL assign filament slots 1..n to distinct (material, color) pairs in order of
first appearance, identically on every run.

#### Scenario: Two materials
- **WHEN** a plan uses PLA white and TPU black
- **THEN** PLA white is slot 1 and TPU black is slot 2

### Requirement: Slot overflow warns and asks
When the number of distinct (material, color) pairs exceeds the profile's `max_materials`,
the plan summary SHALL show a warning naming both counts, and the planner SHALL ask the
user how to proceed before the plan is approved. It SHALL NOT block validation or export.

#### Scenario: Five materials on four slots
- **WHEN** a plan needs 5 pairs and `max_materials` is 4
- **THEN** the summary warns "5 materials, 4 slots" and the planner asks the user

### Requirement: Per-part weight
Weight estimates SHALL use the part's resolved material density (part, else plan).

#### Scenario: Part overrides plan material
- **WHEN** a part sets `material` TPU in a PLA plan
- **THEN** its weight estimate uses TPU density

