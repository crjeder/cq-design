## ADDED Requirements

### Requirement: Export writes a provenance manifest alongside the STLs

The exporter SHALL write a provenance manifest into the STL output directory recording,
for every exported union and every exported keep-out zone, the id of the part script that
produced it and that script's provenance stamp, plus the export's timestamp. The manifest
SHALL be written on every export run, unconditionally, so a consumer never has to special-
case "manifest not yet written" for a project that has been exported at least once since
this mechanism was introduced.

#### Scenario: Manifest is written alongside per-union STLs
- **WHEN** the model exports its per-union assembled-pose STLs
- **THEN** a manifest file also appears in the STL output directory, naming every exported
  union and the provenance stamp of the script that produced it

#### Scenario: Manifest covers keep-out zones too
- **WHEN** a part declares keep-out zones and the model is exported
- **THEN** the manifest also records an entry per zone, keyed by declaring part id and zone
  name, carrying that part's script's provenance stamp
