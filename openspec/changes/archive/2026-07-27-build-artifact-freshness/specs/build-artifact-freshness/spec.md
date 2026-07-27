## ADDED Requirements

### Requirement: Provenance stamp is a hash of the source script's contents

The system SHALL provide a stdlib-only helper that computes a provenance stamp for a
generated artifact as a SHA-256 hex digest of the part script's file contents that produced
it. The stamp SHALL NOT be derived from file modification time or any other filesystem
metadata, since mtime is unreliable across checkouts, copies, and editors.

#### Scenario: Identical script contents produce identical stamps
- **WHEN** the provenance stamp is computed twice for the same part script content
- **THEN** both stamps are identical

#### Scenario: Any content edit changes the stamp
- **WHEN** a part script's contents are edited in any way (including an edit that leaves
  geometry, bounding box, or file size unchanged)
- **THEN** the recomputed stamp differs from the previously recorded stamp

### Requirement: Stamp comparison treats an absent stamp as unknown, not stale

The system SHALL provide a comparison helper that, given a previously recorded stamp (or
its absence) and a script path, reports whether the artifact is stale relative to that
script. An absent recorded stamp SHALL be reported as not stale (unknown provenance), so
that artifacts produced before this mechanism existed, or produced without opting into
stamping, are not treated as mismatches.

#### Scenario: Matching stamp is not stale
- **WHEN** a recorded stamp equals the current hash of the source script
- **THEN** the comparison reports not stale

#### Scenario: Mismatched stamp is stale
- **WHEN** a recorded stamp does not equal the current hash of the source script
- **THEN** the comparison reports stale

#### Scenario: Absent stamp is not stale
- **WHEN** no stamp was recorded for an artifact
- **THEN** the comparison reports not stale, distinguishing "no information" from "known
  mismatch"

### Requirement: Export manifest records per-union and per-zone provenance

The model export SHALL write a sidecar manifest file alongside the exported STLs, mapping
each union id (and each declared keep-out zone, keyed by declaring part id and zone name) to
the provenance stamp of the part script it was built from, plus the export timestamp. The
manifest SHALL be readable independently of any single check stage so every whole-model
consumer of exported STLs shares one provenance record instead of each recomputing or
duplicating it.

#### Scenario: Manifest covers every exported union
- **WHEN** a model with multiple unions is exported
- **THEN** the manifest contains one entry per union id, each carrying the provenance stamp
  of the script that produced it

#### Scenario: Manifest covers declared keep-out zones
- **WHEN** a part declares one or more keep-out zones and the model is exported
- **THEN** the manifest contains one entry per zone, keyed by declaring part id and zone
  name, carrying the provenance stamp of the declaring part's script

### Requirement: A whole-model check stage detects stale exported geometry

A whole-model check stage that validates exported STLs (the kinematic range check, the
plate-clearance check, the keep-out-zone check) SHALL, when both an export manifest and a
directory of current part scripts are available, compare each relevant union's (or zone's)
recorded provenance stamp against its current source script. When the comparison reports
staleness, the stage SHALL emit a `stale_artifact` finding, using the shared
`{source, severity, type, message, hint}` contract with `severity: "error"`, naming the
affected union (or zone) and instructing the user to re-run the export, and SHALL exclude
that union (or zone) from the geometry comparison it would otherwise run — a stale entry
must not be validated as if it were current.

#### Scenario: Stale union is reported and excluded from validation
- **WHEN** a part script changes after export and the whole-model check stage runs with the
  manifest and the part scripts available
- **THEN** the stage emits a `stale_artifact` error naming the affected union and does not
  report a clean pass based on that union's superseded geometry

#### Scenario: Unchanged union passes through unaffected
- **WHEN** a union's current source script still matches its manifest-recorded stamp
- **THEN** the stage validates that union's geometry normally, with no `stale_artifact`
  finding

### Requirement: Absent provenance data degrades to a warning, not a failure

When a whole-model check stage cannot perform the staleness comparison — no manifest is
present (a project exported before this mechanism existed, or an STL placed by hand), or no
directory of current part scripts was supplied — the stage SHALL emit a `check_skipped`
finding with `severity: "warning"` for the freshness check specifically, and SHALL continue
running its other validations rather than failing or refusing to validate.

#### Scenario: Missing manifest degrades to a skipped-check warning
- **WHEN** a whole-model check stage runs against a `stl_dir` with no export manifest
- **THEN** it emits a `check_skipped` warning noting that staleness could not be verified,
  and still runs its geometry/collision checks on the available STLs

#### Scenario: Missing parts directory degrades the same way
- **WHEN** a whole-model check stage runs without a directory of current part scripts
- **THEN** it emits the same `check_skipped` degradation and still runs its other checks
