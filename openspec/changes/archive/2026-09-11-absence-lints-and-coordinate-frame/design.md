## Context

`prompts/planning.md`'s "Coordinate vocabulary" table fixes North=+Y,
East=+X, South=-Y, West=-X as the standard binding, with Down=-Z always the
print-bed face. C5's `request_log` recorded a project-specific override
("East = right side of the ashtray.jpg photo = X=0 ... matching
parameters.py convention" — i.e. East=-X for that project) in prose only.
Nothing persists that resolution structurally, so five separate correction
rounds re-derived "East" from either the default or the buried note and
landed on either end (TODO.md `#c5-compass-language`).

Separately, two merged guards only fire when a part is *authored* under the
new rule:
- `cq_verify.verify_seated(support, boss, axis, label)` (commit 51dc097) is a
  construction-time assertion the script must call; nothing checks a script
  that never calls it.
- `plan_validate.check_shared_interfaces` (commit 814e329,
  `src/plan_validate.py:570`) flags two parts holding the *same non-null*
  `interfaces[].name` with no linking `joints` entry — but C5's plan has
  `interfaces[].name: null` on every entry, so the check has nothing to key
  on and the re-diverged pivot literal passed silently.

Both gaps share the same shape as `attempt-telemetry`'s design (this repo's
sibling proposal `telemetry-on-real-runs`): a guard that only helps a
project going forward, with nothing making its *absence* on an existing
project visible. This proposal closes that gap for these three specific
guards, all advisory (never a hard `plan_invalid` or gate failure — these
checks reason about intent and layout, and a legitimate design can have two
unrelated features at the same position or a script that doesn't need a
hinge guard at all).

## Goals / Non-Goals

**Goals:**
- A project whose plan uses compass language gets a visible nudge to record
  `coordinate_frame` instead of leaving every reader to re-derive it.
- A pre-existing, hand-rolled revolute-hinge script that never adopted
  `verify_seated`/`verify_backed`/`pin_hinge` is flagged at gate time, not
  only a newly-authored one.
- Two parts sharing one physical round mate at the same assembled position
  are flagged even when neither declares a matching `interfaces[].name`.
