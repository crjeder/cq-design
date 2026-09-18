## 1. Tag `reference/CadQuery Pattern Reference.md`

- [x] 1.1 Add a one-line header note explaining the `applies_to` tag convention (matching the note already at the top of `FDM 3D Print Design Guidelines.md`).
- [x] 1.2 Tag every `##` section `<!-- applies_to: always -->` except the two below.
- [x] 1.3 Tag "Advanced 3D Operations (Loft, Sweep, Revolve)" `<!-- applies_to: adv3d -->`.
- [x] 1.4 Tag "Non-Overlapping Part Assembly (Performance)" `<!-- applies_to: multi_union -->`.

## 2. Remove lint-duplicated sections from `reference/CadQuery Anti-Patterns.md`

- [x] 2.1 Remove "Booleans are expensive -- never loop them" (Tier 1); confirm no other prose in the file depends on it staying.
- [x] 2.2 Remove "Origin drift after `.center()`" (Tier 2). The `check_workplane`/`workplane_drift` project-contract note from this section was preserved by folding it into Pattern Reference's "Workplane Context Stacking" section rather than dropped.
- [x] 2.3 Tag every remaining `##` section `<!-- applies_to: always -->`.
- [x] 2.4 Grepped for citations of the removed sections. Found and fixed one dangling reference: Pattern Reference's "Center Selection" section cited `CadQuery Anti-Patterns.md, Tier 2, origin drift` by name - repointed to the retained "Workplane Context Stacking (Origin Drift)" section instead. No other citation named the two removed sections specifically.

## 3. Wire tag-filtering into `render_prompt.py`

- [x] 3.1 In `part_spec()`, compute `adv3d` (via a new `ADV3D_RE` regex over the same fields `TEXT_RE` scans) and `multi_union` (`len(part.get("unions") or []) > 1`) and fold them into a separate `cq_blocks` set, used only for CQ-reference selection (the `blocks` set used for `FDM_GUIDELINES`/`ENGINEERING_RULES` is unchanged). Dropped the originally-planned `text` tag - no section needs it, `emboss_text.md` already covers that case outside this system (see design.md's Goals note).
- [x] 3.2 Replaced the unconditional concatenation with `tagged_sections(...)` calls over both files using `cq_blocks`.
- [x] 3.3 Confirmed `emboss_text.md` appending logic (gated on `textish`) is untouched and still appends after the tag-filtered `cq_ref`.

## 4. Inline-citation rendering (found moot during implementation)

- [x] 4.1 N/A - investigated where the inline-render citation is produced and found no such code path exists: `render_prompt.py builder` has a single rendering function used for both a spawned agent and `"inline"`-routed orchestration (`skill/phase3_build.md`'s Routing section says the orchestrator "follow[s] the rendered builder prompt yourself", reading the same file `render_prompt.py` wrote - it does not hold these documents in its own context per that file's line 5). The base spec's "inline render cites" requirement describes a citation contract that was never implemented in code; reconciling it is a separate, pre-existing issue out of scope for this change. Left the inline-citation wording in `specs/reference-injection/spec.md` unchanged from the base spec (only the cold-context scenario's content changed).
- [x] 4.2 N/A - no phase file hardcodes per-section inline citation text to update (confirmed by grep in task 2.4 territory - `skill/phase3_build.md` never names Pattern Reference/Anti-Patterns section titles).

## 5. Spec and doc sync

- [x] 5.1 `openspec validate builder-prompt-tag-reference` passes with the delta spec as written.
- [x] 5.2 Checked `reference/scripts.md` and `ARCHITECTURE.md` for descriptions of `part_spec()`'s CQ-reference behavior; neither describes it in enough detail to go stale (both only say "rendered by `src/render_prompt.py`"). Nothing to update.

## 6. Tests

- [x] 6.1 Added `test_cq_reference_default_part_gets_only_always_sections` - asserts an always section is present, `adv3d`/`multi_union` sections are absent, and both removed Anti-Patterns sections' text is gone.
- [x] 6.2 Added `test_cq_reference_multi_union_part_gets_compound_assembly_section`.
- [x] 6.3 Added `test_cq_reference_revolve_description_gets_adv3d_section`.
- [x] 6.4 Confirmed: no existing test in `tests/test_render_prompt.py` asserted the old unconditional full-text concatenation; nothing to update.
- [x] 6.5 `uv run pytest tests/test_render_prompt.py tests/test_script_lint.py` - passed (exit 0).

## 7. Validation sweep

- [ ] 7.1 Run `evals/run_evals.py --generate` to produce a fresh scorecard.
- [ ] 7.2 Compare first-shot rate and mean attempts-to-pass against the most recently archived `evals/runs/*/scorecard.json` (or a fresh pre-change baseline sweep if none is archived locally).
- [ ] 7.3 If either metric regresses relative to the baseline, revert the two section removals (task 2.1/2.2) only, keep the tagging infrastructure, and re-run the sweep.
- [ ] 7.4 Archive the accepted run directory under `evals/runs/` per existing convention and record the before/after `prompt_chars` and pass-rate numbers in the change's design.md "Result" addendum.
