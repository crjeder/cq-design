# Phase 2: Planning

**Prerequisite:** The dimension validation checkpoint must be approved before this phase begins. If user-corrected values were provided during the checkpoint, use those values -- not the originally looked-up values -- when populating `BUILD_PLAN.json`.

Build the planning prompt from the template in `prompts/planning.md`. Substitute four placeholders:

| Placeholder | Source |
|-------------|--------|
| `{{USER_REQUEST}}` | User's full description of the part |
| `{{BLOCK_INVENTORY}}` | Condensed name + use lines from `src/blocks/inventory.json` |
| `{{FDM_GUIDELINES}}` | Sections tagged `always` from `reference/FDM 3D Print Design Guidelines.md` |
| `{{PRINTER_PROFILE}}` | `printer`/`material`/`nozzle_mm`/`constraints` from a validated `printer_profile.json` in the working directory, or a note that none is available |

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
`planning_notes`, which explains reasoning rather than listing values for reuse. One
named constant per measurement, each commented with its source:

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

**Interfaces** (omit section if no part has any interfaces)

| Part | Type | Connector | Wall | Position (mm) |
|------|------|-----------|------|---------------|
| ... | ... | ... | ... | ... |

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
