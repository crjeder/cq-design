## Context

The planning phase (SKILL.md Phases 1-2) has Claude perform dimension research via Playwright and web search, then directly populate `BUILD_PLAN.json`. There is no step where found dimensions are surfaced to the user before being committed to the plan. All implementation lives in `SKILL.md` — no Python scripts are involved in Phase 1 or 2.

## Goals / Non-Goals

**Goals:**
- Add a structured summary step after all dimension lookups, before plan generation.
- Give the user a clear table of what was found, from where, and any gaps or conflicts.
- Pause for explicit confirmation or corrections before proceeding.
- Carry user-corrected values into the generated plan.

**Non-Goals:**
- Changing `prompts/planning.md`, `BUILD_PLAN.json` schema, or any Python file.
- Persisting the dimension table anywhere beyond the conversation.
- Automated conflict resolution between sources.

## Decisions

### Decision: Implement as SKILL.md instruction only

The entire planning phase runs as interactive skill execution — Claude follows SKILL.md instructions directly, with no subprocess. Therefore, adding the checkpoint requires only updating SKILL.md with explicit narration and pause instructions.

Alternative considered: adding a `dimension_sources` field to `BUILD_PLAN.json` to record provenance. Rejected — too heavyweight for what is a UX improvement, not a data-model requirement.

### Decision: Tabular format for the dimension summary

Present found dimensions as a markdown table with columns: Item, Value (mm), Source URL, Status. Status values: `confirmed` (two agreeing sources), `single-source` (only one found), `conflict` (sources disagree), `missing` (-1 placeholder).

This is scannable at a glance and matches how SKILL.md already uses tables for block inventory and constraints.

### Decision: Hard pause, not soft suggestion

The skill MUST wait for user acknowledgment before generating the plan. A soft "let me know if anything looks wrong" risks the user missing it. The instruction should explicitly say "Do not generate `BUILD_PLAN.json` until the user approves or corrects the table."

### Decision: Correction handling is conversational

If the user corrects a value inline (e.g., "the depth is 8.5, not 8.0"), Claude notes the correction and uses the corrected value. No structured format required — it is an interactive conversation step.

## Risks / Trade-offs

- [Risk] User ignores the table and says "looks good" without reading it → Mitigation: table is compact and visually prominent; no further mitigation without forcing re-entry of values.
- [Risk] Playwright finds no dimensions → Mitigation: table still renders with `-1` / `missing` rows, making gaps explicit.
- [Trade-off] Adds one user round-trip per build → accepted; the round-trip replaces an implicit one that currently happens after a failed build.

## Migration Plan

Single file edit to `SKILL.md`:
1. Add narration instructions to Phase 1 (announce each lookup before starting).
2. Add the dimension-validation checkpoint between Phase 1 and Phase 2 (present table, wait for approval).
3. Add a note to Phase 2 that corrected values take precedence over looked-up values.

No rollback strategy needed — SKILL.md is in git.
