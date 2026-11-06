"""Record billed token cost for a Claude Code session into ``build/cost.json``.

Reads a session transcript JSONL, sums each assistant turn's reported usage
grouped by model and split main-vs-subagent (transcript sidechain entries),
prices it against ``src/model_prices.json``, and merges the result into
``build/cost.json`` keyed by session id -- so a ``--resume`` (new transcript,
new session id) keeps the earlier session's cost instead of overwriting it.

A running session cannot see its own token usage; this is a post-hoc read of the
transcript. Stdlib only.

Hook mode (wired as a ``Stop`` hook by ``init_permissions.py``): reads the hook
payload from stdin, updates ``build/cost.json`` in the cwd *only when* ``build/``
already exists, and always exits 0 -- a cost recorder must never break a turn.

    python session_cost.py --hook
    python session_cost.py --transcript path/to.jsonl --out build/cost.json [--session-id ID]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_PRICES_PATH = Path(__file__).resolve().parent / "model_prices.json"
_CACHE_READ_MULT = 0.1
_CACHE_CREATION_MULT = 1.25
_TOKEN_KEYS = ("input_tokens", "output_tokens", "cache_read_tokens", "cache_creation_tokens")
_DEFAULT_PRICE = {"input": 15.0, "output": 15.0}


def load_prices(path: Path = _PRICES_PATH) -> dict:
    """Model -> {input, output} USD/MTok, with a guaranteed ``default`` entry."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    prices = {k: v for k, v in raw.items() if not k.startswith("_")}
    prices.setdefault("default", dict(_DEFAULT_PRICE))
    return prices


def _zero() -> dict:
    return dict.fromkeys(_TOKEN_KEYS, 0)


def _add(dst: dict, src: dict) -> None:
    for k in _TOKEN_KEYS:
        dst[k] += src.get(k, 0)


def _price_tokens(tokens: dict, prices: dict, model: str) -> float:
    if model not in prices:
        print(f"session_cost: no price for model {model!r}, using default", file=sys.stderr)
    entry = prices.get(model, prices["default"])
    inp, out = entry["input"], entry["output"]
    return (
        tokens["input_tokens"] * inp
        + tokens["output_tokens"] * out
        + tokens["cache_read_tokens"] * inp * _CACHE_READ_MULT
        + tokens["cache_creation_tokens"] * inp * _CACHE_CREATION_MULT
    ) / 1e6


def _read_turns(path: Path, side_override: str | None, turns: dict) -> None:
    """Add a file's assistant turns to ``turns``, keyed by ``message.id``.

    One API call is written as several lines (one per content block) repeating the
    same id and usage; keying by id counts it once (the last line wins).
    """
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict) or obj.get("type") != "assistant":
            continue
        msg = obj.get("message")
        if not isinstance(msg, dict):
            continue
        usage = msg.get("usage")
        if not isinstance(usage, dict):
            continue
        side = side_override or ("subagent" if obj.get("isSidechain") else "main")
        key = msg.get("id") or f"{path}:{len(turns)}"
        turns[key] = (msg.get("model") or "unknown", side, usage)


def parse_transcript(path: Path) -> tuple[dict, int]:
    """Sum usage per ``(model, side)`` over a transcript's assistant turns.

    Sub-agent turns come from ``<transcript stem>/subagents/*.jsonl`` plus any
    sidechain lines in the main file. Lines that are not assistant turns, do not
    parse, or carry no ``usage`` are skipped; repeated ``message.id`` counts once.
    """
    turns: dict = {}
    _read_turns(path, None, turns)
    for sub in sorted((path.with_suffix("") / "subagents").glob("*.jsonl")):
        _read_turns(sub, "subagent", turns)
    acc: dict[tuple[str, str], dict] = {}
    for model, side, usage in turns.values():
        bucket = acc.setdefault((model, side), _zero())
        bucket["input_tokens"] += usage.get("input_tokens") or 0
        bucket["output_tokens"] += usage.get("output_tokens") or 0
        bucket["cache_read_tokens"] += usage.get("cache_read_input_tokens") or 0
        bucket["cache_creation_tokens"] += usage.get("cache_creation_input_tokens") or 0
    return acc, len(turns)


