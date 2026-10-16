#!/usr/bin/env python3
"""FEM stress advisor: solve a declared load case on a part's STEP geometry.

Tet-meshes only the part's wall-thickness shell -- built from its exported STEP via
OCC's `addThickSolid`, one uniform thickness from the plan's `constraints.wall_min_mm`
applied to every face -- never the full solid volume, since the interior is sparse
infill in a real print (see the `fem-wall-shell-solve` design doc). Solves ONE
linear-static isotropic load case (scikit-fem) on that shell, and evaluates an
anisotropic FDM failure index for every candidate print orientation by rotating the
solved stress tensor -- one solve serves every candidate (see the `fem-stress-advisor`
design doc). Every boundary condition is resolved from the part's declared `load`
(magnitude_n, applied_at, applied_dir, grounded_at) and its named `interfaces[]`;
nothing is inferred from the bounding box or any other geometric heuristic.

This is an ADVISOR, never a gate: it always exits 0, adds no quality_gate.py
stage, and a high failure index is reported, not blocked on. Any missing input
(no load case declared, an anchor naming an interface without position_mm, an
unrecognized material) or missing dependency (the optional `fem` group not
installed) degrades to `{"status": "skipped", "reason": ...}`, also exit 0.

Usage:
    python3 fem_check.py part.step --plan BUILD_PLAN.json --part bracket --mesh-size 1.5

Mesh size is required, not defaulted: convergence is the one thing about an FEM
result a reader must be able to interrogate (see `fem-stress-advisor` design's
"Mesh size is the author's, not a default"). An implausible result -- extreme
concentration ratio, a failure index the geometry doesn't suggest, an unexpected
peak location -- is grounds to re-run at a smaller --mesh-size and compare
fi_p99 between the two runs before citing either.
"""

import argparse
import json
import os
import sys
from typing import Any

import numpy as np

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_MATERIALS_PATH = os.path.join(_THIS_DIR, "material_properties.json")

# fi_max / fi_p99 above this is reported as a stress concentration (peak confined to a
# small neighbourhood -- characteristic of a sharp re-entrant corner, not an undersized
# section); at or below, the elevated stress is spread over a real volume. Starting
# value, not derived -- see the design doc's Open Questions (needs calibrating against a
# filleted/unfilleted reference pair).
CONCENTRATION_THRESHOLD = 3.0


def _load_json(path: str) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _skip(reason: str) -> dict:
    return {"status": "skipped", "reason": reason}


def _resolve_part(plan: dict, part_id: str) -> dict | None:
    for part in plan.get("parts", []):
        if part.get("id") == part_id:
            return part
    return None


def _resolve_material(plan: dict, materials_path: str = _MATERIALS_PATH) -> dict | None:
    """The plan's material's entry from material_properties.json, or None."""
    material = plan.get("material")
    props = _load_json(materials_path)
    return props["materials"].get(material)


def _resolve_interface(part: dict, name: str) -> tuple[dict | None, str | None]:
    """Return (interface, None) or (None, reason) for a named interfaces[] entry."""
    for interface in part.get("interfaces", []):
        if interface.get("name") == name:
            if not interface.get("position_mm"):
                return None, f"interface '{name}' has no position_mm"
            if not interface.get("diameter_mm") and not interface.get("size_mm"):
                return None, f"interface '{name}' has no diameter_mm or size_mm (no footprint)"
            return interface, None
    return None, f"interface '{name}' not found on this part"


def _footprint_radius(interface: dict) -> float:
    if interface.get("diameter_mm"):
        return float(interface["diameter_mm"]) / 2.0
    return float(max(interface["size_mm"])) / 2.0


