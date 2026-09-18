# Phase 0: Sourcing triage

Before designing anything from scratch, check whether a usable model already exists.
A proven, printable model beats a from-scratch rebuild: it saves the full Phase 1-3
token and iteration cost and inherits already-verified topology.

## Entry conditions

- **Runs before Phase 1**, for every `/cq-design` request (or natural-language
  trigger) unless skipped below.
- **Skip entirely** if the user explicitly asks to design from scratch (e.g. "design
  this from scratch", "don't look anything up, just build it"). Jump straight to
  Phase 1.
- **Quick-pass heuristic:** if the request is dominated by user-specific dimensions or
  interfaces (the core cq-design case — a custom bracket sized to the user's own
  measurements, a one-off enclosure for a project the user is building), tell the
  sourcing agent (see "Sourcing agent" below) to run a single quick search pass (one web
  search, one platform search) rather than the full ladder. If that quick pass finds
  nothing rung-1-3 usable, fall through to Phase 1 immediately — do not exhaustively
  search every platform for a request that is inherently custom.

## Collect-then-classify

The sourcing agent (below) returns every plausible candidate. Classify the whole set
against the ladder and take the best (lowest-numbered) rung that fits.

## The five-rung decision ladder

Evaluated top-down; take the first rung that fits.

### Rung 1: Found parametric source

A CadQuery, build123d, OpenSCAD, or FreeCAD source that models the requested part (or
close enough to adapt).

- **CadQuery**: reuse directly, adapting parameters to the request. It already runs
  through the normal wrapper/gate like any generated script — no special handling.
- **build123d**: both build123d and CadQuery wrap OpenCASCADE, so conversion is
  mostly renaming. Use `src/convert_build123d.py`'s `API_MAPPING` table as a reference
  while re-authoring the script (`python "$SKILL_DIR/src/convert_build123d.py" --mapping`
  prints it as JSON), then validate the converted script with its smoke-check mode:
  `python "$SKILL_DIR/src/convert_build123d.py" --smoke-check converted_part.py` — this runs the
  script through `run_cadquery_model.py --strict` and reports the same JSON verdict
  any generated part gets. Fix findings the same way the part loop would.
- **OpenSCAD**: **never transpile the .scad text.** OpenSCAD's CSG tree (`hull()`,
  `minkowski()`, recursive modules) has no direct BRep equivalent, and a naive line-
  by-line port produces broken or silently-wrong geometry. Instead, treat the .scad
  file as the authoritative **topology and parameter source**: read its module
  structure and parameter block, then re-author the part in CadQuery through the
  normal Phase 3 part loop, using the .scad's values as the ground truth for
  dimensions and feature layout.
- **FreeCAD**: treat like build123d in spirit (read the parametric feature tree/
  parameters, re-author the equivalent CadQuery chain) — no dedicated helper exists;
  document the mapping inline in `planning_notes` as you go.

### Rung 2: Found STEP/BREP/IGES

A found STEP/BREP/IGES file for the part or a mating component, with no parametric
source available.

- Import with `cq.importers.importStep(path)` (or the matching IGES/BREP importer).
- Scope it as **exactly** a dumb solid: a mating reference to measure against, or a
  base body for boolean modification (cut/union) inside a normal part script. It is
  **not reparametrizable** — do not attempt to recover features or edit its dimensions
  by any means other than boolean modification against it.
- State in `planning_notes` (and the delivery summary) that the imported body is a
  dumb solid sourced from the found file, not an authored parametric part.

### Rung 3: Found mesh that fits as-is

A found STL/mesh that appears to match the request's dimensions and function without
modification.

- **Never deliver a found mesh blind** — found models are frequently wrong or
  unprintable. Run it through the same vetting a generated part gets:
  1. `uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/measure_stl.py" <path>` — cross-check the measured bounding box and
     any relevant features against the request's stated dimensions.
  2. Run the quality gate's mesh-level stages (watertightness, overhang) against the
     downloaded mesh — the same checks any generated STL passes before delivery.
  3. **Present the candidate to the user** — the model's preview/link, its measured
     dimensions vs. the request, and the license (see below) — and get explicit
     confirmation before delivering it as the result.
