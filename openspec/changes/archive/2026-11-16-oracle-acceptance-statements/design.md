## Context

Today the requirements a design must meet reach the geometry along one path:

```
request.md + intent --> planner --> BUILD_PLAN.json (interfaces, probes) --> builder --> gate
```

`interfaces[]` are checked against the geometry by `feature_presence_check.py`, and
`probes[]` by the step-loop probe registry (`probes.py`). Both are written by the planner,
so they test the plan, not the request. The request-relative review bar
(`request-relative-acceptance`) compares a render with `intent`, but it's an LLM judgment
and advisory only.

The oracle adds a second path that starts from the same input and meets the plan at a
check a script enforces:

```
                 Phase 1 draft (request + reformulation + dimension table)
                          |
                          v
                     +---------+   acceptance.json  (S1..Sn, each cites intent)
                     | oracle  |-----------------+
                     +---------+                 |
                          |  shown at Phase 1    |
                          v  exit checkpoint     |
                  user approves intent +         |
                  statements together            |
                          |                      |
                          v                      v
                     +---------+   BUILD_PLAN.json.acceptance_bindings
                     | planner |-----------> plan.py validate --> oracle.py check
                     +---------+             (unbound / contradicted = error,
                          |                   planner's 3-attempt self-retry)
                          v
                     builder --> quality_gate oracle stage --> oracle.py verify
                                 (geometry vs statement = error to builder,
                                  3 rounds per statement, then blocked)
```

## Goals / Non-Goals

**Goals:**
- A requirement in the approved intent that the plan drops or contradicts fails
  `plan.py validate` before any part is built.
- Statements are tested against the built geometry by scripts, not LLM judgment, wherever
  the vocabulary allows.
- The user sees the statements at Phase 1, when correcting a misread is cheapest.
- Reuse the existing checks (`feature_presence_check`, `probes.py`, `plan_params.evaluate`,
  `measure_stl`/BRep bbox) rather than adding new geometry code.

**Non-Goals:**
- Feature recognition from raw geometry. Statements are checked through the plan entities
  they are bound to, and those entities are checked against the geometry by the gates that
  already exist.
- Cross-part spacing (needs assembly placement). `spacing` covers features in one part.
- Making the oracle see or review the plan. Its independence is the point.
- Changing the existing advisory free-form request-conformance finding.

## Decisions

### D1. The oracle runs inside Phase 1, before the exit checkpoint

The oracle's input is `build/oracle_request.md`: the user's original request, the draft
reformulation, and the dimension table with each row's planned `parameters.py` constant
name. That's all of the intent, and no plan exists yet, so the oracle can't anchor on one.
The statements are shown as the fourth checkpoint item, and the single approval covers
them.

*Alternative:* run the oracle in parallel with the planner after approval. Rejected
because the user asked to see the statements at Phase 1, and a misread caught then saves a
full planning pass.

### D2. Statements cite the intent; new requirements enter only through the intent

Each statement has `cites`: a list of verbatim substrings of `intent` (whitespace-
normalised). Statements that only bound a dimension may cite a `parameters.py` name
instead. `oracle.py validate` checks every citation against the approved `intent` text at
plan-validate time, and an uncited statement is an error. If the user corrects a
statement, the orchestrator edits the reformulation and resumes the oracle. Statements are
never hand-edited, so `intent` stays the single source of what was approved.

### D3. A closed, frame-free statement vocabulary (option C)

The oracle doesn't know the plan's origin or build pose, so no statement carries
coordinates. Each kind lists what it requires and how the planner binds it:

| kind | statement fields | binding | `check` (plan) | `verify` (geometry) |
|---|---|---|---|---|
| `part_count` | `n` | none | count of `parts` | - |
| `feature` | `feature` (interface type family), `count`, `diameter_mm?`, `size_mm?` | `part` + `interfaces` (names, len = count) | types in family, sizes within `tol_mm` | feature_presence result for those interfaces |
| `fit` | `accepts` (`{diameter_mm}` or `{size_mm}`), `clearance_min_mm?` | `part` + one interface | interface size >= accepts + clearance | feature_presence result |
| `spacing` | `distance_mm`, `between` (two feature labels) | `part` + two interfaces | distance of `position_mm` within `tol_mm` | feature_presence result |
| `extent` | `max_mm?` / `min_mm?`, `which` (`largest`/`smallest`/`any`) | `part` | sorted `dimensions` | sorted BRep bbox extents |
| `probe` | `text` (the relation in words) | `part` + `probes` (labels starting `S<n>`) | >= 1 matching probe | probe evaluated on final BRep |
| `visual` | `text` | `part` (or `"*"`) | part exists | review checklist question |

Numeric fields take a number or an expression over `parameters.py` names, evaluated with
`plan_params.evaluate`, so a later edit to a constant reaches the statement. `tol_mm`
defaults to 0.2.

