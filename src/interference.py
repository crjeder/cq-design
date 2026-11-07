#!/usr/bin/env python3
"""Shared static interference primitive.

One overlap test, reused by every stage that asks "do these two posed bodies touch?":
`keep_out_check` (a declared zone vs every foreign union) and the per-pose collision
inside `kinematic_check` (a swept union vs every union outside its subtree). Extracting
it here removes two copies of the trimesh + python-fcl machinery and makes the overlap
test unit-testable in isolation.

Overlap is determined in two stages. fcl is the **broadphase** -- it answers
touch/no-touch fast and reliably. When a tolerance is supplied, the actual interference
is then measured as the **volume of the boolean intersection** (manifold3d, via
`trimesh.boolean.intersection`).

The backend's per-contact penetration *depth* is deliberately not used as the measure.
It is computed per intersecting triangle pair and is ill-conditioned for the large
near-coplanar triangles that flat printed faces tessellate into: on a real assembly it
reported 7.2 mm for a 0.09 mm^3 true overlap, and was non-monotonic in the real overlap
(39.9 mm at one pose vs 30.0 mm at another four times deeper). Volume is physically
meaningful and monotonic, so designed flush contact measures ~0 and never reads as
binding.

Penetration semantics are a caller choice, not a fork:
- `penetration_tol_mm3=None` -> any broadphase contact counts (a bare touch is
  interference) and no boolean is computed. This is the keep-out semantics.
- `penetration_tol_mm3=<float>` -> a contact counts only when the measured intersection
  volume exceeds the tolerance (designed surface contact at a joint is not
  interference). This is the kinematic semantics.

`assembly_interference_check` is a further caller: it measures every touching pair of
union STLs with `_intersection_volume` (volume semantics, fixed epsilon).

Next intended caller: an assembly-clearance placeholder volume -- a declared PSEUDO
volume, posed like a keep-out zone, checked via `check_interference` with its own issue
`type`/`hint`. It plugs in here with no change to this module.

trimesh + python-fcl + manifold3d only; no CadQuery import.
"""

from collections.abc import Iterable
from typing import Any, Literal

# Boolean engine for the volume measurement. Named explicitly so a missing engine fails
# at `load_backend` (-> each caller's `check_skipped`) instead of silently picking
# whatever trimesh happens to find.
_BOOLEAN_ENGINE: Literal["manifold"] = "manifold"


def load_backend() -> tuple[Any, Any]:
    """Import the geometry backend. Return `(trimesh, CollisionManager)`.

    Raises `ImportError` if trimesh, python-fcl, the collision manager, or the boolean
    engine is missing, so each caller can translate the failure into its own
    `check_skipped` warning (keeping its own message/hint and the original exception
    detail). All are treated as one unit: there is deliberately no fallback to a weaker
    interference measure, since two measures with different sensitivity would make
    findings incomparable between runs and would reintroduce the depth-based false
    positives this module exists to avoid.
    """
    import fcl  # noqa: F401
    import manifold3d  # noqa: F401
    import trimesh
    from trimesh.collision import CollisionManager

    return trimesh, CollisionManager


def _intersection_volume(a: Any, b: Any) -> float:
    """Volume (mm^3) of the boolean intersection of two posed meshes, 0.0 if disjoint."""
    import trimesh

    result = trimesh.boolean.intersection([a, b], engine=_BOOLEAN_ENGINE)
    if result is None or len(result.faces) == 0:
        return 0.0
    return abs(float(result.volume))


def colliding_volumes(
    moving_mesh: Any,
    manager: Any,
    penetration_tol_mm3: float | None,
    fixed_meshes: dict[str, Any] | None = None,
) -> dict[str, float]:
    """Map each name in `manager` the moving mesh interferes with to the overlap volume.

    `manager` is a prebuilt `CollisionManager` holding each fixed body as a separately
    named object -- it is the broadphase, reused across poses. `fixed_meshes` maps those
    same names to the trimesh meshes they were built from, needed for the boolean; the
    manager itself only stores fcl geometry, so the meshes are passed rather than read
    back out of it. Required whenever `penetration_tol_mm3` is a float.

    With `penetration_tol_mm3 is None` any broadphase contact counts and no boolean is
    computed -- the reported volume is `0.0`, meaning "not measured". With a float, each
    contacted body's intersection volume is measured and only those above the tolerance
    are returned. A broadphase that over-reports (fcl works on convex geometry for convex
    inputs) is harmless: the volume measurement filters it, and a hull is a superset so
    there are no false negatives.
    """
    hit, names = manager.in_collision_single(moving_mesh, return_names=True)
    if not hit:
        return {}
    if penetration_tol_mm3 is None:
        return dict.fromkeys(names, 0.0)
    if fixed_meshes is None:
        raise ValueError("fixed_meshes is required when penetration_tol_mm3 is a float")

    volumes: dict[str, float] = {}
    for name in names:
        volume = _intersection_volume(moving_mesh, fixed_meshes[name])
        if volume > penetration_tol_mm3:
            volumes[name] = volume
    return volumes


def colliding_names(
    moving_mesh: Any,
    manager: Any,
    penetration_tol_mm3: float | None,
    fixed_meshes: dict[str, Any] | None = None,
) -> set[str]:
    """Return the names in `manager` the moving mesh interferes with.

    Thin wrapper over `colliding_volumes` for callers that only need the names.
    """
    return set(colliding_volumes(moving_mesh, manager, penetration_tol_mm3, fixed_meshes))


def check_interference(
    subject_mesh: Any,
    others: Iterable[tuple[str, Any]],
    *,
    exclude: frozenset[str] | set[str] = frozenset(),
    penetration_tol_mm3: float | None = None,
) -> set[str]:
    """Overlap the subject against `others` (each `(name, mesh)`), skipping `exclude`.

    Builds a `CollisionManager` over the non-excluded others and calls `colliding_names`
    once. Returns the set of colliding names. The backend must already be importable
    (call `load_backend` first to degrade gracefully).
    """
    from trimesh.collision import CollisionManager

    manager = CollisionManager()
    fixed_meshes = {}
    for name, mesh in others:
        if name in exclude:
            continue
        manager.add_object(name, mesh)
        fixed_meshes[name] = mesh
    return colliding_names(subject_mesh, manager, penetration_tol_mm3, fixed_meshes)
