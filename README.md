# CAD Skill for Claude Code

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill for generating parametric 3D-printable models using [CadQuery](https://cadquery.readthedocs.io/). Describe a physical object, and Claude will write a parametric script, export STL, render previews, and iterate with you until it's right.


## Usage

Once installed, the skill activates in two ways inside Claude Code:

- **Auto-trigger.** Describe a part you want to print ("design a wall mount for an Arduino Uno", "I need a snap-fit lid for this box") and Claude picks up the skill from its trigger keywords (3D print, STL, CadQuery, enclosure, bracket, and so on).
- **Explicit slash command.** Type `/cq-design` to invoke it directly, useful when your request does not contain the obvious keywords.

Claude then runs the pipeline: sourcing triage (is there an existing model to reuse?),
requirements and planning (`BUILD_PLAN.json`, approved by you), a per-part build loop with
previews, model export in your slicer's format, and a quality gate (DFM, overhang, fit and
interference checks). See [`documentation/pipeline.md`](documentation/pipeline.md) for the
target pipeline and [`ARCHITECTURE.md`](ARCHITECTURE.md) for the agent roster.

The first time the skill runs in a working directory it seeds that directory's
`.claude/settings.local.json` with the permission patterns and hooks its pipeline needs
(the `uv run`/`python`/`uv sync` calls, build-file copies, dimension-lookup web
searches, attempt and session-cost logging), creates `build/`, `stl/` and `preview/`, and
writes a default `profile.json` and `skill_config.json` when absent (never overwriting
them). The merge is additive and only happens once per directory; ask Claude to "init
permissions" to re-seed after updating the skill.

For more usage instructions see [`USE.md`](USE.md)

## Setup

### With the installer (recommended, local only)

