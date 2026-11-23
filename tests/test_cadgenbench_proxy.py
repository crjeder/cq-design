import io
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "evals"))

import cadgenbench_proxy  # type: ignore[import-not-found]  # noqa: E402  # pyright: ignore[reportMissingImports]


def _row(sid, rev, scores, agg=0.5, status="completed"):
    return {
        "submission_id": sid,
        "submission_name": sid,
        "submitter_name": "x",
        "status": status,
        "cadgenbench_data_revision": rev,
        "aggregate_score": agg,
        "submission_blob_url": f"https://example/{sid}.zip",
        "per_sample_scores": {
            fid: {"status": st, "cad_score": sc} for fid, (st, sc) in scores.items()
        },
    }


def test_pick_proxies_best_valid_on_revision():
    rows = [
        _row("a", "abc123", {"101": ("valid", 0.9), "102": ("valid", 0.5)}),
        _row("b", "abc123", {"101": ("invalid", 0.99), "102": ("valid", 0.7)}),
        _row("old", "zzz999", {"101": ("valid", 1.0)}),
        _row("mine_1", "abc123", {"101": ("valid", 0.95)}),
        _row("failed", "abc123", {"102": ("valid", 1.0)}, status="failed"),
        _row("tie", "abc123", {"102": ("valid", 0.7)}, agg=0.9),
    ]
    picks = cadgenbench_proxy.pick_proxies(rows, "abc123def", exclude=["mine_"])
    assert picks["101"]["submission_id"] == "a"
    assert picks["102"]["submission_id"] == "tie"
    assert picks["102"]["cad_score"] == 0.7
    assert "_key" not in picks["101"]


def test_zip_member_matches_fixture_folder_only():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("meta.json", "{}")
        zf.writestr("1101/output.step", "x")
        zf.writestr("top/101/output.stp", "y")
    with zipfile.ZipFile(buf) as zf:
        assert cadgenbench_proxy.zip_member(zf, "101") == "top/101/output.stp"
        assert cadgenbench_proxy.zip_member(zf, "102") is None
