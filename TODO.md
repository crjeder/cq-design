# TODO

Tasks not tracked in an `openspec/changes/` change. Anything tied to a specific
change lives in that change's `tasks.md`, not here.

- [x] add kinematic analysis using PyBullet
- [x] add install script for skill
- [x] publish on github
- [x] check filament hinge understanding
- [ ] kinematic: explore adding one simple ground/seating plane (lid-hits-floor
      checks); surrounding-geometry questions stay out of scope (external simulation)
- [ ] kinematic: articulated chains (a moving union carries other unions through
      the sweep) -- deferred
- [ ] gate: plate clearance check -- co-plated unions must keep a gap > layer
      height everywhere or they fuse in the print
- [ ] joints: side-tagged `face_mount` docks so the planner derives union
      membership and the world joint axis automatically (interface naming: keep
      assembly/mating docks conceptually distinct from kinematic axes even though
      both live in the block `interfaces` array)
- [ ] `interface`needs a third type: `union` (extending `face_mount`, `hinge_axis`) where it is    
      fused to the body. `hinge_axis`is to narrow.
- [ ] preview: z-buffered renderer -- matplotlib mplot3d has no z-buffer and
      depth-sorts whole triangles (painter's algorithm), so flat faces show
      cosmetic triangular shading patches where angled wall/fillet triangles paint
      over coplanar ones. Geometry and normals are correct (STL/3MF watertight +
      winding-consistent); the artifact is preview-only. Switching `preview.py` to
      a z-buffered renderer (trimesh + pyrender / `Scene.save_image`) removes it,
      at the cost of an OpenGL dependency that `preview.py`/`mesh_io.py` currently
      avoid by design.
## Prior-art ideas

Grouped by change. Items under one heading are a single change (same files /
tests); separate headings are independent.

Integration strategy per item avoids the native-vs-MCP false binary. Options, by
how much they preserve upstream updates while staying self-contained and inline
(no MCP):
- **reimplement** -- own code; no upstream updates; on-design.
- **pinned dep** -- declare as a uv git/pip dep, call from a thin `src/` adapter;
  updates via `uv lock --upgrade-package` (same as the existing `cq-warehouse`
  dep); self-contained via the committed lock.
- **vendored snapshot** -- copy source into the repo with license + recorded
  upstream SHA + a documented refresh procedure; manual updates.
- **optional external** -- native by default, use the external tool if present,
  degrade with a warning otherwise (same pattern as `kinematic_check.py` without
  `python-fcl`); off the critical path.

### Print orientation (Tweaker-3) -- one change -- strategy: reimplement
Clean-room native port of the orientation formulas. Tweaker-3 is GPL-3.0 and this
project is PolyForm Noncommercial; bundling (pinned dep / vendored snapshot) is
license-incompatible, so we reimplement the algorithm (formulas are not
copyrightable) and do NOT copy the GPL code or its verbatim tuned constants --
derive our own. Touches `print_orientation.py` + `mesh_io.overhang_metrics`,
tested via `test_print_orientation.py`.
- [ ] progressive overhang penalty (severity exponent `OV_H`)
- [ ] area-cumulation candidate generation as a fallback/supplement
- [ ] `min_build_height` / volume-minimization mode
- [ ] `FIRST_LAY_H` band for bottom-contact (replaces tight `CONTACT_Z_EPS_MM`)

### CadQuery authoring guidance (jmwright/cadquery-llm-skill) -- one change -- strategy: vendored snapshot
Doc-only; vendoring a doc snapshot is the upstream-recommended usage, so no design
conflict. Record the upstream SHA and refresh periodically. Upgrades `reference/`
and `prompts/part.md`.
- [ ] BRep-vs-CSG mindset + selector cheat sheet + anti-patterns + grep-friendly
      local doc snapshot

### Independent changes
- [ ] `render_cross_sections.py` from thereprocase/cad-skill -- strategy:
      reimplement (dimensioned slices; relates to the preview z-buffer item above)
- [ ] `cq_debug_helpers.py` from thereprocase/cad-skill -- strategy: reimplement
      (catch silent boolean failures / workplane drift in `run_cadquery_model.py`)
- [ ] cadgate-style gate checks -- strategy: optional external (off the critical
      path; gate runs natively, cadgate augments when present). Differential
      geometry (volume/bbox/wall delta vs base) reimplemented in `quality_gate.py`;
      the LLM intent-match is the part that justifies the optional external path
- [ ] `get_parameters`: extract customizable params from a script for parametric
      re-runs (CadQuery/cadquery-contrib mcp-server) -- strategy: reimplement (tiny)
- [ ] DeepCAD evaluation metric: Chamfer distance for golden-mesh regression tests
      -- strategy: reimplement (trimesh already computes it)

## Tech debt

- [x] repo-wide type-checker cleanup. ruff, mypy (gradual-adoption `strict=false`,
      targets py310), and basedpyright (standard) now pass clean on all of `src/`.
      Fixes landed across `model_export.py`, `exporters/threemf*.py`,
      `blocks/joints.py`, `blocks/hardware.py`, `measure_stl.py`, `preview.py`,
      `print_orientation.py`, `plan_validate.py`, `mesh_io.py` (real
      narrows/asserts/annotations, targeted ignores only for runtime-injected
      `insertHole` and stub-union `makeCompound`/`vals()`). CAD-heavy test files
      (`test_blocks`, `test_cq_compat`, `test_model_export`, `test_placement`,
      `test_print_orientation`) carry a top-of-file `# mypy: ignore-errors` /
      `# type: ignore` -- stub-union noise in assertions, ruff still applies; `src/`
      stays fully type-checked. Config + stubless-dep overrides in `pyproject.toml`.

## Code review findings (2026-06-23)

From a full read-only review of changed `src/` on `feat/generated-build-script`.
Severities and `file:line` as reported; mostly pre-existing, not from the lint
cleanup. Confirmed unless marked SPECULATIVE.

### High value
- [ ] **gate runs no plan validation before the kinematic stage** (medium).
      `quality_gate.run_gate` never calls `plan_validate`, but
      `kinematic_check.py:191` raw-indexes `entry["required_range"]`,
      `entry["axis_dir"]`, `entry["moving_union"]`, etc., and
      `_AXIS_VEC[entry["axis_dir"]]` (`kinematic_check.py:102`) KeyErrors on any
      non-XYZ axis. A hand-written/partial plan raises a bare traceback instead of
      the module's structured `{source, severity, type, message, hint}` finding.
      Fix: validate (or guard field access) before the kinematic stage.
- [ ] **thin-wall detection silently weakens above 3000 faces** (medium).
      `measure_stl.py:307-324`: `is_thin` is only true on subsampled faces, but the
      adjacency grouping needs both edge endpoints sampled; above `max_samples=3000`
      thin regions fragment into singletons dropped by `len(comp) < 2`. Grow
      `is_thin` to unsampled faces adjacent to thin sampled faces, or raise the
      sample cap for the thin pass.
- [ ] **O(faces) pure-Python non-manifold loop + triplicated logic** (medium).
      `run_cadquery_model.py:191-201` builds the full `edge_faces` dict over every
      face in Python (the `>= 5` cap only limits reporting, not the build). A
      vectorized numpy version already exists at
      `exporters/threemf_multi.py:151` (`count_nonmanifold_edges`); a third copy is
      in `quality_gate._analyze_3mf`. Consolidate on the numpy one.

### Other confirmed
- [ ] **3MF object names not deduped** (low-med). `model_export.py:94-101` derives
      `<object name=...>` from `description`; identical/empty descriptions become
      indistinguishable to a slicer operator (defeats the named-object feature).
      Suffix collisions with the part id.
- [ ] **`_check_thin_interfaces` swallows all exceptions** (low).
      `run_cadquery_model.py:315` `except Exception: return [], []` makes a real
      `measure_stl` bug look identical to "no thin regions". Narrow the except or
      log to stderr.
- [ ] **`exporters._load_result` leaks `sys.path` inserts** (low).
      `exporters/__init__.py:49-65` restores cwd but never removes inserted
      `sys.path` entries, and `model_export` imports this private helper. Promote to
      a shared `script_loader` module.
- [ ] **repeated per-candidate mesh copies in print_orientation** (low, perf).
      `_support_metrics` (`:168`), `_gentle_incline_fraction` (`:213`), and
      `_build_height` (`:265`) each `mesh.copy(); apply_transform` separately ->
      ~3 full-mesh copies per candidate. Pose once per candidate, share.

### Speculative (confirm before acting)
- [ ] gimbal lock in `print_orientation._rotation_to_bed` (`:146-148`) when the best
      face is +Z-up: matrix is correct but the re-applied euler `rotate` steps may
      not reproduce the exact pose. Path exists; real impact unconfirmed.
- [ ] `plan_validate.py:43` sorts jsonschema errors by `e.path` (deque) -- latent
      `TypeError` if str/int collide at one position; no trigger found against the
      real schema. Safer key: `lambda e: list(map(str, e.absolute_path))`.
- [ ] `_translate_stderr` (`run_cadquery_model.py:96-113`) may misclassify a model's
      `print("Foo: bar")` on stderr as a fake `occ_exception`, which is
      error-severity downstream in the gate. Tighten to require an `Error`/`Exception`
      suffix or OCC prefix.

### Test-coverage gaps
- [ ] malformed-plan kinematic path emits a structured issue, not a traceback (ties
      to the gate-validation item)
- [ ] `measure_stl` thin-wall fixture above 3000 faces (catches the fragmentation
      regression)
- [ ] `model_export` two parts with identical descriptions -> assert object-name
      uniqueness
- [ ] `_translate_stderr` false-positive: a model printing `Foo: bar` to stderr is
      not reported as `occ_exception`
