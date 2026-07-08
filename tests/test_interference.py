"""Tests for the shared interference primitive.

trimesh-generated box meshes (no CadQuery) so the suite stays fast. Covers the overlap
kernel, the exclusion set, the touch-vs-penetration boundary that keeps keep-out and
kinematic behaviors distinct, and the backend degrade signal.
"""

import builtins

import pytest
import trimesh

from interference import check_interference, colliding_names, load_backend


def _box(center, extents=(10, 10, 10)):
    mesh = trimesh.creation.box(extents=extents)
    mesh.apply_translation(center)
    return mesh


# ---- check_interference: overlap / no-overlap / exclusion ----------------------


def test_overlapping_body_reported():
    subject = _box((0, 0, 0))  # x in [-5, 5]
    others = [("a", _box((4, 0, 0))), ("b", _box((100, 0, 0)))]  # a overlaps, b far away
    assert check_interference(subject, others) == {"a"}


def test_no_overlap_reports_nothing():
    subject = _box((0, 0, 0))
    others = [("a", _box((100, 0, 0))), ("b", _box((-100, 0, 0)))]
    assert check_interference(subject, others) == set()


def test_excluded_body_not_tested():
    subject = _box((0, 0, 0))
    others = [("self", _box((4, 0, 0)))]  # would overlap, but excluded
    assert check_interference(subject, others, exclude={"self"}) == set()


def test_exclusion_only_skips_named_body():
    subject = _box((0, 0, 0))
    others = [("self", _box((4, 0, 0))), ("foreign", _box((4, 0, 0)))]
    assert check_interference(subject, others, exclude={"self"}) == {"foreign"}


# ---- touch-vs-penetration boundary (D2) ----------------------------------------


def test_shallow_overlap_counts_when_tolerance_is_none():
    # 0.05 mm penetration: a real contact fcl reports as a hit, below any joint tolerance.
    subject = _box((0, 0, 0))  # x in [-5, 5]
    others = [("shallow", _box((9.95, 0, 0)))]  # x in [4.95, 14.95] -> 0.05 mm overlap
    assert check_interference(subject, others, penetration_tol_mm=None) == {"shallow"}


def test_shallow_overlap_ignored_below_penetration_tolerance():
    subject = _box((0, 0, 0))  # x in [-5, 5]
    others = [("shallow", _box((9.95, 0, 0)))]  # 0.05 mm overlap, below 0.1 mm tolerance
    assert check_interference(subject, others, penetration_tol_mm=0.1) == set()


def test_deep_penetration_counts_above_tolerance():
    subject = _box((0, 0, 0))  # x in [-5, 5]
    others = [("overlap", _box((9, 0, 0)))]  # x in [4, 14] -> 1 mm penetration
    assert check_interference(subject, others, penetration_tol_mm=0.1) == {"overlap"}


# ---- colliding_names against a prebuilt manager --------------------------------


def test_colliding_names_uses_prebuilt_manager():
    _trimesh, collision_manager = load_backend()
    manager = collision_manager()
    manager.add_object("a", _box((4, 0, 0)))
    manager.add_object("b", _box((100, 0, 0)))
    assert colliding_names(_box((0, 0, 0)), manager, None) == {"a"}


# ---- backend degrade -----------------------------------------------------------


def test_load_backend_raises_when_fcl_missing(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "fcl":
            raise ImportError("No module named 'fcl'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(ImportError):
        load_backend()