def _resolve_boundary_conditions(part: dict) -> tuple[dict | None, str | None]:
    """Resolve the part's `load` into applied/grounded interface footprints.

    Returns (bc_dict, None) on success, or (None, skip_reason). `bc_dict` has
    `magnitude_n`, `dir` (the applied traction direction, `applied_dir` or `dir`),
    `applied` (name, interface), and `grounded` (list of (name, interface)).
    """
    load = part.get("load")
    if not load:
        return None, "part declares no 'load'"
    magnitude_n = load.get("magnitude_n")
    if magnitude_n is None:
        return None, "load declares no magnitude_n"
    applied_at = load.get("applied_at")
    if not applied_at:
        return None, "load declares no applied_at"
    grounded_at = load.get("grounded_at")
    if not grounded_at:
        return None, "load declares no grounded_at"

    applied_iface, reason = _resolve_interface(part, applied_at)
    if applied_iface is None:
        return None, f"applied_at: {reason}"

    grounded = []
    for name in grounded_at:
        iface, reason = _resolve_interface(part, name)
        if iface is None:
            return None, f"grounded_at: {reason}"
        grounded.append((name, iface))

    direction = load.get("applied_dir") or load.get("dir")
    if not direction:
        return None, "load declares no dir or applied_dir to apply the traction along"

    return (
        {
            "magnitude_n": float(magnitude_n),
            "dir": np.asarray(direction, dtype=float),
            "applied": (applied_at, applied_iface),
            "grounded": grounded,
        },
        None,
    )


def _resolve_shell_thicknesses(plan: dict, plan_path: str | None = None) -> tuple[float, float]:
    """(wall_mm, topbot_mm) from the plan's `constraints` -- wall thickness is
    `constraints.wall_min_mm` directly (already the physical thickness the constraint
    represents, not re-derived through a wall-loop-count round-trip); top/bottom shell
    thickness is `constraints.top_bottom_layers` (default 4) times the layer height.

    The layer height is read from `profile.json`'s optional `motion` block next
    to `plan_path`, exactly as `quality_gate.py::_emit_print_recipe` reads it, so the two
    never quote different top/bottom-thickness numbers for the same plan; falls back to
    `nozzle_mm * 0.5` when no `motion` block is declared or `plan_path` is not given."""
    constraints = plan.get("constraints", {})
    wall_mm = constraints.get("wall_min_mm", 1.2)
    top_bottom_layers = constraints.get("top_bottom_layers", 4)

    layer_height_mm = plan.get("nozzle_mm", 0.4) * 0.5
    if plan_path is not None:
        profile_path = os.path.join(os.path.dirname(os.path.abspath(plan_path)), "profile.json")
        if os.path.isfile(profile_path):
            motion = _load_json(profile_path).get("motion")
            if motion:
                layer_height_mm = motion["layer_height_mm"]

    topbot_mm = top_bottom_layers * layer_height_mm
    return wall_mm, topbot_mm


def _thickness_mismatch_warning(wall_mm: float, topbot_mm: float) -> dict | None:
    """A `thickness_mismatch_warning` dict when the two shell thicknesses diverge by more
    than 25% -- the uniform-thickness solve treats every face the same, which gets less
    defensible as the profile's own wall and top/bottom settings diverge. None when
    they're within 25% of each other."""
    pct_diff = abs(wall_mm - topbot_mm) / max(wall_mm, topbot_mm)
    if pct_diff <= 0.25:
        return None
    return {
        "wall_min_mm": round(wall_mm, 4),
        "top_bottom_mm": round(topbot_mm, 4),
        "pct_diff": round(pct_diff, 4),
        "message": (
            f"wall thickness ({wall_mm:.2f} mm) and top/bottom shell thickness "
            f"({topbot_mm:.2f} mm) differ by {pct_diff:.0%} -- the solve's uniform-thickness "
            "assumption treats every face the same, which is less defensible the more these "
            "diverge"
        ),
    }


def _probe_dependencies() -> tuple[Any, Any, str | None]:
    """Import gmsh and skfem; return (gmsh, skfem, None) or (None, None, reason)."""
    try:
        import gmsh  # type: ignore[import-not-found]
    except ImportError:
        return (
            None,
            None,
            (
                "gmsh not installed (optional 'fem' dependency group; "
                "run 'uv sync --group fem' to enable the FEM advisor)"
            ),
        )
    try:
        import skfem  # type: ignore[import-not-found]
    except ImportError:
        return (
            None,
            None,
            (
                "scikit-fem not installed (optional 'fem' dependency group; "
                "run 'uv sync --group fem' to enable the FEM advisor)"
            ),
        )
    return gmsh, skfem, None


