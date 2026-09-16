"""Append-only milestone log (build/journal.md).

One markdown line per durable pipeline fact, written by:

    python journal.py append build/journal.md phase3/part_accepted:lid "audit passed"

See skill/resume.md for the journal's format and resume contract. Stdlib only.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def append_line(path: str | Path, milestone: str, text: str) -> str:
    """Append `- <milestone>: <text>` to path (created if absent). Returns the line."""
    line = f"- {milestone}: {text}"
    path = Path(path)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    return line


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    ap = sub.add_parser("append", help="append one milestone line")
    ap.add_argument("journal", help="path to journal.md (e.g. build/journal.md)")
    ap.add_argument("milestone", help="<phase>/<milestone_key>, e.g. phase3/part_accepted:lid")
    ap.add_argument("text", help="the fact being recorded, one line")
    args = parser.parse_args(argv)

    try:
        append_line(args.journal, args.milestone, args.text)
    except OSError as exc:
        print(f"journal: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
