"""documentation/SBOM.md stays in sync with pyproject.toml and the source tree."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SBOM = (ROOT / "documentation" / "SBOM.md").read_text(encoding="utf-8")
PYPROJECT = (ROOT / "pyproject.toml").read_text(encoding="utf-8")


def _section(title: str) -> str:
    """Return the body of the SBOM `## <title>` section."""
    match = re.search(rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", SBOM, re.M | re.S)
    assert match, f"SBOM.md has no '## {title}' section"
    return match.group(1)


def _norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _runtime_deps() -> set[str]:
    """Package names in [project] dependencies (regex: tomllib is 3.11+)."""
    block = re.search(r"^dependencies = \[(.*?)^\]", PYPROJECT, re.M | re.S)
    assert block, "pyproject.toml has no [project] dependencies list"
    names = re.findall(r'^\s*"([A-Za-z0-9_.-]+)', block.group(1), re.M)
    return {_norm(n) for n in names}


def _sbom_packages() -> set[str]:
    rows = _section("1. Third-party package dependencies")
    return {_norm(n) for n in re.findall(r"^\| \[([^\]]+)\]", rows, re.M)}


def test_every_runtime_dependency_is_credited() -> None:
    missing = _runtime_deps() - _sbom_packages()
    assert not missing, f"runtime deps with no SBOM.md section-1 row: {sorted(missing)}"


def test_no_stale_dependency_rows() -> None:
    stale = _sbom_packages() - _runtime_deps()
    assert not stale, f"SBOM.md section-1 rows not in pyproject dependencies: {sorted(stale)}"


def test_adapted_code_paths_exist() -> None:
    body = _section("2. Code and design ideas adapted from other projects")
    paths = []
    for span in re.findall(r"`([^`]+)`", body):
        path = span.split(" --")[0]
        if "/" in path and path.endswith((".py", ".md")):
            paths.append(path)
    assert paths, "no repo paths found in SBOM.md section 2"
    missing = [p for p in paths if not any(ROOT.glob(p))]
    assert not missing, f"SBOM.md section 2 names files that do not exist: {missing}"
