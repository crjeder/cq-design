## Context

`render_prompt.py`'s `part_spec()` builds `{{CQ_REFERENCE}}` by concatenating
the full text of `reference/CadQuery Pattern Reference.md` (15,889 bytes) and
`reference/CadQuery Anti-Patterns.md` (8,684 bytes) unconditionally, for every
part, in cold-context mode. `{{FDM_GUIDELINES}}` and `{{ENGINEERING_RULES}}`
already go through `tagged_sections()`, which keeps a `##` section only if its
`<!-- applies_to: ... -->` comment is `always`, names one of the part's
`blocks_needed`, or is in an `extra_titles` set (used today for load-bearing
and hinge sections).

`script_lint.py` (added 2026-07-15, unchanged since) mechanically detects,
among others, `boolean_in_loop` and `unanchored_feature` (an unresolved
`.center()`/`.hole()` origin shift followed by a placement call) and returns
each as a typed finding with a fix `hint`, before any CadQuery subprocess
runs. Two `CadQuery Anti-Patterns.md` sections narrate exactly these two
mistakes: "Booleans are expensive -- never loop them" (Tier 1) and "Origin
drift after `.center()`" (Tier 2). The second duplicates
`reference/CadQuery Pattern Reference.md`'s "Workplane Context Stacking
(Origin Drift)" section almost line for line (both documents already
cross-reference the other's version).

**Prior decision on the record:** the 2026-08-09 `condense-references` change
surveyed archived `attempts.jsonl` error types and explicitly *kept* all
Tier 1/Tier 2 Anti-Patterns entries, including these two, arguing they map to
the observed `occ_exception`/`disconnected_body`/`non_manifold_edge` failure
surface as a class - `script_lint.py` already existed at that time (a month
earlier) and was not treated as a reason to cut. This change revisits that
call for these two sections specifically, on a narrower and different
rationale than that design considered: not "no error type observed" but
"the exact mistake is mechanically caught with a fix hint, AND the mechanism
is still explained in full in the other retained document" - see the new
requirement in `specs/reference-injection/spec.md`. Every other Anti-Patterns
entry (the OCC failure signatures, the stateful-context footguns with no
lint check, the Tier 3 API mechanics) is unaffected and stays exactly as the
prior condensation left it.

## Goals / Non-Goals

**Goals:**
- `{{CQ_REFERENCE}}` selection goes through the same `tagged_sections()`
  mechanism as `{{FDM_GUIDELINES}}`/`{{ENGINEERING_RULES}}`, with no changes
  to `tagged_sections()` itself.
- Remove exactly the two Anti-Patterns sections meeting the new
  duplicate-and-mechanically-caught rule; no other content is cut.
- Feature-derived tags (`adv3d`, `multi_union`) reuse the part-signal
  computation already in `part_spec()` (the same fields `TEXT_RE` already
  scans), rather than adding a new detection mechanism. No `text` tag is
  added - `emboss_text.md` already covers that case outside this system, and
  no section here is text-specific enough to need one.
- Validate with an eval sweep before accepting, per the existing
  `reference-injection` acceptance requirement.

**Non-Goals:**
- No re-condensation of retained prose (that was the 2026-08-09 change's
  scope; this change only removes the two identified duplicates).
- No change to how `emboss_text.md`, `hardware_dims.md`, or `gridfinity.md`
  are gated - those already use direct membership checks in `part_spec()`,
  not `tagged_sections()`, and stay that way.
- No attempt to invent block-specific tags for content that is genuinely
  API-level and universal - see D2 below.

## Decisions

