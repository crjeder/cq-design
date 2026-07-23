## Why

Part scripts recurrently place a feature's contact face at a coordinate that means
"centerline/axis of the thing it attaches to," when the neighboring solid actually needs
to reach that face's *edge* -- off by exactly half the neighbor's thickness, in whichever
direction happens to matter for structural integrity. Observed in production: the C5
Phone-Holder's hinge-knuckle standoff (`build/cradle.py`) went through three user-visible
correction rounds before the leg was extended to fully back the standoff post; the
attaching feature had partially overlapped it, requiring a live user to notice a "brittle"
joint. `verify_feature_bounds` cannot catch this shape of defect: the standoff's overflow
was intentional on the axis where a new feature is meant to rise off its base (Z), and
incidental on the axis where support was missing (Y) -- an all-axis overflow check can't
tell those apart. A prior design ("Mating area (2D footprint)",
`openspec/changes/archive/2026-07-01-joint-contract/design.md:412-421`) named this exact
problem -- "a mate area MUST be touched by a to-print object in its own union... the
connection surface is realized by real material, not floating" -- for the *inter-union*
joint case, but was captured as exploratory and never implemented; grepping `src/`,
`templates/`, `prompts/` for `mating_area`/`backed_by_material` returns nothing.

This change ports the same vocabulary and rule one level down: **intra-part**, at
construction time, before a part's features are even unioned into a printable body --
buildable today without the archived design's still-open cruxes (satisfaction algebra,
sub-body naming), which belong only to the inter-union half.

## What Changes

- Add `verify_backed(backer, feature, face_normal, label, tolerance)` to `src/cq_verify.py`:
  the author names a face of `feature` as its mating area and declares which solid must
  back it; the helper projects that face's footprint onto the contact plane and raises a
  marked `RuntimeError` (mapped by `run_cadquery_model.py` to a typed `unbacked_mate`
  error) if the footprint is not fully contained in `backer`'s cross-section there.
  Mirrors `verify_boolean`/`verify_feature_bounds`'s before/after, return-the-argument
  contract so it sits inline in a construction chain.
- Extend `prompts/part.md`'s "Construction-time verification" section (and `SKILL.md`'s
  generated-script rules) with guidance on when to declare a mating area: a standoff,
  boss, rib, ear, or other feature that must be fully backed by a *named neighboring
  feature* at a specific face, as distinct from a feature that legitimately extends past
  its base on other axes.
- Note the concept's continuity with the archived block-level "mating area" design in
  `TODO.md`, flagged as the open crux for a later change: does the intra-part face+backer
  check generalize upward into the inter-union, block-declared mating area (row 2 of the
  archived design's classification table), or does it stay a separate, narrower mechanism
  that happens to share a name and a rule ("backed by material")?

## Capabilities

### New Capabilities

(none -- this extends an existing capability)

### Modified Capabilities

- `runtime-boolean-verification`: adds the `verify_backed` assertion and its typed
  `unbacked_mate` error to the `cq_verify.py` helper contract; extends the
  generated-script guidance requirement to cover when a mating area should be declared.

## Impact

- `src/cq_verify.py` -- new `verify_backed` function.
- `src/run_cadquery_model.py` -- map the new marked error kind (`unbacked_mate`) the same
  way `silent_boolean`/`feature_overflow`/`workplane_drift` are mapped today.
- `prompts/part.md`, `SKILL.md` -- new guidance section/examples.
- `tests/test_run_wrapper.py` (or a new `test_cq_verify.py`) -- coverage for the new
  helper, mirroring existing `verify_boolean`/`verify_feature_bounds` test patterns.
- `TODO.md` -- note recording the open crux (intra-part vs. inter-union generalization)
  for the still-shelved block-level mating area design.
- No schema changes (`build_plan_schema.json`, `inventory_schema.json` untouched) --
  this is a script-level assertion, not a plan or block declaration.
