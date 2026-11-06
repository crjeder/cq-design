## Context

Measured in the 2026-11-04 session (`TODO.md`, "Siebtragerhalter session"): main session 43% of cost (84k context at call 1, 96 calls), sub-agents 57% (61k context at spawn, because every spawn is `general-purpose` with the full tool list; only the builder ran Sonnet). `ARCHITECTURE.md:123` currently forbids `.claude/agents/` files for portability, and `install.sh` / `install.ps1` copy an allowlist into `~/.claude/skills/cq-design/`. `Part.param` (`src/blocks/part.py:275`) returns `plan["instances"][id]["params"][name]` as a literal; `parameters.py` is documented as "not imported by the build" (`skill/phase1_requirements.md`, At approval).

## Goals / Non-Goals

**Goals:**
- Cut sub-agent baseline context and move cheap roles to Sonnet.
- Make a dimension change a one-line edit that rebuilds only affected parts.
- Remove relay-only Bash calls from the main session.
- Catch concept mismatches before planning, cheaply.
- Replace ASCII art with SVG.

**Non-Goals:**
- Reducing research-agent call counts, preview defects, or changing the main session's model (the user's choice).
- Making interface `position_mm` values expressions (v1: `params` only; see Open Questions).
- Keeping the skill portable to installs without agent files.

## Decisions

**1. Agent files, local install only.** Add `agents/{sourcing,research,planner,builder,auditor}.md` with frontmatter `name`, `description`, `tools` (minimal), `model`. Builder, auditor, planner: `Bash, Read, Write, Edit` (auditor also reads images via `Read`); sourcing and research add the web tools. Spawns name the agent instead of `general-purpose`; `render_prompt.py` still writes the prompt file and the spawn says "read this file and follow it".
Alternative: keep `general-purpose` and only add `model:` overrides. Rejected: it leaves the 61k baseline, the largest sub-agent cost. Portability is dropped as the user decided; `ARCHITECTURE.md:123-125` is rewritten.

**2. Install paths.** The repo is the plugin (`.claude-plugin/plugin.json`, source `.`); `agents/` at the root is auto-discovered as plugin agents. `install.sh` / `install.ps1` add `agents` to `ALLOWLIST`, so a copy install ships them in the same directory. Whether Claude Code loads `agents/` from a `~/.claude/skills/<name>/` copy (the spec calls it a `skills-dir` plugin) must be verified in task 1.2. If it does not, the installers also copy the files to `~/.claude/agents/cq-design-<role>.md` and remove them on `--uninstall`, and spawns use whichever name resolves. No marketplace is added as a dependency; `marketplace.json` stays as an optional entry only.

**3. Model config.** `skill_config.default.json` gains `sourcing`, `research`, `auditor` under `models`. Precedence: config value, else the agent file's `model:`. `"inline"` keeps its meaning. `part_author_model()` and the attempts log must record the real model id (today `claude-sonnet-5` vs actual `claude-sonnet-5-5`); read it from the agent definition / config rather than hard-coding.
Auditor on Sonnet is a quality risk (it grades blank section previews as passing). Mitigation: the `TODO.md` line-28 defect is tracked separately, and the audit eval case in `evals/` is run before and after (task 2.5).

**4. `parameters.py` as the single source.** New `src/plan_params.py` (stdlib `ast`, no `eval`): loads `parameters.py` constants by parsing it, and evaluates an expression string allowing only numeric literals, names from the module, `+ - * / //`, unary minus, parentheses, and `min`/`max`/`round`. Unknown name or any other node is an error. `plan.py validate` evaluates every string param and fails on error; the loader in `blocks/part.py` evaluates the same way on read, so `Part.param` returns a number and part scripts need no change. Plain numeric params stay valid.
Provenance comments in `parameters.py` carry an origin tag: `# user`, `# researched: <source>`, `# assumed`, `# design choice`. The planner prompt (`prompts/planning.md`) requires every dimension in the plan to trace to a constant; `quality_gate` extends the existing parameters-provenance check to flag a numeric plan literal equal to an existing constant's value (advisory).
Alternative considered: a `source` expression beside a literal that `validate` recomputes. Rejected: two copies of a number still allow a silent edit of one.
Standalone export already copies `parameters.py`, and the bundle keeps working because the evaluation happens when the plan is loaded, not in the part script.

