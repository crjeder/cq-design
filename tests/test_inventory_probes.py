"""Every inventory entry declares probes that pass on its own default build, its params
match its function, and every declared edge set yields curves."""

import importlib
import inspect

import pytest

import probes as pr
from blocks.validate import load_inventory, validate_inventory

INVENTORY = load_inventory()


def _resolve(entry, attr):
    return getattr(importlib.import_module(entry["module"]), attr, None)


def test_inventory_validates():
    assert validate_inventory(INVENTORY) == []


def test_entry_without_probes_fails_validation():
    entry = {k: v for k, v in INVENTORY[0].items() if k != "probes"}
    assert any("'probes'" in e for e in validate_inventory([entry]))


@pytest.mark.parametrize("entry", INVENTORY, ids=[e["name"] for e in INVENTORY])
def test_params_match_function_signature(entry):
    sig = inspect.signature(_resolve(entry, entry["function"])).parameters
    assert set(entry["params"]) <= set(sig)
    required = {n for n, p in sig.items() if p.default is inspect.Parameter.empty}
    assert required <= set(entry["params"])
    assert set(entry.get("optional", [])) == {
        n for n in entry["params"] if sig[n].default is not inspect.Parameter.empty
    }


@pytest.mark.parametrize("entry", INVENTORY, ids=[e["name"] for e in INVENTORY])
def test_default_build_passes_own_probes(entry):
    probe_fn = _resolve(entry, entry["probes"])
    assert probe_fn is not None, f"{entry['name']}: no probe function {entry['probes']}"
    params = entry["defaults"]
    built = _resolve(entry, entry["function"])(**params)
    members = built.values() if isinstance(built, dict) else [built]
    import cadquery as cq

    shape = cq.Compound.makeCompound([s for m in members for s in m.solids().vals()])
    probes = probe_fn(**params)
    assert probes, f"{entry['name']}: probe function returned no probes"
    failed = [(p, got) for p in probes for ok, got in [pr.evaluate(p, shape)] if not ok]
    assert not failed, failed
    tol = 1e-6 * 10
    for p in probes:
        if p.p is not None:
            assert pr.face_distance(shape, p.p) >= max(pr.MIN_FACE_DIST_MM, 10 * tol), p


@pytest.mark.parametrize("entry", [e for e in INVENTORY if e["edge_sets"]], ids=lambda e: e["name"])
def test_declared_edge_sets_yield_curves(entry):
    sets = _resolve(entry, f"{entry['function']}_edge_sets")(**entry["defaults"])
    assert set(sets) == set(entry["edge_sets"])
    assert all(len(curves) >= 1 for curves in sets.values()), sets
