"""Download one reference STL into build/refs/ with scheme, redirect, size and parse checks."""

import argparse
import contextlib
import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MAX_BYTES = 50 * 1024 * 1024
MAX_REDIRECTS = 3
REFS_DIR = os.path.join("build", "refs")


class _Limited(urllib.request.HTTPRedirectHandler):
    max_redirections = MAX_REDIRECTS

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlparse(newurl).scheme not in ("http", "https"):
            raise urllib.error.URLError(f"redirect to non-http scheme: {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _err(kind: str, message: str, hint: str) -> dict:
    return {
        "success": False,
        "errors": [{"type": kind, "message": message, "hint": hint}],
        "path": None,
        "bytes": 0,
        "sha256": None,
    }


def fetch(url: str, out_dir: str = REFS_DIR) -> dict:
    """Download url as an STL under out_dir; return the JSON contract dict."""
    if urllib.parse.urlparse(url).scheme not in ("http", "https"):
        return _err(
            "bad_scheme", f"only http and https are allowed: {url}", "use a direct http(s) STL link"
        )
    os.makedirs(out_dir, exist_ok=True)
    tmp = os.path.join(out_dir, ".download.tmp")
    digest = hashlib.sha256()
    size = 0
    try:
        opener = urllib.request.build_opener(_Limited)
        with opener.open(url, timeout=30) as resp, open(tmp, "wb") as fh:
            while chunk := resp.read(65536):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise ValueError(f"download exceeds {MAX_BYTES} bytes")
                digest.update(chunk)
                fh.write(chunk)
    except ValueError as e:
        _rm(tmp)
        return _err("too_large", str(e), "find a smaller reference or measure by other means")
    except (urllib.error.URLError, OSError) as e:
        _rm(tmp)
        return _err("download_failed", str(e), "check the URL is a direct STL link")
    sha = digest.hexdigest()
    path = os.path.join(out_dir, f"{sha[:16]}.stl")
    os.replace(tmp, path)
    try:
        from mesh_io import load_mesh

        load_mesh(path)
    except ValueError as e:
        _rm(path)
        return _err("not_an_stl", str(e), "the URL did not serve a valid STL")
    return {
        "success": True,
        "errors": [],
        "path": path.replace(os.sep, "/"),
        "bytes": size,
        "sha256": sha,
    }


def _rm(path: str) -> None:
    with contextlib.suppress(OSError):
        os.remove(path)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", required=True)
    args = ap.parse_args()
    result = fetch(args.url)
    print(json.dumps(result))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
