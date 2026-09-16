## Why

Today `skill/phase2_planning.md` has the main session hand-derive two of the three
checkpoint sections after `plan_summary.py` prints its Markdown tables: scanning
`planning_notes` line by line for `OPEN:` items, and spotting which part ids / interface
names the planner coined versus copied from the user. Both are mechanical checks against
data already in `BUILD_PLAN.json` (`planning_notes`, `request_log`) and belong in the
script, not in inline LLM judgment repeated every plan. Automating them also makes the
extraction consistent and testable, instead of depending on the session noticing every
`OPEN:` line and every non-user-word name.

## What Changes

- `plan_summary.py` gains an **Open questions** section: every `planning_notes` line
  starting with `OPEN:` (after stripping bullet markers), rendered as a list, omitted
  when there are none.
- `plan_summary.py` gains a **Names I chose** section: for each part `id` and each
  `interfaces[].name`, flag it when it does not appear as a word in any `request_log[].text`
  (case-insensitive, word-boundary match); omitted when `request_log` is absent or every
  name matches.
- `skill/phase2_planning.md`'s Plan summary checkpoint section is narrowed: it shows the
  script's Markdown output (now including Open questions and Names I chose) and the
  session only adds **Design proposals** (the one category the schema documents as
  planner-authored judgment: things `planning_notes` proposes on its own initiative). The
  session still resolves each open question with the user and resumes the planner per the
  existing rule -- only the extraction step moves into the script.

## Capabilities

### New Capabilities
- `plan-summary-checkpoint`: `plan_summary.py`'s Markdown rendering of a validated
  `BUILD_PLAN.json` for the Phase 2 checkpoint, including the automatically derived Open
  questions and Names I chose sections.

### Modified Capabilities
- `planning-phase`: the Phase 2 plan summary checkpoint workflow changes from "derive
  Names I chose and Open questions by reading `planning_notes`" to "read them from the
  script's output; author only Design proposals."

## Impact

- `src/plan_summary.py`: two new render functions/sections; `summarize()` calls them.
- `tests/test_plan_summary.py`: coverage for both new sections (present, absent, mixed
  case, bullet-prefixed `OPEN:` lines, word-boundary name matching).
- `skill/phase2_planning.md`: trims the checkpoint bullet list from three items to one.
- No schema change -- both features read fields the schema already defines
  (`planning_notes`, `request_log`, `parts[].id`, `parts[].interfaces[].name`).
