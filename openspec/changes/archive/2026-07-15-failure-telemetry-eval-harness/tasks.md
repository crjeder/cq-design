# Tasks: Failure Telemetry + Eval Harness

## 1. Telemetry helper

- [x] 1.1 Create `src/telemetry.py`: attempt-record schema (required fields per
      spec, extra keys allowed), `append_attempt(path, record)` that stamps
      `ts` when absent and appends one JSON line, creating `build/` and the
      file on first use
- [x] 1.2 Add CLI entry point (`python src/telemetry.py append <file> <json>`
      or `--field k=v` flags); invalid records exit non-zero without writing
- [x] 1.3 Add `tests/test_telemetry.py`: valid append, missing-field
      rejection, extra-key preservation, first-append file creation,
      append-only across two calls (no CadQuery needed - fast suite)

## 2. Eval corpus

- [x] 2.1 Create `evals/cases/` layout and pick ~10 canonical requests seeded
      from the archetype list (enclosure body, sliding lid, snap lid,
      L-bracket, flanged adapter ring, plate with boss pattern, hook, clip,
      stand, one multi-part model)
- [x] 2.2 For each case: write `request.md`, author the golden
      `BUILD_PLAN.json` (must pass `plan_validate.py`), and `case.json` with
      `tolerance_mm` and expected part count
- [x] 2.3 Generate golden meshes (authored frame) for each case and commit
      them under `golden/`
- [x] 2.4 Add a corpus sanity test: every case dir is self-contained and every
      case plan passes `plan_validate.py`

## 3. Eval runner

- [x] 3.1 Create `evals/model_prices.json` (per-model input/output token
      prices as editable data)
- [x] 3.2 Implement `evals/run_evals.py` score mode: read a run directory's
      `build/attempts.jsonl` + produced STLs; compute first-shot rate,
      mean attempts-to-pass, symmetric Chamfer distance (trimesh sampling +
      point-to-surface via `trimesh.proximity`, bbox-center alignment), and
      cost per accepted part (chars/4 token estimate x price table)
- [x] 3.3 Emit the scorecard as JSON and markdown, per case and aggregated;
      attempt/cost metrics degrade to "unavailable" when telemetry is missing
- [x] 3.4 Implement `--generate` (invoke `claude -p` per case in a temp
      working dir) and `--cases` subsetting; default invocation never invokes
      a model
- [x] 3.5 Add `tests/test_run_evals.py` for the scoring path using fixture
      attempts.jsonl + small STL pairs (identical meshes -> ~0 Chamfer;
      shifted mesh -> nonzero; missing telemetry -> degraded scorecard)

## 4. Skill wiring

- [x] 4.1 Add the telemetry append step to the SKILL.md part loop (same step
      as the wrapper invocation; one fixed `telemetry.py` command per attempt)
- [x] 4.2 Add the SKILL.md rule: run the eval suite (score mode) before/after
      any prompt, reference, or model-routing change
- [x] 4.3 Document `build/attempts.jsonl` alongside `build/orientations.json`
      in CLAUDE.md's file layout / key constraints