def mesh_step(gmsh_mod: Any, step_path: str, mesh_size: float, wall_thickness_mm: float) -> dict:
    """Tet-mesh only the part's wall-thickness shell (the material the slicer actually
    lays down solid), not its full solid volume -- ignoring infill gives a conservative
    lower bound on stiffness/strength (see the fem-wall-shell-solve design doc). Every
    face gets the same `wall_thickness_mm`, matching the slicer's own single "wall loops"
    setting (no vertical/horizontal split).

    Builds the hollow shell in two OCC steps, verified empirically against the pinned
    gmsh version (a bare `addThickSolid(tag, [], +offset)` with an empty excluded-face
    list does NOT hollow the solid in place -- it returns a new solid uniformly offset
    outward (positive) or inward (negative) from the original, not the wall material
    between the two):
    1. `addThickSolid(tag, [], -wall_thickness_mm)` (negative offset) on each solid volume
       gives the inward-offset cavity solid -- the shape of the void the slicer's infill
       region would occupy.
    2. `occ.cut([original], [cavity], removeTool=True)` subtracts that cavity from the
       original solid, leaving exactly the wall material as a single closed hollow solid
       whose outer boundary matches the original part -- consumes the original tag itself
       (per `removeTool`/the default `removeObject`), so nothing extra to remove before
       meshing.

    Returns node coords (n,3), tet node indices (m,4, 0-based into the node array), and
    boundary triangle node indices (k,3) for the print-orientation candidate enumeration.
    Raises on a gmsh failure (including a degenerate/self-intersecting shell on a local
    feature thinner than the wall thickness) -- the caller turns that into a skipped
    result."""
    gmsh_mod.initialize()
    try:
        gmsh_mod.option.setNumber("General.Terminal", 0)
        imported = gmsh_mod.model.occ.importShapes(step_path)
        solid_tags = [tag for dim, tag in imported if dim == 3]
        for tag in solid_tags:
            cavity = gmsh_mod.model.occ.addThickSolid(tag, [], -wall_thickness_mm)
            gmsh_mod.model.occ.cut([(3, tag)], cavity, removeTool=True)
        gmsh_mod.model.occ.synchronize()
        gmsh_mod.option.setNumber("Mesh.MeshSizeMax", mesh_size)
        gmsh_mod.model.mesh.generate(3)

        tags, xyz, _ = gmsh_mod.model.mesh.getNodes()
        points = np.asarray(xyz, dtype=float).reshape(-1, 3)
        tag_to_idx = {int(t): i for i, t in enumerate(tags)}

        etypes, etags, enodes = gmsh_mod.model.mesh.getElements(dim=3)
        tet_type_idx = list(etypes).index(4)  # 4 = 4-node (linear) tetrahedron
        tet_tags = np.asarray(enodes[tet_type_idx]).reshape(-1, 4)
        tets = np.vectorize(tag_to_idx.get)(tet_tags)

        setypes, _, senodes = gmsh_mod.model.mesh.getElements(dim=2)
        tri_type_idx = list(setypes).index(2)  # 2 = 3-node triangle
        tri_tags = np.asarray(senodes[tri_type_idx]).reshape(-1, 3)
        boundary_tris = np.vectorize(tag_to_idx.get)(tri_tags)
    finally:
        gmsh_mod.finalize()

    # getNodes() can return nodes not referenced by any tet (e.g. leftover lower-dimension
    # mesh entities from a boolean op) -- an unreferenced node contributes an all-zero row
    # to the global stiffness matrix, which is an exact (not just ill-conditioned)
    # singularity. Compact to only tet-referenced nodes and remap indices.
    used = np.unique(tets)
    if len(used) < len(points):
        remap = np.full(len(points), -1, dtype=int)
        remap[used] = np.arange(len(used))
        points = points[used]
        tets = remap[tets]
        boundary_tris = remap[boundary_tris]

    return {"points": points, "tets": tets, "boundary_tris": boundary_tris}


def _nodes_in_footprint(points: np.ndarray, center: np.ndarray, radius: float) -> np.ndarray:
    """Indices of mesh nodes within `radius` of `center`."""
    dist = np.linalg.norm(points - center, axis=1)
    return np.where(dist <= radius)[0]


