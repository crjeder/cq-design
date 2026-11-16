## 1. acceptance.json contract and oracle.py

- [x] 1.1 Add `src/oracle.py` with the `acceptance.json` JSON Schema (statement kinds and fields per design D3; no coordinate fields; numeric = number or expression string; `tol_mm` default 0.2)
- [x] 1.2 Implement `oracle.py validate ACCEPTANCE [--intent TEXT|--plan PLAN] [--params parameters.py]`: schema, unique ids, citation check (whitespace-collapsed substring or parameters.py name), expression names resolve via `plan_params.evaluate`; JSON `{success, errors}` and exit code
- [x] 1.3 Implement `oracle.check(plan, acceptance, params) -> list[str]`: unbound, unknown statement/part/interface/probe, attribute contradictions per kind, `part_count`, probe-label prefix
- [x] 1.4 Implement `oracle.verify(plan, acceptance, part_id, body, feature_presence_issues) -> list[dict]`: `feature`/`fit`/`spacing` via feature-presence failures of bound interfaces, `extent` via sorted BRep bbox, `probe` via `probes.py` on the final body
- [x] 1.5 `tests/test_oracle.py`: validate (coordinate rejected, uncited, unknown param), check (each contradiction kind, absent file = no-op), verify (extent exceeded, probe met/failed)

## 2. Plan schema, validation, summary, log

- [x] 2.1 `build_plan_schema.json`: add `acceptance_bindings` (`statement`, `part`, `interfaces?`, `probes?`) and `acceptance_ts` (ISO-8601)
- [x] 2.2 `plan.py validate_plan`: when `acceptance.json` exists beside the plan, append `oracle.check` errors, and add the `acceptance_ts` staleness rule mirroring `intent_ts` (including unparseable value)
- [x] 2.3 `plan.py summary`: add the Acceptance section (id, text, binding, visual labelled as review)
- [x] 2.4 `log.py request add --acceptance-reconciled` sets `acceptance_ts` to the appended entry's `ts`
- [x] 2.5 Tests in `tests/test_plan.py` (dropped binding, contradiction, staleness, no-file skip, summary section) and the log flag test

## 3. Quality gate oracle stage

- [x] 3.1 Add the `oracle` stage to `quality_gate.py` (runs only when `acceptance.json` exists, after feature presence), emitting `oracle_unmet` issues with `statement` and `round`
- [x] 3.2 Derive `round` from the `--prior` report; action `fix` below 3, `escalate` at 3; keep it outside the 2-round fix cap
- [x] 3.3 Gate tests: round increments across `--prior`, escalate at round 3, no stage without `acceptance.json`

## 4. Oracle agent, prompt, model routing

- [x] 4.1 `agents/oracle.md` (tools exactly `Read`, `Write`, `Bash`; Sonnet model) and its project-agent copy in setup/install
- [x] 4.2 `prompts/oracle.md`: role, vocabulary table, citation rule, `visual` fallback, `probe` for spatial relations, no-plan rule, self-validate up to 3 attempts, status contract
- [x] 4.3 `render_prompt.py oracle --request-file` (inlines the request file only) and `models.oracle` in `skill_config.default.json`
- [x] 4.4 Update `tests/test_agents.py` and `tests/test_render_prompt.py` (six roles, oracle tools, no plan content in the oracle prompt, default model alias)
- [x] 4.5 Add any needed allow entries to `skill_permissions.json` / `init_permissions.py` for `oracle.py`

## 5. Skill prose

- [x] 5.1 `skill/phase1_requirements.md`: write `build/oracle_request.md` (with constant names in the dimension table), spawn the oracle, add the fourth checkpoint item, route statement corrections into the reformulation
- [x] 5.2 `prompts/planning.md` + `skill/phase2_planning.md`: read `acceptance.json`, write `acceptance_bindings` and `acceptance_ts`, `blocked` handling names the failing statements
- [x] 5.3 `prompts/audit.md` + `skill/phase3_build.md`: visual statements as checklist questions; `oracle_unmet` routing to the builder; escalation choices at round 3; mid-build correction re-runs the oracle and uses `--acceptance-reconciled`
- [x] 5.4 `skill/resume.md`: resume at the oracle step when the reformulation exists and `acceptance.json` does not
- [x] 5.5 `reference/scripts.md` (oracle.py contract, gate issue shape), `FILES.md`, `ARCHITECTURE.md` agent roster, `SKILL.md` pointers if needed

## 6. Verify

- [x] 6.1 `uv run pytest tests/` passes; `ruff check` / `ruff format` on changed Python
- [ ] 6.2 (needs a live agent run, not done) Dry run on a small request (e.g. the broom hook): statements shown at Phase 1, a deliberately dropped binding fails `plan.py validate`, the gate emits `oracle_unmet` on a hand-broken part
