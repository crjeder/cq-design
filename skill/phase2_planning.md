# Phase 2: Planning

**Prerequisite:** The dimension validation checkpoint must be approved before this phase begins. If user-corrected values were provided during the checkpoint, use those values -- not the originally looked-up values -- when populating `BUILD_PLAN.json`.

Build the planning prompt from the template in `prompts/planning.md`. Substitute five placeholders:

| Placeholder | Source |
|-------------|--------|
| `{{USER_REQUEST}}` | User's full description of the part |
| `{{BLOCK_INVENTORY}}` | Condensed name + use lines from `src/blocks/inventory.json` |
| `{{ARCHETYPE_INDEX}}` | Condensed name + use lines from `templates/archetypes.json` |
| `{{FDM_GUIDELINES}}` | Sections tagged `always` from `reference/FDM 3D Print Design Guidelines.md` |
| `{{PRINTER_PROFILE}}` | `printer`/`material`/`nozzle_mm`/`constraints` from a validated `printer_profile.json` in the working directory, or a note that none is available |

## Planner agent

Spawn a single agent (Agent tool) whose prompt is the fully rendered `prompts/planning.md`
from above, model override: read `models.planner` from `skill_config.json` in the working
directory; if the file or key is absent, fall back to the strongest available model. A
topology or interface-tree error in the plan costs a full rebuild of every part downstream
of it, which is why this role defaults to the strongest model rather than the builder's
mid-tier default. The agent has no user
channel — everything user-facing (topology clarification, dimension checkpoint approval,
the plan summary below) already happened in main before this call, or happens in main
after it returns.

The agent returns the plan JSON as its final message. Parse it, write it to disk, and
validate exactly as below. **`plan_validate.py` rejection re-enters the planner agent**:
resume the same agent (not a fresh one) with the validator's error list as the next
message — it keeps its own reasoning and the rejected draft in context, so a targeted fix
is cheaper than a cold re-generation. Repeat until the plan validates or the loop needs a
user decision (e.g. a genuinely ambiguous schema conflict), in which case fall back to
asking the user in main.

Follow the planning prompt instructions to produce `BUILD_PLAN.json`. The plan must conform to `src/build_plan_schema.json`.

Write the plan to disk, then validate:

```python
import json
with open("BUILD_PLAN.json", "w", encoding="utf-8") as f:
    json.dump(plan, f, indent=2)
```

```bash
python "$SKILL_DIR/src/plan_validate.py" BUILD_PLAN.json
```

If the write fails (e.g. the working directory is not writable), surface the error and ask the user to confirm or change the working directory before continuing.

**Write `parameters.py`** at the project root alongside `BUILD_PLAN.json`: one module
documenting every real-world measurement this design is based on -- both what the user
stated directly and what came from web search (the Dimension validation checkpoint
table above, when that checkpoint ran). This is durable, human-readable provenance,
separate from each part script's own internal `PARAMETERS` block (which holds resolved/
derived geometry values, not necessarily the raw sourced ones) -- and separate from
`planning_notes`, which explains reasoning rather than listing values for reuse and
describes only the current design state (never a round-by-round changelog -- that
history belongs exclusively in `request_log`). One named constant per measurement,
each commented with its source:

```python
"""Sourced real-world measurements this design is based on.

Not imported by the build -- each part script carries its own resolved PARAMETERS
block. This file keeps the underlying real-world numbers and their sources visible
and easy to re-verify or update independent of how a part script used them.
"""

TV_BASE_WIDTH_MM = 385.0   # user-stated
IPHONE_15_PRO_WIDTH_MM = 70.6  # apple.com/iphone-15-pro/specs, confirmed vs. gsmarena.com
USB_C_PORT_MM = (9.0, 3.5)  # USB-IF spec, single-source
```

Include every dimension from the Dimension validation checkpoint table regardless of
its status (note `single-source`/`conflict`/`missing` in the comment as-is), plus any
measurement the user stated directly that never went through a web lookup at all. Skip
this file only when the design has no sourced real-world measurements whatsoever (e.g.
every dimension is an arbitrary design choice with no external reference).

**Printer profile write-back:** if the plan's `printer`, `material`, `nozzle_mm`, or any
`constraints` field differs from `printer_profile.json` and the user did not flag the value as
a one-time exception during Phase 1, write the changed field(s) back so the profile stays the
project default:

```bash
python "$SKILL_DIR/src/printer_profile_validate.py" printer_profile.json --set nozzle_mm=0.6
```

Repeat `--set` for each changed field (dotted for constraints, e.g.
`--set constraints.overhang_max_deg=50`). Announce the update to the user in the same turn
("Updated printer_profile.json: nozzle_mm -> 0.6"). Skip this step entirely when the plan
matches the profile, or when the user asked for a one-time exception.

