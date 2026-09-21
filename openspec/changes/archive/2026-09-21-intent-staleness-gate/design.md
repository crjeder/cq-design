## Context

`approved-intent` already requires that `intent` describe the design as currently
approved, rewritten in the same turn a `clarification`/`correction` is appended to
`request_log`. That requirement is enforced only by prose in `skill/phase3_build.md`.
`request_log` is append-only and every entry already carries an ISO-8601 UTC `ts`;
`intent` is a free-text string with no provenance of its own. So the two artefacts that
are supposed to move together have no shared marker a program could compare.

The consumers that break when they drift are real and already documented:
`request-relative-acceptance` measures renders against `intent` (a stale `intent` turns
the second acceptance bar into a wrong acceptance bar), `skill/phase4_deliver.md:47`
names a stale `intent` as the cause of a `REGENERATE.md` that rebuilds the superseded
design, and the Phase 2 planner carries `intent` forward across a re-plan.

Constraint: `plan_validate.py` is stdlib + `jsonschema` only and runs both standalone and
inside `quality_gate.py`; `request_log_search.py` is stdlib-only except for the `add`
subcommand's schema validation. Neither may grow a dependency.

## Goals / Non-Goals

**Goals:**

- A machine-checkable invariant that fails a plan whose `request_log` has moved past the
  reconciliation point of its `intent`.
- The check reaches the quality gate without touching gate plumbing.
- Zero cost for the common single-round project: a plan with no `clarification`/
  `correction` entries needs nothing new.
- A one-command path for the orchestrator to append an entry and record that intent was
  dealt with in the same turn.

**Non-Goals:**

- Judging whether the rewritten `intent` is *correct* -- that is a semantic question the
  auditor's request-conformance bar already owns at `severity: advisory`. This change only
  enforces that the reconciliation was performed.
- Promoting request-conformance findings from advisory to blocking (`request-relative-
  acceptance` gates that on eval evidence; untouched here).
- Any whole-model or Phase 4 conformance review.
- Re-auditing a correction for ambiguity before acting on it (TODO item 2, still deferred).

## Decisions

**A timestamp stamp (`intent_ts`), not a boolean or a hash.** Every `request_log` entry
already carries `ts`, so a single ISO-8601 UTC string on the plan makes the invariant a
comparison against data that already exists -- no new ordering machinery, no per-entry
bookkeeping, and the failure message can name exactly which entries are unreconciled.
*Alternatives:* a `reconciled: true` flag per entry (touches `additionalProperties: false`
on the entry schema, N writes instead of one, and lets a plan be half-reconciled); hashing
`intent` and storing the hash (detects an edit but not a deliberate no-op reconciliation,
and says nothing about *which* entry it covers).

**The stamp means "reconciled through", not "last edited".** `approved-intent` explicitly
allows a correction that changes nothing about the design to leave `intent` unchanged.
Naming the field for acknowledgement rather than for an edit covers both cases with one
field: the orchestrator advances `intent_ts` either way, and the no-op case is a stamp
with no text change.

**Absent `intent_ts` with non-`initial` entries present counts as stale.** The alternative
-- check only when the field is present -- makes the invariant opt-out by omission, which
is exactly the failure being fixed (a forgetful orchestrator omits things). The cost is
one eval golden needing the field.

**Blocking, in `validate_plan`'s error list.** The TODO item is specifically about intent
being a *convention* rather than an *invariant*; an advisory finding would leave it a
convention. Placing it in `validate_plan` rather than in a new check site means
`gate-plan-validation` already maps it to a `plan_invalid` issue that blocks a clean pass
and surfaces in the fix prompt, with no change to the gate. It is also a purely structural
claim ("was the stamp advanced?"), not a judgement call, so it is safe to block on --
unlike the semantic intent-match findings that are advisory by design.

**`--reconciled` on `request_log_search.py add` is opt-in, never automatic.** Auto-stamping
on every append would make the plan always validate and the invariant vacuous. The flag
exists so the correct workflow -- rewrite `intent`, append the entry, stamp -- is one
command rather than a hand-edit, while an unflagged `add` deliberately leaves the plan
failing until the intent is addressed.

**String timestamps normalized before comparison.** `ts` values are compared by parsing
with `datetime.fromisoformat` after rewriting a trailing `Z` to `+00:00` (Python 3.10's
`fromisoformat` does not accept `Z`, and the project supports 3.10-3.12). A `ts` that
cannot be parsed is itself reported as an error rather than silently sorting wrong.
Comparison is strict: `intent_ts` equal to the newest entry's `ts` passes.

## Risks / Trade-offs

- **A mid-build correction now blocks the gate until intent is rewritten** → That is the
  intended behaviour, but it turns a forgotten rewrite into a hard stop mid-loop rather
  than a silent drift. Mitigated by `--reconciled` making the correct path a single
  command, and by the error message naming the unreconciled entries verbatim so the fix is
  obvious.
- **The stamp can be advanced without actually rewriting `intent`** → The invariant is
  structural and cannot detect a lazy stamp. Accepted: the semantic bar is the auditor's
  request-conformance check, which reads `intent` plus scoped entries and would surface the
  contradiction as an advisory finding. This change closes the *silent* drift, not the
  deliberate one.
- **Existing plans with unreconciled entries break** → Exactly one eval golden is affected
  and is updated here. Field-deployed project plans are regenerated per session, and the
  error message states the fix.

## Migration Plan

1. Add `intent_ts` to the schema as optional -- every existing plan without
   `clarification`/`correction` entries stays valid unchanged.
2. Add the validator check; run the full eval corpus to confirm only
   `lid-thickness-correction` fails.
3. Add `intent_ts` to that golden, set to its `correction` entry's `ts`.
4. Rollback is removing the check; the schema field is additive and harmless if left.

## Open Questions

None.
