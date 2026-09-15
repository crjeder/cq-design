## Why

`skill/phase1_requirements.md` states the same rule twice in three separate
places: the `-1` placeholder ban appears once in "Ask vs. assume" and again
in the exit checkpoint's "Approval" section; the "one approval, not two
rounds" rule is stated, then immediately restated one paragraph later; and
the topology section spends two lines re-explaining a relationship to the
exit checkpoint that the exit checkpoint section already covers on its own.
This repetition costs context budget on every Phase 1 read and creates two
places a future edit must find and keep in sync.

## What Changes

- Remove the second statement of "no `-1` may leave Phase 1" from the exit
  checkpoint's Approval section, keeping the single statement in "Ask vs.
  assume" and having Approval reference it instead of repeating it.
- Collapse the two adjacent "one approval, not two rounds" sentences in the
  Phase 1 exit checkpoint intro into one.
- Trim the topology section's two-line aside about its relationship to the
  exit checkpoint, keeping only the ordering fact needed (topology confirms
  before dimension lookups), since the exit checkpoint section already
  describes itself as the single gate out of Phase 1.
- Add a `skill-doc-structure` requirement that a `skill/phase*.md` file must
  not state the same rule twice within itself, matching the existing rules
  against restating content from other guaranteed-in-context or
  code-enforced sources.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `skill-doc-structure`: add a requirement that a phase file does not
  restate the same substantive rule more than once within itself.

## Impact

- `skill/phase1_requirements.md` — three trims, no content removed that
  isn't a repeat.
- No code, schema, or script changes; no behavior change to the pipeline.
