## Context

The `cq-design` skill lives in its own directory (the skill root) alongside `src/`, `prompts/`, and `reference/`. SKILL.md is the canonical entry point. When the skill is invoked, two directories matter:

- **Skill root** (`SKILL_DIR`): the directory containing SKILL.md. All internal scripts (`src/orchestrate.py`, `src/plan_validate.py`, etc.) and reference files live here.
- **Caller's cwd** (`CALLER_CWD`): the directory from which the user invoked the skill. All generated artefacts (`BUILD_PLAN.json`, `build/`, STL/3MF exports) belong here.

Currently, SKILL.md uses bare relative paths (`src/orchestrate.py`, `python src/plan_validate.py BUILD_PLAN.json`) with no guidance on how to resolve them. This works only when the caller's cwd happens to equal the skill root, which is never guaranteed.

## Goals / Non-Goals

**Goals:**
- SKILL.md shell commands resolve `src/` scripts via an absolute path anchored to SKILL.md's location.
- All skill-generated artefacts (`BUILD_PLAN.json`, `build/`, exported files) are written to `CALLER_CWD`, not the skill root.
- The orchestrator, plan validator, and any other script that accepts file paths do not assume a particular cwd.

**Non-Goals:**
- Changes to the CadQuery model scripts themselves (they run in a temp dir managed by the wrapper).
- Supporting multiple simultaneous caller cwds.
- Changing what artefacts are produced or their formats.

## Decisions

### Decision 1: Resolve SKILL_DIR in SKILL.md via a shell variable

SKILL.md shell snippets will use a `SKILL_DIR` variable set by the skill activation mechanism:

```bash
SKILL_DIR="$(dirname "$(realpath "$SKILL_MD_PATH")")"
```

All `src/` invocations become:
```bash
python "$SKILL_DIR/src/plan_validate.py" BUILD_PLAN.json
python "$SKILL_DIR/src/orchestrate.py" --plan BUILD_PLAN.json --output-dir build/ --max-retries 3
```

The scripts themselves do not change their path logic -- the skill doc is responsible for passing the correct absolute path to each script.

**Alternative considered**: having each Python script compute `SKILL_DIR` from its own `__file__`. Rejected because it couples the scripts' internal layout to deployment assumptions, and makes unit-testing harder.

### Decision 2: Artefact paths are relative to CALLER_CWD, which is the shell's cwd at invocation time

Shell commands in SKILL.md produce artefacts with relative paths (`BUILD_PLAN.json`, `build/`) that resolve against whatever directory the shell is in when the commands run. The skill doc MUST NOT `cd` into the skill root before running any command.

The only explicit path passed to scripts is the script's own location (`$SKILL_DIR/src/...`). All output paths remain unqualified (relative to cwd), which naturally lands them in the caller's directory.

### Decision 3: Scripts accept file path arguments; they do not derive paths from their own location

`orchestrate.py` already accepts `--plan` and `--output-dir`. `plan_validate.py` accepts the plan path as a positional argument. No changes needed to the scripts' interface. SKILL.md just needs to pass the correct arguments explicitly rather than relying on implicit defaults.

## Risks / Trade-offs

- [Risk] A skill host that changes cwd before invoking scripts will still break. → Mitigation: document that SKILL_DIR must be set before any invocation, and that cwd must not be changed after invocation starts.
- [Risk] Windows vs. POSIX path handling. → Mitigation: use `python -c "import pathlib; ..."` alternatives in SKILL.md where `realpath`/`dirname` are unavailable; or document the Windows equivalent.
- [Trade-off] The skill doc now carries a small setup preamble (`SKILL_DIR=...`). This is a one-time cost at the top of the relevant phases, not repeated per command.