- All three checks are advisory (`check_block_thinness` tier, per
  `check_shared_interfaces`'s existing precedent): printed after `BUILD_PLAN
  OK` / as a gate `warning`, never blocking.

**Non-Goals:**
- Not implementing TODO.md item 4 (`/retrofit`) — these lints already run at
  the point `plan_validate.py`/`quality_gate.py` already run; a project
  doesn't need a separate command to see them.
- Not changing `placement.rotate` / joint `dof.direction` sign conventions —
  `coordinate_frame` is prose/review-frame only, per TODO.md's explicit
  scoping.
- Not attempting semantic hinge detection from free text alone —
  `hinge-guard-lint` keys off the structured `kinematics[].type: "revolute"`
  / `joints[].block == "pin_hinge"` fields, not prose parsing.
- Not asserting the *correctness* of a `coordinate_frame` value — only that
  one is recorded when compass language is used.

## Decisions

**D1: `coordinate_frame` is `{east, north, up}` on the plan root, each one of
the six signed axis tokens, defaulting to the standard binding.** Matches
TODO.md's already-agreed shape. `up` is included even though the standard
binding always pins Down=-Z (print-bed face) for symmetry with `east`/`north`
and because a future non-standard build orientation shouldn't require a
schema change; today's advisory check only ever exercises `east`/`north`.

**D2: The compass-usage advisory is a keyword scan over `intent`,
`planning_notes`, and `request_log[].text`, not an LLM classification.**
Alternative considered: have Phase 1 itself decide whether the user's
language implied a non-standard frame and write `coordinate_frame`
unconditionally. Rejected as out of `plan_validate.py`'s scope (a pure schema
+ structural checker, no LLM calls) and because a cheap keyword scan
(`north|south|east|west` word-boundary match, case-insensitive) is a
sufficient trigger for an advisory nudge — false positives just mean an
unnecessary reminder, not a blocked plan. Mirrors `check_engineering_rationale`'s
existing trigger-then-advise shape in the same file.

**D3: `hinge-guard-lint` is a new `quality_gate.py` stage, not a
`script_lint.py` check.** `script_lint.py` is plan-agnostic (`lint_script(path)`
takes only a script path, stdlib AST only) — it cannot know whether *this*
part's union is the `moving_union` of a `kinematics` entry with
`type: "revolute"`, which requires the plan. `quality_gate.py` already hosts
this exact shape of check (`_run_edge_treatment_stage`,
`_run_feature_presence_stage`: `(plan, script_path[, extra]) -> list[dict]`
via `make_issue`). The new `_run_hinge_guard_stage(plan, script_path)`:
1. Resolves this script's union id(s) via `units.iter_unions(plan)`.
2. A union is "hinge-associated" if it is the `moving_union` of a
   `kinematics` entry with `type: "revolute"`, or a `members[].part` of a
   `joints` entry whose `block == "pin_hinge"`.
3. If hinge-associated, `ast.walk` the script for a `Call` whose function
   name (in the `_flatten_chain` sense `script_lint.py` already uses) is
   `verify_seated`, `verify_backed`, or `pin_hinge`. None found -> one
   `warning` issue naming `cq_verify.verify_seated` and
   `blocks.joints.pin_hinge`, mirroring `prompts/part.md` rule 8's own
   wording so the fix a builder applies matches what a freshly-authored
   script would have done.

**D4: Broadened `check_shared_interfaces` reuses `placement.transform_point`,
not a new position-transform.** For "same assembled-frame position," every
interface with both `position_mm` and `diameter_mm` on every part is
transformed through that part's `placement` (identity when absent — same
default `to_matrix`/`transform_point` already use). Two interfaces from
different parts within a tolerance (reuse `feature_presence_check`'s
`_POS_TOL_MM`) on position and a small relative tolerance on `diameter_mm`,
with no `joints` entry naming both parts as members, produce one finding —
independent of whether `name` matches, is null, or differs. This subsumes
the existing named-match path (two same-named interfaces are already
typically co-located) rather than replacing it: the existing named-only
branch stays, and the new positional branch is additive, so a plan that
already passes today keeps passing.

**D5: The hinge/pivot-intent-with-no-joints check is a keyword scan, same
as D2.** `intent`/`request_log[].text` scanned for
`hinge|pivot|fold|articulat` (word-boundary, case-insensitive); a
multi-part plan (`len(parts) > 1`) matching with `joints` null/empty
produces one advisory finding pointing at the `joints`/`kinematics` schema
fields. Same false-positive tolerance rationale as D2.

## Risks / Trade-offs

- [Keyword scans (D2, D5) fire on incidental compass/hinge words in
  unrelated prose] → Mitigation: advisory only, one-line finding, no gate
  failure; precedent already set by `check_engineering_rationale`'s
  trigger-based advisories.
- [D4's diameter/position tolerance produces a false match between two
  genuinely unrelated round features that happen to coincide] → Mitigation:
  advisory, and the finding's message states this explicitly ("a shared
  vocabulary word for two genuinely independent features is legitimate" —
  same disclaimer `check_shared_interfaces`'s docstring already carries);
  reuse the same tolerance constant already governing
  `feature_presence_check`'s position matching, not a new invented number.
- [`_run_hinge_guard_stage` mis-detects a hinge-associated union when a part
  declares `unions` and only one union is hinge-associated] → Mitigation:
  `iter_unions` already yields `(part, union_id, plate)` per declared union;
  the stage checks the specific union id against `moving_union`/`joints`
  members, not the whole part, avoiding a false positive on a multi-union
  script's unrelated union.
- [`coordinate_frame`'s default matches the existing standard binding, so
  a plan already `coordinate_frame`-annotated today (none exist) needs no
  migration] → no risk; purely additive optional field.

## Migration Plan

1. Schema: add `coordinate_frame` to `build_plan_schema.json` (optional,
   defaulted in prose, not in schema — schema default doesn't enforce
   read-side defaulting, so `plan_validate.py`/checkpoint prose treat absence
   as the standard binding explicitly).
2. `plan_validate.py`: broaden `check_shared_interfaces` (D4); add
   `check_coordinate_frame_usage` (D2) and `check_hinge_intent_without_joints`
   (D5) at the same `check_block_thinness` advisory tier, called from
   `main()` alongside the existing advisory checks.
3. `quality_gate.py`: add `_run_hinge_guard_stage`, wire into `run_gate`
   next to `_run_feature_presence_stage`.
4. `prompts/planning.md`: add the `coordinate_frame` field description near
   the Coordinate vocabulary table; note it is written at the Phase 1 exit
   checkpoint only when the user's stated frame differs from the standard
   table.
5. `skill/phase1_requirements.md`: checkpoint prose reads/writes
   `coordinate_frame` when compass language was used in the request.
6. No data migration: every field is new/optional; existing plans validate
   unchanged and simply don't trigger the new advisories unless their
   content matches the keyword scans.

Rollback: revert the four files; `coordinate_frame` on a plan that already
has it is inert (no code reads it besides the new advisory, since D2 scans
the plan's own text regardless of whether the field is set, so a set field
just means the scan finds no finding to report).

## Open Questions

- Should `_run_hinge_guard_stage`'s "hinge-associated" detection also cover a
  `kinematics` entry with `type: "spherical"` (ball joints), which
  `blocks.joints` also has a matched-pair block for? Left for a follow-up:
  this proposal's evidence (C5) is specifically a revolute pin hinge, and
  `verify_seated`'s docstring itself is written for the tangent-plane shape
  of a round boss, which a ball joint's socket doesn't share in the same
  way.
