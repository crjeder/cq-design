"""Lazy cq_warehouse import: importing blocks must not install the Shape patch.

These run in a fresh subprocess because the pytest session itself may already
have imported cq_warehouse (via other tests), which would mask the isolation.
"""

import os
import subprocess
import sys
import textwrap

import pytest

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")

pytest.importorskip("cq_warehouse", reason="cq_warehouse not installed")


def _run(code: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONPATH=SRC)
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)],
        capture_output=True,
        text=True,
        env=env,
    )


def test_importing_blocks_does_not_load_cq_warehouse():
    result = _run(
        """
        import sys
        from blocks import fillet_box  # noqa: F401
        import blocks.hardware  # noqa: F401
        from cadquery.occ_impl.shapes import Shape

        loaded = sorted(m for m in sys.modules if "cq_warehouse" in m)
        assert not loaded, f"cq_warehouse loaded by import: {loaded}"
        # Native cadquery _apply_transform, not the patched extensions version.
        mod = Shape._apply_transform.__module__
        assert mod.startswith("cadquery"), f"Shape patched on import: {mod}"
        print("ok")
        """
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_heat_set_boss_lazy_imports_extension():
    result = _run(
        """
        import sys
        from blocks.hardware import heat_set_boss
        assert "cq_warehouse.extensions" not in sys.modules

        wp = heat_set_boss("M3-0.5-6", d_outer=7, h=6)
        assert len(wp.vals()) >= 1

        assert "cq_warehouse.extensions" in sys.modules
        assert hasattr(wp, "insertHole")  # method installed by the lazy import
        print("ok")
        """
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout
