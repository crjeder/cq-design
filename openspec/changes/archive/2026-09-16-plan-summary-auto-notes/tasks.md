## 1. plan_summary.py

- [x] 1.1 Add `_open_questions(plan) -> list[str]`: split `planning_notes` on `\n`,
      strip whitespace and a leading `-`/`*`/`+` bullet marker per line, keep lines whose
      remainder starts with literal `OPEN:`.
- [x] 1.2 Add `_coined_names(plan) -> list[str]`: build the lowercased word-token set from
      every `request_log[].text`; for each part `id` and each non-empty
      `interfaces[].name`, tokenize the same way and flag it when its tokens are not a
      subset of the request_log token set.
- [x] 1.3 Wire both into `summarize()`: render an **Open questions** bullet list and a
      **Names I chose** bullet list, each omitted when its source list is empty.

## 2. Tests

- [x] 2.1 `test_plan_summary.py`: `OPEN:` line present (plain and bullet-prefixed) ->
      appears in **Open questions**; no `OPEN:` line -> section absent.
- [x] 2.2 `test_plan_summary.py`: part id / interface name absent from every
      `request_log[].text` -> appears in **Names I chose**; present -> absent from it;
      `hole_2`-style suffix matching root word `hole` -> not flagged.
- [x] 2.3 `test_plan_summary.py`: no `request_log` field -> **Names I chose** section
      absent regardless of naming.
- [x] 2.4 Run `uv run pytest tests/test_plan_summary.py` and confirm
      `test_summary_renders_every_eval_plan` still passes against every eval golden.

## 3. Docs

- [x] 3.1 Update `skill/phase2_planning.md`'s Plan summary checkpoint bullet list to drop
      "Names I chose" and "Open questions" (now in the script's own output) and keep only
      "Design proposals".
