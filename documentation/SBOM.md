# Software Bill of Materials

Tracks the TODO.md item "sbom: add credit for projects where code came from".
Two parts: (1) third-party packages this project depends on, (2) code,
algorithms, and design ideas adapted from other projects' source or
documentation. `documentation/related_projects.md` is the full survey (119
rows, most "reference only" / "not adopted"); this file lists only what
actually shipped, cross-checked against `TODO.md`/`documentation/DONE.md`
`[x]` items and the source tree itself -- a row here means working code in
this repo traces to it, not just an idea that was considered.

Integration-strategy vocabulary (`TODO.md` [Integration
strategies](../TODO.md#integration-strategies)):
- **reimplement** -- own code; no upstream updates.
- **pinned dep** -- declared `uv` dependency, updated via `uv lock --upgrade-package`.
- **vendored snapshot** -- upstream doc/source copied in with recorded SHA; manual refresh.
- **optional external** -- referenced/used only when present, never bundled.

## 1. Third-party package dependencies

Runtime dependencies declared in `pyproject.toml`, with the license each
package's own PyPI/git metadata declares (checked via
`importlib.metadata`, not re-derived).

| Package | License | Role |
|---------|---------|------|
| [cadquery](https://github.com/CadQuery/cadquery) | Apache-2.0 | CAD kernel (OpenCASCADE wrapper) every part script is built on |
| [cq-warehouse](https://github.com/gumyr/cq_warehouse) (git dep, pinned) | Apache-2.0 | Fastener/thread geometry backing `blocks/hardware.py` |
| [trimesh](https://github.com/mikedh/trimesh) | MIT | Mesh loading, watertightness, boolean/interference primitives |
| [matplotlib](https://github.com/matplotlib/matplotlib) | PSF-derived (Matplotlib License) | Headless preview rendering (`preview.py`, Agg backend) |
| [pillow](https://github.com/python-pillow/Pillow) | MIT-CMU | Image I/O for preview/render pipeline |
| [numpy](https://github.com/numpy/numpy) | BSD-3-Clause | Numeric backbone (geometry math, mesh ops) |
| [lxml](https://github.com/lxml/lxml) | BSD-3-Clause | XML writing for 3MF export |
| [jsonschema](https://github.com/python-jsonschema/jsonschema) | MIT | `BUILD_PLAN.json` / `printer_profile.json` schema validation |
| [python-fcl](https://github.com/BerkeleyAutomation/python-fcl) | BSD | Broadphase collision detection (kinematic/clearance/keep-out checks) |
| [manifold3d](https://github.com/elalish/manifold) | Apache-2.0 | Boolean engine behind `trimesh.boolean`, the interference-volume primitive |
| [scipy](https://github.com/scipy/scipy) | BSD-3-Clause | `trimesh.CollisionManager` support, eval-harness matching |
| [networkx](https://github.com/networkx/networkx) | BSD-3-Clause | `trimesh`'s scene graph (3MF export path) |
| [rtree](https://github.com/Toblerity/rtree) | MIT | `trimesh.proximity` (eval-harness Chamfer distance) |

Dev-only tooling (`pytest`, `pytest-cov`, `ruff`, `mypy`, `basedpyright`,
`types-jsonschema`) is standard OSS project infrastructure, not code that
ships in generated models -- omitted from the credit list below but present
in `pyproject.toml`'s `[dependency-groups]` for anyone auditing licenses.

## 2. Code and design ideas adapted from other projects

Only entries with a `[x]`-complete `TODO.md`/`documentation/DONE.md` item
AND a corresponding symbol found in the source tree are listed -- several
`related_projects.md` rows describe ideas that were evaluated and then
deferred (still `[ ]` in `TODO.md`) and are deliberately excluded here.

| Project | License (upstream) | Strategy | What it became |
|---------|---------------------|----------|-----------------|
| [thereprocase/cad-skill](https://github.com/thereprocase/cad-skill) | see upstream repo | reimplement | `cq_debug_helpers.py`'s silent-boolean/workplane-drift catching -> `src/cq_verify.py` (`verify_boolean`, `verify_feature_bounds`, `check_workplane`); dimensioned cross-section rendering -> `src/preview.py --cross-sections` |
| [ChristophSchranz/Tweaker-3](https://github.com/ChristophSchranz/Tweaker-3) | GPL-3.0 (formulas reimplemented, no code copied -- see below) | reimplement (clean-room) | Progressive overhang penalty (severity exponent), area-cumulation candidate generation (`_area_cumulation_normals`), build-height minimization (`min_build_height` mode) in `src/print_orientation.py` |
| [jmwright/cadquery-llm-skill](https://github.com/jmwright/cadquery-llm-skill) | see upstream repo | vendored snapshot | `reference/CadQuery Anti-Patterns.md` (kernel / stateful-context / API-mechanic tiers) + fluent recipes folded into the pattern reference; Free Function API content deliberately excluded |
| [rundiwu/DeepCAD](https://github.com/rundiwu/DeepCAD) | MIT | reimplement (metric only) | Chamfer-distance golden-mesh regression metric -> `chamfer_mm` in `evals/run_evals.py` |
| [Rahix/FusedFilamentDesign](https://github.com/Rahix/FusedFilamentDesign) | see upstream repo | reimplement | Teardrop horizontal holes -> `blocks/connectors.py`'s `teardrop_bore`/`teardrop_post`; counterbore for overhang-free holes -> `blocks/fasteners.py`'s `counterbore_hole`; vertical-edge fillet rule -> `src/edge_treatment_check.py` |
| [lwidm/cq_gears](https://github.com/lwidm/cq_gears) | none declared upstream | optional external (referenced, not bundled) | Not vendored or pinned -- upstream declares no license and this project is PolyForm Noncommercial, so bundling would be unsafe. `prompts/planning.md` rule 13 points the LLM to the repo as a downloadable resource when a design needs gear geometry |

**Tweaker-3 note**: Tweaker-3 is GPL-3.0; this project is PolyForm
Noncommercial, so pinning or vendoring it would be license-incompatible.
`print_orientation.py` and `mesh_io.overhang_metrics` reimplement the
underlying orientation-scoring *formulas* (not copyrightable) from a
clean-room reading of the published algorithm description, with independently
derived constants -- no GPL source or verbatim tuned values were copied. See
`TODO.md`'s [Print orientation Tweaker-3](../TODO.md#print-orientation-tweaker-3)
entry for the full strategy rationale.

## 3. Not credited here

`documentation/related_projects.md` surveys ~119 other projects for ideas.
Most are marked "reference only", "not adopted", or describe an item still
open in `TODO.md` (e.g. cadgate's differential-geometry gate check,
cad-khana's diagnostics-as-assertions, CadAgent's token-budget management) --
nothing from those rows has shipped as code yet, so they are not credited
above. When one of those TODO items ships, add its row here rather than to
`related_projects.md` (which stays a survey, not a credit list).
