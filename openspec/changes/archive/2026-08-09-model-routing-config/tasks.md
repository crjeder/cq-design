## 1. Config file

- [x] 1.1 Add `src/skill_config.default.json` with the `_comment` + `models`
  (`planner: claude-opus-5`, `part_author: claude-sonnet-5`, `fix_loop: inline`) per
  design.md, including the Fable-5 price/capability note in the comment
- [x] 1.2 Add the seed-if-absent step to `skill/setup.md` (bash + PowerShell branches),
  mirroring the existing `printer_profile.json` block, with the never-overwrite note
- [x] 1.3 Add `skill_config.json` to the `.gitignore` working-directory artifacts if
  `printer_profile.json` is listed there (not listed -- no-op, condition false)

## 2. Wiring

- [x] 2.1 `src/quality_gate.py` `_call_claude`: read `models.fix_loop` from
  `skill_config.json` (working directory), append `--model <value>` unless the value is
  `inline`/absent/the file is missing
- [x] 2.2 `skill/phase2_planning.md`: replace "model override: the strongest available"
  with a read of `models.planner`, naming the strongest-available fallback
- [x] 2.3 `skill/phase3_build.md` Agent routing gate: replace "mid-tier
  (Sonnet-class)" with a read of `models.part_author`, naming the mid-tier fallback and
  the `inline` value's meaning (run the part loop in the main session)

## 3. Subagent cap

- [x] 3.1 `skill/phase3_build.md` Agent routing gate: state that one part gets at most
  one builder agent and that no verification/double-check subagents are spawned; the
  routing gate is the only dispatch decision
- [x] 3.2 Grep `skill/`, `prompts/`, `SKILL.md`, `ARCHITECTURE.md` for any
  "delegate"/"prefer subagents" phrasing and remove it (no matches found)

## 4. Tests

- [x] 4.1 Add a fast test (no CadQuery) covering `_call_claude`'s flag construction:
  configured model id -> `--model` present; `inline` -> absent; missing file -> absent

## 5. Docs

- [x] 5.1 `CLAUDE.md`: add `src/skill_config.default.json` to the file layout and note
  the config in the `quality_gate.py` row
- [x] 5.2 `ARCHITECTURE.md`: point the agent roster's Model column at
  `skill_config.json` instead of hardcoded tiers; leave the "No `.claude/agents/` files
  needed" rule in place

## 6. A/B and close-out

- [x] 6.1 Run `evals/run_evals.py --generate` with `models.part_author:
  claude-opus-5` + inline authoring; archive as `evals/runs/c6-opus-inline/`
  (reduced to the single `two-part-box` case -- see 6.4 note)
- [x] 6.2 Run the same sweep with `models.part_author: claude-sonnet-5` + subagent
  authoring; archive as `evals/runs/c6-sonnet-agent/` (same reduced scope)
- [x] 6.3 Compare cost per accepted part and first-shot rate; set
  `src/skill_config.default.json`'s `part_author` to the cheaper arm only if it holds
  first-shot rate outside C2's documented run-to-run spread, otherwise keep the current
  default and say so (tied first-shot, sonnet-agent ~44% cheaper on n=1 -- already the
  shipped default, no change made)
- [x] 6.4 Write the C6 result section into `CLAUDE5_CONVERSION_PLAN.md` with case
  counts, any interrupted sweeps, and the spread caveat
- [x] 6.5 Mark IMPROVEMENT_PLAN.md item 15 done
