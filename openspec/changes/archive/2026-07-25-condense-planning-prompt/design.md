## Context

`prompts/planning.md` is rendered in full into every Phase 1/2 planning LLM call. Its
"Rules" section (currently numbered 1-15, ~200 lines) is the target: verbose multi-
paragraph prose per rule, plus an accidental duplicate -- two blocks both labeled `14.`
(one for `request_log`, one for provenance) followed by a `15.` that restates the first
`14.`'s `request_log` content almost verbatim. `TODO.md`'s "optimize prompts" item
already did a first pass on `part.md`/reference injection and named this file as the
next target. `skill/phase2_planning.md` and `skill/phase3_build.md` cross-reference
several of these rules by number (`rule 3`, `rule 3a`, `rule 10`, `rule 12`, `rule 2a`,
`rule 14`), so numbering stability for referenced rules matters.

## Goals / Non-Goals

**Goals:**
- Cut the Rules section's word count materially (target: roughly half) by converting
  multi-paragraph prose into imperative bullets/tables wherever the meaning survives
  the compression.
- Eliminate the duplicate `request_log` statement and the colliding `14.`/`14.` numbers.
- Preserve every currently-mandated planner behavior -- every SHALL-level obligation
  in the current 15 rules must still be traceable in the condensed version.
- Keep rule numbers 1-13 stable (unchanged content, tighter wording only), since those
  are the numbers cross-referenced from `skill/phase2_planning.md` and
  `skill/phase3_build.md`. Only the colliding/duplicate tail (14/14/15) changes shape.

**Non-Goals:**
- Not touching the required output schema, the `{{BLOCK_INVENTORY}}` /
  `{{ARCHETYPE_INDEX}}` / `{{PRINTER_PROFILE}}` / `{{FDM_GUIDELINES}}` /
  `{{USER_REQUEST}}` placeholders, or the JSON schema example block -- those aren't
  part of the verbose-rules problem and changing them is out of scope.
- Not changing any *existing* requirement in `openspec/specs/planning-phase/spec.md`
  -- those describe planner *behavior* and the *BUILD_PLAN.json* contract, not prompt
  wording, and this change preserves that behavior exactly. The one addition (see
  Decisions) is a new, narrow requirement about rule-identifier uniqueness, not a
  change to an existing one.
- Not re-tuning any rule's actual policy (clearance defaults, load-declaration
  triggers, `review_policy` mapping, etc.) -- wording gets shorter, meaning does not
  change.

## Decisions

**Renumbering: keep 1-13 fixed, collapse the 14/14/15 tail into 14 + 15.**
Rules 1-13 keep their current numbers and sub-letters (`2a`, `3a`, `11a`) unchanged --
only their prose is tightened. The two colliding `14.` blocks and the duplicate `15.`
collapse to exactly two rules: `14` = `request_log` (merging the two near-identical
statements into one), `15` = provenance (the content that was squeezed into the second
`14.`). This means every existing cross-reference in `skill/phase2_planning.md` and
`skill/phase3_build.md` (`rule 3`, `rule 3a`, `rule 10`, `rule 12`, `rule 2a`, `rule 14`)
still resolves correctly with zero edits -- confirmed by grep during implementation
(see tasks.md), not just assumed.
- *Alternative considered*: renumber everything sequentially for a cleaner document.
  Rejected -- it forces edits across two more files for no reader benefit, since the
  only actual defect is the duplicate tail, not the 1-13 sequence.

**New spec requirement: `planning-phase` gains "rules are uniquely numbered."**
The duplicate `14.` pair is a real, if latent, defect -- nothing today enforces that
`prompts/planning.md`'s rule identifiers are unique, so the same drift could recur.
Capturing it as an ADDED requirement on the existing `planning-phase` capability gives
this change a real, testable spec delta (openspec's validator requires at least one)
rather than a fabricated one, and gives future edits to the prompt something concrete
to check against.
- *Alternative considered*: treat this as pure documentation cleanup with no spec
  delta. Rejected -- `openspec validate` requires at least one delta for a change to
  be valid, and more importantly the uniqueness property is a genuine, previously
  unstated invariant this change both violates-in-the-old-file and fixes, so recording
  it is honest, not a formality.

**Compression technique: convert prose paragraphs to imperative bullets/tables; keep
procedural sequences as numbered sub-steps.**
Rules that are already list-shaped (the 8-step proprietary-interface lookup in rule 1,
the clearance table in rule 4) keep their structure, tightened for wording only. Rules
that are narrative paragraphs (5, 6, 7, 9, 10, 11) get restructured into a short lead
sentence (the SHALL) plus bullets for the conditions/exceptions, dropping restated
context and redundant examples but keeping every distinct condition. Worked examples
embedded in prose (e.g. rule 6's `pin_hinge` walkthrough, rule 11's load-type examples)
get reduced to one short parenthetical each rather than a full sentence.
- *Alternative considered*: cut worked examples entirely. Rejected -- some (the
  `pin_hinge` `unions` example, the compression-load example) resolve genuine ambiguity
  in the schema (e.g. what a multi-union `result` dict looks like) that the schema block
  alone doesn't convey; keeping a compressed pointer avoids reintroducing that ambiguity.

**Verification method: rule-by-rule coverage checklist, not a diff-based review.**
Because the goal is compression-without-behavior-change, the safest review isn't "diff
looks reasonable" but an explicit checklist mapping each SHALL/MUST-level obligation in
the current 15 rules to its location in the condensed version, done once during
implementation and kept in the PR/commit description (not committed as a repo file --
this is a one-time authoring aid, not ongoing documentation).
- *Alternative considered*: rely on the eval harness alone to catch regressions.
  Rejected as the sole check -- the eval corpus (~10 cases) won't exercise every rule
  (e.g. `cq_gears` pointer, provenance) in a single run, so it's a spot-check
  complement to the checklist, not a replacement for it.

## Risks / Trade-offs

- [Compression drops a nuance an LLM currently relies on, causing a subtle plan-quality
  regression that the eval corpus doesn't happen to exercise] -> Mitigated by the
  rule-by-rule coverage checklist (every SHALL traced to its new location) plus an
  eval-harness spot-check (`evals/run_evals.py --generate`) on a case that touches
  multiple rules (interfaces, load, archetype) before/after.
- [A rule's condensed wording becomes ambiguous where the verbose version wasn't --
  e.g. collapsing the mating-dock-vs-kinematic-axis-vs-union distinction in rule 5 too
  far] -> Mitigated by keeping the explicit type examples (`face_mount`, `snap_hook`,
  `joint_axis`, `union`) inline rather than summarizing them away.
- [Renumbering assumption turns out wrong -- some other file references rule 15 or a
  rule number I didn't grep for] -> Mitigated by re-running the repo-wide `rule \d+`
  grep (already run during proposal drafting; task list re-runs it after the edit as a
  verification step, not just before).

## Migration Plan

Single-file edit, no data migration. Steps: rewrite `prompts/planning.md`'s Rules
section per the decisions above -> run the coverage checklist -> run
`uv run pytest tests/test_plan_validate.py tests/test_eval_corpus.py` (schema/corpus
sanity, unaffected by wording but cheap to confirm) -> optional eval-harness spot-check
-> re-grep `rule \d+` repo-wide to confirm no stale cross-references -> update
`TODO.md` to mark the sub-item done. Rollback is a plain git revert of the prompt file;
no other system depends on the old wording.

## Open Questions

- None -- scope is bounded to one file's prose plus a verification pass on two
  cross-referencing files and `TODO.md`.