Install [uv](https://docs.astral.sh/uv/), clone the repo, and run `./install.sh` (or `./install.ps1`). It copies the skill and its role agents (`agents/`) from the checkout; no marketplace or network source is needed. The skill requires the agents.

### As a plugin (optional, needs the marketplace)

Install [uv](https://docs.astral.sh/uv/), then in Claude Code:

```
/plugin marketplace add crjeder/cq-design
/plugin install cq-design@cq-design
```

Commands: `/cq-design:design` (full pipeline), `:plan` (phases 1-2), `:edit <file> <change>` (apply a
change to a STEP/BREP solid in its own coordinates, delivers `out/<stem>_edited.step`), `:init` (prepare a
directory; imports printer, process and filament values from an OrcaSlicer-family install when found), `:update` (refresh a bundled project's tooling), `:build [format]` (generate
model files with the project's `build/build.py`), `:render <script>`, `:status` (versions and staleness, read-only), `:sync-profile` (refresh `profile.json` from OrcaSlicer-family presets). The Python
environment lives in the plugin's data directory and survives plugin updates.

### Installer details

Claude Code loads the copy as a plugin (`cq-design@skills-dir`), so the skill and the
`/cq-design:*` commands above both work. The installer provisions its own venv at
`~/.claude/skills/cq-design/.venv`; `/cq-design:init` uses
`${CLAUDE_PLUGIN_DATA}/venv` instead, so a copy install can have both. Command loading
from a `--link` install is not verified.

Run the installer from the repo
root. It copies the skill into the Claude Code personal skills directory
(`~/.claude/skills/cq-design/`) and provisions its Python environment:

```bash
# macOS / Linux
./install.sh

# Windows (PowerShell)
./install.ps1
```

Options:

- `--link` / `-Link` symlinks the repo instead of copying, so your edits are
  picked up live (useful for development).
- `--uninstall` / `-Uninstall` removes the installed skill.
- `--dest <dir>` / `-Dest <dir>` (or the `CLAUDE_SKILLS_DIR` environment
  variable) installs to a different skills directory.

`uv` must be on your PATH; the installer stops with the install URL if it is
not. Python 3.12 is managed automatically. CadQuery requires Python 3.10-3.12;
uv enforces this constraint and downloads the right Python version if needed.

To work in the repo directly without installing, just run `uv sync`.

## Checking what's installed

A copy install can silently go stale -- edits to this repo don't reach
`~/.claude/skills/cq-design/` until you re-run the installer. Check what's
actually there:

```bash
python ~/.claude/skills/cq-design/src/skill_version.py
```

It reports the commit that was copied (or, for a `--link`/`-Link` install,
the live commit of the linked repo -- always current by construction). Pass
`--compare <path-to-this-repo>` to diff the installed commit against the
repo's current `HEAD`:

```bash
python ~/.claude/skills/cq-design/src/skill_version.py --compare .
```

Exits non-zero when the installed copy isn't confirmed up to date, so it
also works as a quick check in a script.

## Updating an existing project

`/cq-design:update` runs the `bundle_project.py` copy below in one step.

A project's `lib/`, `build/build.py`, and `.claude/settings.local.json` are snapshots
of the skill taken when it was last bundled.

```bash
python ~/.claude/skills/cq-design/src/skill_version.py --compare <path-to-this-repo>   # skill stale? reinstall (install.sh / install.ps1)
python ~/.claude/skills/cq-design/src/bundle_project.py --check .                    # is this project's lib/ stale?
python ~/.claude/skills/cq-design/src/bundle_project.py .                            # refresh lib/, build.py, permissions
uv sync
uv run python build/build.py
```

`bundle_project.py` overwrites the bundled tooling, prunes files the skill no longer
ships, and keeps an existing `pyproject.toml` / `.python-version` (it prints a note when
they differ from the template; merge new dependencies by hand). Part scripts are not
touched: if `build.py` fails after a refresh, a `blocks` signature probably changed, so
read the error and edit that part script.

## Generating the model files

When the skill finishes it turns your working directory into a self-contained
[uv](https://docs.astral.sh/uv/) project: a `pyproject.toml`, `.python-version`, and
committed `uv.lock` at the root, alongside `BUILD_PLAN.json` and `profile.json`, plus a
`build/` directory holding the per-part scripts, `build.py`, and `orientations.json` (when
orientations were accepted), and a `lib/` directory with the bundled build tooling (`exporters/`, `blocks/`,
`write_assembly.py`, `deliverables.py`, and friends).
Everything needed to rebuild the model lives here -- the skill does not have to be
installed.

The skill's last phase runs `build.py` for you. To rebuild the model files after
hand-editing a part script, or to get another format, sync the environment once and run
`build.py` with uv instead of re-invoking the skill (or use `/cq-design:build [format]`):

```bash
uv sync
uv run python build/build.py
```

`uv sync` downloads a compatible Python (3.10-3.12) and installs the pinned dependencies
(CadQuery, trimesh, ...); later runs reuse the synced `.venv`. With no arguments the
build writes only the format your slicer prefers (`slicer.preferred_format` in
`profile.json`); pick others with `--formats` (`3mf`, `stl`, `step`, `obj`, `iges`,
`scad`, `estampo`, comma-separated). Everything goes to `out/`, with each object in its print
orientation where the format has one:

- `3mf`: `model.3mf` -- one named object per union, with plate metadata
- `stl`: `<union-id>.stl` -- one print-pose STL per union; `plate_<n>.stl` -- one
  fused STL per multi-union plate
- `step` / `obj` / `iges` / `scad`: `<union-id>.<ext>` per union, print pose
- `estampo`: `estampo.toml` -- a slicer config for estampo (keys target 0.4.x) with one `[[parts]]` entry per STL (plate members are listed through
  their fused `plate_<n>.stl`), per-part `enable_support` / `brim_type` from the overhang and
  brim checks, and `layer_height`, `sparse_infill_density` and `wall_loops` overrides from
  `profile.json`. Also writes the STLs it references. Set the Orca profile names under
  `slicer.estampo` (`printer`, `process`, `filaments`) in `profile.json`; omitted names
  become commented placeholders. It cannot be the `preferred_format`.

The assembled-pose STLs in `stl/` are inputs to the skill's checks only and are never
delivered.

```bash
uv run python build/build.py --formats 3mf,step
```

`build.py` reuses `build/orientations.json` when present (so the plates match what
the skill delivered) and recomputes orientations otherwise. While building it prints `[k/N] <step> <id>` progress
lines to stdout (orientation, loading, stl, plate; each phase counted separately). Override the defaults
when your layout differs:

```bash
uv run python build/build.py --plan BUILD_PLAN.json --parts-dir build --out dist
```

## Regenerating the project with a fresh session

Alongside the model files, delivery writes `REGENERATE.md` at the project root: a
self-contained prompt that rebuilds the *design* from scratch, as opposed to `build.py`,
which rebuilds the *geometry* from the scripts you already have. Paste it into a new
session -- a better model, a newer version of this skill, a different skill -- when you
want the design re-derived rather than re-exported.

It carries what the plan's structured fields cannot be re-narrated from memory: the
approved intent (what is being built, in resolved terms), the verbatim request history
including every correction, `parameters.py` inlined whole so the measured real-world
numbers and their provenance travel along, the print target, and the previous parts and
joints -- labelled reference, so the new session is free to decompose the request
differently. Images cannot be inlined; the prompt lists the `sketches/` paths and asks you
to re-attach those files.

The skill rewrites the file on every delivery, so it always reflects the latest
corrections. To re-export it by hand after editing `BUILD_PLAN.json` (the script is
stdlib-only -- no `uv sync` needed):

```bash
python <skill-dir>/src/regen_prompt.py --plan BUILD_PLAN.json --out REGENERATE.md
```

Omit `--out` to print it to stdout.

## Command-line reference

Claude calls these scripts during the pipeline; you can also run them by hand with
`uv run python <skill-dir>/src/<script>.py ...`. Every script supports `-h`/`--help`.
Required options are marked **(req)**. Exit codes and JSON output shapes are in
[`reference/scripts.md`](reference/scripts.md).

### Installers (`install.sh` / `install.ps1`)

| Option | Effect |
|---|---|
| `--link` / `-Link` | Symlink the repo instead of copying |
| `--uninstall` / `-Uninstall` | Remove the installed skill |
| `--dest <dir>` / `-Dest <dir>` | Install to another skills directory (or set `CLAUDE_SKILLS_DIR`) |

### Build and run

**`run_cadquery_model.py <script>`** runs a part script, validates the geometry, and emits the JSON contract.

| Option | Default | Effect |
|---|---|---|
| `--preview` | off | Render a multi-view preview PNG |
| `--views {iso,multi}` | `multi` | Preview layout |
| `--preview-dir DIR` | next to script | Preview output directory (needs `--preview`) |
| `--cross-sections` | off | Render cross-sections as separate files (needs `--preview`) |
| `--extra-section AXIS=MM` | none | Extra cross-section, e.g. `x=50`; repeatable |
| `--auto-sections` | off | Fill remaining section slots (up to 3) with planes through bore/boss axes (needs `--preview`) |
| `--feature SPEC` | none | Per-feature view along the feature normal plus an axis section, `name=<feature>;center=x,y,z[;diameter=<mm>\|;size=<w>,<h>]`; repeatable (needs `--preview`) |
| `--sheet` | off | Compose a 2 x 2 `<stem>_sheet.png` from at most 4 tiles (`--feature` tiles, then sections; needs `--preview`) |
| `--detail SPEC` | none | High-resolution detail view, `name=<feature>;center=x,y,z;size=<mm>[;section=<axis>=<pos>]`; repeatable |
| `--strict` | off | Fail if an STL is not watertight or none was produced |
| `--timeout SEC` | 180 | Model run timeout |
| `--expected-dims W,D,H` | none | Expected bounding box in mm |
| `--dim-tolerance MM` | 1.0 | Tolerance for `--expected-dims` |
| `--wall-min MM` | 0 | Minimum wall thickness for the DFM check (0 skips it) |
| `--line-width MM` | 0.42 | Extrusion line width for the brittle thin-wall threshold |
| `--density G/CM3` | 1.24 | Filament density for the weight estimate (PLA) |
| `--material NAME` | `PLA` | Material label in the preview footer |
| `--deliver` | off | Run the exporters and populate `stl`/`stls` |
| `--formats LIST` | `stl` | Comma-separated formats for `--deliver` |
| `--output-dir DIR` | next to script | Output directory for `--deliver` |
| `--print-rotate FILE` | none | `print_orientation.py` JSON; sets the print pose for `blocks.print_up()` |
| `--attempts-log FILE` | none | Append this run's attempt record to an `attempts.jsonl` |
| `--model NAME` | none | Model name stored in the attempt record |

#### Export formats and STEP output

`--deliver --formats LIST` writes one file per format. Supported keys: `stl`, `step`, `3mf`, `obj`, `iges`, `scad`.

```bash
uv run python src/run_cadquery_model.py part.py --deliver --formats stl,step --output-dir out
```

- STEP is the exact B-rep (not a mesh), meant for editing in Fusion 360, FreeCAD and similar CAD tools. It is written as `<name>.step`.
- `<name>` is the script stem, or the union id for each union of a multi-union part (one file per union; keep-out zones are never exported).
- Files go to `--output-dir` (default: next to the script) and the JSON lists only the STL (`stls`) and 3MF (`threemfs`) paths; STEP files are on disk but not reported there.
- `build.py --formats step` (also `3mf`, `stl`, `obj`, `iges`, `scad`, `estampo`) writes `<union-id>.step` per union, in the print pose, into `out/`; `run_cadquery_model.py --deliver` does not accept `estampo`; with no `--formats` it writes only the profile's `preferred_format`.
- `fem_check.py` takes a part's exported STEP file as its positional input.

**`render_preview.py`** (preview subprocess) takes `--script` **(req)**, `--output` **(req)**, `--views`, `--title`, `--subtitle`, `--density`, `--material`, `--cross-sections`, `--auto-sections`, `--extra-section`, `--detail`, `--feature`, `--sheet` with the same meaning as above. `preview.py --help-note` prints a usage note.

**`section_select.py <script>`** picks section planes through bore/boss axes: `--max N` (default 3), `--reserve AXIS=MM` (repeatable).

**`build_template.py`** (copied to `build/build.py`): `--plan` (default `<root>/BUILD_PLAN.json`), `--parts-dir` (default script dir), `--out` (default `<root>/out`), `--orientations` (default `orientations.json` in `--parts-dir`), `--profile` (default `<root>/profile.json`), `--formats` (comma-separated: `3mf`, `stl`, `step`, `obj`, `iges`, `scad`, `estampo`; default the profile's `preferred_format`).

**`write_assembly.py`**: `--plan` **(req)**, `--parts-dir` **(req)**, `--out` **(req**, the STL directory, normally `stl`**)**, `--orientations FILE` (part id to orientation JSON; part scripts see it as their finishing pose). Writes assembled-pose STLs, keep-out STLs and `export_manifest.json`; no user-facing files.

**`export_standalone.py`**: `--parts-dir` (default `build`), `--out` (default `standalone`), `--parameters` (default `parameters.py`).

**`bundle_project.py [dir]`** and **`init_permissions.py [dir]`**: `dir` defaults to the current directory. `bundle_project.py --check` reports `current` / `behind` / `unknown` (exit 0 only if current) and changes nothing. `init_permissions.py --check` exits 0 if init already ran, 1 otherwise, and changes nothing; `--venv DIR` also sets `UV_PROJECT_ENVIRONMENT` to `DIR` (plugin install).

**`script_ops.py`** is the only way part and edit scripts are created or changed: `list|show|new|replace|insert|remove|move <script> ...`, each write preflighted (a refused command leaves the file unchanged). **`script_history.py restore|mark <target> <script>`** restores a script to a recorded run (`@last_ok`, `@prev`, `@<hash>`, or a mark name). **`oracle.py validate|check|verify`** handles `acceptance.json`, the intent-derived acceptance statements. Usage for all three is in the module docstrings and [`reference/scripts.md`](reference/scripts.md).

### Quality gate and checks

**`quality_gate.py`**: `--script` **(req)**, `--plan` **(req)**, `--stl FILE`, `--model-3mf FILE`, `--stl-dir DIR` (default: next to `--script`), `--orientation FILE` (a `print_orientation.py` result), `--attempts-log FILE` (default `attempts.jsonl` next to `--script`), `--previous FILE` (the previous round's gate report; adds a `delta`), `--fix` (invoke `claude` to fix errors; default is report-only).

**`plan.py`** subcommands:

| Subcommand | Options |
|---|---|
| `validate <plan>` | `--inventory FILE`, `--archetypes FILE`, `--require-rationale` (engineering_rationale findings become errors; use at the Phase 3 pre-export run) |
| `summary <plan>` | none |
| `import-params <script>` | `--part ID` **(req)**, `--plan FILE` (default `BUILD_PLAN.json`), `--write` (persist the reconciled plan) |

**`script_lint.py <script>`**: AST pre-flight lint, no options.

**`edge_treatment_check.py`**: `--script` **(req)**, `--orientations FILE` (omit to classify in the build pose).
**`feature_presence_check.py`**: `--script` **(req)**.
**`gridfinity_check.py`**: `--script` **(req)**, `--kind {auto,bin,baseplate}` (default `auto`), `--cells COLSxROWS` (default: read from the footprint).

**Whole-model checks** `kinematic_check.py`, `plate_clearance_check.py`, `keep_out_check.py` share `--plan` **(req)**, `--stl-dir` **(req)**, `--parts-dir` (detects STLs stale relative to their scripts; omit to skip). `kinematic_check.py` adds `--penetration-tol-mm3` (default 0.1) and `--inventory FILE`.

**`minimal_cutout_search.py <script>`**: `--param NAME` **(req)**, `--plan` **(req)**, `--part` **(req)**, `--joint-id` **(req)**, `--stl-dir` **(req)**, `--lo` **(req)** (bound that must still collide), `--hi` **(req)** (bound that must already clear), `--tolerance-mm` (0.1), `--margin-mm` (0.2), `--apply` (write the value back into the script).

### Orientation and advisors

**`print_orientation.py <stl>`**:

| Option | Default | Effect |
|---|---|---|
| `--overhang-max-deg` | 45 | Overhang angle above which support is needed |
| `--bridge-max-mm` | built-in | Longest span treated as a bridge |
| `--load x,y,z` | none | Principal load direction in the build pose |
| `--load-type` | `tension` | `tension`, `bending`, `shear`, or `compression` |
| `--optimize-for` | `strength` | `strength`, `min_support`, `visual_quality`, `min_build_height`, or `min_print_time` |
| `--show-face x,y,z` | inferred | Cosmetic surface normal |
| `--source-script FILE` | none | Stamp the result with the script's provenance hash |
| `--fem-stress FILE` | none | `fem_check.py` result; strength = `1 - fi_p99` when status is `ok` |
| `--speed-model FILE` | none | `toolpath_speed.py --emit-candidates` result; enables `min_print_time` ordering |

**`toolpath_speed.py`**: `--script` **(req)**, `--stl FILE` (posed union STL; omit for build-pose corner findings only), `--profile FILE` (default `profile.json` next to `--plan`), `--emit-candidates UNION` (per-candidate table for `--speed-model`; needs `--stl`).

**`fem_check.py <step>`**: `--plan` **(req)**, `--part` **(req)**, `--mesh-size MM` **(req)**, no default by design. Needs the `fem` dependency group.

**`printer_profile_validate.py <profile>`**: `--set KEY=VALUE` writes a field back, e.g. `nozzle_mm=0.6`, `constraints.overhang_max_deg=50`; repeatable.

### Measuring and comparing

**`measure_stl.py <stl>`**: `--min-radius MM` (1.0), `--min-area MM2` (5.0), `--thin-max MM` (2.0), `--line-width MM` (0.42).
**`diff_models.py <a> <b>`**: `--png FILE` (diff image), `--tol` (relative volume tolerance for "identical", default 1e-6).

### Prompts, logs, and housekeeping

**`render_prompt.py <kind>`**:

| Kind | Options |
|---|---|
| `builder` | `--plan` **(req)**, `--part` **(req)**, `--out`, `--override {autonomous,staged}`, `--attempts FILE` |
| `audit` | `--plan` **(req)**, `--part` **(req)**, `--out`, `--script` **(req)**, `--previews FILE...` **(req)** |
| `planning` | `--request-file` **(req)**, `--plan`, `--profile` (default `profile.json`), `--out` |
| `research` | `--targets-file` **(req)**, `--known-file`, `--out` |
| `sourcing` | `--request-file` **(req)**, `--out` |
| `oracle` | `--request-file` **(req)**, `--out` |

**`log.py`**:

| Command | Arguments and options |
|---|---|
| `--hook` | Read a PostToolUse payload from stdin; append a base attempt record |
| `journal append <journal> <milestone> <text>` | `milestone` is `<phase>/<key>`, e.g. `phase3/part_accepted:lid` |
| `attempt append <file> [json]` | `--field KEY=VALUE` (JSON-parsed, repeatable) |
| `attempt audit-fail` | `--part` **(req)**, `--audit FILE` **(req)**, `--file` (default `build/attempts.jsonl`) |
| `request search <plan>` | `--query`, `--kind {initial,clarification,correction}`, `--level {functional,operation,parameter}`, `--target` |
| `request add <plan>` | `--kind {clarification,correction}` **(req)**, `--text` **(req)**, `--level`, `--target` (repeatable), `--reconciled`, `--snapshot-scripts DIR` |

**`session_cost.py`**: `--hook` (read the hook payload from stdin; update `./build/cost.json`), or `--transcript FILE`, `--out FILE`, `--session-id ID` (non-hook mode).
**`regen_prompt.py`**: `--plan` (default `BUILD_PLAN.json`), `--out` (default stdout).
**`skill_version.py`**: `--compare REPO`, `--json`.
**`convert_build123d.py`**: `--mapping` (print the build123d to CadQuery table as JSON), `--smoke-check FILE` (run a converted script through the wrapper).
**`blocks/validate.py`**: `--search KEYWORD` (find blocks mentioning a keyword).

## Files
see FILES.md

## Acknowledgements and Related projects
This skill stands on the work of others. Thank you to:

- **[CadQuery](https://github.com/CadQuery/cadquery)** (Jeremy Wright, Adam Urbanczyk and
  contributors) -- the parametric CAD kernel every part script is built on. A clean,
  scriptable Python API over OpenCASCADE that made an LLM-driven CAD pipeline possible
  at all.
- **[cq_warehouse](https://github.com/gumyr/cq_warehouse)** by Roger Maitland (gumyr)
  -- pinned dependency. Its carefully modelled fasteners and threads back
  `blocks/hardware.py`; getting ISO hardware geometry right is tedious, exacting work,
  and this library does it beautifully.
- **[cadquery-llm-skill](https://github.com/jmwright/cadquery-llm-skill)** by Jeremy
  Wright -- vendored snapshot. Its CadQuery anti-pattern catalogue and fluent recipes
  live on in `reference/CadQuery Anti-Patterns.md` and the pattern reference; hard-won
  knowledge from a CadQuery maintainer, written down so models stop making the same
  mistakes.

Projects whose ideas were reimplemented (no code copied) are credited in
[`SBOM.md`](documentation/SBOM.md).

Projects surveyed for ideas -- see [`documentation/related_projects.md`](documentation/related_projects.md).
Adoption status/tracking lives in `TODO.md`.

## Part Libraries
Libraries which could be usefull are in [`Block_Sources.md`](reference/Block_Sources.md)

## Software Bill of Materials
Third-party dependencies and credit for code/ideas adapted from other
projects -- see [`SBOM.md`](documentation/SBOM.md).

## License

The skill and scripts are licensed under the [PolyForm Noncommercial License 1.0.0](LICENSE). Free to use, modify, and distribute for noncommercial purposes.

## Disclaimer

This project is for educational purposes only. Use it at your own risk. Generated models
are not engineered or certified for any application, and FDM-printed parts can fail
without warning, especially along layer lines. Do not use printed parts where a failure
could injure someone or damage property: loads over people (shelves, ceiling hooks, TV
mounts), climbing or fitness gear, children's products, vehicle or bicycle structural
parts, pressurized parts, or pet restraints. For those, use a certified off-the-shelf or
metal part.
