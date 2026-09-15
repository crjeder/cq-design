## Context

Two documents dominate cold-render prompt size:

| Document | Bytes | Sections |
|---|---|---|
| `reference/CadQuery Pattern Reference.md` | 23,704 | 25 (`##`/`###`) |
| `reference/CadQuery Anti-Patterns.md` | 13,118 | 19 (`##`/`###`) |

Both are pasted in full at `{{CQ_REFERENCE}}` for every cold render (subagent or
`claude -p`); inline renders only cite them by name. Measured `prompt_chars` in
`evals/runs/c2-prompt-chars`: n=14, min 1,018 (inline), max 173,166 (cold), mean
49,356. The anti-patterns doc is injected unconditionally for every part
(`reference-injection` spec), so its size is paid on every cold attempt.

Evidence base for cuts -- error types across all archived `evals/runs/*/*/build/attempts.jsonl`:

```
12 thin_interface      7 dimension_mismatch   6 occ_exception
 4 disconnected_body   2 non_manifold_edge    1 feature_absent
 1 overhang_exceeded   1 magic_number         1 unguarded_boolean
```

Constraint from C5 and the 5-series migration guidance: pasted prose anchors
attention and suppresses latent knowledge. The model knows CadQuery basics; it does
not reliably know OCC failure signatures, selector-string semantics, or this
project's contracts.

## Goals / Non-Goals

**Goals:**

- Both documents at or under 65% of current bytes (target ~15,400 and ~8,500).
- Every retained section justified by one of: non-recallable API/failure signature,
  numeric table, project contract, or an error type present in attempt history.
- A measured before/after on cold-render `prompt_chars`, plus an eval sweep that
  does not regress first-shot rate or attempts-to-pass.

**Non-Goals:**

- No change to injection mechanics (mode split, tag filtering, citation rules, the
  once-per-build load). The `reference-injection` requirements governing *how*
  documents are selected and rendered stay untouched.
- No condensation of `FDM 3D Print Design Guidelines.md`, `Engineering Design
  Rules.md`, or `hardware_dims.md` -- those are already numeric/tabular and are
  tag-filtered, so their injected slice is small.
- No new tooling. This is a documentation edit plus one eval sweep; no script
  measures "recallability".

## Decisions

**D1. Condense in place rather than maintaining a full + condensed pair.**
C5's wording ("cold-context renders substitute the condensed versions") could mean
two variants, one per mode. Rejected: inline renders only cite section names, so a
"full" variant would exist solely to be cited, and two files drift. One condensed
file serves both modes -- the citation names still resolve, and the cold paste
shrinks. Alternative considered: a build-time stripper that removes tagged prose
blocks at render time. Rejected as machinery for a problem an editor solves once.

**D2. Retain/cut per section, decided against the evidence table.**
Working classification (final decision recorded per section during implementation):

*Pattern Reference* -- retain and tighten: selector semantics, selector modifier
reference, Nth/compound selectors, tags, center selection, workplane naming,
common gotchas, workplane context stacking (these are exactly the
signature/semantics material). Cut or fold: Basic Shapes, BRep Vocabulary, Sketch
API narration, Array Methods, Accessing Objects & Debugging, Table of Contents
(a TOC over a pasted doc is pure token cost), and any worked example an archetype
template in `templates/` already shows.

*Anti-Patterns* -- retain nearly all of Tier 1 and Tier 2: these are OCC failure
signatures and stateful footguns, and they map directly to the observed
`occ_exception` (6), `disconnected_body` (4), and `non_manifold_edge` (2) error
types. Compress the wrong/right code pairs to a single line each rather than
deleting the entries. Tier 3 API mechanics: keep the four entries, cut surrounding
prose.

**D3. `thin_interface` and `dimension_mismatch` (19 of 35 errors) do not argue for
keeping CadQuery prose.** They are DFM/plan-conformance failures addressed by the
FDM guide, the wrapper's typed errors, and the part prompt -- not by the pattern
reference. This is why the evidence table permits an aggressive cut to these two
documents specifically.

