"""Grader-equivalent mesh gate: does a body's STEP tessellate into a closed 2-manifold?

Mirrors CADGenBench's validity gate (cadgenbench/common/mesh.py: tessellate_shape,
validate_mesh, robust_tessellate_shape): the body is written to STEP and read back (the
round trip alone can flip the result on a high-tolerance solid), meshed with
BRepMesh_IncrementalMesh, and the per-face triangulations are stitched by *topology*
(shared-edge polygon node indices, union-find), never by a coordinate weld. A
BRepCheck-valid solid can still fail here: coincident faces left by a clean=False boolean,
or high edge tolerances, leave open or over-shared mesh edges. The welded STL watertight
check the wrapper runs does not see these.
"""

import os
import tempfile

import numpy as np

DEFLECTION_RELATIVE = 0.001
DEFLECTION_MIN_MM = 0.005
DEFLECTION_MAX_MM = 0.5
DEFLECTION_LADDER = (1, 4, 16, 32)


class MeshGateError(RuntimeError):
    pass


def _tessellate(shape, deflection: float) -> tuple[np.ndarray, np.ndarray]:
    """Topology-stitched (vertices, triangles) of `shape` at `deflection` mm."""
    from OCP.BRep import BRep_Tool
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_REVERSED, TopAbs_VERTEX
    from OCP.TopExp import TopExp
    from OCP.TopLoc import TopLoc_Location
    from OCP.TopoDS import TopoDS
    from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape, TopTools_IndexedMapOfShape

    mesher = BRepMesh_IncrementalMesh()
    mesher.SetShape(shape)
    params = mesher.ChangeParameters()
    params.Deflection = deflection
    params.Angle = 0.5
    params.Relative = False
    params.InParallel = True
    mesher.Perform()

    faces = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape, TopAbs_FACE, faces)
    if faces.Size() == 0:
        raise MeshGateError("shape has no faces to tessellate")

    verts: list[tuple[float, float, float]] = []
    tris: list[tuple[int, int, int]] = []
    face_base: dict[int, int] = {}
    face_tri: dict[int, tuple] = {}
    for fi in range(1, faces.Size() + 1):
        face = TopoDS.Face_s(faces.FindKey(fi))
        loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(face, loc)
        if tri is None:
            raise MeshGateError(f"face #{fi} missing triangulation after meshing")
        trsf = loc.Transformation()
        base = len(verts)
        face_base[fi] = base
        face_tri[fi] = (tri, loc)
        for i in range(1, tri.NbNodes() + 1):
            p = tri.Node(i).Transformed(trsf)
            verts.append((p.X(), p.Y(), p.Z()))
        rev = face.Orientation() == TopAbs_REVERSED
        for i in range(1, tri.NbTriangles() + 1):
            n1, n2, n3 = tri.Triangle(i).Get()
            a, b, c = base + n1 - 1, base + n2 - 1, base + n3 - 1
            tris.append((b, a, c) if rev else (a, b, c))
    if not tris:
        raise MeshGateError("tessellation produced no triangles")

    parent = list(range(len(verts)))

    def find(x: int) -> int:
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[max(rx, ry)] = min(rx, ry)

    pts = np.asarray(verts, dtype=np.float64)
    vmap = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape, TopAbs_VERTEX, vmap)
    vertex_nodes: dict[int, list[int]] = {}
    edge_faces = TopTools_IndexedDataMapOfShapeListOfShape()
    TopExp.MapShapesAndAncestors_s(shape, TopAbs_EDGE, TopAbs_FACE, edge_faces)
    for ei in range(1, edge_faces.Extent() + 1):
        edge = TopoDS.Edge_s(edge_faces.FindKey(ei))
        curves = tuple(edge.TShape().Curves())
        lists: list[list[int]] = []
        seen: set[int] = set()
        for adj in edge_faces.FindFromIndex(ei):
            fi = faces.FindIndex(adj)
            if fi == 0:
                continue
            tri, loc = face_tri[fi]
            if id(tri) in seen:  # a seam lists its face twice
                continue
            seen.add(id(tri))
            off = face_base[fi] - 1
            pred = loc.Predivided(edge.Location())
            for cr in curves:
                if not cr.IsPolygonOnTriangulation(tri, pred):
                    continue
                p1 = cr.PolygonOnTriangulation()
                if p1 is not None:
                    lists.append([n + off for n in p1.Nodes()])
                if cr.IsPolygonOnClosedTriangulation():
                    p2 = cr.PolygonOnTriangulation2()
                    if p2 is not None:
                        lists.append([n + off for n in p2.Nodes()])
        if not lists:
            continue
        ref = lists[0]
        for other in lists[1:]:
            if len(other) != len(ref):
                raise MeshGateError(
                    f"edge #{ei}: shared-edge node arrays differ in length "
                    f"({len(ref)} vs {len(other)}); cannot stitch by index"
                )
            fwd = float(np.abs(pts[ref] - pts[other]).max())
            bwd = float(np.abs(pts[ref] - pts[other[::-1]]).max())
            if bwd < fwd:
                raise MeshGateError(f"edge #{ei}: shared-edge node arrays in opposite order")
            for u, v in zip(ref, other, strict=True):
                union(u, v)
        v_first = vmap.FindIndex(TopExp.FirstVertex_s(edge))
        v_last = vmap.FindIndex(TopExp.LastVertex_s(edge))
        for arr in lists:
            if v_first:
                vertex_nodes.setdefault(v_first, []).append(arr[0])
            if v_last:
                vertex_nodes.setdefault(v_last, []).append(arr[-1])

    for vi, nodes in vertex_nodes.items():
        vp = BRep_Tool.Pnt_s(TopoDS.Vertex_s(vmap.FindKey(vi)))
        far = float(np.abs(pts[nodes] - np.array([vp.X(), vp.Y(), vp.Z()])).max())
        if far > deflection:
            raise MeshGateError(
                f"vertex #{vi}: an edge endpoint node is {far:.3e} mm from the vertex"
            )
        for n in nodes[1:]:
            union(nodes[0], n)

    roots = np.array([find(i) for i in range(len(verts))], dtype=np.int64)
    uniq, inv = np.unique(roots, return_inverse=True)
    merged = inv[np.asarray(tris, dtype=np.int64)]
    keep = (
        (merged[:, 0] != merged[:, 1])
        & (merged[:, 1] != merged[:, 2])
        & (merged[:, 0] != merged[:, 2])
    )
    merged = merged[keep]
    # cancel opposite-winding duplicate pairs (a folded degenerate region), as the grader does
    groups: dict[tuple, list[int]] = {}
    for i, t in enumerate(merged.tolist()):
        groups.setdefault(tuple(sorted(t)), []).append(i)
    remove: list[int] = []
    for idxs in groups.values():
        if len(idxs) < 2:
            continue
        even = [i for i in idxs if _even(merged[i])]
        odd = [i for i in idxs if not _even(merged[i])]
        n = min(len(even), len(odd))
        remove += even[:n] + odd[:n]
    if remove:
        merged = np.delete(merged, remove, axis=0)
    if merged.shape[0] == 0:
        raise MeshGateError("stitching collapsed all triangles")
    return pts, merged


