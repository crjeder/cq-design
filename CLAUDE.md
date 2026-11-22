# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is the **cq-design** Claude Code skill. It generates parametric 3D models
using [CadQuery](https://cadquery.readthedocs.io/) (Python) via the pipeline:
Sourcing Triage -> Planning -> Part Loop -> Model Export -> Quality Gate.

The skill definition lives in `SKILL.md` (trigger, contracts, and per-phase pointers)
with phase detail split into `skill/phase1_requirements.md` through
`skill/phase4_deliver.md`, plus `skill/phase0_sourcing.md` and `skill/resume.md`,
read on demand as each phase starts.
Claude itself drives
the pipeline inline (reads `BUILD_PLAN.json`, writes each part script, runs the tool
scripts via Bash, iterates on errors) -- there is no `orchestrate.py` script. The
Python files under `src/` are the tool boundaries Claude calls. This CLAUDE.md covers
development of those scripts.

Phase 1-3 LLM roles (dimension research, planning, and autonomous part authoring) may
execute in sub-agents rather than inline in the main session -- see `ARCHITECTURE.md`
for the agent roster and `skill/phase1_requirements.md` / `skill/phase2_planning.md` /
`skill/phase3_build.md` for the invocation, return-contract, and escalation details.
The agent-routing gate itself (autonomous vs. progressive per part) lives in
`skill/phase3_build.md`'s Routing section; user checkpoints always stay in
the main session regardless of routing.

## Python Version Constraint

**Python 3.11-3.14 only.** CadQuery 2.8 needs 3.11+; its OpenCASCADE (OCC) kernel wheels stop at 3.14.
This is enforced by `requires-python` in `pyproject.toml`; uv handles version selection automatically.

## Setup

```bash
uv sync --group dev   # dev group (pytest, ruff, mypy, basedpyright) is opt-in; installs omit it
```

Python 3.12 is pinned in `.python-version`. uv downloads it if not present.

To update the `cq-warehouse` git dep: `uv lock --upgrade-package cq-warehouse`

## Running Tests

```bash
# Full suite (CadQuery tests are slow -- a few seconds per file)
uv run pytest tests/

# Single file
uv run pytest tests/test_run_wrapper.py

# Single test
pytest tests/test_run_wrapper.py::test_happy_path

# Fast subset (plan validate -- no CadQuery)
uv run pytest tests/test_plan.py
```

`test_plan.py` only exercises JSON Schema validation, summary rendering, and
parameter round-trip, and runs in well under a second with no CadQuery installation. All other test files are integration tests that
run real CadQuery scripts (a few seconds each).

## Key Constraints

- **Program vs. prompt**: before adding or changing a pipeline step, decide which fits.
  Deterministic, checkable work (geometry math, validation, measurements, file I/O) goes
  in a `src/` script with a JSON contract and a test. Prompts in `SKILL.md` / `skill/`
  cover only judgment (interpreting intent, choosing a design, reading previews). A
  prompt rule that a script could enforce belongs in the script.

- **Three poses**: *build pose* is the frame a part script is authored in; every
  direction from the user, the plan or a CLI flag (`load.dir`, `--load`, `--show-face`,
  "top"/"front") is in build pose. *Assembly pose* is build pose plus `placement`
  (`write_assembly.py`'s `stl/` meshes, the whole-model checks' input, never delivered).
  *Print pose* is build pose rotated by the accepted `orientations.json` `rotate` (the
  only build -> print mapping); every file `build.py` writes is in print pose.

- **JSON contract**: `run_cadquery_model.py` always emits `success`, `errors`, `geometry`,
  `stl`, `stls`, `preview`, `previews`, `watertight`, `stdout`, `stderr`, `returncode`.
  Do not rename or remove keys — Claude parses them inline during the part loop.
- **`errors` field**: always present, empty list on a clean run. Each entry has `type`,
  `message`, `hint`. Claude uses these typed errors to build structured correction prompts.
- **Multi-union parts**: a script's `result` may be a `dict[str, Workplane]`; the wrapper
  validates and aggregates per-union. See `reference/scripts.md` for the exact fields.
- **Thin-interface check** (`--wall-min` set): adds `thin_regions` to the `geometry` block.
  See `reference/scripts.md` for its shape and which regions become blocking errors.
- **STL hidden during iteration**: scripts run in `tempfile.mkdtemp()`. STL paths are
  `null`/`[]` in normal JSON output. Use `--deliver --formats stl,...` to get output files.
- **Exit codes**: 0 = success, 1 = failure, 2 = interpreter not found, 3 = timeout.
- **PYTHONPATH**: `run_cadquery_model.py` and `quality_gate.py` each set
  `PYTHONPATH=<src_dir>` on the model subprocess so generated scripts can
  `from blocks import fillet_box` without any path manipulation. Tests do the same via
  `conftest.py` (`sys.path.insert(0, src)`).
- **Block imports**: Always import from `blocks` (the package), not from individual
  submodules. Claude writes the `from blocks import ...` lines directly when generating
  part scripts (no automatic import injection).
- **`build/cost.json`**: written by the `session_cost.py` `Stop` hook (seeded by
  `init_permissions.py`), not by the pipeline. It is a cumulative billed-cost record
  keyed by session id, safe to delete, and must not be bundled into `lib/` or a
  deliverable. The eval scorecard reads it as a cost source; nothing else depends on it.

## File Layout

[FILES.md](FILES.md) is the single repository layout tree (one line per file). **Full
per-script contract detail** (JSON shapes, CLI flags, typed error names, edge cases) lives in
[reference/scripts.md](reference/scripts.md) for `src/` and [evals/README.md](evals/README.md)
for `evals/` -- read it before modifying or calling a script. A new script gets a line in
`FILES.md` and a contract entry in one of those two files.
