## MODIFIED Requirements

### Requirement: Emit the chosen orientation transform with rationale

The system SHALL emit, per union, the recommended print orientation as a rotation
transform (compatible with the `placement.py` rotation convention), together with the
strength, support, and visual score breakdown, the active optimization mode, and a
human-readable rationale that names the mode and explains why the pose won under it. This
output SHALL be distinct from the union's assembled-frame `placement`.

The orientation tool SHALL accept an optional source-script path identifying the part
script whose authored-frame geometry produced the mesh being scored. When supplied, the
result SHALL carry that script's provenance stamp (`source_script_hash`) so the result is
self-describing about which script version it was computed from. When omitted, the result
SHALL carry no such stamp, and a consumer comparing against it SHALL treat the absence as
unknown provenance, not a mismatch.

#### Scenario: Result carries transform, scores, and mode

- **WHEN** orientation optimization completes for a union
- **THEN** the result contains the rotation transform, the strength score, the support
  score, the visual score, the active `optimize_for` mode, and a rationale string, and does
  not overwrite the union's `placement`

#### Scenario: Source script is stamped when supplied

- **WHEN** the orientation tool is invoked with a source-script path
- **THEN** the result carries that script's provenance stamp

#### Scenario: Result is unstamped when no source script is given

- **WHEN** the orientation tool is invoked without a source-script path
- **THEN** the result carries no provenance stamp, and a consumer treats this as unknown
  provenance rather than a staleness mismatch
