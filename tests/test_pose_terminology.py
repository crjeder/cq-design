"""Guard: retired frame terms stay out of docs, prompts, src and specs (no CadQuery)."""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RETIRED = re.compile(
    r"part[- ]frame|authored[- ]frame|assembled[- ]frame|print[- ]frame|build[- ]frame", re.I
)
EXEMPT = (
    "openspec/changes/",
    "documentation/DONE.md",
    "TODO.md",
    "documentation/todo-",
    "tests/test_pose_terminology.py",
)


def test_no_retired_frame_terms():
    files = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.split(".stdout.split()")
    hits = []
    for rel in files:
        if (
            not rel
            or rel.startswith(EXEMPT)
            or Path(rel).suffix not in {".md", ".py", ".json", ".txt"}
        ):
            continue
        for n, line in enumerate(
            (ROOT / rel).read_text(encoding="utf-8", errors="ignore").splitlines(), 1
        ):
            if RETIRED.search(line):
                hits.append(f"{rel}:{n}")
    assert not hits, hits
