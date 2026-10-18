## Why

The "Updating an existing project" command block exists twice: `README.md:95-114` and `skill/resume.md:78-96`. Both hardcode `~/.claude/skills/cq-design/src/...` and `<path-to-this-repo>`, which contradicts the `SKILL_DIR` convention (`SKILL.md:13-19`) and is wrong for plugin installs. `resume.md` is loaded in full on every resumed run, so the stale copy costs context each time.

## What Changes

- Delete the command block and trailing `bundle_project.py` explanation from the "Updating an existing project" section of `skill/resume.md`; keep a one-line pointer to `/cq-design:update`.
- Keep `README.md` as the single canonical copy.

## Capabilities

### New Capabilities

### Modified Capabilities
- `plugin-packaging`: the "Shipped prose does not name the installer scripts" scenario cites `skill/resume.md` as a place that tells the reader how to refresh a stale skill; after this change `resume.md` only points to `/cq-design:update`.

## Impact

- `skill/resume.md` (shorter).
- `openspec/specs/plugin-packaging/spec.md` (scenario wording).
- No script, test, or JSON-contract changes.
