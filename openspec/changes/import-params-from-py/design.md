## Context

Part scripts are generated from `BUILD_PLAN.json` via the part template, which seeds a
`PARAMETERS` block: `width = {{W_MM}}`, `depth = {{D_MM}}`, `height = {{H_MM}}`, `wall =
{{WALL_MIN_MM}}`, plus feature-specific constants. The plan stores those three dimensions
as `parts[].dimensions.{w_mm,d_mm,h_mm}`. Users edit the `PARAMETERS` block directly to
adjust fit, so the script becomes the newest truth while the plan goes stale. This change
adds a one-directional importer that folds the edited dimensions back into the plan.

The tool mirrors the shape of existing plan-adjacent tools -- `plan_validate.py` and
`printer_profile_validate.py`: a small stdlib-only `src/` script, emitting structured JSON,
with a fast (no-CadQuery) test file.

## Goals / Non-Goals

**Goals:**
- Parse a part script's `PARAMETERS` block statically (never execute it) and read numeric
  parameter values.
- Reconcile the three conventional dimension names (`width`/`depth`/`height`) back into the
  named part's `dimensions` and diff against current plan values.
- Dry-run by default; `--write` persists only a schema-valid plan.
- Report every parsed parameter, including ones that can't be mapped, so nothing is silently
  dropped.

**Non-Goals:**
- Mapping arbitrary parameters (walls, feature offsets, boss diameters) into the plan. There
  is no stable name->field convention for these; they are reported as advisory only.
- Round-tripping `interfaces[].position_mm` / `diameter_mm` / `size_mm`. Interface features
  aren't authored as conventionally-named top-level parameters, so their mapping is out of
  first scope.
- Re-importing `parameters.py` (the sourced-measurements provenance file). This tool targets
  a part script's resolved `PARAMETERS` block only.
- Executing the script or importing CadQuery.

## Decisions

**Static AST parse, not import.** Parse with `ast.parse`, walk module-level `ast.Assign`
nodes with a single `ast.Name` target, and accept a value only if `ast.literal_eval`
succeeds and yields an int/float (or a tuple/list thereof). This avoids running CadQuery,
side-effecting geometry code, or evaluating computed expressions like `inner = width - 2*wall`.
Non-literal assignments are skipped, not evaluated.

**Scope of the PARAMETERS region.** Accept module-level literal assignments regardless of the
banner comment position. The template brackets parameters with a `# PARAMETERS` banner, but
relying on comment text is brittle; a top-level numeric literal past the `MODEL` banner is
rare and harmless to read (it is still just a named constant). Keep it simple: all
module-level numeric-literal names are candidates; only the three conventional names are ever
written.

**Fixed name map.** `{"width": "w_mm", "depth": "d_mm", "height": "h_mm"}`. These are the
names the template emits; anything else falls through to `unmapped`. A future change can widen
the map or add per-part overrides, but a fixed map keeps the first version deterministic and
false-positive-free.

**Write guard reuses `plan_validate`.** On `--write`, apply changes to a deep copy, call the
existing schema-validation entry point from `plan_validate` (import it; do not re-implement),
and write the file only on a clean pass. This keeps a single validation authority and prevents
the importer from ever producing a plan the gate would reject.

**CLI surface.** `python src/import_params.py <script.py> --part <id> [--plan BUILD_PLAN.json]
[--write]`. `--plan` defaults to `BUILD_PLAN.json` in the working directory. Exit 0 on a clean
dry-run or successful write; non-zero on parse error, missing part, or refused write.

## Risks / Trade-offs

- **Name-collision false mapping.** If a script renames a dimension (e.g. `w` instead of
  `width`), the edit won't be picked up. Accepted: silent no-op on the import side is safer
  than guessing; the report's `unmapped`/`unchanged` lists make the omission visible.
- **Partial round-trip.** Only three fields flow back; walls and interface positions do not.
  Mitigated by surfacing them as advisory so the user knows to reconcile those by hand, and by
  the plan-validate/feature-presence gate still catching a genuine mismatch on the next run.
- **Number formatting drift on write.** Re-serializing `BUILD_PLAN.json` may reformat unrelated
  numbers/whitespace. Mitigated by writing with stable `json.dump` settings (`indent=2`,
  `ensure_ascii=False`) matching how the plan is otherwise written, minimizing diff noise.
