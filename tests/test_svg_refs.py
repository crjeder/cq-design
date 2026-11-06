"""Every SVG referenced from tracked prose exists and parses; shipped prose has no box art."""

import re
import xml.dom.minidom as minidom
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROSE: list[Path] = []
for pattern in ("*.md", "skill/*.md", "reference/*.md", "prompts/*.md", "commands/*.md"):
    PROSE += sorted(ROOT.glob(pattern))
PROSE.append(ROOT / "documentation" / "Knowledge Domains.md")
IMG = re.compile(r"!\[[^\]]*\]\(([^)\s]+\.svg)\)")
BOX = re.compile(r"[\u250c\u2514\u251c\u2502\u2510\u2518\u25b2\u25bc\u25ba]")


def test_referenced_svgs_exist_and_parse():
    seen = 0
    for md in PROSE:
        for ref in IMG.findall(md.read_text(encoding="utf-8")):
            path = md.parent / ref
            assert path.is_file(), f"{md.name}: missing {ref}"
            root = minidom.parse(str(path)).documentElement
            assert root is not None and root.tagName == "svg"
            seen += 1
    assert seen >= 2


def test_no_box_drawing_art_in_prose():
    for md in PROSE:
        assert not BOX.search(md.read_text(encoding="utf-8")), md
