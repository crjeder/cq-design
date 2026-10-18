## MODIFIED Requirements

### Requirement: Mesh size is chosen by the author and the result is re-runnable

`fem_check.py` SHALL take the mesh size as a required `--mesh-size <mm>` argument rather
than deriving a default. The result SHALL echo the mesh size together with the resulting
node and element counts, so the author can judge whether the discretisation supports the
number reported.

`skill/phase3_build.md` SHALL instruct the author that an implausible
result -- an extreme concentration ratio, a failure index far from what the geometry
suggests, or a peak at an unexpected location -- is grounds to re-run at a smaller mesh
size and compare: a `fi_p99` that moves substantially between the two runs means the
coarser mesh was not converged and its number SHALL NOT be cited; a `fi_p99` that holds
means the result is mesh-independent at that size.

#### Scenario: Mesh size must be stated
- **WHEN** `fem_check.py` is invoked without `--mesh-size`
- **THEN** it reports the missing argument rather than choosing a size on the author's
  behalf

#### Scenario: Result carries its discretisation
- **WHEN** a solve completes
- **THEN** the result states the mesh size used and the resulting node and element counts

#### Scenario: Implausible result is re-run finer
- **WHEN** a result's concentration ratio or failure index does not match what the geometry
  suggests
- **THEN** the author re-runs at a smaller mesh size and compares `fi_p99` between the two
  runs before citing either number
