## 1. Edit CLAUDE.md

- [x] 1.1 Remove the "Core Scripts" table section (the `| Script | Role |`
      table and its intro line) from `CLAUDE.md`.
- [x] 1.2 Update the `File Layout` section's intro sentence to be the single
      pointer to `reference/scripts.md` for full per-script contract detail
      (JSON shapes, CLI flags, typed error names, edge cases).
- [x] 1.3 Check every script's `File Layout` one-line comment is still
      present and accurate — nothing dropped when the "Core Scripts" table
      was removed. (Found 7 scripts that only existed in the removed table —
      `cq_verify.py`, `interference.py`, `feature_presence_check.py`,
      `print_orientation.py`, `convert_build123d.py`, `cq_compat.py`,
      `init_permissions.py` — added them to `File Layout`.)

## 2. Verify

- [x] 2.1 Confirm `reference/scripts.md` is unchanged.
- [x] 2.2 Confirm no other file in the repo (README, SKILL.md, skill/*.md)
      links to or quotes the removed "Core Scripts" table by name/anchor.
