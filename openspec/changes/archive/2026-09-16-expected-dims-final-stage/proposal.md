## Why

`render_prompt.py`'s `validate_args()` always includes `--expected-dims` and
`--dim-tolerance`, so every stage of a staged part build (`profile_stub`,
`base_shape`, `features`, `finishing`) validates against the part's final
dimensions even though `base_shape`/`features` intentionally don't have the
full geometry yet. `prompts/builder.md` papers over this with a special-cased
exception: ignore `dimension_mismatch` errors on non-final stages. Passing
`--expected-dims` only on the final stage removes the false-positive error at
the source instead of instructing the builder to ignore it.

## What Changes

- `validate_args()` in `src/render_prompt.py` takes the current stage and
  the full stage list, and only appends `--expected-dims`/`--dim-tolerance`
  when the stage is the last one in the list.
- `render_builder()` renders one validate command per stage instead of one
  static `VALIDATE_ARGS` string reused for every stage in the prompt.
- `prompts/builder.md`'s Commands section shows the per-stage command; step 3
  drops the `dimension_mismatch` exception clause, since intermediate stages
  no longer receive dimension checking.

## Capabilities

### New Capabilities
- `staged-validate-args`: validate command arguments are computed per build
  stage, with `--expected-dims`/`--dim-tolerance` present only on a part's
  final stage.

### Modified Capabilities
(none -- no existing spec documents the dimension_mismatch exception being
removed; it lived only in `prompts/builder.md` prose)

## Impact

- `src/render_prompt.py`: `validate_args()`, `render_builder()`.
- `prompts/builder.md`: Commands section, step 3.
- `tests/test_render_prompt.py`: cover per-stage validate args.
