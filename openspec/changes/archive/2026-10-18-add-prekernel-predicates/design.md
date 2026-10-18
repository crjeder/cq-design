## Context

`cq_verify.py` holds construction-time assertions that raise
`RuntimeError("[cq-verify:<kind>:<label>] <detail>")` via `_fail()`. The wrapper's
`_translate_verify_marker` turns a marker into a typed error only when `<kind>` is a
key of `_VERIFY_HINTS`; unknown kinds fall through to `occ_exception`. Today a bad
fillet never reaches that path: OCC raises first, with no feature name.

The backlog item asked to reuse an existing radius-vs-edge rule from `prompts/part.md`.
That rule does not exist (the only fillet text there is the toolpath-speed advisory),
so the rule below is the one this change introduces. It is a geometric necessity, not a
tuned threshold.

## Goals / Non-Goals

**Goals:**
- Name the feature and the violated limit before OCC sees an impossible fillet/chamfer.
- Zero false positives on fillets OCC can build in the common prismatic case.
- Reuse the existing marker -> typed-error path; no new wrapper code beyond dict keys.

**Non-Goals:**
- Predicting every OCC fillet failure (variable-radius, fillets across tangent-chain
  seams, fillets on curved faces whose curvature radius is smaller than the fillet).
- Auto-clamping the radius. The helper reports; the author decides.
- Wiring a ligament minimum from `profile.json`. `min_mm` is caller-supplied.

## Decisions

**Rule: limit by the adjacent edges.** For each selected edge E, look at every edge A
of the body (selected or not) that shares a vertex with E. The material A offers is its
length L. If both ends of A touch a selected edge other than A, two treatments eat into
A from both ends, so the limit is L/2; otherwise it is L. (Selecting all edges of a
20x20x5 box therefore gives 2.5.) The
predicate fails when `radius >= limit` (strict: OCC usually fails at exactly the
limit). Example: `box(20, 20, 5).edges(">Z")` -> adjacent edges are the 5 mm verticals
with an unselected far end -> limit 5. `edges("|Z")` -> adjacent edges are the 20 mm
horizontals with selected edges at both ends -> limit 10.
- Alternative: "radius < half the shortest edge on any adjacent face". Simpler, but it
  counts edges parallel to E (the other filleted vertical in the `|Z` example) and
  would reject a valid R3 on a 5 mm tall box. Rejected for false positives.
- Alternative: try the fillet in a `try/except` and re-raise marked. Catches
  everything but cannot say which limit was broken, and costs a kernel op per check.
  Rejected: the point is a pre-kernel message with numbers in it.

**Chamfer uses the same rule** with the chamfer length in place of the radius (a
symmetric chamfer consumes `length` along each adjacent face, same as a fillet's
tangent setback).

**`selector=None` means all edges**, mirroring `.fillet()` on a bare solid. A string is
passed to `body.edges(selector)`. Edge identity uses `Shape.isSame` so shared edges
between faces are not double-counted.

**Ligament is arithmetic only:** ligament = `(wall_mm - hole_d_mm) / 2` (a hole centered
in a wall of width `wall_mm`). Fails when `ligament < min_mm`. There is no body to pass
through, so it returns the computed ligament in mm, which the caller may ignore.

**Detail string** names the selector, the requested size, the limiting edge length and
the computed limit, e.g. `radius 6.00 mm >= limit 5.00 mm set by a 5.00 mm adjacent
edge (selector '>Z')`.

## Risks / Trade-offs

- [Rule misses curved-face failures] -> Non-goal; those still surface as
  `occ_exception`, same as today. No regression.
- [Edge on a circle has no "other vertex"] -> a closed edge (one vertex, e.g. a hole
  rim) contributes adjacent edges only via that seam vertex; the far-end test treats a
  closed adjacent edge as limit L (no halving). Covered by a test on a filleted bore rim.
- [Strict `>=` rejects a fillet OCC would build exactly at the limit] -> rare and
  produces a degenerate face anyway; the hint tells the author to back off by 0.1 mm.

## Open Questions

- Should `check_ligament` default `min_mm` to the profile's `wall_min`? Deferred: the
  helper runs inside the part script, which has no profile handle today.
