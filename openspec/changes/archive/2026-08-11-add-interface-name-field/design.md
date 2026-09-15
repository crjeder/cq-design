## Context

The `shared-feature-vocabulary` change (archived 2026-07-23) built a complete
feature-naming system: user nouns become plan names, named features get numbered badges on
the preview tile, and checkpoint prose refers to features by `name (badge)`. The renderer
side shipped and is covered by tests (`tests/test_run_wrapper.py:531`, `:547`, `:603`);
the prompt and skill-doc side shipped. The one file the change never touched is
`src/build_plan_schema.json`, which closes `parts[].interfaces[]` with
`additionalProperties: false`.

Current state, for any plan that passes `plan_validate.py`:

```
planner --> BUILD_PLAN.json --> plan_validate.py   (name rejected)
                                      |
                     interfaces with name + position_mm == {} always
                                      |
                                      v
              skill/phase3_build.md Step 3 emits zero --callout flags
                                      |
                                      v
     render_preview.py / preview.py callout overlay  (implemented, never reached)
```

The gap also contradicts the spec store: `openspec/specs/planning-phase/spec.md`
enumerates the closed interface field set without `name` at one requirement and requires
`interfaces[].name` at another, while `openspec/specs/preview-feature-callouts/spec.md`
requires legend names byte-identical to `interfaces[].name`.

The 11 golden plans under `evals/cases/` currently declare only
`type`/`description`/`wall`/`diameter_mm` on their interfaces -- none carries a `name` --
so an optional field costs the corpus nothing.

## Goals / Non-Goals

**Goals:**

- Make `interfaces[].name` a schema-declared, machine-readable field so a plan can carry
  the agreed vocabulary word.
- Enforce the mechanical normalization the naming rule already promises, in the schema,
  using the pattern already established for `parts[].id`.
- Reject duplicate names within a part, so a badge number maps to exactly one name.
- Leave the spec store internally consistent.

**Non-Goals:**

- Making `name` required. That would invalidate the eval corpus and force a name onto
  interfaces that have no conversational identity.
- Changing `preview.py`, `render_preview.py`, or `run_cadquery_model.py`. The callout
  plumbing is correct and complete; it only lacks input.
- Using `name` in `feature_presence_check.py` diagnostics. Its messages currently identify
  interfaces by index and type; improving them is a separate concern.
- Retrofitting names onto the eval goldens or the archetype templates.
- Implementing the `TODO.md` request-log-to-cross-section join. This change unblocks it;
  it does not deliver it.

## Decisions

**D1: `name` is optional, not required.**
An optional field keeps all 11 golden plans and `tests/test_eval_corpus.py` valid with no
edits, and matches how the sibling placement fields (`wall`, `position_mm`, `diameter_mm`)
are already modeled -- an interface may declare only its `type`. Alternative considered:
making `name` required, which would force the planner to coin a vocabulary word for every
interface including ones the user will never mention, and would break the corpus on the
same commit. Rejected: the naming rule itself says coin names only for things worth
naming.

**D2: Pattern `^[a-z][a-z0-9_]*$`, copied from `parts[].id`.**
`prompts/planning.md` rule 2a already promises names are the user's noun with mechanical
normalization only (lowercased, spaces and hyphens to underscores). Enforcing that in the
schema turns a prompt-level convention into a validated one, and reusing the `id` pattern
verbatim keeps part ids and interface names in one namespace shape -- which matters
because rule 2a treats them as interchangeable targets for the same user noun. The
schema rejects the unnormalized form rather than normalizing it: `plan_validate.py` is a
validator, not a rewriter, and silently rewriting a name would break the
byte-identical-legend requirement in `preview-feature-callouts`. Alternative considered:
a permissive `string` with normalization left to the prompt. Rejected -- that is exactly
the arrangement that produced this gap.

**D3: Uniqueness is a `plan_validate.py` cross-check, not a schema constraint.**
JSON Schema can express uniqueness only over whole items (`uniqueItems`), not over one
property of an item, so a schema-level rule would also have to consider `type` and
`position_mm` and would miss the actual collision. The codebase already has the right
shape for this: `_check_unions` walks the plan, keeps a `seen` dict, and appends a
human-readable error naming both colliding owners. `_check_interface_names` follows it
directly and is wired into `validate_plan` alongside the other `errors.extend(...)` calls.

**D4: Uniqueness scope is per-part, not per-model.**
Callout badges are threaded per part -- `skill/phase3_build.md` Step 3 renders one part at
a time -- so the ambiguity a duplicate creates is confined to one tile's legend. Two parts
each having a `mount_hole` is natural vocabulary and the part id disambiguates them in
conversation. This differs deliberately from `_check_unions`, which is model-wide because
union ids name files and 3MF objects in one flat namespace.

**D5: Interfaces without a `name` are skipped by the uniqueness check.**
Absence is not a value; three unnamed interfaces on one part must not collide with each
other.

## Risks / Trade-offs

- **Callouts light up for the first time in real runs, on geometry no one has previewed
  with badges.** The overlay projection code has only ever run against test fixtures and
  the one manual render from task 5.2 of the archived change. → Verify end to end on a
  real plan part with two named+positioned interfaces before closing the change, per the
  same eyeball step the original change used.
- **Planners may start emitting names that fail the pattern**, turning a previously silent
  omission into a hard validation failure mid-run. → `_hint_for_error` in
  `plan_validate.py` is the existing mechanism for turning a schema error into an
  actionable message; the pattern violation should produce a hint stating the normalization
  rule, not just a raw regex.
- **Per-part uniqueness will read as inconsistent** next to model-wide union uniqueness.
  → Stated explicitly in the spec requirement text and in the helper's docstring so the
  asymmetry is deliberate on the record.
- **The eval goldens stay unnamed**, so the corpus continues to exercise the no-callout
  path only. → Acceptable for this change; adding names to a golden would change its
  preview output and is better done when the callout flow has been seen working.
