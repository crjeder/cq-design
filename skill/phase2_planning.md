# Phase 2: Planning

Starts only after the Phase 1 exit checkpoint is approved; user-corrected values win over
looked-up ones.

## Planner agent

Write `build/request.md`: the user's original request, the approved Phase 1 reformulation
(labelled as such), and each Phase 1 clarification verbatim with its UTC time. Then render:

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/render_prompt.py" planning \
    --request-file build/request.md [--plan BUILD_PLAN.json] [--profile printer_profile.json]
```

Pass `--plan` only on a re-plan. It writes `build/planning_prompt.txt` and prints
`{"out", "chars", "profile"[, "profile_errors"]}`. When `profile` is not `loaded`, ask the
user for printer, material, nozzle, and constraints; do not open `printer_profile.json`
yourself.

Spawn one agent with `Read <out> in full and follow it. Working directory: <absolute cwd>.`
on `models.planner` from `skill_config.json` (absent: the strongest available model -- a
topology error here costs a rebuild of every part). It has no user channel and returns the
plan JSON as its final message. Write that to `BUILD_PLAN.json` (indent 2), then:

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/plan_validate.py" BUILD_PLAN.json
```

On rejection, resume the same planner agent with the error list; repeat until it validates
or needs a user decision. Then:
```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/journal.py" append build/journal.md \
    phase2/plan_written "BUILD_PLAN.json validated, <n> parts"
```

**`parameters.py`:** add or amend a sourced constant (with its source comment) only when
planning introduced a real-world measurement Phase 1 did not capture.

**Printer profile write-back:** for each `printer`, `material`, `nozzle_mm`, or
`constraints` value that differs from `printer_profile.json` and was not flagged as a
one-time exception:

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/printer_profile_validate.py" printer_profile.json --set nozzle_mm=0.6 --set constraints.overhang_max_deg=50
```

and tell the user ("Updated printer_profile.json: nozzle_mm -> 0.6").

## Vocabulary (all user-facing text in Phases 2 and 3)

- Spatial references use compass/up-down terms (North = +Y, East = +X, Up = +Z);
  left/right/front/back only when quoting the user.
- A partial revolution is a clock position on the view looking down the rotation axis
  (above <-> Z, South <-> Y, West <-> X), e.g. "swings to the 90° position in the above
  view" -- never "clockwise", whose sign flips between views. For an off-axis rotation,
  name the start and end reference features.

## Plan summary checkpoint

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/plan_summary.py" BUILD_PLAN.json
```

Show its Markdown output (never raw JSON) -- it already includes **Names I chose** (every
part id / interface name not found in `request_log`) and **Open questions** (every
`OPEN:` item in `planning_notes`) when applicable. Then add:

- **Design proposals:** anything `planning_notes` proposes on the planner's initiative
  (e.g. `shadow_gap` on a visible seam), one line each, to accept or decline.

Resolve each open question with the user, then resume the planner agent with the answers;
it re-writes and re-validates `BUILD_PLAN.json` itself and returns an updated status
contract. Re-run `plan_summary.py` against the file before Phase 3.

Wait for approval or edits. If the user edited `BUILD_PLAN.json` on disk directly, run
`plan_validate.py` on it yourself before proceeding (no agent involved for a user's own
edit). On approval append `- phase2/plan_approved: <n> parts, review_policy <policy>` to
`build/journal.md`.