**D1. Tag almost every Pattern Reference / Anti-Patterns section `always`.**
Unlike the FDM/Engineering guides - which describe *physical* behavior of
specific hardware features (a screw boss's pull-out strength, a snap-hook's
strain formula) and are naturally block-scoped - the CQ reference documents
describe the *scripting API itself* (selector syntax, workplane state,
boolean semantics), which every part's script uses regardless of which
blocks it needs. Block-specific CQ material (fastener dimensions, Gridfinity
grid math, servo spline profiles, text/emboss gotchas) already lives in its
own gated file (`hardware_dims.md`, `gridfinity.md`, `servo_splines.md`,
`emboss_text.md`), outside these two documents by design. So after removing
the two duplicate sections, essentially all remaining `##` sections in both
documents are tagged `always` - this is not an oversight, it is what the
content actually is. The `tagged_sections()` wiring is still worth adding
(matches the FDM/Engineering rendering path, and gives future block-specific
CQ gotchas - e.g. a Gridfinity-specific selector trap - a place to land
without falling back to unconditional injection), but the immediate byte
saving in this change comes almost entirely from the two removed sections,
not from block-based filtering. **Alternative considered:** invent
plausible-sounding block tags for sections like "Index-selector fragility"
just to demonstrate filtering. Rejected - a tag that doesn't reflect a real
"only relevant when this block is present" fact is worse than no tag; it
would silently drop material a part actually needs.

**D2. Two non-`always` tags earn their keep via existing signals, not new ones.**
- "Advanced 3D Operations (Loft, Sweep, Revolve)" (Pattern Reference) is
  genuinely rare - no block or template in the repo uses loft/sweep/revolve
  today (`grep` confirms). Gating it on a feature regex over the same fields
  `TEXT_RE` already scans (`description`, `part_notes`, `interfaces`) costs
  one more compiled regex and one more entry in the tag set passed to
  `tagged_sections()`.
- "Non-Overlapping Part Assembly (Performance)" (Pattern Reference) documents
  a compound-instead-of-loop pattern that matters once a part actually
  produces more than one solid to merge; `part.get("unions")` having more
  than one entry is an exact, already-computed proxy (`union_ids()` already
  exists in `render_prompt.py`).
Both tags are additive to the `blocks` set already passed into
`tagged_sections()` for `FDM_GUIDELINES`/`ENGINEERING_RULES` - no signature
change to that function.

**D3. Anti-Patterns.md sections all stay `always`.**
Surveyed every remaining Tier 1/2/3 entry (see table below) against a
`multi_union`/`adv3d`/`text`/block-name signal; none has a defensible
narrower scope after the two removals - they are boolean/selector/workplane
mechanics that apply to any script. Splitting a bullet list (e.g. Common
Gotchas items 8/9, which are text-specific) into per-item `##` sections just
to tag two lines out of twelve is not worth the structural churn; text parts
already get the full, more detailed `emboss_text.md` appended separately.

**D4. This reopens a call the 2026-08-09 change deliberately made the other
way, on different grounds than that change considered.**
That design explicitly weighed lint's existence and chose "keep the prose
anyway" on the theory that proactive prose reduces the *chance* of the
mistake, while lint only catches it *after* it's written (still costing a
retry round). This change's premise - stated as the task ask - is that the
duplicate explanation elsewhere plus a typed, hinted lint finding is now
sufficient. Both are defensible; the eval sweep (D5) is the tie-breaker, not
argument.

**D5. Acceptance gate: same as the existing `reference-injection` requirement.**
Run `evals/run_evals.py --generate`, compare first-shot rate and
attempts-to-pass against the most recently archived run. `evals/runs/` is
gitignored and empty in this worktree - there is no local baseline to diff
against from a prior session, so the comparison baseline is whatever the
person applying this change has most recently archived, or a fresh baseline
sweep taken immediately before this change's sections are removed. If either
metric regresses, revert just the two section removals (`git revert` on a
docs-only commit) rather than the tagging machinery.

## Retain/cut record (this change's slice only)

