## Context

The Build phase copies `src/build_template.py` into `build/build.py`, substituting a
`{{SKILL_SRC}}` placeholder with the absolute path to the installed skill's `src/`
directory. At run time `build.py` prepends that path to `sys.path` and imports the
shared tooling (`exporters._load_result`, `mesh_io.load_mesh`, `model_export.export_model`,
`print_orientation.optimize_orientation`, and transitively `blocks`, `placement`,
`exporters/threemf_multi`). The script therefore only runs on the machine that has the
skill installed at that exact path, inside the skill's own venv (CadQuery, trimesh, etc.).

The skill repo's own environment is already uv-managed (`pyproject.toml`,
`.python-version`, `uv.lock`) and specified by the `uv-environment` capability. That
capability is unchanged here. This change concerns the *delivered working directory*,
which today has no environment of its own.

The runtime dependency surface the tooling actually needs is the non-dev set already
pinned in the repo `pyproject.toml`: cadquery, trimesh, numpy, lxml, matplotlib, pillow,
scipy, networkx, and the `cq-warehouse` git source.

## Goals / Non-Goals

**Goals:**
- The delivered `build/` working directory is a standalone uv project: `uv sync` then
  `uv run python build/build.py` regenerates all artifacts on any machine with uv.
- No dependency on a `SKILL_SRC` absolute path or the skill being installed at run time.
- The uv workflow (sync + build command) is documented in `build.py`'s docstring and in
  the README's "Regenerating" section.
- Reproducible: a committed `uv.lock` pins versions including the `cq-warehouse` commit.

**Non-Goals:**
- Changing the skill repo's own `uv-environment` setup.
- Changing what `build.py` produces or its orientation/exit-code behavior (covered by the
  existing `build-script` requirements that are not modified here).
- Publishing the tooling to PyPI or running a package index.

## Decisions

### Decision: Bundle the tooling by vendoring it into the working directory

The skill copies the tooling modules `build.py` needs into a package alongside it
(`build/_cqtools/`), and `build.py` imports from that package instead of from `SKILL_SRC`.
The vendored set is the import closure of `build.py`: `exporters/` (incl.
`threemf_multi`), `mesh_io`, `model_export`, `print_orientation`, `placement`, `blocks/`
(incl. `inventory.json`, `inventory_schema.json`), and any of their intra-`src` imports.
`build.py` adds its own directory to `sys.path` (or uses a relative package import) so the
bundle resolves without configuration.

**Why vendoring over the alternatives:**
- *Installable package on PyPI* — would let `pyproject.toml` simply declare a dependency,
  but the tooling is not published, and publishing + versioning it is a much larger scope
  than this change. Rejected.
- *Git dependency on the skill repo* (`[tool.uv.sources]` git entry pointing at this repo)
  — keeps the working dir small and updates flow from the repo, but requires network
  access and a stable public repo URL/commit at build time, and couples every delivered
  project to the repo's availability. It is "self-contained" only as long as the remote
  exists. Rejected as the default; may be offered later.
- *Vendoring* — the working directory literally contains everything; `uv sync` only needs
  the third-party deps from PyPI/the cq-warehouse git source. This is the most faithful
  reading of "the project working directory should contain everything the user needs."
  Chosen.

### Decision: `pyproject.toml` declares the runtime deps only (no dev group)

The scaffolded `pyproject.toml` pins exactly the runtime dependency set the tooling
imports (cadquery, trimesh, numpy, lxml, matplotlib, pillow, scipy, networkx, cq-warehouse
via its git source) with `requires-python = ">=3.10,<3.13"` and `package = false`. No
pytest/dev group — the deliverable is not a test project. The `cq-warehouse` git source is
declared under `[tool.uv.sources]` exactly as in the repo so the lock pins the same commit.

### Decision: The skill runs `uv sync` / `uv lock` during the Build phase

After scaffolding `pyproject.toml`, `.python-version`, and the vendored tooling, the skill
runs `uv sync` in the working directory to create `.venv` and produce `uv.lock`, then
verifies the build by running `uv run python build/build.py`. This guarantees the delivered
project is already synced and the lockfile is committed, so the user's first run works
offline (except for the initial dependency download that already happened).

### Decision: `build.py` docstring and README document the uv workflow

`build_template.py`'s module docstring replaces the `SKILL_SRC` explanation with the uv
workflow: `uv sync` once, then `uv run python build/build.py` (with the same optional
`--plan`/`--parts-dir`/`--out`/`--orientations` flags). The README's "Regenerating the
3MF / STL files" section is rewritten to describe the standalone uv project and drop the
"imports the skill's tooling from the baked `src/` path" paragraph.

## Risks / Trade-offs

- **Vendored tooling drifts from the skill `src/`.** → The bundle is copied fresh from
  `src/` on every Build-phase run, so a re-run picks up the current tooling; there is no
  hand-edited copy to maintain. Document that re-running the skill refreshes the bundle.
- **Larger working directory / duplicated code across delivered projects.** → Accepted:
  self-containment is the explicit requirement, and the tooling is small relative to the
  CadQuery dependency it already pulls in.
- **`uv sync` needs network for the cq-warehouse git source and PyPI on first run.** →
  Inherent to any dependency install; the committed `uv.lock` makes the resolution
  deterministic, and subsequent runs use the cached `.venv`.
- **Vendored `blocks` data files (`inventory.json`) must be copied, not just `.py`.** →
  The copy step bundles the whole `blocks/` and `exporters/` directories, not a curated
  file list, to avoid missing data files.

## Open Questions

- Should the skill additionally offer a git-source variant for users who prefer a thin
  working directory that tracks the repo? Deferred; vendoring is the default deliverable.
- Exact vendored layout (`build/_cqtools/` package vs. flat modules beside `build.py`):
  resolved during implementation to whatever keeps `build.py`'s imports cleanest without a
  `sys.path` hack if possible.
