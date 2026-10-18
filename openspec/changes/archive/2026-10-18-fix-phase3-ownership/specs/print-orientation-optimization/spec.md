## ADDED Requirements

### Requirement: Per-union pipeline commands name the union id
Every per-union Phase 3 command in `skill/phase3_build.md` (print-orientation input STL,
toolpath-speed candidate input and output, the per-union orientation file, the
`--print-rotate` hint, and the quality gate's `--orientation`) SHALL name its files by
`<union_id>`. Part script paths SHALL stay `build/<part_id>.py`. The skill SHALL state that
a part without declared `unions` has a single union whose id equals its part id.
`build/orientations.json` SHALL be keyed by union id.

#### Scenario: Multi-union part resolves its STLs
- **WHEN** a part declares unions `leaf_a` and `leaf_b` and its STLs are delivered to `stl/`
- **THEN** the print-orientation commands read `stl/leaf_a.stl` and `stl/leaf_b.stl` and
  write `build/leaf_a.orientation.json` and `build/leaf_b.orientation.json`

#### Scenario: Single-union part is unchanged
- **WHEN** a part declares no `unions`
- **THEN** its union id is its part id and every per-union path equals the part-keyed path