**5. Partial rebuild after a dimension edit.** `plan.py validate` writes `build/params_resolved.json` (part -> resolved params hash) after a successful run and prints the parts whose hash changed. The rule in `skill/phase3_build.md`: rebuild and re-gate only those parts; the visual audit re-runs only for those parts. This is deterministic, so it lives in the script, not the prompt.
Dropped from the earlier idea: a `plan.py set` command. A dimension edit is now one `Edit` of `parameters.py`.

**6. Journal side effects.** `plan.py validate`, `print_orientation.py`, `build.py` and the other milestone-completing scripts call `log.journal_append` on success with the milestone name from `skill/resume.md`'s table. The `skill/` prose drops the matching standalone Bash calls. User-decision milestones (approvals) have no completing script and keep a call, batched with the checkpoint's other call.

**7. Concept sketch.** New `src/concept_sketch.py` takes a small JSON (`{"title", "shapes": [...], "labels": [...], "dims": [...]}`: rectangles, circles, lines, polylines, text, each with a view tag `front|top|side`) and writes `sketches/concept.svg` with fixed styling and dimension annotations. At the end of Phase 1 the main session (or research agent) writes the JSON from the approved intent and dimensions, renders it, and shows it with the exit checkpoint; the user approves it with the dimensions. The JSON is kept as `sketches/concept.json` and listed by `regen_prompt.py` (images cannot be inlined; the paths are listed). The sketch is a communication aid: no geometry is derived from it.
Alternative: a cheap blocky CadQuery render. Rejected for now: needs a plan or topology, which does not exist yet at Phase 1 exit; an SVG from intent plus dimensions is available earlier and costs no kernel start.

**8. SVG instead of ASCII art.** Inventory first (task 6.1): the pattern search over `SKILL.md`, `skill/`, `prompts/`, `reference/`, `README.md` matches markdown tables too, so the real set of diagrams is found by hand. Each diagram becomes `reference/img/<name>.svg` (inside an allowlisted directory, so a copy install ships them; hand-written SVG, text kept as `<text>`), referenced from the markdown with an image link and a one-line text alt. Prompts that the LLM reads (`prompts/*.md`) cannot rely on an image; for those, the ASCII diagram is replaced by a prose description plus the SVG path in a comment, only where the diagram carried information. Layout trees (file trees) are not diagrams and stay as text. `FILES.md` gets the SVG entries. A test checks that every referenced SVG exists and parses.

## Risks / Trade-offs

- [Agent files not discovered in a copy install] -> Verify in task 1.2; fallback is the `~/.claude/agents/` copy with uninstall handling.
- [Sonnet auditor misses defects] -> Run the audit eval before/after; keep `models.auditor` configurable, one config change reverts it.
- [Expression params break old plans or the round-trip reconciler] -> Literals remain valid; `parameter_round_trip` resolves expressions before comparing; add a test with a mixed plan.
- [Planner writes literal numbers anyway] -> The gate's duplicate-literal advisory plus a `plan.py validate` check for params that match a constant.
- [Partial rebuild misses a dependency between parts] -> Shared constants change the resolved params of every part that uses them, so each such part is rebuilt; geometry coupling through `placement` is still caught by the whole-model gate stages, which run on any rebuild.
- [Image diagrams invisible to the LLM] -> Only for prompts; those keep a prose description.

## Migration Plan

Existing projects keep working: literal params stay valid, `parameters.py` stays optional, and the new `skill_config.json` keys fall back to the agent file's `model:`. `/cq-design:update` re-copies tooling; reinstalling picks up `agents/`. Rollback is reverting the agent spawn names to `general-purpose`.

## Open Questions

- Can plan `interfaces[].position_mm` also be expressions? Most derived numbers (71 = 70 + 1) land in `params`, but positions drift the same way. Left for a follow-up once `params` expressions are proven.
- Does `Task`/Agent spawning in the current Claude Code version accept plugin-namespaced agent names (`cq-design:builder`) and enforce `tools:` for them? Confirm against docs in task 1.1 before wiring spawns.
