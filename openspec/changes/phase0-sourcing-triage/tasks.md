## 1. Phase 0 skill file

- [x] 1.1 Write `skill/phase0_sourcing.md`: entry conditions (runs before Phase 1; skip on explicit from-scratch request; quick-pass heuristic for custom-dimension requests), the five-rung decision ladder, and the collect-then-classify rule
- [x] 1.2 Add per-rung handling sections: rung 1 (CadQuery reuse / build123d convert via `src/convert_build123d.py` / OpenSCAD re-author, never transpile), rung 2 (`cq.importers` dumb-solid scoping), rung 3 (measure + gate + user confirmation before delivery), rung 4 (tractable-subset rebuild only), rung 5 (fall through to Phase 1)
- [x] 1.3 Add the license section: mandatory at rungs 1-4, no-license = all-rights-reserved, ND blocks rungs 1/2/4, rung-3 ND redistribution rule, provenance recording (planning_notes vs delivery summary)
- [x] 1.4 Reference the Phase 1 search workflow by pointer (`skill/phase1_requirements.md`), including the rule that Phase 1 dimension lookup reuses Phase 0 search results already in context

## 2. SKILL.md and cross-references

- [x] 2.1 Add Phase 0 to SKILL.md's phase overview: short summary + mandatory read pointer to `skill/phase0_sourcing.md` (keep SKILL.md under 10 KB)
- [x] 2.2 Add a cross-reference note in `skill/phase1_requirements.md` distinguishing sourcing search (Phase 0) from dimension lookup (Phase 1) and the no-second-sweep rule

## 3. Planning prompt provenance rule

- [x] 3.1 Add the provenance rule to `prompts/planning.md`: when the plan derives from a found source, `planning_notes` records source URL, license, and rung

## 4. build123d converter helper

- [x] 4.1 Write `src/convert_build123d.py`: known import/API mappings (build123d -> CadQuery) plus a smoke-check mode that runs a converted script through `run_cadquery_model.py` and reports the wrapper JSON verdict
- [x] 4.2 Add `tests/test_convert_build123d.py` covering the mapping table and the smoke-check path on a minimal converted fixture

## 5. Validation

- [x] 5.1 Run `uv run pytest tests/test_convert_build123d.py` and the fast subset (`tests/test_plan_validate.py`) to confirm nothing regresses
- [x] 5.2 Verify SKILL.md remains under 10 KB and `skill/phase0_sourcing.md` reads standalone (ladder, license rules, per-rung handling all present) -- SKILL.md was already over 10 KB (10,641 bytes) before this change; flagged to user, not fixed here (out of scope)
- [x] 5.3 Dry-run the ladder on one request answerable by a found model (e.g. a common phone stand): confirmed via live Thingiverse search (10,000 results, top result 37.7K makes) that rung 3 is reachable for a common request; Phases 1-3 would be skipped per the documented flow
