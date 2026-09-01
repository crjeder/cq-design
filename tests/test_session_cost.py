"""session_cost.py: transcript parse, pricing, per-session merge -- fast, no CadQuery."""

import io
import json

import session_cost

PRICES = {
    "default": {"input": 15.0, "output": 15.0},
    "claude-sonnet-5": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5": {"input": 1.0, "output": 5.0},
}

TRANSCRIPT = "\n".join(
    [
        json.dumps(
            {
                "type": "assistant",
                "isSidechain": False,
                "message": {
                    "model": "claude-sonnet-5",
                    "usage": {
                        "input_tokens": 1000,
                        "output_tokens": 500,
                        "cache_read_input_tokens": 2000,
                        "cache_creation_input_tokens": 100,
                    },
                },
            }
        ),
        json.dumps(
            {
                "type": "assistant",
                "isSidechain": True,
                "message": {
                    "model": "claude-haiku-4-5",
                    "usage": {"input_tokens": 4000, "output_tokens": 800},
                },
            }
        ),
        json.dumps({"type": "user", "message": {"role": "user", "content": "hi"}}),
        "not json at all",
    ]
)


def _transcript(tmp_path, text=TRANSCRIPT, name="sess-a.jsonl"):
    p = tmp_path / name
    p.write_text(text + "\n", encoding="utf-8")
    return p


def test_block_totals_and_splits(tmp_path):
    block = session_cost.session_block(_transcript(tmp_path), PRICES)

    assert block["message_count"] == 2
    assert block["totals"] == {
        "input_tokens": 5000,
        "output_tokens": 1300,
        "cache_read_tokens": 2000,
        "cache_creation_tokens": 100,
        "cost_usd": block["totals"]["cost_usd"],
    }
    # main: (1000*3 + 500*15 + 2000*3*0.1 + 100*3*1.25) / 1e6 = 0.011475
    assert abs(block["main_vs_subagent"]["main"]["cost_usd"] - 0.011475) < 1e-9
    # subagent: (4000*1 + 800*5) / 1e6 = 0.008
    assert abs(block["main_vs_subagent"]["subagent"]["cost_usd"] - 0.008) < 1e-9
    assert set(block["by_model"]) == {"claude-sonnet-5", "claude-haiku-4-5"}
    assert abs(block["totals"]["cost_usd"] - 0.019475) < 1e-9


def test_unknown_model_uses_default(tmp_path):
    text = json.dumps(
        {
            "type": "assistant",
            "message": {
                "model": "mystery-model",
                "usage": {"input_tokens": 1000, "output_tokens": 0},
            },
        }
    )
    block = session_cost.session_block(_transcript(tmp_path, text), PRICES)
    assert abs(block["totals"]["cost_usd"] - 0.015) < 1e-9  # 1000 * 15 / 1e6


def test_merge_keeps_prior_session(tmp_path):
    out = tmp_path / "cost.json"
    session_cost.merge_cost(out, "a", session_cost.session_block(_transcript(tmp_path), PRICES))
    b_transcript = _transcript(tmp_path, name="sess-b.jsonl")
    data = session_cost.merge_cost(out, "b", session_cost.session_block(b_transcript, PRICES))

    assert data["combined"]["sessions"] == ["a", "b"]
    assert set(data["sessions"]) == {"a", "b"}
    one = data["sessions"]["a"]["totals"]["cost_usd"]
    assert abs(data["combined"]["cost_usd"] - 2 * one) < 1e-9


def test_hook_noop_without_build_dir(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    transcript = _transcript(tmp_path)
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps({"transcript_path": str(transcript), "session_id": "x"})),
    )

    rc = session_cost.main(["--hook"])

    assert rc == 0
    assert not (tmp_path / "build" / "cost.json").exists()


def test_hook_writes_when_build_dir_exists(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "build").mkdir()
    transcript = _transcript(tmp_path)
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps({"transcript_path": str(transcript), "session_id": "x"})),
    )

    rc = session_cost.main(["--hook"])

    assert rc == 0
    data = json.loads((tmp_path / "build" / "cost.json").read_text(encoding="utf-8"))
    assert data["sessions"]["x"]["message_count"] == 2
    assert data["combined"]["cost_usd"] > 0


def test_hook_survives_bad_transcript_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "build").mkdir()
    monkeypatch.setattr(
        "sys.stdin", io.StringIO(json.dumps({"transcript_path": str(tmp_path / "nope.jsonl")}))
    )

    assert session_cost.main(["--hook"]) == 0
    assert not (tmp_path / "build" / "cost.json").exists()
