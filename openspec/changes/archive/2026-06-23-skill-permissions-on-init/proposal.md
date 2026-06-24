## Why

Every cq-design run fires a stream of `uv run`, `python`, `cp`/`Copy-Item`, `uv sync`,
`WebSearch`/`WebFetch`, and Playwright MCP calls. With a fresh working directory none of
these are allow-listed, so the user is interrupted by a permission prompt for nearly every
step of the pipeline. The skill already knows exactly which command shapes it issues; it
should record them once, on first use in a directory, so the rest of the run (and every
later run in that directory) proceeds without repeated prompts.

## What Changes

- **Add a one-time init step to the skill workflow.** On the first invocation of the skill
  in a working directory (detected by the absence of the skill's permission block), or when
  the user explicitly asks to init, the skill SHALL write the permission patterns its own
  commands need into that directory's `.claude/settings.local.json`.
- **Define the permission set the skill needs.** A fixed, documented list of allow patterns
  covering the command shapes the pipeline issues (the `uv run`/`python`/`uv sync` tool
  invocations, the build-bundle file copies and directory creation, dimension-lookup
  `WebSearch`/`WebFetch`, and the Playwright browser MCP tools), expressed as wildcard
  patterns that match regardless of the interpolated `$SKILL_DIR` and per-part arguments.
- **Merge, never clobber.** The init step SHALL create `.claude/settings.local.json` if
  absent and otherwise merge its patterns into the existing `permissions.allow` array
  without removing or duplicating entries the user (or a prior init) already has.
- **Idempotent and re-runnable.** A second invocation in the same directory SHALL detect the
  block is already present and skip the write (explicit init re-runs the merge to pick up any
  newly added patterns). The write is a no-op when all patterns are already present.

## Capabilities

### New Capabilities
- `skill-permission-bootstrap`: on first use in a working directory (or on explicit init),
  the skill writes the curated set of permission patterns its pipeline commands require into
  the working directory's `.claude/settings.local.json`, merging idempotently with any
  existing allow list, so the user is not prompted for each skill-issued tool call.

### Modified Capabilities
<!-- none: this is additive to the skill workflow; no existing spec's requirements change -->

## Impact

- Skill workflow: `SKILL.md` gains an init/bootstrap step run before the pipeline (and a
  documented explicit-init entry point), plus the canonical permission list.
- No `src/` tool boundary changes are required — the write is a small, documented step the
  skill performs directly (read JSON, merge `permissions.allow`, write back). A tiny helper
  script under `src/` is optional and decided in design.md.
- Output location: the working directory's `.claude/settings.local.json` (the project-local,
  git-ignored Claude settings file), not the user's global settings and not `$SKILL_DIR`.
- Docs: `README.md` notes that the first run seeds project-local permissions.
