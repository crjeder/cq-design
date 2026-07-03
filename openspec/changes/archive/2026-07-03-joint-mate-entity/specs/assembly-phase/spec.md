## MODIFIED Requirements

### Requirement: Multi-part models are assembled declaratively from placement

The build pipeline SHALL combine multiple validated parts into the final assembled
model declaratively, from each union's `placement`, via the model-level export
(`model_export.py`). The pipeline SHALL NOT generate a hand-written fused CadQuery
assembly script, and SHALL NOT write `build/assembly.py`. Each part SHALL remain a
separately authored and separately validated single-body union; assembled position is
determined by each union's `placement` (identity when absent), EXCEPT for a part reached
via a `joints` mate chain (see `joint-mate-entity`), whose assembled position is instead
DERIVED by composing the mate chain from `root_part` -- such a part SHALL NOT carry its
own `placement`. Neither case is determined by code that unions or cuts parts into one
body.

#### Scenario: No fused assembly script is generated
- **WHEN** a plan has more than one part and every part passes the part loop
- **THEN** the pipeline produces the assembled model via `model_export.py` and does not
  generate or write a fused `build/assembly.py` CadQuery script

#### Scenario: Assembled position comes from placement
- **WHEN** a two-part model declares a `lid` union with a `placement`
- **THEN** the assembled model positions the lid by applying its placement, with no
  hand-coded positions in any assembly script

#### Scenario: Assembled position comes from the mate chain for a joint-mated part
- **WHEN** a part is reached via a `joints` mate chain from `root_part`
- **THEN** the assembled model positions that part using the derived mate-chain transform,
  and the part carries no `placement` of its own

#### Scenario: No assembly prompt template exists
- **WHEN** the build pipeline reaches the assembly phase
- **THEN** there is no `prompts/assembly.md` template and no `claude -p` assembly-script
  generation step
