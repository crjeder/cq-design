## Context

Two consumers want cost data: the eval scorecard (today, estimated) and any
future post-hoc analysis of a real user run (today, nothing). The estimate lives
in `run_evals.attempt_metrics`; the raw material lives in the Claude Code session
transcript and, for `--generate`, in the `claude -p` result envelope.

`init_permissions.py` already owns writing `.claude/settings.local.json` in the
working directory (`skill-permission-bootstrap`), so a hook block there is a
consistent extension, not a new surface.

## Goals / Non-Goals

**Goals:**
- Record billed token cost (input, output, cache read, cache creation) for every
  skill run into `build/cost.json`, surviving `--resume`.
- Attribute cost to main session vs. builder subagents, and per model.
- Let the eval scorecard report billed cost when it exists, estimate otherwise.

**Non-Goals:**
- Per-attempt real-token attribution in `attempts.jsonl` (option A). Matching
  transcript turns to a specific attempt of a specific part is fuzzy; deferred.
- A live/streaming cost display.
- Exact cache pricing -- multipliers are approximate and documented as such.
- Transcript retention/pruning, or reading transcripts from outside the hook.
- Changing the `prompt_chars` field or its measurement.

## Decisions

- **`Stop` hook, not `SessionEnd`.** `Stop` fires after every assistant response,
  so `build/cost.json` is always current even if the session is later killed;
  `SessionEnd` can be missed on a crash, losing the whole record. The cost of a
  per-turn full-transcript reparse is small (line-delimited JSON, O(file),
  <~50 ms typical) and only paid when `build/` exists.
- **No `SubagentStop` hook.** By the time `Stop` fires, the subagent's
  `isSidechain` turns are already in the transcript; a separate event would only
  double-count.
- **`build/cost.json` is a dict keyed by session id, not a single flat rollup.**
  A `--resume` starts a new transcript path; keying by session id lets the hook
  replace only its own session's entry and recompute a `combined` total, so
  resumed work does not erase the first session's cost.
- **Hook is defensive and always exits 0.** Transcript unreadable, schema drift
  (`message.usage` / `isSidechain` are Claude Code internals), missing `build/`
  -> write nothing (or `{"error": ...}`) and exit 0. A cost recorder must never
  block a turn from completing.
- **Hook invokes plain `python`, not `uv run`.** `session_cost.py` is
  stdlib-only, so any Python 3 runs it, and per-turn `uv run` startup overhead
  (~200-500 ms) every turn is not worth paying. `init_permissions.py` bakes the
  absolute `session_cost.py` path (its own `src` dir) into the seeded hook
  command. If plain `python` is unavailable the hook fails silently (exits 0) and
  no cost is recorded -- degraded, not broken.
- **`model_prices.json` becomes `{input, output}` per model.** The only caller of
  `load_prices` is `run_evals.py`; both change together. Cache tokens are priced
  as `input_rate * 0.1` (read) and `input_rate * 1.25` (creation), matching
  Anthropic's published cache multipliers closely enough for a cost estimate.
- **Scorecard cost precedence: `<case>/cost.json` > `<case>/build/cost.json` >
  estimate.** The E envelope is the exact billed number for that one `claude -p`
  and needs no transcript parse; the B file is the fallback when the skill's hook
  ran but the runner did not capture the envelope (e.g. older run dir); the
  `prompt_chars` estimate stays as the last resort so score-only runs over
  pre-change run directories still produce a number.
- **Both B and E, not one.** E always works (the runner owns the subprocess) and
  carries `duration_ms` / `num_turns`; B works for interactive runs and carries
  the per-model / main-vs-subagent split. During `--generate` both fire; the
  numbers should agree within rounding.

## `build/cost.json` shape

```json
{
  "combined": {
    "input_tokens": 0, "output_tokens": 0,
    "cache_read_tokens": 0, "cache_creation_tokens": 0,
    "cost_usd": 0.0,
    "sessions": ["<id>"]
  },
  "sessions": {
    "<id>": {
      "transcript": "<abs path>",
      "last_update_ts": "<iso8601 utc>",
      "message_count": 0,
      "totals": { "input_tokens": 0, "output_tokens": 0,
                  "cache_read_tokens": 0, "cache_creation_tokens": 0,
                  "cost_usd": 0.0 },
      "by_model": { "<model>": { "...tokens...": 0, "cost_usd": 0.0 } },
      "main_vs_subagent": {
        "main":     { "...tokens...": 0, "cost_usd": 0.0 },
        "subagent": { "...tokens...": 0, "cost_usd": 0.0 }
      }
    }
  },
  "pricing": { "prices_path": "<abs>", "cache_read_mult": 0.1, "cache_creation_mult": 1.25 }
}
```

## `<case>/cost.json` shape (E)

The relevant subset of the `claude -p --output-format json` envelope:

```json
{
  "session_id": "...", "num_turns": 0, "duration_ms": 0,
  "total_cost_usd": 0.0,
  "usage": { "input_tokens": 0, "output_tokens": 0,
             "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0 }
}
```

On timeout or unparseable stdout, `generate_case` writes nothing; the scorer
falls through to `build/cost.json` then the estimate.

## Risks / Trade-offs

- [Transcript schema is a Claude Code internal and may change] -> hook degrades
  to exit 0 with no write; E path is independent and uses the documented
  `--output-format json` envelope.
- [`Stop` hook reparses the transcript every turn] -> cheap and bounded; optional
  future optimization: skip when transcript mtime is unchanged since last write.
- [Seeding a hook into user project settings is a surprising side effect] ->
  written only to project-local `.claude/settings.local.json` (the file bootstrap
  already writes), stdlib-only, no network, writes one file under `build/`,
  reported in the bootstrap output line.
- [`model_prices.json` format change breaks external callers] -> the only caller
  is `run_evals.py`; changed in the same diff.

## Migration Plan

Additive for the pipeline: new script, new hook, new `build/cost.json`. The
`model_prices.json` reshape and the two `run_evals.py` call sites change
together. Score-only runs over run directories produced before this change keep
working via the unchanged `prompt_chars` fallback. Rollback = revert the diff and
drop the seeded `hooks` block (bootstrap re-merge will not re-add it after
revert).
