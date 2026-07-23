# Proposal: shared-feature-vocabulary

## Why

At review checkpoints the user and the LLM talk about the same geometry with different
words: the LLM speaks plan-internal snake_case ids it coined itself, the user speaks
their own nouns ("the handle") and ad-hoc spatial phrases, and the preview tile labels
its panels with a third vocabulary ("Front, Left side") that contradicts the documented
compass convention (USE.md, prompts/planning.md, prompts/part.md). Every mismatch costs
a clarification round-trip or, worse, a silently mis-applied fix on a full re-render
cycle. The goal is an agreed vocabulary: when the user says "make the handle bigger",
both sides already know exactly which feature "the handle" is.

## What Changes

- **User nouns become plan names.** When the user has named a thing in their request or
  during conversation, that word becomes the part id / interface name in
  `BUILD_PLAN.json` (`handle`, not a synonym the LLM prefers). The LLM only coins names
  for things the user never mentioned and must introduce them explicitly at the plan
  checkpoint.
- **Annotated preview glossary.** The preview tile gains a deterministic callout
  overlay: number badges with leader lines at each named feature's projected position
  (from `interfaces[].position_mm`), plus a legend mapping badges to plan names. No
  vision or LLM drawing involved -- pure 3D-to-2D projection with the panel's known
  camera. The checkpoint render becomes the ratification artifact for the vocabulary.
- **Compass-consistent artifacts and prose.** Preview panel labels change from
  "Front / Left side / Top" to compass terms matching the documented convention
  (North/South/East/West/Top), derived from each panel's actual camera direction. The
  skill's checkpoint prose gets an enforcement rule: all user-facing spatial references
  use compass/up-down terms; left/right/front/back only when quoting the user.
- **Echo-back confirmation.** Before acting on a spatial or ambiguous feature
  reference from the user, the LLM restates it in agreed names ("'the slot on the
  left' -- I read that as `cable_slot` (2), correct?").

## Capabilities

### New Capabilities

- `feature-vocabulary`: the naming contract -- user nouns flow into plan names, coined
  names are introduced explicitly, spatial prose uses the compass convention, ambiguous
  references are echoed back in agreed names before acting.
- `preview-feature-callouts`: the deterministic callout overlay -- badge + leader-line
  annotation of named features on the preview tile from plan-declared positions, with a
  badge-to-name legend.

### Modified Capabilities

- `cq-preview-rendering`: panel labels change from "Front / Left side / Top" to
  compass-convention names derived from the actual camera direction (spec currently
  mandates the old labels verbatim).
- `planning-phase`: part ids and `interfaces[].name` values must reuse the user's own
  nouns when the user has named the thing; the plan summary's interfaces table shows
  these agreed names.

## Impact

- `src/preview.py` -- callout overlay (project 3D positions per panel, draw badges +
  leaders + legend), panel label rename.
- `src/render_preview.py` -- new repeated `--callout` flag (name + authored-frame
  center), threaded like the existing `--extra-section` plumbing.
- `src/run_cadquery_model.py` -- pass-through of callout specs to the renderer.
- `prompts/planning.md` -- user-noun naming rule.
- `skill/phase2_planning.md`, `skill/phase3_build.md` -- vocabulary ratification at
  checkpoints, compass-only prose rule, echo-back confirmation rule, threading of
  interface names/positions into preview calls.
- `tests/test_preview.py` -- overlay + label coverage.
- Overlaps TODO.md's intra-part-anchors item only at its open question (3) ("archetype
  anchor sets as shared vocabulary for visual review"); no anchor machinery is built
  here. Unnamed geometry (walls, ribs) stays unnamed -- out of scope.
