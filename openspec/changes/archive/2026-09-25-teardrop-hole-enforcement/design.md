## Context

Blocks exist (`src/blocks/connectors.py`, `inventory.json`) and the FDM guideline reference documents them, but the builder prompt and gates never point at them. Print orientation is chosen after authoring, so the lint cannot know the true pose.

## Goals / Non-Goals

**Goals:** make the teardrop blocks discoverable at authoring time; make hand-rolled horizontal holes visible.
**Non-Goals:** blocking gates, mesh-based bore detection, changing print orientation choice, auto-rewriting scripts.

## Decisions

- **Advisory AST lint keyed on the authored frame** (side-facing workplane + `hole`/`circle().cut*`). Alternative: detect bore roofs in the print-posed mesh; rejected as costly and duplicative of `overhang_metrics`. Authored frame is a heuristic, hence advisory, same tier as `magic_number`.
- **Prompt rule over new gate**: cheapest fix for the root cause (builder never told).
- **Hint only in the gate**: no new finding type, so the JSON contract is untouched.

- **Peak direction is a print-pose fact.** `_drop_profile` already supports `apex="down"`; expose it as `peak` on `teardrop_bore`. Sideways print-up needs a builder-side rotation of the cutter, stated in the prompt rule. Alternative: auto-derive from the print orientation; rejected, orientation runs after authoring.

## Risks / Trade-offs

- [False positives when print pose differs from authored pose] -> advisory only; message says "if this axis is horizontal at print pose".
- [Blocks assume axis +Y, peak +Z] -> prompt rule reminds to orient the cutter via existing placement helpers.
