"""fetch_stl.py: scheme, size cap, parse check, any-domain download."""

import contextlib
import functools
import http.server
import os
import threading

import trimesh

import fetch_stl


@contextlib.contextmanager
def _serve(tmp_path):
    root = tmp_path / "www"
    root.mkdir()
    trimesh.creation.box(extents=(10, 10, 10)).export(str(root / "box.stl"))
    (root / "page.html").write_text("<html>nope</html>", encoding="utf-8")
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def test_valid_stl_any_domain(tmp_path):
    out = str(tmp_path / "refs")
    with _serve(tmp_path) as server:
        r = fetch_stl.fetch(f"{server}/box.stl", out)
    assert r["success"] and r["errors"] == []
    assert os.path.isfile(r["path"]) and r["bytes"] > 0
    assert os.path.basename(r["path"]) == r["sha256"][:16] + ".stl"


def test_file_scheme_rejected(tmp_path):
    out = str(tmp_path / "refs")
    r = fetch_stl.fetch("file:///etc/passwd", out)
    assert not r["success"] and r["errors"][0]["type"] == "bad_scheme"
    assert not os.path.exists(out)


def test_oversize_aborted(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch_stl, "MAX_BYTES", 100)
    out = str(tmp_path / "refs")
    with _serve(tmp_path) as server:
        r = fetch_stl.fetch(f"{server}/box.stl", out)
    assert not r["success"] and r["errors"][0]["type"] == "too_large"
    assert os.listdir(out) == []


def test_html_deleted(tmp_path):
    out = str(tmp_path / "refs")
    with _serve(tmp_path) as server:
        r = fetch_stl.fetch(f"{server}/page.html", out)
    assert not r["success"] and r["errors"][0]["type"] == "not_an_stl"
    assert os.listdir(out) == []
