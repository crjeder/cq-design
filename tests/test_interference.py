"""Tests for the shared interference primitive.

trimesh-generated box meshes (no CadQuery) so the suite stays fast. Covers the overlap
kernel, the exclusion set, the touch-vs-penetration boundary that keeps keep-out and
kinematic behaviors distinct, and the backend degrade signal.
"""

import builtins

import pytest
import trimesh

from interference import (
    check_interference,
    colliding_names,
    colliding_volumes,
    load_backend,
)


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


# ---- touch-vs-penetration boundary (volume semantics) --------------------------


def test_shallow_overlap_counts_when_tolerance_is_none():
    # 0.05 mm penetration: a real contact fcl reports as a hit. Any-contact semantics
    # (keep-out) flag it without measuring a volume.
    subject = _box((0, 0, 0))  # x in [-5, 5]
    others = [("shallow", _box((9.95, 0, 0)))]  # x in [4.95, 14.95] -> 0.05 mm overlap
    assert check_interference(subject, others, penetration_tol_mm3=None) == {"shallow"}


def test_flush_face_contact_is_not_interference():
    # Exactly abutting faces: the broadphase reports contact, the intersection volume is
    # zero. This is the designed-flush-contact case that depth thresholding got wrong.
    subject = _box((0, 0, 0))  # x in [-5, 5]
    others = [("flush", _box((10, 0, 0)))]  # x in [5, 15] -> touching at x=5, no volume
    assert check_interference(subject, others, penetration_tol_mm3=0.1) == set()


def test_overlap_below_volume_tolerance_ignored():
    # 0.001 mm over a 10x10 face = 0.1 mm^3, at the tolerance -> not interference.
    subject = _box((0, 0, 0))  # x in [-5, 5]
    others = [("sliver", _box((9.999, 0, 0)))]
    assert check_interference(subject, others, penetration_tol_mm3=0.1) == set()


def test_deep_penetration_counts_above_tolerance():
    subject = _box((0, 0, 0))  # x in [-5, 5]
    others = [("overlap", _box((9, 0, 0)))]  # x in [4, 14] -> 1 mm x 10 x 10 = 100 mm^3
    assert check_interference(subject, others, penetration_tol_mm3=0.1) == {"overlap"}


def test_measured_volume_matches_analytic_overlap():
    _trimesh, collision_manager = load_backend()
    manager = collision_manager()
    other = _box((9, 0, 0))  # 1 mm x 10 mm x 10 mm overlap = 100 mm^3
    manager.add_object("overlap", other)
    volumes = colliding_volumes(_box((0, 0, 0)), manager, 0.1, {"overlap": other})
    assert volumes["overlap"] == pytest.approx(100.0, rel=1e-3)


# ---- colliding_names against a prebuilt manager --------------------------------


def test_colliding_names_uses_prebuilt_manager():
    _trimesh, collision_manager = load_backend()
    manager = collision_manager()
    manager.add_object("a", _box((4, 0, 0)))
    manager.add_object("b", _box((100, 0, 0)))
    assert colliding_names(_box((0, 0, 0)), manager, None) == {"a"}


def test_volume_measurement_requires_fixed_meshes():
    _trimesh, collision_manager = load_backend()
    manager = collision_manager()
    manager.add_object("a", _box((4, 0, 0)))
    with pytest.raises(ValueError):
        colliding_names(_box((0, 0, 0)), manager, 0.1)


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


def test_load_backend_raises_when_boolean_engine_missing(monkeypatch):
    # No fallback to a weaker measure: a missing boolean engine must reach the caller's
    # check_skipped path, not silently degrade to depth thresholding.
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "manifold3d":
            raise ImportError("No module named 'manifold3d'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(ImportError):
        load_backend()
