## 0. Prerequisite

- [x] 0.1 `split-skill-md` is implemented and archived (its `skill/phase*.md`
  files are the orchestration text this change edits)

## 1. Orchestration instructions

- [x] 1.1 `skill/phase3_build.md`: extend the build-mode gate into the agent
  routing gate - autonomous parts dispatch to a builder agent (rendered
  `prompts/part.md` as the agent prompt, mid-tier model override), progressive
  parts stay inline unchanged
- [x] 1.2 Define the builder return contract in the same file: `{part_id,
  status, bbox, preview_paths, attempts, error_summary}`; main never ingests
  image content, only paths
- [x] 1.3 Escalation path: on `blocked`, main summarizes errors, asks the user
  (hint / accept / skip); on hint, RESUME the same builder agent - never
  respawn
- [x] 1.4 Auditor instructions: spawn per accepted part with the plan entry +
  preview/section/detail paths (no script); checklist answers with cited
  views; failure resumes the builder with the named question, view, and
  discrepancy
- [x] 1.5 `skill/phase2_planning.md`: planner agent invocation (rendered
  `prompts/planning.md`, strong-model override); `plan_validate.py` loop stays
  in main, errors resume the planner
- [x] 1.6 `skill/phase1_requirements.md`: research agent invocation gated on
  "a real-world lookup is needed"; return contract is the validation table +
  source URLs; requirements Q&A and the approval checkpoint stay in main
- [x] 1.7 Cross-part pitfall injection: before spawning builder k, scan this
  session's `build/attempts.jsonl` for repeated error types and prepend a
  one-to-two-line "known pitfalls this session" note to the rendered prompt

## 2. Telemetry

- [x] 2.1 Update the telemetry instructions (part-loop step 5) so `model`
  records the executing model per attempt; builder agents write their own rows
- [x] 2.2 Verify `attempts.jsonl` append behavior is safe for the sequential
  case; document that parallel builders are blocked on a concurrency check

## 3. Eval gate

- [ ] 3.1 Baseline: score a run of the eval corpus on the current inline
  pipeline (`evals/run_evals.py --run-dir <baseline>`)
- [ ] 3.2 Post-change: generate and score a run with agent routing active;
  compare first-shot rate, attempts-to-pass, cost per accepted part, Chamfer
  distance
- [ ] 3.3 Decide per the adoption gate: regression means fix or revert; record
  the comparison in the change before archiving

## 4. Docs

- [x] 4.1 Keep `ARCHITECTURE.md` in sync with any decision that changes during
  implementation (checked: no divergence — the phase-file edits implement
  exactly the roster/rules/return contracts already drafted there)
- [x] 4.2 CLAUDE.md overview: note that Phase 1-3 LLM roles may execute in
  sub-agents and where the routing gate lives
