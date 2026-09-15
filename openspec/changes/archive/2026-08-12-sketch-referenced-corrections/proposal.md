## Why

Correction rounds are sometimes driven by an annotated image (a hand-drawn sketch, a
screenshot with markup) rather than words alone -- observed in the C5 Phone-Holder
session (rounds 5-7, `ear-placement.png`, `hinge-ear.png`, `C5 Aschenbecher-annotated.jpg`).
Today `request_log` is text-only, so the image itself has no durable place in the plan:
that session kept the files in the project root and referenced them ad hoc from
`part_notes`, which is exactly the free-text drift the `request_log` schema exists to
prevent (see `bound-planning-notes`). Nothing tells a later build attempt, an escalation,
or a re-plan that a sketch exists or where to find it.

## What Changes

- `request_log` entries gain an optional `images` field: an array of repo-relative paths
  to sketch/annotated-image files that motivated that entry.
- A `sketches/` directory convention: when the user attaches an image to a clarification
  or correction, the orchestrator copies it into `sketches/` under a stable name and
  records that path in the new `request_log` entry's `images` field.
- `skill/phase3_build.md`'s Request log section is extended to prescribe this copy step,
  and to instruct that when iterating on a feature during a correction round or
  Escalation, the orchestrator re-reads any sketch referenced by the relevant
  `request_log` entry before re-authoring -- the same "read before you re-render"
  discipline already prescribed for preview renders, applied to user-supplied sketches.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `request-log`: `request_log` entries may carry an optional `images` array of
  repo-relative sketch paths; the orchestrator copies referenced images into `sketches/`
  and re-reads them when iterating on the feature they annotate.

## Impact

- `src/build_plan_schema.json`: `request_log` entry schema gains optional `images`.
- `skill/phase3_build.md`: Request log section (copy-in + re-read guidance).
- New `sketches/` directory convention (created on first use, not scaffolded).
- No change to `src/plan_validate.py`'s existing request_log validation logic (single
  `initial` entry, append-only) beyond accepting the new optional field.
