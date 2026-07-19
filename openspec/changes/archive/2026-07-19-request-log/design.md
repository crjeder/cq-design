## Context

`BUILD_PLAN.json` is the single validated artifact describing a build, produced by
the planning prompt and cross-checked by `plan_validate.py`. The user's actual
words - the initial request plus the clarifications and corrections that shaped the
plan - are recorded nowhere durable. Item 11 needs them for resume; they are also
the provenance that explains why the plan looks the way it does. The week-1 scope
is only the data: an append-only `request_log` array added while the schema is
already being touched.

## Goals / Non-Goals

**Goals:**
- Verbatim, dated, append-only request history inside `BUILD_PLAN.json`.
- Schema-validated shape; old plans stay valid.
- Population and append rules stated where the writing happens (planning prompt,
  SKILL.md).

**Non-Goals:**
- No resume procedure (re-validating scripts on disk, skipping passing parts) -
  later change.
- No summarization or normalization of user text: verbatim only.
- No new cross-checks in `plan_validate.py` beyond schema validation.

## Decisions

1. **In the JSON, not a sidecar file.** The log travels with the plan, is
   schema-validated, and cannot drift from it. Alternative (a `REQUEST_LOG.md`)
   rejected: second source of truth, unvalidated, easy to forget when copying a
   project directory.

2. **Entry shape `{ts, kind, text}`.** `ts` is ISO-8601 UTC (same convention as
   `build/attempts.jsonl` records), `kind` is an enum
   `initial | clarification | correction`, `text` is verbatim user wording.
   Minimal on purpose: anything richer (who said it, which part it affected) is
   derivable later or belongs to the resume change. Schema requires `ts` and
   `text`; requires exactly one `initial` entry when the array is present, first
   in the array.

3. **Optional at the top level, constrained when present.** Existing plans -
   including the ten eval-corpus golden `BUILD_PLAN.json` files - must not become
   invalid. When present, entries are fully constrained (`additionalProperties:
   false`, enum on `kind`, non-empty `text`). New plans get the array populated by
   the planning rule; enforcement of presence stays a prompt rule, not a schema
   requirement, until the corpus is migrated.

4. **Append-only is a behavioral rule in SKILL.md, not a schema property.** JSON
   Schema cannot express "never rewrite earlier entries". The rule lives with the
   actor that edits the file: SKILL.md instructs appending a dated entry per
   mid-build clarification/correction and forbids editing or removing existing
   entries; the planning prompt writes the initial entry.

5. **Corrections are logged even when they change the plan.** A correction that
   triggers re-planning appends to the same log in the regenerated plan (the
   planner carries the existing `request_log` forward verbatim and appends). This
   is the one subtle rule; it is stated in planning.md so a re-plan does not reset
   history.

## Risks / Trade-offs

- [Log grows unbounded in long sessions] -> Entries are user utterances, not tool
  output; realistic sessions produce a handful. No cap needed now.
- [Planner forgets to carry the log forward on re-plan] -> Explicit planning.md
  rule (Decision 5) plus a plan_validate-friendly shape; a dropped log is visible
  in review since the plan is shown to the user before the loop starts.
- [Verbatim text may contain characters that complicate JSON] -> JSON handles
  arbitrary strings; no escaping rules needed beyond standard serialization.
- [Optional field means old habits skip it] -> The planning prompt rule makes it
  unconditional for new plans; telemetry/evals are unaffected either way.

## Migration Plan

Additive schema change, one commit. No migration of existing plans; the field is
optional. Rollback is removing the property and the two prompt rules.

## Open Questions

- Whether `kind: correction` should carry an optional `supersedes` index pointing
  at the entry it overrides. Default: no - resume logic (later change) can infer
  ordering from array position and timestamps.
