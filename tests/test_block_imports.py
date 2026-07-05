"""Flat block-import contract (spec: block-import-injection).

Every block registered in inventory.json must resolve via `from blocks import
<name>`, and the runner must inject nothing -- a script that calls a block
without importing it fails with NameError.
"""

import importlib
import json
import os
import subprocess
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO_ROOT, "src")
INVENTORY = os.path.join(SRC, "blocks", "inventory.json")


def _inventory_names() -> list[str]:
    with open(INVENTORY, encoding="utf-8") as f:
        return [entry["name"] for entry in json.load(f)]


@pytest.mark.parametrize("name", _inventory_names())
def test_every_inventory_block_is_flat_importable(name: str):
    blocks = importlib.import_module("blocks")
    assert hasattr(blocks, name), (
        f"{name} is in inventory.json but not re-exported by blocks/__init__.py; "
        "a flat `from blocks import "
        f"{name}` would fail"
    )


def test_runner_does_not_inject_block_imports(tmp_path):
    """A script that uses a block without importing it must NameError.

    This proves the shim performs no import injection: nothing binds block
    names for the script; the script alone is responsible.
    """
    script = tmp_path / "no_import.py"
    script.write_text("result = hollow_box(30, 20, 15, wall=1.5, floor_t=1.5, corner_r=2)\n")

    env = dict(os.environ, PYTHONPATH=SRC)
    proc = subprocess.run(
        [sys.executable, os.path.join(SRC, "run_model_shim.py"), str(script)],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        env=env,
    )
    assert proc.returncode != 0
    assert "NameError" in proc.stderr
    assert "hollow_box" in proc.stderr
