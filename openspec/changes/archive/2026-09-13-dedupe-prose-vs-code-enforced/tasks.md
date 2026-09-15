## 1. SKILL.md error-handling table

- [x] 1.1 Replace the full typed-error table (lines ~233-260) with a short
      category summary (e.g. geometry/boolean failures, dimension/mate
      failures, print-orientation failures) and a pointer to
      `run_cadquery_model.py`'s `errors[].hint` and `cq_verify.py` as the
      source of exact error names and remediation text.
- [x] 1.2 Confirm SKILL.md stays under its 10 KB budget after the edit
      (per the existing skill-doc-structure requirement). NOTE: SKILL.md was
      already 17541 bytes before this change (pre-existing violation,
      unrelated to this task's scope); the edit shrank it to 16094 bytes but
      it remains over budget. Flagged, not fixed here.

## 2. skill/phase3_build.md lint-check list

- [x] 2.1 Replace the prose lint-check list (~lines 342-346) with a pointer
      to `reference/scripts.md`'s `script_lint.py` entry.

## 3. skill/phase3_build.md block/inventory tables

- [x] 3.1 Remove the block-name list (~lines 1000-1006) that restates
      `src/blocks/inventory.json`, keeping only the instruction to consult
      `inventory.json` directly.
- [x] 3.2 Remove the Gridfinity block table (~lines 1013-1019), keeping any
      procedural guidance that has no equivalent in `inventory.json`.

## 4. CLAUDE.md Key Constraints

- [x] 4.1 Trim the multi-union and thin-interface bullets to name the fields
      only, deferring shape/field detail fully to `reference/scripts.md`.
      (Moved the field-shape detail into `reference/scripts.md`'s
      `run_cadquery_model.py` entry first, since it wasn't documented there
      yet -- CLAUDE.md was the only place carrying it.)

## 5. Verification

- [x] 5.1 Grep the edited files for the removed enumerations/tables to
      confirm they don't reappear elsewhere, and confirm each fact now has
      exactly one authoritative location (schema, script, or
      `reference/scripts.md`).
- [x] 5.2 Re-read SKILL.md and skill/phase3_build.md end to end to confirm
      no instruction was lost, only restated detail.