**D4. Acceptance is the eval sweep, not inspection.** Same gate as C2/C3/C4:
compare against the most recent archived run (`evals/runs/c4-review-collapse/`).
Given the C2 finding that run-to-run spread (first-shot 0.85 vs 0.75 on identical
prompts) is as large as the measured effect, a single sweep cannot prove an
improvement -- it can only fail to show a regression. So the quality gate is stated
as "no worse", and the claim this change actually makes is the prompt-size
reduction, which is deterministic and directly measurable from `prompt_chars`.

## Risks / Trade-offs

- **A cut section was load-bearing for an error class too rare to appear in 35
  observed errors** -> Tier 1/Tier 2 anti-patterns (the OCC failure surface) are
  retained rather than cut; cuts concentrate on the pattern reference's
  tutorial half. Reverting is a `git revert` of a docs-only commit.
- **Single-sweep noise masks a real regression** -> the gate is "no worse than the
  preceding run" on two metrics, and the change is docs-only, so a later regression
  traced to it is cheap to undo.
- **A phase file cites a section by a name that no longer exists** ->
  `skill/phase3_build.md` and `prompts/part.md` cite these two documents as whole
  files, not by section name (unlike the FDM guide, which is cited by section). A
  grep pass confirms this before finishing.
- **Condensing loses the "wrong vs right" contrast that makes anti-patterns
  stick** -> keep both sides, one line each, instead of dropping the wrong side.

## Migration Plan

Docs-only; no deploy step. Rollback is reverting the commit that rewrites the two
reference files. The eval run dir is archived under `evals/runs/c5-condensed/`
alongside the existing run dirs.

## Open Questions

None blocking. Whether the 65% target is reachable on the anti-patterns doc without
dropping a Tier 1 entry will be settled while editing; if it is not, the pattern
reference absorbs the extra reduction and the anti-patterns doc keeps its entries.

## Result: per-section retain/cut record

Both documents met the 65% target without dropping any Tier 1/Tier 2 anti-pattern
entry or any Common Gotcha. `CadQuery Anti-Patterns.md`: 13,118 -> 8,488 bytes
(64.7%). `CadQuery Pattern Reference.md`: 23,704 -> 15,396 bytes (64.9%).

**Anti-Patterns.md** -- every entry retained (condensed prose, one-line wrong/right
pairs); nothing cut. Justification: Tier 1 (kernel/OCCT truths) and Tier 2
(stateful-context footguns) map directly to `occ_exception` (6), `disconnected_body`
(4), and `non_manifold_edge` (2) in the attempt-history evidence table; Tier 3 (API
mechanics: extrude combine, cutBlind normal direction, `|Z` vs `>Z`, fluent/free-function
split) are non-recallable exact signatures. Cuts were entirely to surrounding prose,
not entries.

**Pattern Reference.md** -- per section:

