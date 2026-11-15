# Intent, assumptions and clarification -- details

Tasks: [TODO.md](../TODO.md#4-intent-assumptions-and-clarification).

### Assumption pinning

Source: SmartAI/Chamfer, CadAgent smart clarification policy.

- Why: structurally different readings of one prompt (bearing bore along X vs Y)
  shipped silently with zero assumption statements; same defect class as the
  compass-language and shared-pivot items. Cheaper than asking the user.
- Do: (a) `prompts/part.md` and `prompts/builder.md` (Return contract): when a
  frame, axis, facing, datum or direction is underdetermined, choose the standard
  engineering reading and emit `ASSUMPTION: <one line>` before building; list them in
  the return contract. (b) `src/build_plan_schema.json`: add `"assumption"` to the
  `request_log` `kind` enum (currently `initial | clarification | correction`);
  `skill/phase3_build.md` records each via `log.py request add --kind assumption`.
  (c) `plan_validate`'s intent-reconciliation check (`check_intent_reconciled`) must
  NOT treat `assumption` as a user clarification/correction that stales `intent`;
  add that exclusion. (d) Escalation rule from CadAgent: ask the user only when two
  readings differ in a way the part cannot be built to satisfy both.
- Test: `tests/test_plan.py` (schema accepts `assumption`, reconciliation ignores it)
  and `tests/test_log.py` (`request add --kind assumption`).
- Done when: an eval case with an ambiguous axis shows the assumption in
  `request_log` and the audit can cite it.

### One measured reconciliation pass

Source: SmartAI/Chamfer, rated Medium-High.

- Why: positions were recited from input constants in 21/21 Chamfer runs; open-ended
  self-verification added 21% cost without correctness. Our parts self-report from
  their own `PARAMETERS` block.
- Do: `skill/phase3_build.md` and `prompts/part.md`: replace free-form verification
  with ONE pass: for every requested dimension, hole count and diameter, and
  `interfaces[]` position, quote the value from tool output
  (`run_cadquery_model.py` `geometry`, `feature_presence_check.py`, `measure_stl.py`),
  never from the script's variables; stop unless a mismatch appears; no completion
  claim while a discrepancy is open. Also bound the per-part completion report to
  assumptions plus one summary line (output-token economy). Pairs with item 5.
- Test: `tests/test_render_prompt.py` asserts the rule text is in the rendered
  builder prompt; add one eval case whose request has a numeric position the author
  could mis-recite.
- Done when: the rendered prompts carry the rule and the eval case passes.

### Intent as invariant

Question resolved 2026-08-29: yes, adopting the OpenSpec-style flow (user
states an intent -> skill asks enough questions to write a spec -> the spec
drives generation) was a good idea, and it shipped as `REQUIREMENTS.md`
(Phase 1 writes it; Phase 2 amends it in place; see [Canonical intent
restatement](related_projects.md#canonical-intent-restatement) and `openspec/changes/
capture-requirements-spec/`).

That closes the *capture* half. Three further changes close the *invariant*
half:

- `openspec/changes/archive/2026-09-21-intent-staleness-gate/`: `BUILD_PLAN.json`'s
  `intent_ts` field plus `plan_validate.py`'s `check_intent_reconciled` block a plan
  whose `request_log` has a `clarification`/`correction` newer than the last
  reconciled `intent` rewrite -- `intent` can no longer silently drift stale
  relative to the log (sync enforcement).
- `openspec/changes/archive/2026-09-01-typed-request-log/`: `request_log` entries
  gained optional `level`/`targets` fields, so an entry can be scoped to a specific
  part instead of matched by keyword.
- `openspec/changes/archive/2026-09-01-request-relative-acceptance/`: both the
  autonomous implementation audit and the progressive inline self-review now check
  the delivered render against `intent` + the entries scoped to that part
  (`prompts/audit.md` group 3, `render_prompt.py`'s `scoped_request`) as a second,
  advisory-unless-also-blocking acceptance bar (conformance checking).

Together these close what the earlier draft of this item called items 1 and 3 of
`documentation/intent_recognition.md`'s gaps 2-3 ([Typed request_log
entries](related_projects.md#typed-request_log-entries), [Request-relative
acceptance](related_projects.md#request-relative-acceptance)) -- the generation loop's output is now
checked against `intent`/`request_log`, not only against the plan's structure.

What is still open, narrowly:
- (closed by `openspec/changes/parameter-entry-routing-check/`: a `parameter`-level
  entry appended with `--snapshot-scripts` is diffed by `quality_gate.py`, which warns
  `routing_violation` on an untargeted, non-joint-linked script change -- advisory
  only, so it does not yet stop the C5 sibling-literal edit, only surfaces it);
- promotion of advisory request-conformance findings to blocking-by-default is
  still eval-gated and undone (item 5, [Under-specified eval
  cases](related_projects.md#under-specified-eval-cases));
- `REQUIREMENTS.md` itself (as opposed to its `intent` mirror in
  `BUILD_PLAN.json`) is still never read by any gate or agent.

Update (change `intent-staleness-gate`): the mechanical half is closed -- the plan's
`intent_ts` stamp plus a blocking `plan_validate.py` check fail any plan whose
`request_log` has moved past the last reconciliation of `intent`. Still open: a
model-level conformance bar before delivery, promoting request-conformance findings from
advisory to blocking (eval-gated), and the ambiguity re-audit of mid-build corrections.

### Fixed geometry and testable statements

the skill should have a way to distinguish between geometry which is fixed and one that is flexible and can be changed by the skill any time e. g. during optimization
- [ ] generate testable statements from user intent (different agent then planer)
