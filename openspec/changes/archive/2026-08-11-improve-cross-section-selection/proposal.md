## Why

`--extra-section` cuts already exist and replace the useless bbox-centerline fallback
(the one place on a hollow box guaranteed to show air), but `skill/phase3_build.md`
only tells the part author to add one *conditionally* ("if this part unions a feature
into a body that already has a cavity..."). That judgement call gets skipped under
load, so the fallback fires anyway and cross-section previews stay uninformative
(TODO.md line 17). The user's ranking -- clarification-flagged features first,
user-complained features second, everything else third -- has no mechanism: nothing
turns `request_log.text` prose into a feature name plus a cut coordinate.
`add-interface-name-field` (shipped) closed that gap by letting `interfaces[]` declare
a `name`, so a name<->position join is now possible via `request_log_search.py`.

## What Changes

- Turn `skill/phase3_build.md`'s `--extra-section` guidance from a conditional
  ("if this part unions a feature...") into an unconditional rule: every named+
  positioned `interfaces[]` entry gets a `--extra-section` cut, same list already
  used to build `--callout`.
- Order and cap that cut list before passing it to `render_preview.py`:
  1. features named in a `request_log` entry with `kind: clarification`
  2. features named in a `request_log` entry with `kind: correction`
  3. all other named+positioned interfaces
  within a tier, most recent `request_log` entry first (append-only order already
  gives recency for free). Matching a feature to a `request_log` entry is a
  `request_log_search.py <name>` substring lookup against `text` (the shared
  vocabulary that `add-interface-name-field` established), not new NLP.
  Cap the resulting cut list at a fixed budget (3, matching today's fallback cut
  count) so a part with many interfaces doesn't flood the tile.
- `axis` selection per cut: the axis normal to the interface's `wall` field when
  present, else all three axes are no longer cut -- pick the axis matching the
  interface's declared `position_mm` component with the largest magnitude relative
  to the part bbox center (a cheap deterministic default; document the choice in
  design.md rather than leaving it to author judgement).
- Fallback (bbox-centerline cuts) only fires when a part has zero named+positioned
  interfaces -- unchanged mechanically, just now the true last resort instead of the
  common case.

## Capabilities

### New Capabilities
(none -- this changes selection policy for an existing capability, no new spec area)

### Modified Capabilities
- `preview-cross-sections`: the fallback-vs-declared-positions selection rule changes
  from caller-optional to caller-mandatory-when-available, with a defined priority
  order and cap instead of "when supplied".

`preview-feature-callouts` is unaffected (its `--callout` list stays plan-order,
unchanged) -- this change reuses that list as an input for section-cut ranking but
does not alter callout behavior.

## Impact

- `skill/phase3_build.md`: Step 3 section guidance (~lines 317-345) becomes a rule,
  not a conditional; adds the priority-ordering/cap procedure.
- `src/request_log_search.py`: used as-is (keyword lookup), no code change expected.
- No schema change (`interfaces[].name` already shipped).
- Affects future part-authoring sessions' preview quality; no change to
  `render_preview.py`/`run_cadquery_model.py` internals (the `--extra-section`
  plumbing already exists and is unchanged).
