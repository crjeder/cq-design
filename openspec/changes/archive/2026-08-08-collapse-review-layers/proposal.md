## Why

Phase C4 of `CLAUDE5_CONVERSION_PLAN.md`. The pipeline currently carries three
verification layers that the Claude 5 series makes counterproductive:

1. `quality_gate.py` auto-fixes by default — it spawns a cold `claude -p` (up to
   2 rounds) that rewrites the part script with none of the plan, render, or
   attempt history the orchestrating session already holds. This is also
   IMPROVEMENT_PLAN item 10.
2. The Visual Review Checklist is pass/fail-gated: a question is a "yes" or a
   `visual_mismatch`, with no channel for a low-confidence observation.
   Severity-filtered review prompts measurably depress recall on 5-series
   models — the model sees the defect and declines to report it.
3. The autonomous builder runs a "light self-check" on its own render before
   returning, even though `phase3_build.md` already states that check is not the
   acceptance bar (the fresh-context auditor is). That is self-verification
   scaffolding the 5-series does unprompted, paid for twice.

## What Changes

- **BREAKING (CLI):** `quality_gate.py` becomes report-only by default. `--no-fix`
  is replaced by `--fix`; `run_gate`'s `allow_fix` defaults to `False`.
  `_call_claude` and the fix-prompt renderer stay for explicit `--fix` runs.
- Phase 3's Quality gate section routes gate findings back into the inline
  part-loop fix path: the orchestrating session (or the part's builder agent)
  applies the fix with full context instead of a cold subprocess.
- `reference/Visual Review Checklist.md` switches to coverage-first reporting:
  every observed discrepancy is reported with a confidence and a severity, and
  the pass/fail decision consumes that list rather than the reviewer withholding
  findings. Blocking semantics are unchanged — what changes is what gets
  reported, not what fails.
- The builder agent's light self-check is deleted from Step 4's autonomous
  branch; the builder returns after its deterministic checks (lint, wrapper,
  feature presence) pass, and the Implementation audit remains the acceptance
  bar. Deterministic checks are untouched — they are programs, not prompts.

## Capabilities

### New Capabilities
- `quality-gate-fix-policy`: whether and how the quality gate mutates the part
  script — report-only by default, opt-in `--fix` for the cold-context fixer,
  and the requirement that gate findings route into the caller's fix path.

### Modified Capabilities
- `visual-self-review`: the review reports every discrepancy it observes with a
  confidence and severity instead of emitting only pass/fail per question.
- `subagent-orchestration`: the builder agent's internal loop no longer includes
  a self-check step before returning `passed`.

## Impact

- `src/quality_gate.py` (CLI flag, `run_gate` default, docstring usage lines).
- `skill/phase3_build.md`: Quality gate section (add `--fix` absence rationale +
  finding routing), Step 4 autonomous branch (drop self-check), Builder return
  contract wording for `status: passed`.
- `reference/Visual Review Checklist.md`: Rules section.
- `openspec/specs/visual-self-review/`, `openspec/specs/subagent-orchestration/`.
- `tests/test_quality_gate.py` and the four gate-stage tests that already pass
  `allow_fix=False` explicitly (behavior unchanged for them).
- `CLAUDE.md` quality_gate row; `CLAUDE5_CONVERSION_PLAN.md` C4 result section;
  `IMPROVEMENT_PLAN.md` item 10 status.
- Acceptance is an eval sweep compared against the C2/C3 runs, not inspection.
