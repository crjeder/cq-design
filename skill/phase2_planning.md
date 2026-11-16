# Phase 2: Planning

Starts only after the Phase 1 exit checkpoint is approved; user-corrected values win over
looked-up ones.

## Planner agent

Write `build/request.md`: the user's original request, the approved Phase 1 reformulation
(labelled as such), and each Phase 1 clarification verbatim with its UTC time. Then render:

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/render_prompt.py" planning \
    --request-file build/request.md [--plan BUILD_PLAN.json] [--profile profile.json]
```

Pass `--plan` only on a re-plan. It writes `build/planning_prompt.txt` and prints
`{"out", "chars", "profile"[, "profile_errors"]}`. When `profile` is not `loaded`, ask the
user for printer, material, nozzle, and constraints; do not open `profile.json`
yourself.

Spawn the `cq-design-planner` agent (fall back to `cq-design:planner` if the project agent is not offered) with `Read <out> in full and follow it. Working directory: <absolute cwd>.`
passing the render output's `agent_model` as the Agent tool's `model` (`models.planner`; a topology error here costs a rebuild of
every part). It has no user channel. It writes
`BUILD_PLAN.json` (indent 2) itself, runs `plan.py validate` itself, and retries against
its own validator errors internally (up to 3 attempts, same convention as the builder
agent in Phase 3) before returning its status contract (`status`, `parts`, `attempts`,
`open_items`, `error_summary`) as its final message -- never the plan JSON.

- `status: "valid"` -> proceed to the plan summary checkpoint below. (`plan.py validate`
  already journaled `phase2/plan_written`; do not append it.)
- `status: "blocked"` -> the agent exhausted its retries with validator errors remaining
  (`error_summary`). Summarize the errors to the user, get a decision, and resume the same
  planner agent with it -- never spawn a second planner. An `oracle: S<n> ...` error is an
  acceptance statement the plan could not bind or satisfy: quote the statement's `text`
  and ask whether to change the plan (resume the planner with the answer) or the intent
  (a correction: re-run the oracle as in Phase 1, then resume the planner).

The planning prompt lists `acceptance.json`'s statements (rule 18); the planner binds each
one in `acceptance_bindings`, and `plan.py validate` checks the bindings.

Read `BUILD_PLAN.json` from disk only if you need to inspect it yourself; the plan summary
checkpoint below reads it through `plan.py summary`, not through this session parsing the
agent's reply.

**`parameters.py`:** it is the single source of every dimension. Add a constant (origin tag
`# user`, `# researched: <source>`, `# assumed`, or `# design choice` for a clearance, gap or
wall allowance) for every number the plan needs that Phase 1 did not capture, and write
every `blocks_needed[].params` value that derives from one as an expression over those
names (`"w": "BASKET_RIM_OD_MM + GROOVE_CLEARANCE_MM"`), never as a hand-computed literal.
`plan.py validate` evaluates the expressions; an unknown name is an error.

**Printer profile write-back:** for each `printer`, `material`, `nozzle_mm`, or
`constraints` value that differs from `profile.json` and was not flagged as a
one-time exception:

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/printer_profile_validate.py" profile.json --set nozzle_mm=0.6 --set constraints.overhang_max_deg=50
```

and tell the user ("Updated profile.json: nozzle_mm -> 0.6").

## Vocabulary (all user-facing text in Phases 2 and 3)

- Spatial references use compass/up-down terms (North = +Y, East = +X, Up = +Z);
  left/right/front/back only when quoting the user.
- A partial revolution is a clock position on the view looking down the rotation axis
  (above <-> Z, South <-> Y, West <-> X), e.g. "swings to the 90° position in the above
  view" -- never "clockwise", whose sign flips between views. For an off-axis rotation,
  name the start and end reference features.

## Plan summary checkpoint

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/plan.py" summary BUILD_PLAN.json
```

Show its Markdown output (never raw JSON) -- it already includes **Names I chose** (every
part id / interface name not found in `request_log`), **Open questions** (every
`OPEN:` item in `planning_notes`), **Acceptance** (each oracle statement and the plan
entities bound to it), and **Load cases** (every part whose `load` declares
`magnitude_n`, with the source mass, safety factor, and resulting force -- see below) when
applicable. Then add:

- **Design proposals:** anything `planning_notes` proposes on the planner's initiative
  (e.g. `shadow_gap` on a visible seam), one line each, to accept or decline.

**Load cases:** every stress number the FEM advisor (Phase 3) produces scales linearly
with `magnitude_n`, and that value is a derivation (`mass_g * 9.81 / 1000 * safety_factor`,
see `reference/Engineering Design Rules.md`), not something the user stated. When the
**Load cases** table is present, confirm the source mass with the user alongside the rest
of the plan. If the user corrects the mass, resume the planner agent with the correction so
it re-derives `magnitude_n`, updates the `LOAD_MASS:` planning-note, and re-validates
`BUILD_PLAN.json`; then record the correction:

```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/log.py" request add BUILD_PLAN.json \
    --kind correction --text "<part> mass corrected to <value> <unit>" --level parameter --target <part>
```

Resolve each open question with the user, then resume the planner agent with the answers;
it re-writes and re-validates `BUILD_PLAN.json` itself and returns an updated status
contract. Re-run `plan.py summary` against the file before Phase 3.

Wait for approval or edits. If the user edited `BUILD_PLAN.json` on disk directly, run
`plan.py validate` on it yourself before proceeding (no agent involved for a user's own
edit). On approval:
```bash
uv run --project "$SKILL_DIR" python "$SKILL_DIR/src/pipeline.py" advance \
    phase2/plan_approved "<n> parts, review_policy <policy>"
```
