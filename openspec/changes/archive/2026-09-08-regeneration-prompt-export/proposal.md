## Why

A finished project is delivered as a self-contained uv project: the geometry rebuilds
from `build/build.py` without the skill installed. What does *not* survive the session is
the design's origin -- why the part is shaped this way, what the user actually asked for,
which numbers were measured off real hardware, which sketch a face was drawn from. Those
live in `BUILD_PLAN.json`'s `intent` and `request_log`, in `parameters.py`, and in
`sketches/`, spread across four artifacts in three formats.

So the one thing a user cannot do today is the thing the tooling improves fastest:
re-run the same design brief against a better model, a newer version of this skill, or a
different skill entirely. Doing it by hand means re-reading the plan JSON and
re-narrating the request, which loses exactly the verbatim wording and the stated
assumptions that made the first run correct.

`TODO.md` has tracked this as "export a project-regeneration prompt for a fresh LLM
session"; `documentation/intent_recognition.md` item 4 identifies it as the export half
of the same artifact the `approved-intent` capability produces. That capability made
`intent` a durable, user-approved, current-state reformulation -- which is what makes a
mechanical export worth writing now: there is finally a single field that states what is
being built.

## What Changes

- New `src/regen_prompt.py` (stdlib only) serializes a finished project's intent
  artifacts into one Markdown file: the approved `intent`, the verbatim `request_log`
  with each entry's `level`/`targets`/`images`, `parameters.py` inlined whole, the
  `sketches/` file list, the print target, and the parts/joints decomposition.
- Phase 4 gains a step: run the script to write `REGENERATE.md` at the project root, on
  every delivery, overwriting the previous copy. The orchestrator does not hand-author
  the file.
- The decomposition section is labelled reference-only. Regenerating is worth doing
  precisely because the new session may decompose the request better; a prompt that
  reads as "build these parts" would defeat its own purpose.
- `README.md` (the delivered one, written by Phase 4) points at `REGENERATE.md`.
- The file is a snapshot, not a build dependency: it is **not** bundled into `lib/`, and
  nothing in the pipeline reads it back.

## Impact

- Additive. No schema change, no existing artifact's contents change, no phase before 4
  is touched.
- The export is only as good as `intent`: a plan whose `intent` was never rewritten by a
  Phase 3 correction produces a stale prompt. That is a defect in the existing
  intent-rewrite rule, surfaced rather than introduced -- Phase 4 reads the exported file
  before reporting, and fixes `intent` rather than the export.
- Images cannot be inlined into a Markdown prompt. The prompt names their paths and tells
  the user to re-attach them.

## Capabilities

### New Capabilities
- `regeneration-prompt`: the delivered `REGENERATE.md` -- what it must carry (approved
  intent, verbatim request history, sourced measurements, drawing references, print
  target), how the previous decomposition is framed, when it is regenerated, and the
  omit-when-absent rule for optional sections.
