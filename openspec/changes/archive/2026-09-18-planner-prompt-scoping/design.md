## Context

`render_prompt.py`'s `tagged_sections(md, blocks, extra_titles)` walks `## `-delimited
sections of a reference doc and keeps a section if its `<!-- applies_to: ... -->` tag set
contains `always`, intersects `blocks`, or its title is in `extra_titles`. Both
`render_builder` (part prompts) and `render_planning` (planner prompt) call it against
`reference/FDM 3D Print Design Guidelines.md`, both hard-coding the `always` scope. The
builder needs `always` (every part-authoring section applies regardless of blocks). The
planner does not: it is deciding part count, splits, materials, and interfaces, not
modeling mechanics like chamfer sizing, cosmetic-slope avoidance, or vase mode.

Similarly, `skill/phase0_sourcing.md` (read into the main session every Phase 0 run)
carries the full license-reusability rule set even though the Sourcing agent already
reads each candidate's license off its source page — the main session re-derives a
verdict from a raw string the agent could compute itself.

## Goals / Non-Goals

**Goals:**
- Cut planner-prompt FDM content to the sections that inform BUILD_PLAN-level decisions.
- Move license-reusability derivation to the agent that already has the source page in
  context, shrinking `skill/phase0_sourcing.md`.
- Keep the builder/part prompt's FDM section selection unchanged (still `always` +
  block-matched).

**Non-Goals:**
- Not condensing the FDM guidelines file's byte size (that's the separate "Injected
  CadQuery references carry only non-recallable content" track for the CQ pattern/anti-
  pattern docs). No section is deleted from disk; the `planning` tag only narrows what
  the *planner* render selects. The "reference cuts backed by attempt-history evidence"
  and "validated by an eval sweep" requirements govern content *removal*, which this
  change does not do.
- Not changing the five-rung ladder logic, `measure_stl.py` vetting, or provenance
  recording (what gets recorded and shown to the user is unchanged; only who derives the
  reusability verdict moves).
- Not touching `reference/Engineering Design Rules.md`'s tag scheme (out of scope; the
  user's request named the FDM guidelines file specifically).

## Decisions

### 1. Additive `planning` tag, not a second file or a scope rewrite

Add `planning` as an additional tag value on the 4 sections that matter for planning
(`Baseline & Tolerances`, `Print Orientation`, `Strength & Load Orientation`, `Make It
Adjustable (Tolerance Compensation)`), e.g. `<!-- applies_to: always, planning -->`.
`tagged_sections` gains a `scope: str = "always"` parameter; `render_builder` keeps
calling it with the default, `render_planning` passes `scope="planning"`. Block-matched
inclusion (`tags & blocks`) is untouched in both callers.

Alternatives considered:
- **Separate `reference/FDM Planning Guidelines.md` file** — rejected: duplicates content
  that must stay in sync with the builder-facing file; the tag approach keeps one source
  of truth.
- **Invert the default (untag planner-irrelevant sections)** — rejected: the file's own
  header docs the tag contract as "always or a block name"; adding a third generic value
  a maintainer must remember for every new section is more error-prone than opting in the
  4 sections that need it, which are unlikely to grow.

Which sections get `planning`, and why:
| Section | Planning-relevant because |
|---|---|
| Baseline & Tolerances | clearance/accuracy numbers feed interface dimensioning |
| Print Orientation | the "no orientation satisfies both → split the part" rule is a BUILD_PLAN structural decision |
| Strength & Load Orientation | `load.type` declaration is a BUILD_PLAN field (`schema` / `print_orientation.py --load-type`) |
| Make It Adjustable | explicitly instructs proposing `shadow_gap` "during planning" by default |

Sections left `always`-only (builder path unaffected): Basic Dimension Rules, Wall
Thickness, Chamfer/Fillet, Cosmetic Slopes, Press Fits & Interference, Avoiding Support
Material, Print-in-Place & Flexures, Text & Surface Finish, Warping Resistance, Vase
Mode — all modeling-mechanics guidance the part author applies while cutting a script,
not the planner while sizing/splitting parts.

### 2. Sourcing agent computes the reusability verdict, main session trusts it

`prompts/sourcing.md`'s return contract gains a `Reusable` column. The agent already
reads the license text off the source page (existing rule: "Record the license exactly
as stated"); it now also applies the same fixed rule set (moved from
`skill/phase0_sourcing.md`'s License check section into `prompts/sourcing.md`) to
classify each candidate: `yes`, `no (all-rights-reserved / none stated)`, `no (ND)`, or
`rung-3-only (ND, redistribution permitted)` / `rung-3-only (ND, file not
redistributable — link only)`. `skill/phase0_sourcing.md`'s License check section is
replaced with: trust the `Reusable` column; a rung fails if its candidate's verdict says
so; still record license/URL/rung in `planning_notes` or the delivery summary
(unchanged).

The agent still does not choose the rung itself (unchanged constraint in
`prompts/sourcing.md`: "Do not classify candidates onto the five-rung ladder yourself") —
license reusability and rung classification are separable judgments; the agent handles
the former (it has the page), the main session still does the latter (it has the full
candidate set and the request context to compare against).

Alternatives considered:
- **Leave license derivation in the main session, just compress the prose** — rejected:
  doesn't remove the duplicated reasoning step; the agent has strictly more information
  (the actual page) than the string it currently hands back.
- **Have the agent choose the rung too** — rejected: `sourcing-triage`'s existing
  "collect then classify" design deliberately keeps rung selection in the main session so
  a better candidate found later doesn't get pre-empted by an agent that classifies as it
  goes; out of scope for this change and not requested.

## Risks / Trade-offs

- [Sourcing agent misapplies a license rule without the main session's ladder context to
  catch it] → The rule set is small and mechanical (no license → not reusable; ND →
  blocks rungs 1/2/4; rung-3 ND exception) and moves verbatim from the existing
  `phase0_sourcing.md` prose, not reauthored; `tests/test_render_prompt.py` gets a
  fixture asserting the rendered sourcing prompt contains the rule text and the
  `Reusable` column header.
- [A future contributor adds an `## ` section to the FDM guidelines file and forgets the
  `planning` tag] → Matches the existing risk for `always` vs block tags already accepted
  by `reference-injection`'s "malformed or missing tag → excluded" rule; no new failure
  mode.
- [Existing `--plan` planner reruns mid-Phase-2 lose previously-`always`-only sections
  they may have relied on informally] → Builder/part rendering is unaffected (still
  `always`); only the planner's own prompt shrinks, and the planner does not author
  geometry, so modeling-mechanics sections were never actionable there.

## Migration Plan

1. Tag the 4 sections in `reference/FDM 3D Print Design Guidelines.md`.
2. Add `scope` param to `tagged_sections`; switch `render_planning`'s call site.
3. Move license-rule prose into `prompts/sourcing.md`; add `Reusable` column to its
   return-contract table and example row; shrink `skill/phase0_sourcing.md`'s License
   check section to the trust-the-verdict form.
4. Update `tests/test_render_prompt.py` (planning FDM selection assertions) and any
   sourcing-prompt fixture/test for the new column and moved rule text.
5. No feature flag or rollback complexity — single-repo prompt/doc change; a revert is a
   plain `git revert` if evals regress.

## Open Questions

None — scope confirmed by the user's numbered request (planner FDM tagging, Phase 0
license move).
