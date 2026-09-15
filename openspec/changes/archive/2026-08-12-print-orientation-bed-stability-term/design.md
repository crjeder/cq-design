## Context

`print_orientation.py` enumerates candidate bed-down poses (`enumerate_candidate_normals`)
and scores each on strength, support cost, and visual quality (`optimize_orientation`).
`_select` picks a winner per `optimize_for` mode via a lexicographic ordering with a
tolerance band on the primary key.

When strength is orientation-neutral — no declared `load` or `load_type=compression` — every
candidate ties on strength (all 1.0), so `strength` mode's contender set is every candidate,
and the deciding key collapses to `(support, -bed_contact, idx)`: minimize support cost
first, bed contact only breaks an exact tie. Support cost is computed purely from
overhang-angle severity above `overhang_max_deg` (`mesh_io.support_cost`); it has no notion
of resting stability. A candidate balanced on a small facet, edge, or vertex can have a
lower support cost than the flat resting face (whose small holes/bosses/ribs cost a few
points of overhang) and win outright, producing a pose that tips over once actually placed
on a bed.

This affects `min_support` and `visual_quality` modes too, since both use support and
bed_contact only as ties/tiebreakers, never as a stability gate.

## Goals / Non-Goals

**Goals:**
- Prevent the optimizer from ever recommending a pose that will physically tip over when a
  stable alternative exists, in every `optimize_for` mode.
- Keep the fix a pure addition to candidate scoring/selection — no change to strength,
  support, or visual scoring formulas.
- Degrade gracefully: if no candidate is stable (unusual meshes, e.g. a sphere), fall back to
  existing behavior rather than returning nothing.

**Non-Goals:**
- Simulating real physical tipping dynamics (friction, vibration, print-head knock). This is
  a static resting-stability check, not a physics simulation.
- Changing how strength or support are computed.
- Adding a new CLI flag; the stability gate is unconditional (always-on), matching how
  `bed_contact` is already always computed today.

## Decisions

### Stability metric: center-of-mass over bed-contact footprint hull

For each posed candidate, project the mesh's center of mass onto the bed plane (XY) and test
whether it falls within the convex hull of the bed-contact footprint (the vertices of faces
already classified as bed-contact in `_support_metrics`, i.e. within `FIRST_LAYER_BAND_MM` of
the lowest point). This is the standard static-stability criterion for a rigid body resting
under gravity on a support polygon: if the COM's vertical projection lands outside the
polygon, gravity produces a net tipping torque.

`trimesh.Trimesh.center_mass` gives the COM (assumes uniform density, consistent with how the
rest of the module treats the mesh as a solid proxy). The footprint hull uses
`scipy`/`trimesh`'s 2D convex hull machinery already available transitively (trimesh depends
on scipy); no new dependency.

**Alternative considered:** minimum bed-contact-area threshold alone (simpler: flag any
candidate whose bed_contact is below some fraction of the max footprint as unstable).
Rejected because area alone doesn't catch an off-center flat resting face where the COM
still overhangs the edge (a real tipping case with substantial contact area), and a fixed
fraction threshold is an arbitrary magic number with no physical grounding. COM-in-hull is
correct for the general case and only needs the hull, which the footprint's own vertices
already provide with no extra sampling.

### Degenerate-footprint guard

A footprint with fewer than 3 distinct XY points (a single point or a line of nearly
collinear points — the near-point/knife-edge balance case this change targets) cannot form a
polygon, so containment is vacuous. Treat this as unstable directly: no polygon, no support.
This is what actually rules out the observed pathological pose (balancing on a corner or
edge), since the COM-in-hull test alone would be undefined there anyway.

### Selection: hard gate ahead of existing lexicographic key, with all-unstable fallback

Add a `stable` boolean per candidate. In `_select`, filter `candidates` to the stable subset
before applying the existing per-mode key; if the stable subset is empty, fall back to the
full candidate set (existing behavior unchanged). This is a pre-filter, not a new sort key,
so it doesn't disturb the existing strength/support/visual tolerance-band logic for any mode
— it only removes candidates that were never legitimate choices.

**Alternative considered:** folding stability into the lexicographic key as a leading sort
term (e.g. `(-stable, support, -bed_contact, idx)`) instead of a pre-filter. Rejected as
equivalent in outcome but more invasive: it touches all four mode branches' key tuples
instead of one shared filter step, and a pre-filter reads more directly as "these aren't
valid resting poses" rather than folding it into a score.

### Output: report `stable` and the metrics behind it

Each candidate's dict gains `stable: bool`; the chosen candidate's stability is surfaced in
the returned JSON (e.g. `"stable": true`) and the rationale notes when unstable candidates
were excluded, so a consumer/reader can see the gate fired.

## Risks / Trade-offs

- [Uniform-density COM assumption may not match a part with strongly non-uniform mass
  distribution (e.g. embedded metal insert)] → Existing scoring already treats the mesh as a
  uniform-density solid proxy throughout (support cost, bed contact); this is consistent with
  that existing simplification, not a new one.
- [COM-in-hull is a necessary but not sufficient real-world stability condition — a large but
  very thin contact polygon can still be practically unstable under vibration] → Out of scope
  per Non-Goals; the degenerate-footprint guard catches the specific pathological case this
  change targets (near-point balance), which is the reported problem.
- [All-candidates-unstable fallback silently reverts to old (buggy) behavior for meshes with
  no flat resting face at all] → Acceptable: such meshes (spheres, organic blobs) already
  need support material regardless of pose, so the stability gate has nothing useful to add
  there; falling back preserves today's behavior rather than returning no recommendation.

## Migration Plan

Pure addition to `src/print_orientation.py`; no data migration. Existing callers
(`quality_gate.py`) read `strength_score`/`support_score`/`visual_score` and are unaffected
by the new `stable` field. Roll out as a normal code change; no flag, no rollback path needed
beyond reverting the commit.

## Open Questions

None — the degenerate-footprint guard plus COM-in-hull covers the reported failure mode
without introducing new tunable thresholds.
