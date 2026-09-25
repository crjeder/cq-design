# standalone-part-export Specification

## Purpose

Defines the minimal per-part deliverable: `standalone/` holds each part script plus only the skill helper modules it imports and a cadquery-only environment, for users who want the parametric code without the full `lib/` bundle.

## Requirements

### Requirement: Standalone export writes each part with only its imported helpers

The skill SHALL provide `src/export_standalone.py`, which for each part script in the parts directory writes `<out>/<part_id>.py` and copies into `<out>` only the skill helper modules (`cq_verify`, `cq_compat`, and the `blocks` package) that the script imports, directly or through another copied helper. It SHALL NOT copy mesh, export, orientation, placement, or preview tooling.

#### Scenario: Part importing only cadquery ships alone

- **WHEN** a part script imports only `cadquery`
- **THEN** `<out>` contains that script and no `cq_verify.py`, `cq_compat.py`, or `blocks/`

#### Scenario: Part importing helpers gets exactly those

- **WHEN** a part script contains `from cq_verify import verify_boolean` and `from blocks import fillet_box`
- **THEN** `<out>` contains `cq_verify.py` and the `blocks/` package, and does not contain `mesh_io.py` or `exporters/`

#### Scenario: Shipped script runs in place

- **WHEN** `python <part_id>.py` is run from inside `<out>` in an environment with cadquery installed
- **THEN** it executes without an `ImportError` from a skill helper

### Requirement: Standalone export declares a minimal environment

The export SHALL write a `pyproject.toml` in `<out>` whose dependencies are `cadquery` only, plus `cq-warehouse` (as the same git source the skill uses) only when a shipped `.py` file references `cq_warehouse` or `heat_set_boss`. It SHALL also copy the project's `parameters.py` when one exists.

#### Scenario: Default environment is cadquery only

- **WHEN** no shipped file references `cq_warehouse` or `heat_set_boss`
- **THEN** `<out>/pyproject.toml` lists `cadquery` and does not list trimesh, matplotlib, scipy, networkx, lxml, or cq-warehouse

#### Scenario: Heat-set insert pulls in cq-warehouse

- **WHEN** a part script calls `heat_set_boss`
- **THEN** `<out>/pyproject.toml` also declares `cq-warehouse`

### Requirement: Phase 4 delivers the standalone directory

Phase 4 SHALL run the standalone export on every delivery, overwriting `standalone/`, and SHALL list it among the output files.

#### Scenario: Delivery regenerates standalone

- **WHEN** a correction is delivered after `standalone/` already exists
- **THEN** Phase 4 re-runs the export and `standalone/` reflects the current part scripts
