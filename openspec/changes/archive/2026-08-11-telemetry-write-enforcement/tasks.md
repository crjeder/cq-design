## 1. Gate stage

- [x] 1.1 Add `_run_telemetry_stage(attempts_log: str) -> list[dict]` to
      `src/quality_gate.py`: returns one `warning` finding
      (`source: "telemetry"`, `type: "telemetry_missing"`, with `message` naming
      the path and a `hint` pointing at `skill/phase3_build.md` Step 5) when the
      file is absent, empty, or has no parseable JSON line; empty list otherwise.
      Stop scanning at the first parseable line.
- [x] 1.2 Add an `attempts_log: str | None = None` parameter to `run_gate`,
      defaulting to `attempts.jsonl` in the part-script directory (the same
      derivation `parts_dir` already uses), and call the stage once alongside the
      other outside-the-fix-loop stages. It must run unconditionally, not gated
      on plan validity -- a malformed plan is exactly when telemetry matters.
- [x] 1.3 Add the `--attempts-log` CLI flag and thread it into `run_gate`.

## 2. Tests

- [x] 2.1 Add `tests/test_quality_gate_telemetry.py` (stdlib + pytest only, no
      CadQuery) covering the four spec scenarios against `_run_telemetry_stage`:
      absent file, empty file, unparseable-only content, populated log.
- [x] 2.2 Add one case for path resolution: default lands next to `--script`,
      explicit override wins.
- [x] 2.3 Run `uv run pytest tests/test_quality_gate_telemetry.py tests/test_telemetry.py`.

## 3. Skill + docs

- [x] 3.1 `skill/phase4_deliver.md`: in the Status item, report a
      `telemetry_missing` warning from `build/quality_gate.json` as a named line
      ("no attempt telemetry was written this session").
- [x] 3.2 `reference/scripts.md`: add the telemetry stage and `--attempts-log`
      flag to the `quality_gate.py` entry.
- [x] 3.3 `TODO.md`: mark the "telemetry not written in real runs" item done,
      noting that Step 5's prescription was verified present and the gate warning
      is what shipped.