| Section | Document | Decision | Justification |
|---|---|---|---|
| Booleans are expensive -- never loop them | Anti-Patterns Tier 1 | **Remove** | `boolean_in_loop` lint finding + hint covers detection/fix; the compound-instead-of-loop pattern itself is fully explained in Pattern Reference's "Non-Overlapping Part Assembly" |
| Origin drift after `.center()` | Anti-Patterns Tier 2 | **Remove** | `unanchored_feature` lint finding + hint covers detection/fix; the mechanism is fully explained in Pattern Reference's "Workplane Context Stacking (Origin Drift)", which this section already pointed to as "full treatment" |
| Everything else in Anti-Patterns.md | Anti-Patterns | Retain, tag `always` | No mechanical lint check exists (Tier 1 kernel truths, most Tier 2 footguns, all Tier 3 mechanics), or a check exists but no duplicate explanation exists elsewhere (`shell_after_fillet`/`fillet_after_chamfer` have no dedicated Anti-Patterns prose to begin with - only Pattern Reference's Common Gotcha #1) |
| Advanced 3D Operations (Loft, Sweep, Revolve) | Pattern Reference | Retain, tag `adv3d` | No block/template uses these ops today; gate on feature-regex over description/notes/interfaces |
| Non-Overlapping Part Assembly (Performance) | Pattern Reference | Retain, tag `multi_union` | Directly proxied by `part.get("unions")` length |
| Everything else in Pattern Reference.md | Pattern Reference | Retain, tag `always` | Universal CadQuery scripting mechanics (workplane naming, selectors, sketch API, machining ops, transforms, gotchas, center selection) |

Cross-references naming the removed sections (`Pattern Reference.md`'s
"Feature operations vs. booleans... Skill rule" note, and the "Fresh
Workplane Pattern" section's "not the hardcoded global coordinates
anti-pattern" aside) point at Tier 1/Tier 2 by name/number, not at the two
removed section titles specifically - confirmed by grep before finishing;
any that do need their citation text updated in the same change per the
existing "Cited section names remain resolvable after condensation"
requirement.

## Implementation note: inline citation is dead code, left alone

While wiring task 4, found that the base `reference-injection` spec's
"inline render cites instead of pasting" requirement has no corresponding
code in `render_prompt.py` - there is one rendering path, used unchanged for
both a spawned agent and `"inline"`-routed orchestration
(`skill/phase3_build.md`'s Routing section: `"inline"` means "do not spawn;
follow the rendered builder prompt yourself" - reading the same file, not a
separately-cited version). This is a pre-existing spec/implementation
mismatch predating this change, not something introduced here. Fixing it
would require its own investigation (was inline citation removed on purpose
when subagent-orchestration landed, or just never implemented?) and is out
of scope. This change's delta spec leaves that requirement's inline wording
exactly as the base spec had it, and only changes the cold-context
scenario's content, since cold-context is the actually-exercised path.

## Risks / Trade-offs

- **Reopening the 2026-08-09 call regresses attempts-to-pass** -> the eval
  sweep gate (D5) catches this before merge; revert is a docs-only commit.
- **A part with `unions: [single]` but genuinely repeated non-touching
  geometry (e.g. an array of screw bosses in one union) loses the
  Non-Overlapping Part Assembly tip** -> accepted; that pattern is about
  merging *separate top-level unions*, and a single-union part with an
  internal array is a narrower case this proxy doesn't claim to catch. Not a
  regression versus today (today the section is always injected, so this is
  a real narrowing) - flagged here rather than hidden.
- **Feature regex false-negative** (a part description doesn't use the words
  revolve/loft/sweep/twist but the author still needs that section) -> low
  severity: worst case is the model reaches for a boolean/extrude idiom
  instead of loft/sweep, which still works, just less elegantly; the
  inline-render citation mode already relies on citing by name rather than
  guaranteeing completeness.

## Migration Plan

Docs-only content edit plus a `render_prompt.py` wiring change; no data
migration. Rollback is `git revert` of the commit(s). Sequencing:
1. Add `adv3d`/`multi_union` feature-tag computation and the two
   `applies_to` tags in `Pattern Reference.md`.
2. Tag remaining sections `always` in both documents (mechanical pass, no
   content change).
3. Remove the two duplicate sections from `Anti-Patterns.md`; verify no
   dangling cross-reference (grep pass).
4. Wire `part_spec()`'s `CQ_REFERENCE` build through `tagged_sections()`;
   update the inline-citation text to list selected section titles.
5. Run the eval sweep; accept or revert per D5.

## Open Questions

- None blocking. Whether `multi_union` should also fire for a single-union
  part with a large repeated feature array is left open for a future change
  if it turns out to matter in practice (see Risks).
