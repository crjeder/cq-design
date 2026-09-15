## Context

Phase 1 ends with two user approvals -- a topology confirm (only when the request was
shape-ambiguous) and a dimension table -- and then writes three artifacts:
`parameters.py` (sourced numbers), `REQUIREMENTS.md` (a six-section prose spec), and,
one phase later, `intent` inside `BUILD_PLAN.json`.

Only the numbers are ever read back to the user. The resolved reading of the request --
what is being built, how it decomposes, which fits apply, what was assumed rather than
established -- is written by the Phase 2 planner, unapproved, into a field whose schema
description is "Plain-English description of what is being built and why" and whose
`minLength` is 5.

That weakness surfaces in Phase 3. The `request-relative-acceptance` capability measures
every render against "the user's own words", sourced from `request_log`'s `initial`
entry. For a request that opened vague, the bar is close to meaningless -- precisely
where a strong bar is cheapest to apply, because a render is already in hand.

`REQUIREMENTS.md` was added (change `capture-requirements-spec`, archived 2026-08-29) to
hold the resolved state. Its own design.md deferred the question of whether it earns its
place: "Revisit once `REQUIREMENTS.md` has shipped in a handful of real projects." This
change revisits it early, on structural grounds rather than field evidence.

## Goals / Non-Goals

**Goals:**

- Make the resolved reading of the request an artifact the user explicitly approves.
- Put it in the field that Phase 2 and Phase 3 already read, so approving it binds
  something.
- Give the Phase 3 conformance bar a target worth measuring against.
- Decide, per ambiguity, whether Phase 1 must ask or may assume -- so "no ambiguity
  survives Phase 1" does not become an interrogation.
- Remove the duplication `REQUIREMENTS.md` introduced.

**Non-Goals:**

- Changing how dimensions are researched, cross-checked, or presented. The lookup
  workflow, the sources, and the table's columns are untouched apart from one new status
  value.
- Making request-conformance findings blocking. They stay advisory; promotion remains
  eval-gated under the existing `request-relative-acceptance` requirement.
- Adding structure to `intent`. It stays a prose string.
- Retrofitting existing projects. A `REQUIREMENTS.md` already on disk stays there, inert.

## Decisions

### `intent` carries the reformulation, rather than a new field or a file

Three candidates could hold the approved text: a new schema field, `REQUIREMENTS.md`, or
the existing `intent`.

A new field means two fields describing the same thing, and the immediate question of
which one Phase 3 reads. `REQUIREMENTS.md` is a file no script or schema reads, that
Phase 1 may skip, and that Phase 2 is instructed not to parse -- approving it would bind
nothing.

`intent` is required, schema-validated, carried forward across a re-plan, and already in
front of every downstream consumer. Redefining it as the approved contract costs one
schema description edit and gets every consumer for free.

The cost is that `intent`'s meaning changes for plans that already exist. Mitigated by
the fallback in the `request-relative-acceptance` delta: a plan whose `intent` is too
short to be a reformulation falls back to the `initial` entry, exactly as today.

### `intent` is current-state; `request_log` is history

The alternative is freezing `intent` at Phase 1 approval, which keeps "user approved" a
clean point-in-time record but leaves the Phase 3 conformance bar measuring parts against
a contract several corrections stale.

Rewriting it keeps the bar sharp, and the repository already answers the resulting
history question twice, identically: `planning_notes` "describes the CURRENT design state
only -- never a round-by-round changelog; that history belongs exclusively in
`request_log`", and `part_notes` "delete content the correction supersedes rather than
appending a dated round entry". Applying the same rule to `intent` adds no new concept.

The asked/approved pair survives either way, because `request_log[0]` is append-only:
`request_log[0].text` is always the original ask, `intent` is always the latest approved
reading.

### Ask vs. assume is decided by rebuild cost, reusing the `level` vocabulary

"Phase 1 finishes only when all ambiguities are cleared" taken literally produces a
question per unknown, including ones whose wrong answer costs a one-line parameter edit.

`skill/phase1_requirements.md` already states the right principle for topology and never
generalizes it: "A wrong dimension is a parameter edit; a wrong topology is a full
rebuild of every part built on that assumption." The typed `request_log` `level` enum --
`functional` / `operation` / `parameter` -- is that same cost axis, already in the
schema. So: `functional` and `operation` ambiguity is asked; `parameter` ambiguity may be
assumed with a concrete value, stated in the approved text.

This makes the exit checkpoint the place a wrong assumption is caught, at the cost of one
correction rather than one question round per unknown -- and it is why the reformulation
must name its assumptions explicitly rather than presenting assumed values as settled.

### One exit checkpoint, not two

Phase 1 can already stop the user twice. A third approval round is where rubber-stamping
starts.

The topology confirm stays separate and early: it gates which dimensions are worth
looking up at all, so it cannot be deferred to the exit. The dimension table and the
reformulation are the same moment -- the table is already presented "before generating
`BUILD_PLAN.json`", and the reformulation quotes its own assumed values -- so they merge
into one message taking one approval.