def solve_elasticity(
    skfem_mod: Any,
    points: np.ndarray,
    tets: np.ndarray,
    fixed_nodes: np.ndarray,
    loaded_nodes: np.ndarray,
    load_dir: np.ndarray,
    magnitude_n: float,
    e_mpa: float,
    nu: float,
) -> dict:
    """Solve one linear-static isotropic case. Returns per-element stress tensors
    (n_elem, 3, 3) and their centroids (n_elem, 3), both in the mesh's own frame."""
    from skfem import (  # type: ignore[import-not-found]
        Basis,
        ElementTetP1,
        ElementVector,
        asm,
        condense,
    )
    from skfem import solve as skfem_solve  # type: ignore[import-not-found]
    from skfem.models.elasticity import linear_elasticity  # type: ignore[import-not-found]

    mesh = skfem_mod.MeshTet(points.T, tets.T, sort_t=True)
    basis = Basis(mesh, ElementVector(ElementTetP1()))

    mu = e_mpa / (2 * (1 + nu))
    lam = e_mpa * nu / ((1 + nu) * (1 - 2 * nu))
    stiffness = asm(linear_elasticity(lam, mu), basis)

    nodal_dofs = basis.nodal_dofs  # (3, n_nodes)
    force = np.zeros(basis.N)
    per_node = np.asarray(load_dir, dtype=float) / np.linalg.norm(load_dir) * magnitude_n
    per_node = per_node / len(loaded_nodes)
    for node in loaded_nodes:
        for comp in range(3):
            force[nodal_dofs[comp, node]] += per_node[comp]  # type: ignore[index]

    fixed_dofs = nodal_dofs[:, fixed_nodes].flatten()  # type: ignore[index]
    displacement = skfem_solve(*condense(stiffness, force, D=fixed_dofs))

    n_nodes = mesh.p.shape[1]
    u_nodal = np.zeros((n_nodes, 3))
    for comp in range(3):
        u_nodal[:, comp] = displacement[nodal_dofs[comp, :]]  # type: ignore[index]

    # Constant-strain tetrahedra (P1): stress is exactly constant per element, so a
    # per-element evaluation needs no quadrature. B-matrix via the barycentric-coordinate
    # gradients (edges from vertex 0 give the Jacobian; grad(lambda0) = -sum of the rest).
    p = mesh.p.T
    t = mesh.t.T
    n_elem = t.shape[0]
    sigmas = np.zeros((n_elem, 3, 3))
    centroids = p[t].mean(axis=1)
    for e in range(n_elem):
        verts = p[t[e]]
        disp = u_nodal[t[e]]
        edges = (verts[1:] - verts[0]).T
        grad123 = np.linalg.inv(edges).T
        grad0 = -grad123.sum(axis=0)
        grads = np.vstack([grad0, grad123])
        eps = np.zeros((3, 3))
        for i in range(4):
            eps += 0.5 * (np.outer(grads[i], disp[i]) + np.outer(disp[i], grads[i]))
        sigmas[e] = 2 * mu * eps + lam * np.trace(eps) * np.eye(3)

    return {"sigma": sigmas, "centroid": centroids}


def _rotation_to_bed(down_normal: np.ndarray) -> np.ndarray:
    """4x4 rotation mapping `down_normal` to -Z. Same operation as
    print_orientation._rotation_to_bed -- a fixed geometric transform (align a
    normal to -Z), not a policy decision, so it is replicated rather than
    importing a private symbol across the module boundary."""
    import trimesh

    norm = np.linalg.norm(down_normal)
    unit = down_normal / norm if norm else down_normal
    return np.asarray(trimesh.geometry.align_vectors(unit, np.array([0.0, 0.0, -1.0])))


def failure_index(sigma: np.ndarray, s_z: float, s_shear: float, s_inplane: float) -> float:
    """FI = max(sigma_zz/S_z, tau_z/S_shear, vm_inplane/S_inplane) for a stress tensor
    already rotated into the candidate's print pose (z = build direction)."""
    sigma_zz = sigma[2, 2]
    tau_xz, tau_yz = sigma[0, 2], sigma[1, 2]
    tau_z = float(np.hypot(tau_xz, tau_yz))
    sxx, syy, txy = sigma[0, 0], sigma[1, 1], sigma[0, 1]
    vm_inplane = float(np.sqrt(max(sxx**2 - sxx * syy + syy**2 + 3 * txy**2, 0.0)))
    return max(sigma_zz / s_z, tau_z / s_shear, vm_inplane / s_inplane)