**Vocabulary rules for all user-facing text in this phase (and Phase 3):**

- Use compass/up-down terms (North/South/East/West, up/down) for any spatial
  reference, per the coordinate table in `prompts/planning.md`. Use
  left/right/front/back only when directly quoting the user's own words.
- Describe a partial revolution (a hinge sweep, a dial or screw-pattern angular
  position) as a clock position on the view whose sight-line is the rotation
  axis -- above<->Z, South<->Y, West<->X (e.g. "swings to the 90° position in
  the above view") -- never as "clockwise"/"counterclockwise": right-hand-rule-
  positive rotation reads clockwise on South/West but counterclockwise on
  above, so a bare direction word has no axis-independent correct sign. For an
  axis not aligned to X/Y/Z, name the start and end reference features instead
  of a clock position.
- Every part id or interface name the planner coined (rule 2a in
  `prompts/planning.md`) -- i.e. not a word the user themselves used -- must be
  introduced explicitly in the summary below, e.g. "I'm calling the bottom part
  `base`." so the user can correct it before Phase 3 starts. A colliding user
  noun that got a disambiguating suffix is introduced the same way (state the
  mapping, e.g. "two features are both called `hole` -- the second is `hole_2`").

Display a human-readable Markdown summary of the validated plan (do not show raw JSON in chat) and confirm the write path using the absolute path:

> Written to: `/absolute/path/to/BUILD_PLAN.json`

(Use `os.path.abspath("BUILD_PLAN.json")` or `Path("BUILD_PLAN.json").resolve()` to obtain the absolute path before displaying it.)

The summary must include:

**Printer / Material**

| Printer | Material | Nozzle |
|---------|----------|--------|
| `<printer>` | `<material>` | `<nozzle_mm>` mm |

**Parts**

| # | ID | Description | W x D x H (mm) | Orientation | Load | Blocks |
|---|-----|-------------|----------------|-------------|------|--------|
| 1 | ... | ... | ... x ... x ... | ... | ... | ... |

(The `Load` column shows each part's `load.dir` hint (plus `load.type` when it differs
from the `tension` default, e.g. `compression`), or `inferred` when the part omits it —
it drives print-orientation strength scoring.)

**Print optimization**

State the plan-level `optimize_for` (`strength` default, `min_support`, or
`visual_quality`) and call out any part that overrides it. For `visual_quality`, note each
part's `show_face.dir` (or `inferred`). This is the objective the print-orientation step
uses.

**Review policy**

State the plan's effective `review_policy` (`every_stage` default, `checkpoints`, or
`minimal`) and one line on what it means for this build: `every_stage` -- every part
shows a Step 0 profile-stub checkpoint and builds progressively with per-stage
checkpoints; `checkpoints` -- every part shows the stub checkpoint, but only parts
matching the complexity gate (an interface, or 3+ blocks) build progressively; `minimal`
-- the stub is self-reviewed with no pause and every part builds autonomously with no
stage checkpoints. This is the setting the Phase 3 part loop reads to decide when to
pause for review.

**Interfaces** (omit section if no part has any interfaces)

| Part | Name | Type | Connector | Wall | Position (mm) |
|------|------|------|-----------|------|---------------|
| ... | ... | ... | ... | ... | ... |

(The `Name` column is the agreed vocabulary word -- `interfaces[].name` verbatim,
whether it came from the user or was coined by the planner and introduced above.
This table is what the checkpoint preview's callout legend will echo once a
callout-annotated render exists, so names here should match exactly.)

**Constraints**

| Wall min | Overhang max | Dim tolerance |
|----------|-------------|---------------|
| `<wall_min_mm>` mm | `<overhang_max_deg>` deg | `<dimension_tolerance_mm>` mm |

**Design proposals** (omit section if `planning_notes` proposes nothing)

Surface any proposal the planning step made on its own initiative — most commonly the
`shadow_gap` block (`blocks.joints`) on a visible multi-part seam (see
`prompts/planning.md` rule 12) — as an explicit line the user can accept or decline,
e.g.:

> Proposed: `shadow_gap` along the quadrant seams (visible on the finished piece) —
> a return-lip on the front member with a ~1 mm reveal, so fit tolerance shows as a
> deliberate line instead of a raw gap. Reply to decline for a flush seam.

Do not let this sit silently inside `planning_notes` where the user won't see it —
it must appear in the chat-visible summary.

After displaying the summary, wait for the user to approve or request edits. If the user edits `BUILD_PLAN.json` on disk before confirming, re-validate from disk before proceeding to Phase 3.
