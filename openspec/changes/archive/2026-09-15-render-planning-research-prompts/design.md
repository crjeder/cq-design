## Context

`src/render_prompt.py` has `builder` and `audit` subcommands. Both require `--plan` and
`--part`, and `main()` resolves the part before branching. It already has the pieces the
planner prompt needs: `fill()` (single-pass `{{KEY}}` substitution that raises on an
unfilled placeholder), `tagged_sections()` (FDM `applies_to` filtering), and `SKILL_DIR`.
`printer_profile_validate.validate_profile(path)` returns a list of schema errors.

`prompts/planning.md` placeholders: `USER_REQUEST`, `BLOCK_INVENTORY`, `ARCHETYPE_INDEX`
(appears twice), `PRINTER_PROFILE`, `FDM_GUIDELINES`. `prompts/research.md` placeholders:
`LOOKUP_TARGETS`, `KNOWN_CONTEXT`, `SKILL_DIR` (twice).

## Goals / Non-Goals

**Goals:**
- Main session never reads `inventory.json`, `archetypes.json`, the FDM guidelines, or
  `research.md`/`planning.md` to build these prompts.
- Same inputs always render the same prompt.

**Non-Goals:**
- Changing the prompt templates' content.
- Changing planner/research agent models, resume loops, or checkpoints.
- Validating that the request or lookup targets are sensible.

## Decisions

- **Free text arrives by file, not argv.** `planning --request-file PATH`,
  `research --targets-file PATH [--known-file PATH]`. The user request and target
  bullets are multi-line and contain quotes; passing them on a shell command line on
  Windows and POSIX is fragile. The main session writes them with the Write tool first
  (e.g. `build/request.md`, `build/lookup_targets.md`). Alternative: stdin -- rejected,
  harder to express in a single Bash call from the skill docs.
- **Condensed index lines.** Inventory: `- **name** -- use`. Archetypes:
  `- **name** (`templates/file`) -- use`. Matches the "name and use only" headings in
  `planning.md` and `start_point()`'s existing archetype line format.
- **FDM sections.** `planning --plan BUILD_PLAN.json` (optional) unions every part's
  `blocks_needed` via `block_name`; without `--plan`, `tagged_sections(md, set())` yields
  only `always` sections. This makes the existing union requirement implementable (it
  needs a plan) instead of silently unmet on a fresh plan.
- **Printer profile.** `--profile` defaults to `printer_profile.json` in the cwd. If
  present and `validate_profile` returns no errors, inject a JSON object of `printer`,
  `material`, `nozzle_mm`, `constraints` (keys that exist). Otherwise inject a fixed note
  telling the planner none is available and the values come from the user. The JSON report
  carries `"profile": "loaded" | "absent" | "invalid"` (plus `profile_errors` when invalid)
  so the main session knows whether to ask the user, without reading the file.
- **Outputs.** Default `build/planning_prompt.txt` and `build/research_prompt.txt`,
  `--out` overrides; print `{"out", "chars", ...}` like the existing modes. Exit 1 on
  `ValueError` from `fill()`.
- **CLI restructure.** Move the `--plan`/`--part` arguments and part lookup into the
  `builder`/`audit` branch only; `planning`/`research` do not take `--part`.
- **Spawn line.** Docs switch to `Read <out> in full and follow it. Working directory:
  <cwd>.` -- the Phase 3 pattern -- so the rendered text never enters main either.

## Risks / Trade-offs

- [Planner reads the prompt file itself, one extra tool call] -> negligible next to
  keeping ~inventory+archetypes+guidelines out of main.
- [`--request-file` left stale from a previous run] -> docs write it immediately before
  rendering; the file is the verbatim request, the same text the main session had.
- [Profile note wording now fixed in code] -> that is the point (no drift); change it in
  one place if needed.