def session_block(transcript: Path, prices: dict) -> dict:
    """The per-session block written under ``cost.json``'s ``sessions`` map."""
    acc, count = parse_transcript(transcript)
    by_model: dict[str, dict] = {}
    by_side = {
        "main": {**_zero(), "cost_usd": 0.0},
        "subagent": {**_zero(), "cost_usd": 0.0},
    }
    totals = _zero()
    total_cost = 0.0
    for (model, side), tokens in acc.items():
        cost = _price_tokens(tokens, prices, model)
        total_cost += cost
        _add(totals, tokens)
        _add(by_side[side], tokens)
        by_side[side]["cost_usd"] += cost
        m = by_model.setdefault(model, {**_zero(), "cost_usd": 0.0})
        _add(m, tokens)
        m["cost_usd"] += cost

    def _round(d: dict) -> dict:
        return {**d, "cost_usd": round(d["cost_usd"], 6)}

    return {
        "transcript": str(transcript),
        "last_update_ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "message_count": count,
        "totals": {**totals, "cost_usd": round(total_cost, 6)},
        "by_model": {k: _round(v) for k, v in by_model.items()},
        "main_vs_subagent": {k: _round(v) for k, v in by_side.items()},
    }


def merge_cost(out_path: Path, session_id: str, block: dict) -> dict:
    """Merge ``block`` under ``session_id`` into ``out_path`` and recompute ``combined``."""
    sessions: dict = {}
    if out_path.is_file():
        try:
            existing = json.loads(out_path.read_text(encoding="utf-8"))
            if isinstance(existing, dict) and isinstance(existing.get("sessions"), dict):
                sessions = existing["sessions"]
        except json.JSONDecodeError:
            pass
    sessions[session_id] = block

    combined = _zero()
    combined_cost = 0.0
    for blk in sessions.values():
        t = blk.get("totals", {})
        _add(combined, t)
        combined_cost += t.get("cost_usd", 0.0)

    data = {
        "combined": {
            **combined,
            "cost_usd": round(combined_cost, 6),
            "sessions": sorted(sessions),
        },
        "sessions": sessions,
        "pricing": {
            "prices_path": str(_PRICES_PATH),
            "cache_read_mult": _CACHE_READ_MULT,
            "cache_creation_mult": _CACHE_CREATION_MULT,
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return data


def _run_hook() -> int:
    """Stop-hook entry point: never raises, never exits non-zero."""
    try:
        payload = json.load(sys.stdin)
        transcript = Path(payload["transcript_path"])
        session_id = payload.get("session_id") or transcript.stem
        build_dir = Path.cwd() / "build"
        if not build_dir.is_dir() or not transcript.is_file():
            return 0
        block = session_block(transcript, load_prices())
        merge_cost(build_dir / "cost.json", session_id, block)
    except Exception as exc:  # a cost recorder must never break a turn
        print(f"session_cost: {exc}", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--hook",
        action="store_true",
        help="read the hook payload from stdin; update ./build/cost.json",
    )
    parser.add_argument("--transcript", help="transcript JSONL path (non-hook mode)")
    parser.add_argument("--out", help="cost.json path to write/merge (non-hook mode)")
    parser.add_argument("--session-id", help="session id key (default: transcript filename stem)")
    args = parser.parse_args(argv)

    if args.hook:
        return _run_hook()

    if not args.transcript or not args.out:
        parser.error("--transcript and --out are required without --hook")
    transcript = Path(args.transcript)
    block = session_block(transcript, load_prices())
    merge_cost(Path(args.out), args.session_id or transcript.stem, block)
    return 0


if __name__ == "__main__":
    sys.exit(main())
