## Why

The quality gate's overhang/printability check is implied by an external slicer
(the orca-check MCP, which runs OrcaSlicer CLI) in the project docs, but the
running code in `quality_gate.py` already performs a minimal in-process trimesh
overhang check while the docs still claim orca-check is part of the pipeline.
This split leaves the gate dependent on an unspecified external MCP that may be
absent, produces only a single "worst angle" signal with no location or extent,
and has no spec to anchor its behavior. Replacing it with a hardened,
self-contained trimesh analysis removes the external dependency, makes the gate
deterministic and offline, and gives Claude actionable overhang locations.

## What Changes

- Harden the in-process trimesh overhang analysis in `quality_gate.py` so it is a
  genuine replacement for orca-check: report total overhang area, the worst
  overhang region's location (face-centroid coordinates), and classify each
  flagged region as support-needed vs. self-supporting against the plan's
  `overhang_max_deg`.
- Emit overhang findings as structured issues consistent with the existing
  `errors`/`issues` contract (`type`, `message`, `hint`, plus location/area
  fields), so the fix-prompt and print-recipe stages can consume them.
- Make the check degrade gracefully and deterministically when trimesh/numpy are
  unavailable (already a warning) and document that the gate no longer requires
  any slicer or MCP.
- **BREAKING (docs/pipeline)**: Remove the orca-check and scad-analyzer MCP from
  the stated quality-gate pipeline. Purge stale references in `CLAUDE.md`
  (notably the `src/quality_gate.py` row and the pipeline description) and align
  `SKILL.md`/`README.md` wording to "in-process trimesh geometry + overhang
  analysis".

## Capabilities

### New Capabilities
- `overhang-analysis`: In-process, slicer-free geometry overhang and printability
  analysis performed by the quality gate on the exported STL using trimesh:
  detection thresholding against `overhang_max_deg`, overhang area and worst-
  region location reporting, support-needed classification, structured issue
  emission, and graceful degradation when trimesh is unavailable.

### Modified Capabilities
<!-- No existing spec defines the quality-gate overhang check; behavior is newly specified. -->

## Impact

- **Code**: `src/quality_gate.py` (`_analyze_stl` and issue assembly); possible
  small helper reuse from `src/measure_stl.py` for location reporting.
- **Tests**: new/updated coverage for overhang area, location, and support
  classification (no existing `tests/test_quality_gate.py` yet).
- **Docs**: `CLAUDE.md`, `SKILL.md`, `README.md` references to orca-check /
  scad-analyzer / external slicer.
- **Dependencies**: removes any implied runtime dependency on the orca-check MCP
  and OrcaSlicer CLI from the gate; relies only on the existing trimesh + numpy
  deps.