def _even(t) -> bool:
    x, y, z = sorted(int(v) for v in t)
    return (int(t[0]), int(t[1]), int(t[2])) in {(x, y, z), (y, z, x), (z, x, y)}


def _validate(tris: np.ndarray) -> None:
    """Closed, edge-manifold, consistently wound, no pinch vertex."""
    n_v = int(tris.max()) + 1
    e = np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]])
    lo, hi = e.min(axis=1), e.max(axis=1)
    keys, counts = np.unique(lo * (n_v + 1) + hi, return_counts=True)
    if counts.max() > 2:
        k = int(keys[np.argmax(counts)])
        raise MeshGateError(
            f"mesh non-manifold: edge ({k // (n_v + 1)}, {k % (n_v + 1)}) shared by "
            f"{int(counts.max())} triangles (expected <= 2)"
        )
    if 2 * len(keys) != 3 * len(tris):
        raise MeshGateError(f"mesh not closed: {int((counts == 1).sum())} open edges")
    directed = np.unique(e[:, 0] * (n_v + 1) + e[:, 1])
    if len(directed) != len(e):
        raise MeshGateError("mesh orientation inconsistent")
    pinched = _pinch_vertices(tris, n_v)
    if pinched:
        raise MeshGateError(f"mesh non-manifold vertex: {pinched} pinch vertex/vertices")


def _pinch_vertices(tris: np.ndarray, n_v: int) -> int:
    """Count vertices whose link is more than one cycle (the grader's _nonmanifold_vertices)."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components

    src = np.concatenate([tris[:, 0], tris[:, 1], tris[:, 2]])
    p = np.concatenate([tris[:, 1], tris[:, 2], tris[:, 0]])
    q = np.concatenate([tris[:, 2], tris[:, 0], tris[:, 1]])
    half = np.concatenate([np.stack([src, p], 1), np.stack([src, q], 1)])
    node = np.unique(half[:, 0] * (n_v + 1) + half[:, 1], return_inverse=True)[1]
    n_nodes = int(node.max()) + 1
    m = src.size
    graph = coo_matrix((np.ones(m, dtype=np.int8), (node[:m], node[m:])), shape=(n_nodes, n_nodes))
    n_comp, label = connected_components(graph, directed=False)
    node_src = np.empty(n_nodes, dtype=np.int64)
    node_src[node[:m]] = src
    owners, cycles = np.unique(np.unique(node_src * n_comp + label) // n_comp, return_counts=True)
    return int((cycles > 1).sum())


def mesh_gate_error(shape) -> str | None:
    """None if `shape` passes the grader's mesh gate after a STEP round trip, else the reason."""
    import cadquery as cq

    fd, path = tempfile.mkstemp(suffix=".step")
    os.close(fd)
    try:
        cq.Shape.cast(shape).exportStep(path)
        loaded = cq.importers.importStep(path)
        wrapped = cq.Compound.makeCompound(
            [v for v in loaded.vals() if isinstance(v, cq.Shape)]
        ).wrapped
    finally:
        os.remove(path)
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib

    bnd = Bnd_Box()  # the grader's bbox: tolerance-enlarged, not optimal
    BRepBndLib.Add_s(wrapped, bnd, True)
    x0, y0, z0, x1, y1, z1 = bnd.Get()
    diag = ((x1 - x0) ** 2 + (y1 - y0) ** 2 + (z1 - z0) ** 2) ** 0.5
    base = min(DEFLECTION_MAX_MM, max(DEFLECTION_MIN_MM, DEFLECTION_RELATIVE * diag))
    last = ""
    for divisor in DEFLECTION_LADDER:
        try:
            _validate(_tessellate(wrapped, base / divisor)[1])
            return None
        except MeshGateError as exc:
            last = str(exc)
    return last