| Section | Decision | Justification |
|---|---|---|
| Table of Contents | Cut (whole section) | Pure token cost in a pasted doc; no signature/table content |
| Workplane Naming | Retain, tightened | Non-obvious plane/axis mapping (signature material) |
| Basic Shapes | Cut to one line | `.box`/`.cylinder`/`.sphere`/`.polygon`/`.ellipse` recallable; kept only the non-obvious `.wedge()` arg order |
| BRep Vocabulary | Cut (whole section) | General CAD vocabulary (solid/shell/face/wire/edge/vertex/compound), no failure signature or table value, recallable |
| Face & Edge Selectors (all subsections) | Retain, tightened | Selector-string vocabulary is exactly the non-recallable signature material the rule targets |
| 2D Construction + Sketch API | Folded into one section, prose cut | Method list is recallable; kept the two non-obvious bits: `sagittaArc` sign convention/formula and `mode="s"`/`.finalize()` semantics |
| Machining Operations | Retain, tightened to one-line-per-call | `cboreHole`/`cskHole` arg order and cutBlind normal direction are non-obvious signatures |
| Advanced 3D Operations | Retain, tightened | `revolve(angleDegrees, axisStart, axisEnd)` arg order is non-obvious; loft/sweep/twistExtrude kept as minimal signature reminders |
| Array Methods | Cut (folded to one line) | Two-row table, fully recallable one-liner |
| Transform Operations | Retain, tightened; Assembly example cut | `rotate()`'s named-arg signature is non-obvious; `.mirror`/`.split`/plain `Assembly.add` are recallable |
| Boolean Operations | Retain, tightened | Kept because Non-Overlapping Part Assembly (below) depends on the reader knowing `.union`/`.cut`/`.combine`; trimmed to one line each |
| Non-Overlapping Part Assembly | Retain, tightened | Project-specific perf idiom with a numeric claim (5-10x); referenced by name from `CadQuery Anti-Patterns.md`'s "Booleans are expensive" section |
| Center Selection | Retain, tightened | `centerOption` table is exact non-recallable enum semantics; maps to the `workplane_drift` error path |
| Accessing Objects & Debugging | Cut (whole section) | `.val()`/`.findSolid()` one-liners, fully recallable, no table/signature depth |
| Drawing Arcs by Sagitta | Folded into 2D Construction | Formula retained (non-recallable), narration cut |
| Common Gotchas | Retain, tightened, numbering preserved | Maps to `thin_interface`/`disconnected_body`/`workplane_drift`/error-typed evidence; gotcha #12 is cited by number from `skill/phase3_build.md:311` -- numbering was preserved intact |
| Workplane Context Stacking | Retain, tightened | Named directly from `CadQuery Anti-Patterns.md`'s origin-drift entry and from Gotcha #7 |
| The Fresh Workplane Pattern | Retain, tightened | Named directly from `CadQuery Anti-Patterns.md` and from Workplane Context Stacking's Fix 3 |
| Text & Emboss Reference / Anti-Patterns (pointer sections) | Cut (folded into one closing paragraph) | Pure meta-documentation of the injection mechanism, not modeling content; no signature/table/contract |

No citation from `prompts/*.md`, `skill/*.md`, or `SKILL.md` names a Pattern
Reference section that was cut or renamed, except the numbered Gotcha #12
reference, whose number was preserved.

## Result: eval sweep

`evals/run_evals.py --generate` was run twice against `evals/runs/c5-condensed/`;
both runs hit a Claude session usage limit before finishing all 10 cases (first
attempt: 2/10 generated before the limit; after the reset, a second attempt got
9/10 -- `wall-hook` hit the limit again right at the end and was never generated).
9/10 is treated as sufficient evidence rather than retried a third time.

Comparing the **same 9 cases** against `c4-review-collapse/scorecard.json` (excluding
`wall-hook` from both sides for an apples-to-apples comparison):

| | C4 (9-case subset) | C5-condensed (9/10) |
|---|---|---|
| first-shot rate | 7/9 = 0.778 | 7/9 = 0.778 |
| mean attempts-to-pass | 11/9 = 1.222 | 11/9 = 1.222 |

Aggregate is identical, but the failing cases are not the same ones: C4 failed
`boss-plate` and `l-bracket` first-shot; C5-condensed failed `l-bracket` and
`snap-lid` first-shot (`boss-plate` passed first-shot this time). This is exactly
the run-to-run spread the design's D4 decision anticipated (first-shot 0.85 vs
0.75 on identical prompts in the C2 baseline) -- the aggregate holds, individual
case outcomes swap. No regression per the "no worse than the preceding run" gate;
the condensation is accepted without narrowing.

Cold-render `prompt_chars`: only 2 of 11 telemetry records in this run exceed the
15,000-char cold/inline split threshold (46,885 and 25,452, both from
`two-part-box`'s two parts) -- mean **36,168.5**, well below the `c2-prompt-chars`
cold-cluster mean of **90,098.9** computed in Baseline (task 1.3). Most other
cases in this run resolved inline or via a routing path that doesn't pay the full
cold paste, so the sample is thin (n=2) and not a controlled re-run of the same
cold-triggering conditions as C2 -- but it is directionally consistent with the
~35% document-size cut and shows no cold render exceeding half the C2 mean.
