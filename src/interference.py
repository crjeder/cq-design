#!/usr/bin/env python3
"""Shared static interference primitive.

One overlap test, reused by every stage that asks "do these two posed bodies touch?":
`keep_out_check` (a declared zone vs every foreign union) and the per-pose collision
inside `kinematic_check` (a swept union vs every union outside its subtree). Extracting
it here removes two copies of the trimesh + python-fcl machinery and makes the overlap
test unit-testable in isolation.

The core, `colliding_names`, takes a moving mesh and an already-built `CollisionManager`
of named fixed objects -- a prebuilt manager because the kinematic stage reuses one
manager across every swept pose and must not rebuild it per call. `check_interference`
is the static single-subject convenience: it builds the manager (honoring an exclusion
set) and calls the core once.

Penetration semantics are a caller choice, not a fork:
- `penetration_tol_mm=None` -> any contact counts (a bare touch is interference). This is
  the keep-out semantics.
- `penetration_tol_mm=<float>` -> a contact counts only when its deepest penetration
  exceeds the tolerance (designed surface contact at a joint is not interference). This
  is the kinematic semantics (called with 0.1).

Next intended caller: an assembly-clearance placeholder volume -- a declared PSEUDO
volume, posed like a keep-out zone, checked via `check_interference` with its own issue
`type`/`hint`. It plugs in here with no change to this module.

trimesh + python-fcl only; no CadQuery import.
"""

from collections.abc import Iterable
from typing import Any


def load_backend() -> tuple[Any, Any]:
    """Import the collision backend. Return `(trimesh, CollisionManager)`.

    Raises `ImportError` if trimesh, python-fcl, or the collision manager is missing, so
    each caller can translate the failure into its own `check_skipped` warning (keeping
    its own message/hint and the original exception detail).
    """
    import fcl  # noqa: F401
    import trimesh
    from trimesh.collision import CollisionManager

    return trimesh, CollisionManager


def colliding_names(moving_mesh: Any, manager: Any, penetration_tol_mm: float | None) -> set[str]:
    """Return the names in `manager` the moving mesh interferes with.

    `manager` is a prebuilt `CollisionManager` holding each fixed body as a separately
    named object. With `penetration_tol_mm is None` any contact counts; with a float,
    only a contact whose deepest penetration exceeds the tolerance counts.
    """
    hit, names, data = manager.in_collision_single(moving_mesh, return_names=True, return_data=True)
    if not hit:
        return set()
    if penetration_tol_mm is None:
        return set(names)
    max_depth = max((abs(c.depth) for c in data), default=0.0)
    return set(names) if max_depth > penetration_tol_mm else set()


def check_interference(
    subject_mesh: Any,
    others: Iterable[tuple[str, Any]],
    *,
    exclude: frozenset[str] | set[str] = frozenset(),
    penetration_tol_mm: float | None = None,
) -> set[str]:
    """Overlap the subject against `others` (each `(name, mesh)`), skipping `exclude`.

    Builds a `CollisionManager` over the non-excluded others and calls `colliding_names`
    once. Returns the set of colliding names. The backend must already be importable
    (call `load_backend` first to degrade gracefully).
    """
    from trimesh.collision import CollisionManager

    manager = CollisionManager()
    for name, mesh in others:
        if name in exclude:
            continue
        manager.add_object(name, mesh)
    return colliding_names(subject_mesh, manager, penetration_tol_mm)
