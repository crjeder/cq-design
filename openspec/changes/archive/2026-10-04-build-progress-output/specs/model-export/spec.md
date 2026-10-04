## ADDED Requirements

### Requirement: Optional progress callback

`export_model` SHALL accept an optional keyword-only `progress` callable taking one string, default `None`. When supplied, it SHALL be called with a `[k/N] <step> <id>` line for each part loaded, each per-union STL written, and each fused plate STL written, each phase counted separately, and once with `writing model.3mf` (no counter) before the 3MF is written. When `None`, `export_model` SHALL produce no progress output. The files written and the returned dict SHALL NOT depend on whether `progress` is supplied.

#### Scenario: Callback receives per-phase lines

- **WHEN** `export_model` is called with a recording callback on a plan with two parts and three unions on one multi-union plate
- **THEN** the callback receives two part-loading lines numbered `[1/2]` and `[2/2]`, one `writing model.3mf` line, three union-STL lines numbered `[1/3]` to `[3/3]`, and one plate line `[1/1]`

#### Scenario: No callback

- **WHEN** `export_model` is called without `progress`
- **THEN** nothing is printed by `export_model` and the files written are identical to a call with a callback

#### Scenario: JSON CLI unchanged

- **WHEN** `model_export` is run as a CLI
- **THEN** stdout is the same JSON document as before and contains no progress lines
