#!/usr/bin/env python3
"""Write a minimal, cadquery-only deliverable: each part script plus only the skill
helpers it imports.

For every <parts-dir>/*.py (except build.py) copies the script into <out>, then copies
the helper modules (cq_verify, cq_compat, blocks/) that the scripts import, directly or
through another copied helper. Also writes <out>/pyproject.toml and <out>/README.md and
copies parameters.py when present. Overwrites on every run.

Usage:
    python export_standalone.py [--parts-dir build] [--out standalone] [--parameters parameters.py]
"""

import argparse
import ast
import shutil
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
HELPERS = ("cq_verify", "cq_compat", "blocks")
WAREHOUSE_MARKERS = ("cq_warehouse", "heat_set_boss")
STDLIB = sys.stdlib_module_names

WAREHOUSE_SOURCE = (
    '\n[tool.uv.sources]\ncq-warehouse = { git = "https://github.com/gumyr/cq_warehouse.git" }\n'
)

PYPROJECT = """[project]
name = "cq-design-part"
version = "0.1.0"
requires-python = ">=3.10,<3.13"
dependencies = [
    "cadquery>=2.6.1,<3",{warehouse_dep}
]
{sources}"""


def _imports(path: Path) -> set[str]:
    """Top-level module names imported by a python file."""
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names


def _copy_helper(name: str, out: Path) -> list[Path]:
    """Copy one helper into out; return the copied .py files."""
    if name == "blocks":
        shutil.copytree(
            SRC / name, out / name, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__")
        )
        return sorted((out / name).rglob("*.py"))
    shutil.copy(SRC / f"{name}.py", out / f"{name}.py")
    return [out / f"{name}.py"]


def export(parts_dir: Path, out: Path, parameters: Path | None = None) -> list[str]:
    """Write the standalone directory; return the part ids exported."""
    out.mkdir(parents=True, exist_ok=True)
    scripts = sorted(p for p in parts_dir.glob("*.py") if p.name != "build.py")
    shipped = []
    for script in scripts:
        shutil.copy(script, out / script.name)
        shipped.append(out / script.name)
    if parameters and parameters.exists():
        shutil.copy(parameters, out / parameters.name)

    copied: set[str] = set()
    queue = list(shipped)
    external: set[str] = set()
    while queue:
        for name in _imports(queue.pop()):
            if name in HELPERS and name not in copied:
                copied.add(name)
                queue.extend(_copy_helper(name, out))
            elif name not in HELPERS and name not in STDLIB and name not in ("cadquery", "cq"):
                external.add(name)
    external -= {p.stem for p in out.glob("*.py")}

    all_py = [*out.glob("*.py"), *out.rglob("blocks/*.py")]
    needs_warehouse = any(
        m in p.read_text(encoding="utf-8") for p in all_py for m in WAREHOUSE_MARKERS
    )
    (out / "pyproject.toml").write_text(
        PYPROJECT.format(
            warehouse_dep='\n    "cq-warehouse",' if needs_warehouse else "",
            sources=WAREHOUSE_SOURCE if needs_warehouse else "",
        ),
        encoding="utf-8",
    )
    _write_readme(out, [s.stem for s in scripts], sorted(external))
    return [s.stem for s in scripts]


def _write_readme(out: Path, part_ids: list[str], external: list[str]) -> None:
    lines = [
        "# Standalone parts",
        "",
        "Run from this directory (`uv sync`, then `uv run python <part>.py`).",
        "Each script builds a CadQuery `result`; edit its `# PARAMETERS` block to resize.",
        "",
    ]
    lines += [f"- `{pid}.py`" for pid in part_ids]
    if external:
        lines += [
            "",
            "Imports this export could not resolve (install them yourself): " + ", ".join(external),
        ]
    (out / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parts-dir", default="build")
    parser.add_argument("--out", default="standalone")
    parser.add_argument("--parameters", default="parameters.py")
    args = parser.parse_args()
    ids = export(Path(args.parts_dir), Path(args.out), Path(args.parameters))
    print(f"Wrote {len(ids)} part(s) to {Path(args.out).resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
