## Context

`through-hole-genus-check` added `interfaces[].through_count` and a gate error when the
built b1 differs from the plan's total. Evidence from `evals/runs/cgb-104-119-150-*`
(2026-11-22):

```
fixture       plan                 b1 check           outcome
opus/104      10 ifaces, tc sum 9  FAIL 9 vs 6        plan edited to 6 -> pass
opus/119      11 ifaces            pass               -
opus/150      none                 never ran          script written directly
sonnet/104    none                 never ran          script written directly
sonnet/119    interfaces: []       never ran          intent text lists 4 holes, 2 slots
sonnet/150    interfaces: []       never ran          -
```

The pipeline state machine (`src/pipeline.py`) is stateless: state comes from
`build/journal.md` plus artifact hashes, and `part_accepted` already pins a script with an
appended `sha=`. A later `plan_approved` voids every `part_accepted` that came before it.

## Goals / Non-Goals

**Goals:**
- The planned b1 the gate enforces cannot be lowered or raised by editing the plan after
  approval without paying for a re-approval and rebuild.
- Under CAD intent, a run that declares no holes still gets its built b1 checked.
- A benchmark fixture that bypasses the pipeline is visible in the run output.

**Non-Goals:**
- Telling which hole is wrong (#340).
- Classifying interface `type` strings as hole-like. The type field is free-form, and
  treating a missing value as 0 under CAD avoids needing a vocabulary.
- Making the drawing interpretation itself correct. That is the planner's judgment and stays
  in `prompts/planning.md`.
- Pinning the whole plan at approval. Only b1 is enforced here.

## Decisions

1. **Record b1 in the `plan_approved` journal line, not in a snapshot file.** `advance`
   appends `b1=<part_id>:<n>,<part_id>:<n>` computed from `BUILD_PLAN.json`. This matches the
   `sha=` pattern, keeps the state machine stateless, and gets void-on-re-approval for free.
   Alternative: copy `BUILD_PLAN.json` to `build/plan_approved.json`. Rejected because it is
   a second source of truth, and nothing would void it when the plan is re-approved.
   A part with no `through_count` anywhere is recorded with its sum treated as 0 (`part:0`) only under CAD
   intent. Under print intent such a part is left out, so the gate still skips it.

2. **The gate reads the approved b1 and falls back to the live plan.** `quality_gate.py`
   reads `build/journal.md` next to the plan. If it holds a valid `plan_approved` line
   with `b1=`, that value is the planned b1. Otherwise (a standalone gate run, a test, or an
   older journal) the gate uses the live sum. When the two differ, the issue carries
   `approved_b1` and `plan_b1`, and its message says the plan was edited after approval.
   The severity stays `error` with action `fix`, so a run in which nobody fixes the
   geometry still fails the gate.
   Alternative: a separate `through_count_changed_after_approval` issue routed to
   `ask_user`. Rejected because in an unattended run the agent answers its own
   question, which is exactly the hole this change closes.

3. **Under CAD intent, missing counts as 0.** `_through_hole_issues` runs whenever
   `design_intent` is `"cad"`. The planned b1 is the sum of declared counts with missing
   treated as 0. A part that cuts through holes without declaring them fails, which pushes
   the agent to declare its interfaces. Print intent keeps opt-in, because real printed
   parts often have openings the plan does not list (handles, lattices).

4. **Runner audit reads artifacts, not transcripts.** For each generation fixture (one
   without `edit_description.txt`), the runner checks: `BUILD_PLAN.json` exists, the journal
   has a valid `phase3/gate_result`, and every `build/*.quality_gate.json` has
   `passed: true`. "b1 checked" is derived from the plan-approval `b1=` record. The audit uses
   `pipeline.py status --dir <work>` for journal validity rather than re-parsing it. The
   result goes into `sanity.json` under `<fid>.pipeline`. The audit never blocks packaging,
   because the Space still scores the output.
   Alternative: fail the fixture (empty folder). Rejected because a bypassed run may still
   score above 0, and the audit is diagnostic.

5. **Slash command for generation fixtures.** `build_prompt` starts with `/cq-design:design`
   (it expands only at the start of the prompt, like `/cq-design:edit`), followed by the
   existing UNATTENDED, FIDELITY and drawing text as its argument.

## Risks / Trade-offs

- [Re-approving the plan to fix a genuine planning error voids every accepted part] ->
  Intended. A count change is a design change. Benchmark fixtures are single-part, so the
  cost is one rebuild.
- [CAD intent with a part that has a legitimate undeclared handle] -> The gate fails and
  the agent must declare it. That is the existing prompt rule ("any other closed opening
  gets an interface").
- [The agent edits `journal.md` by hand to change `b1=`] -> Not prevented. Only
  `pipeline.py` should append to the journal, and a hand edit is visible in review. Signing
  journal lines is out of scope.
- [The slash command changes how `claude -p` loads the skill, and cost per fixture] ->
  Compare `cost.json` on the next three-fixture run before a full submission.

## Open Questions

- Should the runner audit also record `built_b1` from the delivered `output.step`, so the
  later Space score can be compared against it? It is cheap (the genus helper exists), but it
  needs a STEP tessellation in the runner env.
