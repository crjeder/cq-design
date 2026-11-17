"""Repo hygiene: every test reached, no retries, no unregistered src/ scripts.

Static checks only (text + ast); no CadQuery import. Each check is a function over a
root path so the negative tests can run it on a tmp tree.
"""

import ast
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CI_GLOBS = [
    ".github/workflows/*.yml",
    ".github/workflows/*.yaml",
    ".gitlab-ci.yml",
    "azure-pipelines.yml",
]
RETRY_PLUGINS = ("pytest-rerunfailures", "pytest-retry", "flaky")
# src/*.py modules exempt from the FILES/scripts/test registration rule.
SRC_ALLOWLIST: set[str] = set()


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def check_collection(root: Path) -> list[str]:
    """Findings for pytest exclusions in config/conftest and subset CI pytest steps."""
    found = []
    cfg = _text(root / "pyproject.toml") + "\n" + _text(root / "pytest.ini")
    for opt in ("--ignore", "--deselect"):
        if opt in cfg:
            found.append(f"pyproject.toml/pytest.ini uses {opt}")
    if "collect_ignore" in _text(root / "tests" / "conftest.py"):
        found.append("tests/conftest.py sets collect_ignore")
    for pattern in CI_GLOBS:
        for ci in root.glob(pattern):
            for line in _text(ci).splitlines():
                if "pytest" not in line:
                    continue
                if re.search(r"\.py\b", line) or re.search(r"\s-k\b", line):
                    found.append(f"{ci.name}: pytest step filters tests: {line.strip()}")
    return found


def check_no_retries(root: Path) -> list[str]:
    """Findings for retry plugins/flags, flaky marks, retry loops, bare skip/xfail."""
    found = []
    cfg = _text(root / "pyproject.toml")
    for name in RETRY_PLUGINS:
        if re.search(rf"[\"']{re.escape(name)}\b", cfg):
            found.append(f"pyproject.toml depends on {name}")
    if "--reruns" in cfg:
        found.append("pyproject.toml passes --reruns")
    for path in sorted((root / "tests").glob("test_*.py")):
        if path.name == Path(__file__).name:
            continue
        tree = ast.parse(_text(path), filename=str(path))
        found += [f"{path.name}:{n.lineno} {msg}" for n, msg in _walk(tree)]
    return found


def _mark_name(node: ast.AST) -> str | None:
    """Return 'skip'/'skipif'/'xfail'/'flaky' for a pytest.mark.<x> decorator or call."""
    target = node.func if isinstance(node, ast.Call) else node
    if not (isinstance(target, ast.Attribute) and isinstance(target.value, ast.Attribute)):
        return None
    return target.attr if target.value.attr == "mark" else None


def _walk(tree: ast.AST):
    called = {id(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and id(node) not in called:
            bare = _mark_name(node)
            if bare == "skip":
                yield node, "skip without reason"
            elif bare == "xfail":
                yield node, "xfail without strict=True"
        name = _mark_name(node) if isinstance(node, (ast.Attribute, ast.Call)) else None
        if name == "flaky":
            yield node, "uses pytest.mark.flaky"
        no_reason = isinstance(node, ast.Call) and not any(k.arg == "reason" for k in node.keywords)
        if name in ("skip", "skipif") and no_reason:
            yield node, f"{name} without reason"
        if isinstance(node, ast.Call) and name == "xfail":
            strict = [k for k in node.keywords if k.arg == "strict"]
            if not (strict and getattr(strict[0].value, "value", None) is True):
                yield node, "xfail without strict=True"
        if isinstance(node, (ast.For, ast.While)):
            for sub in ast.walk(node):
                if isinstance(sub, ast.ExceptHandler) and "AssertionError" in ast.dump(
                    sub.type or ast.Constant(None)
                ):
                    yield node, "retry loop around an assertion"
                    break


def check_src_registered(root: Path) -> list[str]:
    """Findings for src/*.py missing a FILES.md line, scripts.md entry, or referencing test."""
    files_md = _text(root / "FILES.md")
    scripts_md = _text(root / "reference" / "scripts.md")
    tests = "\n".join(_text(p) for p in (root / "tests").glob("*.py"))
    found = []
    for path in sorted((root / "src").glob("*.py")):
        stem = path.stem
        if stem in SRC_ALLOWLIST or stem.startswith("__"):
            continue
        name = path.name
        if not re.search(rf"\b{re.escape(name)}\b", files_md):
            found.append(f"src/{name}: no FILES.md line")
        if not re.search(rf"\b{re.escape(name)}\b", scripts_md):
            found.append(f"src/{name}: no reference/scripts.md entry")
        if not re.search(rf"\b{re.escape(stem)}\b", tests):
            found.append(f"src/{name}: no test references it")
    return found


def test_every_test_file_is_reached():
    assert check_collection(REPO) == []


def test_no_retries_or_bare_skips():
    assert check_no_retries(REPO) == []


def test_src_scripts_are_registered_and_tested():
    assert check_src_registered(REPO) == []


# ---- negative tests: each check must fail on a bad tree ----


def _tree(tmp_path, pyproject="", conftest="", ci=None, tests=None, src=None, files="", scripts=""):
    (tmp_path / "tests").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "reference").mkdir()
    (tmp_path / "pyproject.toml").write_text(pyproject)
    (tmp_path / "tests" / "conftest.py").write_text(conftest)
    for name, body in (tests or {}).items():
        (tmp_path / "tests" / name).write_text(body)
    for name in src or []:
        (tmp_path / "src" / name).write_text("")
    (tmp_path / "FILES.md").write_text(files)
    (tmp_path / "reference" / "scripts.md").write_text(scripts)
    if ci:
        wf = tmp_path / ".github" / "workflows"
        wf.mkdir(parents=True)
        (wf / "ci.yml").write_text(ci)
    return tmp_path


def test_exclusion_and_ci_subset_detected(tmp_path):
    root = _tree(
        tmp_path,
        pyproject='addopts = "--ignore=tests/a.py"',
        conftest="collect_ignore = ['x']",
        ci="run: pytest tests/test_a.py",
    )
    assert len(check_collection(root)) == 3


def test_ci_full_run_passes(tmp_path):
    root = _tree(tmp_path, ci="run: uv run pytest tests/")
    assert check_collection(root) == []


def test_retry_constructs_detected(tmp_path):
    body = (
        "import pytest\n"
        "@pytest.mark.skip\ndef test_a(): pass\n"
        "@pytest.mark.skipif(True, reason='r')\ndef test_b(): pass\n"
        "@pytest.mark.xfail\ndef test_c(): pass\n"
        "@pytest.mark.flaky\ndef test_d(): pass\n"
        "def test_e():\n    for _ in range(3):\n        try:\n            assert 1\n"
        "        except AssertionError:\n            continue\n"
    )
    root = _tree(tmp_path, pyproject='dev = ["pytest-rerunfailures"]', tests={"test_x.py": body})
    msgs = check_no_retries(root)
    assert len(msgs) == 5, msgs


def test_unregistered_script_detected(tmp_path):
    root = _tree(tmp_path, src=["foo.py"])
    assert len(check_src_registered(root)) == 3


def test_registered_script_passes(tmp_path):
    root = _tree(
        tmp_path,
        src=["foo.py"],
        files="foo.py  # x",
        scripts="### foo.py",
        tests={"test_foo.py": "import foo\n"},
    )
    assert check_src_registered(root) == []
