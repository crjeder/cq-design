"""Prose-layer checks: paths and CLI flags named in SKILL.md, commands/, skill/ and
prompts/ must still exist. Fast tier, no CadQuery."""

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PROSE = [
    ROOT / "SKILL.md",
    *sorted((ROOT / "commands").glob("*.md")),
    *sorted((ROOT / "skill").glob("*.md")),
    *sorted((ROOT / "prompts").glob("*.md")),
]
IDS = [p.relative_to(ROOT).as_posix() for p in PROSE]

PATH_RE = re.compile(r"(?<![\w.-])((?:src|skill|prompts|reference|templates)/[^\s`\"')\]|,;]+)")
PLACEHOLDER = set("<>{}*$")
SCRIPT_RE = re.compile(r"src/(\w+)\.py\b(.*)")
FLAG_RE = re.compile(r"(?<![\w-])(--[A-Za-z][\w-]*)")


def _exists(ref: str) -> bool:
    ref = ref.rstrip(".:")
    p = ROOT / ref
    if p.exists():
        return True
    # a name with spaces (reference/Engineering Design Rules.md) stops at the space
    return any(ROOT.glob(glob_escape(ref) + " *")) if p.parent.is_dir() else False


def glob_escape(s: str) -> str:
    return re.sub(r"([\[\]*?])", r"[\1]", s)


@pytest.mark.parametrize("prose", PROSE, ids=IDS)
def test_referenced_paths_exist(prose):
    missing = []
    for ref in PATH_RE.findall(prose.read_text(encoding="utf-8")):
        if PLACEHOLDER & set(ref):
            continue
        if not _exists(ref):
            missing.append(ref)
    assert not missing, f"{prose.name} references missing paths: {sorted(set(missing))}"


def _bash_commands(text: str):
    """Yield command lines from bash/sh fenced blocks, `\\` continuations joined."""
    for block in re.findall(r"```(?:bash|sh)\n(.*?)```", text, re.S):
        block = re.sub(r"\\\n\s*", " ", block)
        yield from block.splitlines()


def _flags_in(path: Path) -> set[str]:
    flags: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "add_argument":
            flags.update(
                a.value
                for a in node.args
                if isinstance(a, ast.Constant)
                and isinstance(a.value, str)
                and a.value.startswith("--")
            )
    return flags


def _script_flags(name: str) -> set[str] | None:
    path = ROOT / "src" / f"{name}.py"
    if not path.exists():
        return None
    flags = _flags_in(path)
    if re.search(r"add_\w+_argument\(", path.read_text(encoding="utf-8")):
        flags |= _flags_in(ROOT / "src" / "units.py")  # shared add_*_argument helpers
    return flags


@pytest.mark.parametrize("prose", PROSE, ids=IDS)
def test_cli_flags_match_argparse(prose):
    bad = []
    for line in _bash_commands(prose.read_text(encoding="utf-8")):
        m = SCRIPT_RE.search(line)
        if not m:
            continue
        known = _script_flags(m.group(1))
        if not known:  # missing script is the path test's job; no literal flags -> skip
            continue
        args = re.sub(r"\"[^\"]*\"|'[^']*'", "", m.group(2))  # drop quoted text
        bad += [f"{m.group(1)}.py {f}" for f in FLAG_RE.findall(args) if f not in known]
    assert not bad, f"{prose.name} uses flags unknown to argparse: {sorted(set(bad))}"