- If the mesh fails measurement cross-check or either gate stage, rung 3 does not fit;
  continue down the ladder (a different candidate may fit rung 3, or fall to rung 4).
- On acceptance, no `BUILD_PLAN.json` is produced — the vetted mesh is the deliverable.
  Skip straight to a Phase-4-style delivery report; record source URL, license, and
  rung in the delivery summary (see License section).

### Rung 4: Found mesh that's close

A found mesh that is close to the request but has some tractable discrepancy — a hole
pattern in the wrong place, a slightly different extrusion height, a boss that needs
moving.

- Limit the rebuild to what `measure_stl.py` actually detects and characterizes:
  extrusions, revolutions, axis-aligned features (bosses, holes, flat layers). Use the
  mesh's measured dimensions as the source values feeding the normal planning and part
  loop (Phase 1 onward) — the found mesh becomes reference data, not a shortcut around
  the build.
- **General mesh -> parametric reverse engineering is out of scope.** If the
  discrepancy lies in freeform or organic geometry that `measure_stl.py` cannot
  characterize (curved surfaces, sculpted features, anything not an extrusion/
  revolution/axis-aligned primitive), rung 4 does not fit — fall through to rung 5.
- When rung 4 is taken, `planning_notes` records the found model's URL, license, and
  rung (see Planning phase provenance rule, `prompts/planning.md`).

### Rung 5: Nothing usable

No candidate fits rungs 1-4. Proceed with the current pipeline unchanged, starting at
Phase 1 (`skill/phase1_requirements.md`).

## Journal

Once the ladder resolves (any rung, including rung 5), append one line to
`build/journal.md` (see `skill/resume.md` for the contract):

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/journal.py" append build/journal.md \
    phase0/rung_decision "rung <n>, source <url or \"none\">, license <verdict or \"n/a\">"
```

## License check (mandatory at rungs 1-4)

The sourcing agent already read each candidate's license off its source page and
classified it (see `prompts/sourcing.md`'s "License reusability verdict"); trust its
`Reusable` column rather than re-deriving the verdict from the raw license string.

- A candidate whose verdict is `no (none stated)` or `no (ND)` does not fit any rung —
  move to the next candidate or the next rung.
- A candidate whose verdict is `rung-3-only (ND, redistribution permitted)` may only be
  delivered unmodified at rung 3, never rebuilt or boolean-modified at rungs 1, 2, or 4.
- A candidate whose verdict is `rung-3-only (ND, link only)` does not fit rung 3 either —
  give the user the source link instead and let them download it directly.
- **Provenance recording:** when a `BUILD_PLAN.json` is produced (rung 1 reuse
  expressed as a plan, rung 4 partial rebuild), record the license name, source URL,
  rung, and verdict in `planning_notes` per the Phase 2 provenance rule. When no plan is
  produced (rung 3 mesh delivery), record the same facts in the delivery summary shown
  to the user instead. Either way, state the license and source to the user at the point
  they confirm reuse — never reuse silently.

## Sourcing agent

Write the user's request to `build/sourcing_request.md` (on the quick-pass heuristic, append
"Quick pass: one web search and one platform search only."). Render the prompt:

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/render_prompt.py" sourcing \
    --request-file build/sourcing_request.md
```

It writes `build/sourcing_prompt.txt` and prints `{"out", "chars"}`. Spawn one agent with
the prompt `Read <out> in full and follow it. Working directory: <absolute cwd>.` on the
session default model. It returns a candidate table (source,
platform, kind, license, notes); classify it against the ladder above.

A later component-level dimension need is a Phase 1 research-agent lookup, not a second
sourcing dispatch.
