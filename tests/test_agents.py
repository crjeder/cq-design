"""Agent definitions: frontmatter, minimal tools, and no general-purpose spawns in prose."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROLES = ["sourcing", "research", "planner", "builder", "auditor"]
HEAVY = ("mcp__", "Artifact", "browser", "Terminal", "visualize")


def _front(role):
    text = (ROOT / "agents" / f"{role}.md").read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---", text, re.S)
    assert match
    block = match.group(1)
    return dict(line.split(": ", 1) for line in block.splitlines())


def test_agent_frontmatter_and_minimal_tools():
    for role in ROLES:
        fm = _front(role)
        assert fm["name"] == f"cq-design-{role}"
        tools = json.loads(fm["tools"])
        assert "Bash" in tools and "Read" in tools
        assert not any(h in t for t in tools for h in HEAVY)
        web = {"WebSearch", "WebFetch"} & set(tools)
        assert bool(web) == (role in ("sourcing", "research"))


def test_models_cheap_roles_sonnet_planner_opus():
    for role in ROLES:
        want = "opus" if role == "planner" else "sonnet"
        assert _front(role)["model"] == want


def test_default_config_has_all_roles():
    cfg = json.loads((ROOT / "src/skill_config.default.json").read_text(encoding="utf-8"))
    for key in ("planner", "part_author", "fix_loop", "sourcing", "research", "auditor"):
        assert cfg["models"][key]


def test_no_general_purpose_spawn_in_prose():
    files = [ROOT / "SKILL.md", *(ROOT / "skill").glob("*.md"), *(ROOT / "commands").glob("*.md")]
    for f in files:
        assert "general-purpose" not in f.read_text(encoding="utf-8"), f


def test_spawn_prose_passes_agent_model():
    for role in ROLES:
        hits = [
            line
            for f in (ROOT / "skill").glob("phase*.md")
            for line in f.read_text(encoding="utf-8").splitlines()
            if f"cq-design-{role}" in line and "spawn" in line.lower()
        ]
        assert hits, role
    prose = "\n".join(f.read_text(encoding="utf-8") for f in (ROOT / "skill").glob("phase*.md"))
    assert prose.count("agent_model") >= 5
    for role in ROLES:
        assert f"`cq-design:{role}`" in prose, role
