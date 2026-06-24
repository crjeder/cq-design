## Context

The skill's Build phase already runs the two tools needed to produce print-ready plates:
`print_orientation.optimize_orientation` chooses how each union sits on the bed, and
`model_export.export_model` writes `model.3mf` + per-union/per-plate STLs, accepting a
`print_orientations` map. Today that orchestration only happens while Claude drives the
pipeline. The deliverable `build/` directory ends up with the part scripts and meshes but
no entry point to reproduce the plates after a manual edit.

Constraints that shape the design:

- Generated part scripts import `from blocks import ...`, which requires the skill's
  `src/` on `sys.path` (the wrapper sets `PYTHONPATH=<src>` today). Any standalone script
  loading those parts inherits the same requirement.
- `export_model` already loads each part's `result`, applies placement, and applies a
  supplied orientation to the deliverables. `optimize_orientation` operates on a union
  mesh in its authored frame. The new script must wire these together, not duplicate them.
- `build.py` ships into the user's working directory, which has no knowledge of where the
  skill is installed. The src path must be resolved at copy time.

## Goals / Non-Goals

**Goals:**

- One template in `src/` that the skill copies verbatim (with one substitution) into
  `build/build.py`.
- Running `python build/build.py` reproduces exactly the deliverable plates the skill
  produces, in print orientation, with no Claude involvement.
- Reuse `optimize_orientation` and `export_model` unchanged.

**Non-Goals:**

- No changes to how orientation is scored or how the 3MF/STL is written (existing specs
  own that behavior).
- No bin-packing or multi-plate auto-layout beyond the existing `plate` grouping.
- Not a replacement for the skill's quality gate or kinematic check.
- Not fully decoupled from the installed skill: build.py imports the skill's `src/`
  tooling; it is reproducible, not relocatable to a machine without the skill.

## Decisions

### Template with a substituted src path, not a vendored bundle

`src/build_template.py` carries a single placeholder for the skill `src/` directory (e.g.
`SKILL_SRC = "{{SKILL_SRC}}"`). At copy time the skill replaces it with the absolute path
to its own `src/`, then writes `build/build.py`. At runtime the script inserts `SKILL_SRC`
into `sys.path[0]` before importing `model_export`, `print_orientation`, and `mesh_io`,
and relies on the same path for the part scripts' `from blocks import ...`.

*Alternative considered:* vendor `blocks/`, `model_export.py`, `print_orientation.py`
into `build/` so the script is fully portable. Rejected — it duplicates a large surface,
drifts from the skill's source, and the proposal only asks for reproducibility in place.

*Alternative considered:* have build.py shell out to `model_export.py`/`print_orientation.py`
as subprocesses (mirroring SKILL.md). Rejected — in-process import is simpler, avoids
re-resolving `$SKILL_DIR`, and lets the script pass the orientation map directly rather
than marshalling it through a temp JSON file.

### build.py owns orchestration only

The script's logic is: locate `BUILD_PLAN.json` (alongside the working directory) and the
part scripts (its own directory), resolve each union's orientation, collect them into the
`{part_id: {"rotate": [...]}}` map `export_model` already accepts, and call
`export_model(plan, parts_dir, out, print_orientations)`.

Orientation resolution prefers the skill's accepted `orientations.json` when it sits next
to the part scripts, so re-running build.py reproduces the exact plates the skill
delivered (including any manual orientation tweaks the design loop accepted). When that
file is absent, build.py recomputes per union by calling `optimize_orientation` with the
part's `load` hint and the plan's `overhang_max_deg`; the authored per-union mesh it needs
is obtained the same way `export_model` loads results (via `exporters._load_result` + a
temporary STL export), so orientation is computed on the authored frame as
`print_orientation.py` expects.

### Path conventions

build.py resolves its own directory as `parts_dir` and `out` (the `build/` dir), and
`BUILD_PLAN.json` from the parent (the working directory). These can be overridden by
argparse flags mirroring `model_export.py` (`--plan`, `--parts-dir`, `--out`) so the
script is also usable from arbitrary locations, but the defaults make `python build/build.py`
work with no arguments.

## Risks / Trade-offs

- **[Stale src path if the skill is moved/uninstalled]** → build.py's substituted
  `SKILL_SRC` points at the install location at copy time; moving the skill breaks the
  script. Mitigation: the script fails fast with a clear message naming the missing
  `SKILL_SRC` path so the user knows to re-run the skill or fix the path.
- **[Orientation recomputed on every run]** → re-running build.py recomputes orientations
  rather than reading a cached choice, so a non-deterministic tie-break could change a
  plate between runs. Mitigation: `optimize_orientation` selection is already deterministic
  (lexicographic, lowest-index tie-break), so identical input yields identical output.
- **[Divergence from the skill's in-run export]** → if the skill's Phase 3 export and
  build.py drift, deliverables differ. Mitigation: both call the same `export_model` and
  `optimize_orientation`; build.py is the same orchestration captured as a script.
