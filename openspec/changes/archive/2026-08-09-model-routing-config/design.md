## Context

Three places name a model today, none of them configurable:

- `skill/phase2_planning.md:18` — planner agent, "model override: the strongest available".
- `skill/phase3_build.md:97` — builder agent, "Model override: mid-tier (Sonnet-class);
  a default, not a hard requirement".
- `src/quality_gate.py:288` `_call_claude` — invokes `["claude", "-p", prompt_text]`
  with no `--model`, so the fix loop silently inherits whatever the CLI defaults to.

Everything else C6 asked for already landed: `evals/model_prices.json` carries the
5-series entries, `skill/phase3_build.md` Step 5 records the executing model per
attempt, and the Agent routing gate (`skill/phase3_build.md:85`) already dispatches
sequentially. What remains is the config file, the wiring, the 5-series subagent cap,
and the A/B measurement.

`printer_profile.json` is the established precedent for a working-directory config:
shipped default in `src/`, copied by `skill/setup.md` only when absent, never
overwritten.

## Goals / Non-Goals

**Goals:**

- Change which model runs planning, part authoring, or the gate fix loop by editing one
  JSON file, with no skill-file edits.
- Keep `inline` (run in the calling session, no spawn, no `--model`) expressible.
- Prevent a 5-series orchestrator from multiplying agent spawns beyond the routing gate.
- Decide the default authoring configuration from an eval A/B, not from assumption.

**Non-Goals:**

- A JSON Schema and validator module for `skill_config.json`. The printer profile has
  one because its numbers feed DFM checks that must not silently accept garbage; a
  model name is a string passed to the Agent tool or `claude -p`, which fails loudly on
  its own if wrong. A schema here is a second file to maintain for no caught error.
- `.claude/agents/*.md` files. `ARCHITECTURE.md` ("No `.claude/agents/` files needed")
  already settled this: the part prompt is a fully rendered, self-contained artifact
  passed as an Agent-tool prompt with a per-call model override. Agent files would put
  the same model names in a second place that can drift from the config.
- Raising the planner to `claude-fable-5`. It stays a documented option in the config
  comment (2x Opus 5 price, capability aimed at long-horizon work rather than one-shot
  planning) — measure before defaulting to it.
- Automatic per-part model escalation, cost budgets, or fallback chains.

## Decisions

**One file, one section, three string keys.** `skill_config.json`:

```json
{
  "_comment": "Model per LLM role. 'inline' = run in the calling session (no spawn, no --model). Fable 5 is 2x Opus 5 price and targets long-horizon work, not one-shot planning - measure before setting planner to claude-fable-5.",
  "models": {
    "planner": "claude-opus-5",
    "part_author": "claude-sonnet-5",
    "fix_loop": "inline"
  }
}
```

Alternative considered: fold the models into `printer_profile.json`. Rejected — that
file is about the physical printer and is the thing a user hand-edits per machine;
mixing pipeline routing into it makes both harder to reason about.

**Reads are direct, not via a helper module.** The skill phases are prose executed by
Claude; they read the file with the same `cat`/`Get-Content` pattern they already use
for `BUILD_PLAN.json`. `quality_gate.py` reads it with `json.load` in `_call_claude`
and treats a missing file or missing key as `inline`. Alternative considered: a
`src/skill_config.py` loader. Rejected — one caller in Python, ~5 lines, and adding a
module means adding its tests for no behavior.

**`inline` is a value, not a special case.** `models.fix_loop: "inline"` means
`_call_claude` builds `["claude", "-p", prompt]` exactly as today; any other value
appends `["--model", <value>]`. That keeps the current behavior as the default and
makes the flag opt-in by config edit, matching C4's report-only posture.

**Missing config is not an error.** The pipeline must run in a directory where setup
was never executed. Absent file → each role falls back to its current documented
behavior (planner: strongest available; part_author: mid-tier; fix_loop: inline). The
skill files state the fallback so the prose stays complete on its own.

**Subagent cap is stated where the gate lives.** The cap ("one part gets at most one
builder agent; no verification subagents") goes into the Agent routing gate section of
`skill/phase3_build.md`, next to the decision it constrains, not into a new document.
Verification subagents are the specific 5-series failure mode: the auditor is already a
separate agent by design and the deterministic checks are programs, so any additional
"check the builder's work" agent is duplicated cost.

**A/B is scored on the existing harness.** Two `evals/run_evals.py --generate` sweeps
with `models.part_author` set to `claude-opus-5` + inline routing vs `claude-sonnet-5`
+ subagent routing, compared on cost per accepted part and first-shot rate. The cheaper
configuration that holds first-shot rate becomes the shipped default in
`src/skill_config.default.json`.

## Risks / Trade-offs

- **A sweep may not complete.** C4 and C5 both had runs interrupted by the account's
  Claude session usage limit, and C2 documented run-to-run spread (0.85/1.15 vs
  0.75/1.35) as large as the measured effect → report the A/B with the same honesty:
  case counts, which cases are missing, and no default flip on a difference inside that
  spread. If both arms land inside the spread, keep the current documented defaults
  (`part_author: claude-sonnet-5` + subagent) and say so.
- **A typo'd model name fails at spawn time, not at config-write time** (the deliberate
  cost of skipping a validator) → the error surfaces immediately on the first spawn with
  the model name in it, which is a legible failure; document the accepted values in the
  config's `_comment`.
- **Config and prose can drift** — the skill files still describe the fallback tiers in
  words → each mention cites `skill_config.json` as the source of truth and marks its
  own text as the absent-file fallback.
- **The 5-series orchestrator may still over-delegate** despite the stated cap, since it
  is prose, not an enforced limit → the telemetry `model` field plus attempt counts make
  extra spawns visible in `build/attempts.jsonl` after the fact.
