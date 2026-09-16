## Context

`render_prompt.py:validate_args()` builds one CLI arg string for the whole
builder prompt, reused verbatim as `{{VALIDATE_ARGS}}` in `prompts/builder.md`
across every stage of a part (`profile_stub` -> `base_shape` -> `features` ->
`finishing`, or the single `full` stage for non-staged parts). Because
`--expected-dims`/`--dim-tolerance` are always in that string, `run_cadquery_model.py`
raises `dimension_mismatch` on `base_shape`/`features` stages whose geometry is
intentionally incomplete. `prompts/builder.md` step 3 currently tells the builder
to ignore that specific error type on non-final stages -- a prompt-level workaround
for an orchestrator-level bug.

## Goals / Non-Goals

**Goals:**
- Only the part's final stage validates against `--expected-dims`.
- Drop the now-dead `dimension_mismatch` exception clause from `prompts/builder.md`.

**Non-Goals:**
- No change to `run_cadquery_model.py`'s dimension-check logic itself (`structured-errors` spec is untouched).
- No change to which stages a part builds (`stages()` in `render_prompt.py` is untouched).

## Decisions

- **Per-stage validate command, computed in `render_builder`.** `validate_args(plan, part)`
  gains a `stage: str, is_final: bool` (or equivalently takes the full `part_stages` list
  and an index) and omits `--expected-dims`/`--dim-tolerance` unless `is_final`.
  `render_builder` renders one command block per entry in `part_stages` and joins them
  into `{{VALIDATE_ARGS}}`, instead of calling `validate_args` once.
  Alternative considered: keep one static command and have the builder pass
  `--expected-dims` conditionally at runtime -- rejected, the builder has no reliable
  way to know which stage is "final" without the orchestrator already knowing it and
  `{{STAGES}}` already lists them in order, so the substitution belongs in
  `render_prompt.py`.
- **`prompts/builder.md` shows the stage -> command mapping directly** (e.g. a small
  table or one fenced command per stage) rather than a single generic command, since
  the command now differs by stage.

## Risks / Trade-offs

- [Builder prompt gets longer/more repetitive with one command per stage] -> acceptable;
  the stage list is at most 4 entries and the repeated text is a single `uv run` line.
- [Any other reader of `validate_args()` besides `render_builder`] -> checked: `render_prompt.py`
  has no other caller of `validate_args`; safe to change its signature.
