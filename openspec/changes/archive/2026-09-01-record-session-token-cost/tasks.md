## 1. `session_cost.py` recorder

- [x] 1.1 Add `src/session_cost.py` (stdlib only: `json`, `sys`, `argparse`,
      `pathlib`, `datetime`). Core function parses a transcript JSONL, sums
      `message.usage` (`input_tokens`, `output_tokens`,
      `cache_creation_input_tokens`, `cache_read_input_tokens`) grouped by
      `message.model` and split on `isSidechain` (main vs. subagent), prices it
      via a price table + the cache multipliers, and returns the per-session
      block from `design.md`'s shape.
- [x] 1.2 `--hook` mode: read the hook JSON from stdin, take `transcript_path`
      and `session_id`, and only when `build/` exists in cwd, merge this
      session's block into `build/cost.json` (dict keyed by session id) and
      recompute `combined`. Any error -> print to stderr, exit 0, write nothing.
- [x] 1.3 `--transcript PATH --out PATH` mode for manual/testing use (no stdin,
      no `build/` guard).
- [x] 1.4 Price lookup reuses `evals/model_prices.json`; unknown model -> the
      `default` entry. Cache read priced at `input * 0.1`, cache creation at
      `input * 1.25`.
- [x] 1.5 `tests/test_session_cost.py` (fast, no CadQuery): synthetic transcript
      fixture with a main turn + a sidechain turn on a different model ->
      per-model split, main/subagent split, and combined total are correct;
      second session id merges without dropping the first; missing `build/` in
      `--hook` mode is a silent exit 0.

## 2. Price table reshape

- [x] 2.1 Restructure `evals/model_prices.json` entries to
      `{"input": <usd/MTok>, "output": <usd/MTok>}`, keep `_`-prefixed keys as
      comments, add `_cache_multipliers` note. Populate from the current
      `_comment` output prices.
- [x] 2.2 Update `run_evals.load_prices` and `run_evals.attempt_metrics` to the
      new shape (estimate path uses `entry["input"]` only, unchanged math).
- [x] 2.3 `tests/test_run_evals.py`: update fixtures to the new price shape;
      assert the estimate is unchanged for an input-only record.

## 3. Bootstrap seeds the hook

- [x] 3.1 Add an optional `hooks` block to `src/skill_permissions.json`
      describing the `Stop` hook (command template with a placeholder for the
      resolved `session_cost.py` path).
- [x] 3.2 `src/init_permissions.py`: `load_canonical` also returns `hooks`;
      `merge_permissions` resolves the command placeholder to the absolute
      `session_cost.py` path (its own `src` dir) and merges the entry into
      `settings["hooks"]["Stop"]` only when an equivalent entry is absent.
      Idempotent; leaves existing hook entries untouched.
- [x] 3.3 Bootstrap output line reports the seeded hook alongside the permission
      count.
- [x] 3.4 `tests/test_init_permissions.py`: fresh dir gets the hook; re-run adds
      nothing; a pre-existing unrelated `Stop` hook is preserved and the
      session-cost entry is appended.

## 4. Eval generation captures the envelope

- [x] 4.1 `run_evals.generate_case`: run `claude -p <prompt>
      --dangerously-skip-permissions --output-format json` with
      `capture_output=True`; parse stdout; write `session_id`, `num_turns`,
      `duration_ms`, `total_cost_usd`, `usage` to `<case>/cost.json`. Timeout or
      parse failure -> log to stderr, write nothing.
- [x] 4.2 Add `read_recorded_cost(case_run_dir)` -> USD or None: prefer
      `<case>/cost.json` (`total_cost_usd`), else `<case>/build/cost.json`
      (`combined.cost_usd`), else None.
- [x] 4.3 `attempt_metrics` / `score_case`: when `read_recorded_cost` returns a
      value, use it for `total_cost_usd` and `cost_per_accepted_part_usd` and
      tag the result `cost_source: "recorded"`; otherwise keep the
      `prompt_chars` estimate and tag `cost_source: "estimate"`.
- [x] 4.4 `render_markdown`: note which cost source each row used (or a single
      footnote when mixed).
- [x] 4.5 `tests/test_run_evals.py`: a run dir with `<case>/cost.json` ->
      recorded cost used, `cost_source: "recorded"`; without it -> estimate
      path unchanged.

## 5. Docs

- [x] 5.1 `CLAUDE.md`: add `src/session_cost.py` to the script index and File
      Layout; note `build/cost.json` under Key Constraints (hook-written, not a
      pipeline output, safe to delete).
- [x] 5.2 `reference/scripts.md`: `session_cost.py` contract (modes, stdin shape,
      `build/cost.json` shape, exit-0-always guarantee).
- [x] 5.3 Working-directory tree + `lib/` bundling live in `skill/phase3_build.md`
      (Model export); added `build/cost.json` / `attempts.jsonl` to the tree and a
      "do not copy into `lib/` or the deliverable" note there.
- [x] 5.4 `skill/phase0_sourcing.md` (or wherever bootstrap output is described):
      mention the seeded session-cost hook.

## 6. Verification

- [x] 6.1 `uv run pytest tests/test_session_cost.py tests/test_init_permissions.py
      tests/test_run_evals.py`.
- [ ] 6.2 Manual: run the skill on one small request, confirm `build/cost.json`
      appears with a plausible non-zero `combined.cost_usd` and a
      main/subagent split.
- [ ] 6.3 Manual: `uv run python evals/run_evals.py --run-dir <dir> --generate
      --cases <one>` writes `<case>/cost.json` and the scorecard row shows
      `cost_source: recorded`.
- [x] 6.4 `openspec validate record-session-token-cost --strict`.
