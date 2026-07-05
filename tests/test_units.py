"""Tests for units.py: part -> unions expansion and keep-out zone extraction.

`resolve_unions`/`resolve_keep_out` are duck-typed over whatever `result` values a script
returns, so plain strings stand in for Workplanes here -- no CadQuery needed.
"""

import pytest

from units import KEEP_OUT_KEY, keep_out_stl_name, resolve_keep_out, resolve_unions


def _part(pid, unions=None):
    part = {"id": pid}
    if unions is not None:
        part["unions"] = unions
    return part


def test_resolve_unions_ignores_keep_out_key_when_declared():
    part = _part("enclosure", unions=[{"id": "enclosure"}])
    result = {"enclosure": "WP_ENCLOSURE", "keep_out": {"zone1": "WP_ZONE"}}
    assert resolve_unions(part, result) == [("enclosure", "WP_ENCLOSURE")]


def test_resolve_unions_ignores_keep_out_key_when_undeclared():
    part = _part("solo")
    result = {"solo": "WP_SOLO", "keep_out": {"zone1": "WP_ZONE"}}
    assert resolve_unions(part, result) == [("solo", "WP_SOLO")]


def test_resolve_unions_multi_union_plus_keep_out():
    part = _part("hinge", unions=[{"id": "leaf_a"}, {"id": "leaf_b"}])
    result = {
        "leaf_a": "WP_A",
        "leaf_b": "WP_B",
        "keep_out": {"clearance": "WP_ZONE"},
    }
    assert resolve_unions(part, result) == [("leaf_a", "WP_A"), ("leaf_b", "WP_B")]


def test_resolve_unions_mismatch_still_raises_ignoring_keep_out():
    part = _part("hinge", unions=[{"id": "leaf_a"}, {"id": "leaf_b"}])
    result = {"leaf_a": "WP_A", "WRONG": "WP_B", "keep_out": {"z": "WP_ZONE"}}
    with pytest.raises(ValueError, match="do not match declared unions"):
        resolve_unions(part, result)


def test_resolve_keep_out_extracts_zones():
    part = _part("enclosure")
    result = {"enclosure": "WP", "keep_out": {"z1": "WP_Z1", "z2": "WP_Z2"}}
    assert set(resolve_keep_out(part, result)) == {("z1", "WP_Z1"), ("z2", "WP_Z2")}


def test_resolve_keep_out_absent_returns_empty():
    part = _part("enclosure")
    result = {"enclosure": "WP"}
    assert resolve_keep_out(part, result) == []


def test_resolve_keep_out_non_dict_result_returns_empty():
    part = _part("solo")
    assert resolve_keep_out(part, "WP_PLAIN") == []


def test_keep_out_stl_name_is_part_qualified_and_prefixed():
    name = keep_out_stl_name("enclosure", "screwdriver_clearance")
    assert name == f"{KEEP_OUT_KEY}__enclosure__screwdriver_clearance.stl"
