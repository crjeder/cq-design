## Context

`SKILL.md` Prerequisites lists three init commands that `commands/init.md` also lists. The command version is newer (venv in `${CLAUDE_PLUGIN_DATA}`, `--venv` flag).

## Goals / Non-Goals

**Goals:** one copy of the init command lines, in `commands/init.md`.

**Non-Goals:** changing init behavior, `init_permissions.py`, or other commands.

## Decisions

- SKILL.md says "run `/cq-design:init` logic (see `commands/init.md`)" and drops the code block. Reason: the skill may load without the slash command being invoked (design/plan already do the init steps when `--check` reports uninitialized), so a pointer to the file works in both cases.
- The prose after the block (what `init_permissions.py` seeds, manual `skill_permissions.json` fallback, how to run scripts) stays: it holds no command lines that duplicate init.md.

## Risks / Trade-offs

- A reader of SKILL.md must open one more file for the exact commands. Accepted; that is the point of a single copy.
- The old SKILL.md copy lacked `--venv`; following init.md changes non-plugin behavior to match the command. Intended.
