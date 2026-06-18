## Context

Phase 2 of the `cq-design` skill generates `BUILD_PLAN.json` via an LLM call, validates it with `plan_validate.py`, then shows it to the user as a code block. The skill's Phase 3 instruction is to run `python src/orchestrate.py --plan BUILD_PLAN.json`, which reads the file from disk. Currently no step writes the file, so running Phase 3 immediately after Phase 2 always fails with a file-not-found error unless the user manually saves the code block.

## Goals / Non-Goals

**Goals:**
- The skill writes `BUILD_PLAN.json` to the working directory after validation passes, before showing it to the user.
- The user sees confirmation of the write path alongside the JSON display.
- Re-validation after user edits reads from the same path on disk.

**Non-Goals:**
- No changes to `orchestrate.py`, `plan_validate.py`, or any Python source files.
- No changes to the planning prompt template (`prompts/planning.md`).
- No support for configurable output paths (always `BUILD_PLAN.json` in the working directory).
- No versioning or backup of previous plan files.

## Decisions

**Write path is always `BUILD_PLAN.json` in the current working directory.**
Rationale: `orchestrate.py --plan BUILD_PLAN.json` uses this name by default. Using any other path would require the user to pass `--plan` explicitly, adding friction. The schema already includes `schema_version` for forward compatibility if needed later.

**Write happens after validation, before user display.**
Rationale: Writing before display ensures the file exists even if the user immediately opens a terminal without waiting. Writing before validation would leave an invalid file on disk if validation fails.

**Skill handles the write directly (no helper script).**
Rationale: Writing a JSON file to disk from a Python string the skill already holds does not warrant a subprocess or new script. The write is one `json.dumps` + open/write. Keeping it in the skill avoids a new code artifact for a two-line operation. The write step in SKILL.md references `plan_validate.py` for validation (already exists) and a direct Python one-liner or `> BUILD_PLAN.json` redirect for the write itself - whichever is cleaner in context.

## Risks / Trade-offs

[Risk] Existing `BUILD_PLAN.json` is silently overwritten if the user runs the skill twice in the same directory.
Mitigation: The overwrite is intentional - the skill is always producing a fresh plan for a new design session. Log the path written so the user can see it happened.

[Risk] Skill writes file but user has read-only working directory.
Mitigation: File write errors will surface as a Python exception or shell error; the skill should surface that error and ask the user to confirm the working directory before proceeding.

## Open Questions

None - scope is narrow and implementation path is clear.