`probe` is the escape hatch for relations the other kinds can't express ("handle cannot
lift out"). The oracle states the relation, and the planner, who knows the frame, writes
the probe. The binding check confirms the probe exists, and `verify` evaluates it.

*Alternatives:* free-text statements checked by an LLM (that's the current advisory bar
over again); oracle-chosen datum (option D, which ties both agents to one frame).

### D4. Files and ownership

- `acceptance.json` (project root): written by the oracle only. Shape
  `{"schema_version": 1, "statements": [{"id": "S1", "kind": ..., "cites": [...], "text": ..., ...}]}`.
  `text` is the plain-language form shown to the user, required for every kind.
- `BUILD_PLAN.json.acceptance_bindings`: written by the planner only.
  `[{"statement": "S3", "part": "hook", "interfaces": [...], "probes": [...]}]`.
- `BUILD_PLAN.json.acceptance_ts`: ISO-8601 UTC, the newest `request_log` entry that
  `acceptance.json` has been reconciled against.

The plan holds the bindings rather than `acceptance.json` because binding is the planner's
claim about its own entities, while the oracle file stays plan-free. `oracle.py` finds
`acceptance.json` next to the plan file.

### D5. Where findings go and the 3-round cap

- **Planner side**: `plan.py validate` calls `oracle.check` when `acceptance.json` exists.
  Errors look like `oracle: S3 (spacing "holes 156 mm apart") unbound`. The planner's
  existing self-retry handles them, and after 3 attempts it returns `blocked` to the user.
  No new loop.
- **Builder side**: a quality-gate stage `oracle` runs `oracle.verify` on the delivered
  part and emits `{"source": "oracle", "severity": "error", "type": "oracle_unmet",
  "statement": "S3", ...}`. Each issue carries a round count, which the gate derives from
  `--previous`: count + 1 when the same statement failed in the prior report, else 1. When a
  statement reaches round 3 still failing, the issue's action is `ask_user` instead of
  `fix`. The orchestrator then stops resuming the builder for it and asks the user to
  amend the intent (correction -> oracle re-run), accept as-is, or skip the part. The
  counter is separate from the gate's 2-round `fix` cap, because the user set 3 for oracle
  findings. Keeping the count in the gate keeps it out of prose.
- **`visual`**: added to the audit prompt as checklist questions numbered by statement id.
  A "no" is a blocking `visual_mismatch` in the existing retry budget.

### D6. Staleness mirrors `intent_ts`

A `clarification`/`correction` entry newer than `acceptance_ts` (or present with
`acceptance_ts` absent while `acceptance.json` exists) is a `plan_invalid` error. The fix
is to resume the oracle with the correction, show the changed statements to the user, then
run `log.py request add ... --acceptance-reconciled` (or re-stamp, when the entry is
already logged). The planner then re-binds. When the oracle's statements don't change, the
stamp still advances, the same "acknowledgement, not edit" rule as `intent_ts`.

### D7. Model and tools

`models.oracle` defaults to `claude-sonnet-5-5`. Using a different model from the planner
(Opus) makes it less likely that both make the same misread. One call is cheap, and the
user reviews the output anyway. Tools: `Read`, `Write`, `Bash` (to run `oracle.py
validate` on its own output and retry up to 3 times, like the planner). No web, MCP, Glob
or Grep. The prompt forbids reading `BUILD_PLAN.json`. On a re-run a plan may exist and
tools can't stop the oracle from reading it, so its rendered prompt includes everything it
needs.

## Risks / Trade-offs

- [The oracle over-specifies and invents requirements, causing false failures] ->
  citations are script-checked, and the user approves every statement at Phase 1.
- [The vocabulary is too narrow and many statements end up `visual`] -> `probe` covers
  spatial relations. Track the `visual` share in evals before widening the vocabulary.
- [The planner binds to the wrong entity just to pass] -> `check` compares the entity's
  attributes with the statement, and `verify` re-checks the geometry. `plan.py summary`
  shows every binding to the user at the plan checkpoint.
- [A more crowded Phase 1 checkpoint] -> statements are shown as one short numbered list of
  `text` lines, not JSON.
- [`extent` sorted-bbox comparison is wrong for a rotated part] -> parts are built
  axis-aligned in build pose, and print-pose rotation is applied after `verify`.
- [Extra cost: one agent call, plus one per correction] -> Sonnet default, configurable.

## Migration Plan

No plan migration. Everything is gated on `acceptance.json` existing: legacy plans, eval
goldens and `/cq-design:edit` runs skip it. Rollback is deleting `acceptance.json` from a
project, or reverting the change. `skill/resume.md` resumes at the oracle step when Phase 1
was interrupted after the reformulation and `acceptance.json` is missing.

## Open Questions

- Should `/cq-design:plan` (phases 1-2 only) also run the oracle? Assumed yes, since it
  runs Phase 1.
- The eval harness may later score the `visual` share and oracle-blocked rate. Not in this
  change.