def evaluate_orientations(
    sigmas: np.ndarray, boundary_mesh: Any, s_z: float, s_shear: float, s_inplane: float
) -> list[dict]:
    """Per candidate orientation (from print_orientation.enumerate_candidate_normals),
    rotate every element's stress tensor into that candidate's print pose and report
    fi_max / fi_p99 -- ONE solve serves every candidate; only the rotation changes."""
    from print_orientation import enumerate_candidate_normals

    candidates = []
    for idx, normal in enumerate(enumerate_candidate_normals(boundary_mesh)):
        rotation = _rotation_to_bed(normal)[:3, :3]
        rotated = np.einsum("ij,ejk,lk->eil", rotation, sigmas, rotation)
        fis = np.array(
            [failure_index(rotated[e], s_z, s_shear, s_inplane) for e in range(len(rotated))]
        )
        fi_max = float(fis.max())
        fi_p99 = float(np.percentile(fis, 99))
        candidates.append(
            {
                "idx": idx,
                "normal": [round(float(v), 6) for v in normal],
                "fi_max": round(fi_max, 4),
                "fi_p99": round(fi_p99, 4),
                "peak_element": int(np.argmax(fis)),
            }
        )
    return candidates


def run_fem_check(
    step_path: str,
    plan: dict,
    part_id: str,
    mesh_size: float,
    materials_path: str = _MATERIALS_PATH,
    plan_path: str | None = None,
) -> dict:
    """Resolve preconditions, mesh, solve, and evaluate -- or return a skipped result
    naming the first missing input or dependency. Never raises for an ordinary
    precondition miss; a gmsh/skfem exception during meshing or solving is caught and
    turned into a skipped result too (see the fem-stress-advisor spec's "Meshing
    fails" scenario)."""
    part = _resolve_part(plan, part_id)
    if part is None:
        return _skip(f"part '{part_id}' not found in plan")

    material = _resolve_material(plan, materials_path)
    if material is None:
        return _skip(f"material '{plan.get('material')}' has no entry in material_properties.json")

    bc, reason = _resolve_boundary_conditions(part)
    if bc is None:
        return _skip(reason or "no load case to resolve")

    gmsh_mod, skfem_mod, reason = _probe_dependencies()
    if gmsh_mod is None:
        return _skip(reason or "FEM dependencies not available")

    wall_mm, topbot_mm = _resolve_shell_thicknesses(plan, plan_path)

    try:
        meshed = mesh_step(gmsh_mod, step_path, mesh_size, wall_mm)
    except Exception as e:
        return _skip(f"gmsh meshing failed: {e}")

    points, tets, boundary_tris = meshed["points"], meshed["tets"], meshed["boundary_tris"]

    applied_name, applied_iface = bc["applied"]
    applied_center = np.asarray(applied_iface["position_mm"], dtype=float)
    applied_radius = _footprint_radius(applied_iface)
    loaded_nodes = _nodes_in_footprint(points, applied_center, applied_radius)
    if len(loaded_nodes) == 0:
        return _skip(f"no mesh nodes found within applied_at '{applied_name}' footprint")

    grounded_sets = []
    fixed_nodes_list = []
    for name, iface in bc["grounded"]:
        center = np.asarray(iface["position_mm"], dtype=float)
        radius = _footprint_radius(iface)
        nodes = _nodes_in_footprint(points, center, radius)
        if len(nodes) == 0:
            return _skip(f"no mesh nodes found within grounded_at '{name}' footprint")
        grounded_sets.append(
            {
                "name": name,
                "node_count": int(len(nodes)),
                "centroid_mm": [round(float(v), 3) for v in points[nodes].mean(axis=0)],
            }
        )
        fixed_nodes_list.append(nodes)
    fixed_nodes = np.unique(np.concatenate(fixed_nodes_list))

    try:
        solved = solve_elasticity(
            skfem_mod,
            points,
            tets,
            fixed_nodes,
            loaded_nodes,
            bc["dir"],
            bc["magnitude_n"],
            material["E_mpa"],
            material["nu"],
        )
    except Exception as e:
        return _skip(f"FEM solve failed: {e}")

    sigmas, centroids = solved["sigma"], solved["centroid"]

    import trimesh

    boundary_mesh = trimesh.Trimesh(vertices=points, faces=boundary_tris, process=False)
    s_z = material["s_z_mpa"]
    s_shear = material["s_shear_mpa"]
    s_inplane = material["s_inplane_mpa"]
    candidates = evaluate_orientations(sigmas, boundary_mesh, s_z, s_shear, s_inplane)

    # Peak location + concentration ratio reported against the build pose solve
    # (orientation-independent), matching the part's own frame that engineering_rationale
    # and the author's edits are expressed in.
    fis_authored = np.array(
        [failure_index(sigmas[e], s_z, s_shear, s_inplane) for e in range(len(sigmas))]
    )
    fi_max = float(fis_authored.max())
    fi_p99 = float(np.percentile(fis_authored, 99))
    peak_idx = int(np.argmax(fis_authored))
    concentration = fi_max / fi_p99 if fi_p99 > 0 else float("inf")

    if concentration > CONCENTRATION_THRESHOLD:
        hint = (
            "stress concentration: the peak is confined to a small neighbourhood near "
            f"{[round(float(v), 2) for v in centroids[peak_idx]]} (build pose) -- "
            "characteristic of a sharp re-entrant corner, not an undersized section. "
            "Fillet the concave edge, or chamfer the bearing face at the load/ground "
            "interface, so the load distributes instead of terminating on an edge."
        )
    else:
        hint = (
            "distributed stress: the elevated failure index is spread over a real volume "
            "around " + f"{[round(float(v), 2) for v in centroids[peak_idx]]} (build pose) "
            "-- the section is genuinely undersized. Thicken it, or compare the candidate "
            "orientation table for a pose that keeps this load in the layer plane."
        )

    thickness_warning = _thickness_mismatch_warning(wall_mm, topbot_mm)

    result = {
        "status": "ok",
        "part_id": part_id,
        "material": plan.get("material"),
        "assumptions": (
            "solved isotropically (E, nu) in the part's build pose; FDM material "
            "anisotropy is applied only at the per-orientation failure criterion, not "
            "the stiffness; the solved geometry is the wall-thickness shell only "
            "(infill ignored) -- see the fem-wall-shell-solve design doc"
        ),
        "mesh": {
            "mesh_size_mm": mesh_size,
            "node_count": int(points.shape[0]),
            "element_count": int(tets.shape[0]),
            "shell_thickness_mm": wall_mm,
        },
        "boundary_conditions": {
            "magnitude_n": bc["magnitude_n"],
            "applied_dir": [round(float(v), 6) for v in bc["dir"] / np.linalg.norm(bc["dir"])],
            "applied": {
                "name": applied_name,
                "node_count": int(len(loaded_nodes)),
                "centroid_mm": [round(float(v), 3) for v in points[loaded_nodes].mean(axis=0)],
            },
            "grounded": grounded_sets,
        },
        "authored_frame": {
            "fi_max": round(fi_max, 4),
            "fi_p99": round(fi_p99, 4),
            "peak_location_mm": [round(float(v), 3) for v in centroids[peak_idx]],
        },
        "concentration_ratio": round(concentration, 3),
        "concentration_threshold": CONCENTRATION_THRESHOLD,
        "hint": hint,
        "candidates": candidates,
    }
    if thickness_warning is not None:
        result["thickness_mismatch_warning"] = thickness_warning
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("step", help="Part's exported STEP file")
    parser.add_argument("--plan", required=True, help="Path to BUILD_PLAN.json")
    parser.add_argument("--part", required=True, help="Part id within the plan")
    parser.add_argument(
        "--mesh-size",
        type=float,
        required=True,
        help="Target tet edge length (mm), gmsh Mesh.MeshSizeMax. No default -- "
        "convergence must be an author decision, not a heuristic (see the "
        "fem-stress-advisor design doc).",
    )
    args = parser.parse_args()

    plan = _load_json(args.plan)
    result = run_fem_check(args.step, plan, args.part, args.mesh_size, plan_path=args.plan)
    print(json.dumps(result, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
