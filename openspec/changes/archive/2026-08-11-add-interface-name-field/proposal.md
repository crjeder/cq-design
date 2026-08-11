## Why

`src/build_plan_schema.json` closes `parts[].interfaces[]` with `additionalProperties: false`
and never declares `name`, so a plan that names an interface fails `plan_validate.py`. Yet
`prompts/planning.md` rule 2a, `skill/phase2_planning.md`'s interfaces summary table, and
`skill/phase3_build.md` Step 3's `--callout "name=<name>;center=..."` invocation all key off
`interfaces[].name`. The set of interfaces carrying both `name` and `position_mm` is therefore
always empty for a schema-valid plan, and the entire `preview-feature-callouts` capability --
implemented and unit-tested in `preview.py` / `render_preview.py` / `run_cadquery_model.py` --
can never fire from a real plan. The `shared-feature-vocabulary` change that introduced the
vocabulary system had no task touching the schema, so it archived with this hole in it.

The contradiction is inside the spec store itself: `planning-phase` enumerates the closed set
of interface fields without `name` in one requirement, then requires `interfaces[].name` in
another, and `preview-feature-callouts` requires legend names byte-identical to
`interfaces[].name`. This also blocks the request-log-to-cross-section join tracked in
`TODO.md`, which needs a name-to-position table to resolve a user complaint to a cut plane.

## What Changes

- Add `name` (optional string) to the `parts[].interfaces[]` item schema in
  `src/build_plan_schema.json`, constrained to `^[a-z][a-z0-9_]*$` -- the same normalization
  pattern already used for `parts[].id`.
- Add a `plan_validate.py` cross-check enforcing that interface names are unique within a
  part, mirroring the existing `_check_unions` uniqueness check. Names may repeat across
  different parts.
- Reconcile the `planning-phase` spec: the interface-field enumeration gains `name` so it no
  longer contradicts the naming requirement in the same spec file.
- No change to the callout plumbing, `preview.py`, or `render_preview.py` -- they already
  consume names correctly and light up once plans can carry them.
- Not breaking: `name` is optional, so all 11 golden plans under `evals/cases/` stay valid
  unchanged.

## Capabilities

### New Capabilities

None. This closes a gap in existing capabilities rather than introducing behavior.

### Modified Capabilities

- `planning-phase`: the `interfaces[]` field enumeration adds `name` as an optional,
  schema-declared field with a snake_case pattern, and gains a per-part uniqueness
  requirement for it. Resolves the internal contradiction with the existing
  "Plan names reuse the user's own nouns" requirement.

## Impact

- `src/build_plan_schema.json` -- one new property on the interfaces item schema.
- `src/plan_validate.py` -- one new `_check_interface_names` helper wired into
  `validate_plan`.
- `tests/test_plan_validate.py` -- coverage for the accepted name, the rejected
  non-normalized name, and the duplicate-within-a-part rejection.
- Unblocks `preview-feature-callouts` end to end (no code change there) and the
  `TODO.md` request-log-driven cross-section item.
- No change to `evals/cases/` goldens, `feature_presence_check.py`, or the exporters.