### The `-1` rule lands on `parameters.py`, not on the plan

The literal instruction was a `-1` check in `plan_validate.py`. Reading the schema shows
most of it is already there and the rest would be wrong:

| Field group | Fields | `-1` today |
|---|---|---|
| Size-valued | `dimensions.{w,d,h}_mm`, `interfaces.diameter_mm`, `interfaces.size_mm[]`, `blocks_needed.extents_mm[]`, `kinematics.step` | already rejected by `exclusiveMinimum: 0` |
| Signed by design | `interfaces.position_mm[]`, `load.dir[]`, `show_face.dir[]`, `placement.translate_mm[]`, `placement.rotate[].angle_deg`, `kinematics.{axis_origin_mm,required_range,mechanical_limit}[]` | legitimate value |

A blanket plan-level `-1` rejection would fail valid plans -- `load.dir: [0, 0, -1]` is
the ordinary way to say "downward".

The placeholder's actual escape route is `parameters.py`, which records the checkpoint
table verbatim including a `missing` row's `-1`, and which no check reads. So the rule
lands there, as a `warning` at the gate: by then geometry exists and was built from some
concrete number, so blocking delivery over a provenance gap would be disproportionate.

The real enforcement is the Phase 1 exit gate refusing approval while a row reads `-1`.
The gate warning is the net, not the gate.

### `intent` gains a length floor rather than a content check

Nothing can mechanically verify that a string is a good reformulation. A `minLength` can
verify that the planner did not leave a token phrase where the approved text belongs,
which is the failure mode worth catching. The floor is a heuristic; it is set high enough
to exclude a bare noun phrase and low enough that a genuinely simple part passes.

### `assumed` joins the table's status vocabulary

Without it, a deliberately-picked starting value has to be recorded as `missing` (wrong
-- it blocks the gate) or `single-source` (wrong -- it implies a source). One new enum
value keeps the table honest and gives `parameters.py` the right comment to write.

## Risks / Trade-offs

- **Removing a capability three days old, without field evidence** -> The removal is
  argued structurally (five of six sections restate structured fields, nothing reads the
  file), not from usage data. If the resolved state turns out to need sectioned structure
  after all, the reintroduction cost is one new capability -- and the archived
  `capture-requirements-spec` change documents the original design.

- **`intent` becomes a paragraph of prose in a JSON field, which diffs poorly** ->
  Accepted. The alternative is a second file that has to be kept in sync with the field
  Phase 2 and 3 actually read, which is the problem being removed. Prose is also what the
  Phase 3 conformance bar consumes, so a structured form would need flattening anyway.

- **Rewriting `intent` on every correction could drift from what the user approved** ->
  The rewrite happens in the same turn as the `request_log` append, and `request_log`
  keeps the correction's verbatim wording, so any drift is auditable against the entry
  that caused it.

- **The reformulation could restate the dimension table and become unmaintainable** ->
  The `approved-intent` spec forbids restating values that a structured field already
  carries in full, mirroring the existing "planning_notes does not restate structured
  fields in prose" requirement.

- **Assumed values could silently become permanent** -> They are stated as assumptions in
  `intent`, carried at status `assumed` in the table and `parameters.py`, and the Phase 3
  conformance bar has a scenario for a render contradicting a stated assumption.

- **Golden-plan churn collides with in-flight work** -> Raising `intent`'s `minLength`
  invalidates every eval-corpus golden whose intent is short. The
  `import-external-eval-corpus` change (0/21 tasks) is editing the same corpus.
  Sequencing, not design, resolves this: land whichever finishes first and rebase the
  other. If the collision proves expensive, the floor can be applied to new plans only by
  validating it outside the schema.

## Migration Plan

1. Schema and validation first (`intent` description + `minLength`, gate warning), so the
   contract exists before any prose references it.
2. Phase 1 documentation: merged exit checkpoint, ask-vs-assume rule, initial-entry sketch
   handling, `REQUIREMENTS.md` section deleted.
3. Phase 2/3/4 documentation: intent consumed not authored, conformance bar re-sourced,
   intent rewrite on correction, delivery pointer removed.
4. Eval-corpus goldens updated to satisfy the floor.
5. `requirements-spec-capture` removed from the spec store at archive time.

Rollback is per-step and cheap: every change is documentation or a single schema
constraint, and the `request-relative-acceptance` fallback means a plan with a short
`intent` still reviews exactly as it does today.

## Open Questions

- What value does `intent`'s `minLength` take? It has to clear a token phrase without
  failing a genuinely simple one-part request. Settling it needs a look at the shortest
  legitimate reformulation across the eval corpus, which happens during implementation.
- Should `intent` name the `sketches/` paths inline, or is `request_log[0].images` enough
  now that Phase 1 populates it? Inline is specified here because the conformance bar is
  fed `intent` and would otherwise have to join back to the log to find the images.
