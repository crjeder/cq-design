## Context

The pipeline (Planning -> Part loop -> Model export -> Quality gate) produces geometry
and validates it, but the print orientation is never a decision variable. Two facts make
this a gap:

- The print recipe in `quality_gate.py` hardcodes `"orientation": "flat_bottom_down"`.
- `model_export.py` bakes each union's **assembled-frame `placement`** into the
  deliverable 3MF and writes per-union STLs in that same pose. The assembled pose is
  chosen for display and for the kinematic sweep, not for printing.

On FDM the orientation dominates two quality axes: **strength** (the Z/interlayer bond is
the weak direction, so a load crossing layer lines fails early) and **support** (downward
faces steeper than `overhang_max_deg` need support, which costs material and scars
surfaces). The overhang math already exists in `quality_gate._analyze_stl` (downward
face normals, area above the threshold). What is missing is (a) a notion of where the
load goes, (b) enumeration and scoring of candidate orientations, and (c) a path for the
chosen orientation to reach the deliverables without disturbing the assembled-pose meshes
the kinematic check consumes.

Constraints: in-process trimesh + numpy only (no slicer, no new dependency); Python
3.10-3.12; the existing `placement.py` transform convention and the `{source, severity,
type, message, hint}` issue contract should be reused.

## Goals / Non-Goals

**Goals:**
- A deterministic, slicer-free tool that enumerates candidate bed-down orientations for a
  union mesh and scores each on strength (primary) and support (secondary).
- A recommended print orientation per union, expressed as a rotation transform plus a
  score breakdown and human-readable rationale.
- An LLM optimization loop that can act on the scores: re-orient, or apply targeted
  geometry tweaks to cut support, then re-score until converged.
- Deliverable 3MF/STL written in the recommended print orientation; assembled-pose meshes
  for the kinematic check preserved.
- An optional, declared load direction in the plan that drives strength scoring, with a
  geometry fallback when absent.

**Non-Goals:**
- Full FEA or true support-volume slicing. Both objectives use cheap mesh proxies.
- Arbitrary (non-axis-aligned, continuously optimized) orientations. The candidate set is
  the convex-hull resting faces plus the six axis-aligned faces, not a continuous search.
- Multi-material, tree-support modeling, or per-slicer support estimation.
- Changing the kinematic check or the assembled-frame `placement` semantics.

## Decisions

### Decision: Print orientation is a separate transform from `placement`
`placement` stays the assembled-frame pose (kinematics, display). The optimizer emits a
distinct **print orientation** rotation per union. Export applies the print orientation to
the deliverable 3MF/STL; the per-union assembled-pose STLs for the kinematic check are
produced from `placement` exactly as today.

*Alternative considered:* overwrite `placement` with the print pose. Rejected — it would
break the kinematic sweep, which depends on the authored assembled pose, and conflate two
unrelated concerns.

### Decision: Candidate set = convex-hull resting faces + 6 axis-aligned faces
Enumerate the orientations that lay a flat face on the bed: the convex hull's significant
facets (a part can only rest stably on a hull face) plus the six axis-aligned box faces as
a guaranteed baseline. Each candidate is the rotation that maps that face's outward normal
to -Z. Deduplicate near-identical normals. This is the standard cheap stand-in for stable
resting poses without a physics drop test.

*Alternative considered:* continuous gradient search over SO(3). Rejected as overkill for
FDM, where useful orientations are dominated by flat-on-bed poses, and far harder to make
deterministic/testable.

### Decision: Strength is primary, support is the tiebreaker (lexicographic, not weighted sum)
Score each candidate with a strength score and a support score, then select
lexicographically: maximize strength first, break ties (within a tolerance band) by
minimum support. The user's ordering ("strength first, minimal support second") is an
explicit priority, not a blend, so a weighted sum that could trade strength away for less
support is wrong.

- **Strength score**: layer planes are XY; the interlayer-weak direction is the build Z.
  Given a load direction (declared or inferred), reward orientations that keep the load
  **in-plane** (perpendicular to build Z) and penalize orientations that put the load
  across layers. Concretely, score on `1 - |load_dir_after_rotation . Z|` (1.0 = load
  fully in-plane, 0.0 = load fully along layers). With no declared load, infer the
  principal load axis from geometry (longest bounding-box axis / slenderest direction is
  the most bending-prone) as a conservative default.
- **Support score**: reuse the overhang computation — total downward face area with
  overhang angle above `overhang_max_deg` (lower is better), with bed-contact area as a
  secondary nudge (more contact = better adhesion, fewer brim concerns). This is a proxy
  for support volume, not a slice.

*Alternative considered:* single weighted objective `w1*strength + w2*support`. Rejected:
the requested priority is strict ordering; weights would silently let support win.

### Decision: The optimization is an LLM loop over a deterministic scoring tool
`print_orientation.py` is pure scoring/selection (deterministic, unit-testable). The
*loop* lives in SKILL.md as a new phase: the LLM runs the tool, reads the score breakdown,
and may (1) accept the top orientation, or (2) make a targeted geometry edit to reduce the
support that the best strength-orientation still incurs (e.g. chamfer a steep overhang,
add a print-in-place foot), then re-run the tool. Bounded retries, same shape as the part
loop. This keeps the algorithm honest and the judgment where the model context is.

### Decision: Load hint is optional plan data, frame = part authored frame
Add an optional per-part `load` to the schema: a principal load direction in the part's
own authored frame (the frame the script builds in, before `placement`). The optimizer
transforms it by the candidate rotation to evaluate in-plane alignment. Absent → geometry
inference. Declaring it in the part frame keeps it stable regardless of assembled pose.

## Risks / Trade-offs

- **Proxy metrics diverge from a real slicer** → Document that support score is a mesh
  proxy, not a slice; the orca-check MCP remains the optional ground truth. Keep the
  metric monotonic and conservative so "less proxy support" rarely means "more real
  support".
- **Strength inference without a declared load can pick the wrong axis** → Default to the
  conservative slender-axis heuristic and surface the inferred load direction in the
  rationale so the user (or LLM) can override by declaring `load`.
- **Lexicographic selection can flip on tiny strength deltas** → Use a tolerance band so
  near-equal strength candidates are treated as tied and decided by support, avoiding
  jitter between near-identical poses.
- **Deliverable pose no longer matches assembled pose may confuse downstream tooling** →
  The 3MF still records assembled metadata per object; only the deliverable geometry pose
  changes, and the change is explicit in the export result and the recipe rationale.
- **Convex-hull facet count can explode on organic meshes** → Cap/cluster candidate
  normals (merge within an angular tolerance) before scoring to bound runtime.

## Open Questions

- Should the strength heuristic consider feature-level stress concentrations (thin necks,
  cantilevers) beyond a single principal load axis? Deferred — single-axis first.
- Should a multi-union plate be oriented as a locked cluster or per-union? Initial scope:
  per-union; plates that fuse for STL adopt the first union's orientation. Revisit if
  needed.
