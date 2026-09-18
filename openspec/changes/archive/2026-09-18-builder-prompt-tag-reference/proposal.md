## Why

Every part prompt injects the full `CadQuery Pattern Reference.md` +
`CadQuery Anti-Patterns.md` (~24K chars) unconditionally, unlike the FDM and
Engineering guides, which are already tag-filtered to the part's
`blocks_needed`. Part of that unconditional payload is now redundant:
`script_lint.py` mechanically detects several of the exact mistakes the
Anti-Patterns doc describes (boolean-in-a-loop, a feature placed on a
workplane an unresolved `.center()`/`.hole()` shifted) and reports them as
typed findings with fix hints during the correction loop — so every part pays
prose-explanation cost for mistakes the lint already explains only when they
actually happen.

## What Changes

- Remove or fold down Anti-Patterns sections whose failure mode
  `script_lint.py` already detects and explains via a typed finding + hint
  (`boolean_in_loop`, `unanchored_feature`); keep a short pointer to the lint
  check in place of the full worked example.
- Add `<!-- applies_to: block1, block2 -->` / `always` section tags to
  `CadQuery Pattern Reference.md` and `CadQuery Anti-Patterns.md`, using the
  same vocabulary as `FDM 3D Print Design Guidelines.md` /
  `Engineering Design Rules.md`.
- Wire `render_prompt.py`'s cold-context `CQ_REFERENCE` substitution through
  `tagged_sections()` (selecting `always` sections plus sections matching the
  part's `blocks_needed`), instead of concatenating both files' full text
  unconditionally.
- Extend the inline-render citation to name only the selected section titles,
  matching how `FDM_GUIDELINES`/`ENGINEERING_RULES` already cite.
- Validate with an eval sweep (`evals/run_evals.py --generate`) that first-shot
  rate and attempts-to-pass hold, per this capability's existing
  condensation-validation requirement.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `reference-injection`: `{{CQ_REFERENCE}}` selection becomes tag-filtered by
  `blocks_needed` (like `{{FDM_GUIDELINES}}`/`{{ENGINEERING_RULES}}`) instead
  of always-full-text; lint-duplicated Anti-Patterns content is removed.

## Impact

- `reference/CadQuery Pattern Reference.md`, `reference/CadQuery Anti-Patterns.md`
  — section tags added, lint-duplicated sections trimmed.
- `src/render_prompt.py` (`part_spec()`) — `CQ_REFERENCE` built via
  `tagged_sections()` instead of unconditional concatenation.
- `openspec/specs/reference-injection/spec.md` — requirements updated for
  tag-filtered CQ reference selection.
- `evals/` — one validation sweep to confirm no first-shot/attempts regression.
