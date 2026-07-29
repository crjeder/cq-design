## MODIFIED Requirements

### Requirement: Anti-pattern finding catalog
The linter SHALL detect the following anti-patterns, each with a stable `type`
identifier: `boolean_in_loop`, `missing_result`, `submodule_import`,
`direct_export`, `magic_number`, `unanchored_feature`, `unguarded_boolean`,
`shell_after_fillet`, `fillet_after_chamfer`.

#### Scenario: Boolean inside a loop
- **WHEN** a script calls `.cut(...)`, `.union(...)`, or `.intersect(...)` inside a
  `for` or `while` body
- **THEN** a `boolean_in_loop` finding is reported with the offending line number

#### Scenario: Missing result assignment
- **WHEN** a script contains no top-level assignment to `result`
- **THEN** a `missing_result` finding is reported

#### Scenario: Submodule block import
- **WHEN** a script imports from a `blocks` submodule (e.g.
  `from blocks.primitives import fillet_box`)
- **THEN** a `submodule_import` finding is reported with a hint to import from
  `blocks` directly

#### Scenario: Direct exporter call
- **WHEN** a script calls `cq.exporters.export(...)`
- **THEN** a `direct_export` finding is reported with a hint that the shim owns
  export

#### Scenario: Shell after fillet
- **WHEN** a fluent chain calls `.shell(...)` after `.fillet(...)`
- **THEN** a `shell_after_fillet` finding is reported

#### Scenario: Fillet after chamfer
- **WHEN** a fluent chain calls `.fillet(...)` after an earlier `.chamfer(...)`
  in the same chain
- **THEN** a `fillet_after_chamfer` finding is reported with a hint to apply
  fillets before chamfers in the chain

#### Scenario: Clean script produces no findings
- **WHEN** a script contains none of the cataloged anti-patterns
- **THEN** the findings list is empty and `success` is `true`
