## Context

Per-feature presence is verified today only by the VLM visual review. The
`disconnected_body` change established the target pattern: a deterministic hard gate plus
the visual question as cross-check. We want the same for "the plan declared a Ø4 port on
+X at (10,15) -- is it actually there?".

Two grounding facts shape the mechanism:

1. **The `interfaces[]` schema does not carry a machine-readable position.** The
   `planning-phase` spec *narrates* `wall` / `position_mm` (scenario line 97) but
   `build_plan_schema.json` requires only `type` and leaves the rest
   `additionalProperties: true`. There is nothing structured to assert against yet.
2. **Interface blocks return unpositioned solids.** `port_cutout(w, h, depth, chamfer)`,
   `cable_slot(...)`, `screw_boss(...)` etc. produce a solid at the origin; the *author's*
   surrounding code (`.cut(port_cutout(...).translate(p))`, a located workplane) places it.
   So wrapping the block -- the brief's first framing, by analogy to
   `edge_treatment_check` wrapping `fillet`/`chamfer` -- captures the feature's **size but
   not its placement**. `fillet`/`chamfer` were hookable-in-place because they carry their
   own edge geometry; interface blocks do not carry their final position.

This refutes the naive "hook the block" plan and drives the mechanism decision below.

## Goals / Non-Goals

**Goals:**
- Make interface placement machine-readable (structured, optional schema fields).
- Deterministically confirm every plan-declared, structured-position interface is realized
  at that position, as a blocking finding when absent.
- Reuse the construction-time / re-run pattern (no mesh reverse-engineering).

**Non-Goals:**
- Free-form / implicit-position features, and features built by construction paths the
  hook cannot attribute a position to (see D5). Reported as `check_skipped`, never as a
  false "absent".
- Generic invariants (min-wall, clearance, no-interference) -- already covered.
- `assert_clearance` and assembly-clearance placeholder volumes -- separate follow-ups.
- Making position/size *required* in the schema (would break every existing plan).

## Decisions

### D1: Hook the placement-bearing operation, not the block
Because the block output is unpositioned, the hook must sit where the feature acquires its
position: the boolean that consumes the *positioned* tool. Wrap `cq.Workplane.cut` /
`.union`, re-run the part script (same `exporters._load_result` re-run
`edge_treatment_check` uses), and for each call record the **authored-frame** bbox center
and extents of the tool argument it applies. That set of `(center, extents)` is the
"features actually built". Position is captured in the authored frame -- the same frame
`position_mm` is declared in -- so, unlike `edge_treatment_check`, **no print-orientation
rotation is needed**.

The in-place hole family (`.hole` / `.cboreHole` / `.cutBlind` / `.cutThruAll`) is
**deferred**: its position lives in the workplane's pending points, not in a positioned
tool solid, so it needs a separate frame-aware capture and is materially more fragile.
Block-emitted bores are already covered, because a block (`screw_boss`, `pcb_standoff`,
...) is applied via `.union` / `.cut` of its positioned solid -- the tool bbox captures it.
- Alternative: hook the block only -> rejected, captures size not placement (Context 2).
- Alternative: query the constructed BRep for a cylindrical/opening face near the declared
  position -> viable and needs no re-run, but matching a face to an interface `type` is
  its own classifier; deferred as a possible later mechanism. BRep query (not mesh) would
  avoid the triangle-signature ambiguity the brief worried about, so it stays on the table.
- Alternative: author-inserted `assert_feature(...)` (cq_verify style) -> rejected as
  primary: it is author-declared, so an author who omits the feature also omits the
  assert; the point is to check plan intent independently.

### D2: Structured, optional schema fields; authored-frame absolute position
Add to an `interfaces[]` entry (all optional): `wall` (enum of the six faces),
`position_mm` (`[x, y, z]`, authored frame, the feature's intended center), and a size
field (`diameter_mm` for round features, `size_mm: [w, h]` for rectangular). The
assertion only runs for an entry that declares `position_mm` (and, for drift, a size).
Optional keeps existing plans valid and lets implicit-position features opt out.

### D3: Present / absent / drift matching semantics
For each interface entry declaring `position_mm`, search the recorded features for one
whose center is within `_POS_TOL_MM` of the declared position:
- **none** within `_POS_TOL_MM` -> `error`, `type: "feature_absent"` (the declared feature
  was not built at that position).
- **one** within `_POS_TOL_MM`, but its center or size differs beyond a tighter
  `_DRIFT_TOL_MM` / size tolerance -> `warning`, `type: "feature_drift"`.
- **one** within tolerance and matching size -> pass.
Tolerances are single constants at the top of the module (mirroring
`edge_treatment_check`'s `_BBOX_TOL_MM` etc.); `_POS_TOL_MM` is generous (feature exists
somewhere near), the drift/size tolerance tight.

### D4: A whole-model gate stage, re-running per part
Wire it into `quality_gate.py` as a once-outside-the-fix-loop stage, exactly like
`edge_treatment_check`: it needs the plan's `interfaces[]` (which the gate has) and it
re-runs each part script with the hooks installed. Not the per-part wrapper: the wrapper
runs the untouched author script once for geometry, whereas this needs a hooked re-run and
the plan, which is the gate's job. Emits the shared `{source, severity, type, message,
hint}` contract; attribute each finding to its part (and union, by the recorded feature's
bbox, as `edge_treatment_check` does).

### D5: First scope is an allowlist of assertable interface types
A feature built by a construction path the hook does not cover (e.g. an `.extrude` boss, a
loft, raw geometry) would have no recorded `(center, extents)` and would false-positive as
`feature_absent`. To avoid that, the check only asserts interface `type`s known to be
emitted through a hooked op -- an allowlist: `port_cutout`, `cable_slot`, `vent_grid`,
`screw_boss`, `pcb_standoff` (all applied via `.cut`/`.union`). An entry whose `type` is outside
the allowlist (or whose part script cannot be re-run) is `check_skipped`, never `absent`.
The allowlist is the conservative first cut; it can grow as more emit paths are hooked.

## Risks / Trade-offs

- **[False "absent" from an un-hooked construction path]** -> D5 allowlist + `check_skipped`
  for unknown types is the guard; better to miss a real feature (silent) than fail a valid
  part (false positive). The visual review still covers the skipped ones.
- **[Ambiguous match when a part has several same-size features close together]** -> nearest
  center within `_POS_TOL_MM` wins; a declared position that matches the wrong-but-nearby
  feature is a plan-authoring problem the drift warning surfaces, not a check bug.
- **[Re-run cost]** -> same cost `edge_treatment_check` already pays; both are
  once-outside-the-fix-loop, not per-iteration.
- **[Schema change ripple]** -> fields are additive and optional; existing plans and the
  `planning-phase` "empty interfaces still validates" scenario are preserved. The tightening
  is from `additionalProperties: true` to a defined-but-optional shape.
- **[Mechanism may prove too brittle in practice]** -> the behavioral specs are written at
  the present/absent/drift level, independent of D1's hook set, so the BRep-query
  alternative (D1) can replace the mechanism without a spec change.
