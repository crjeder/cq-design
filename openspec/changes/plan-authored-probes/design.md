## Context

`src/probes.py` already evaluates `solid_at`, `empty_at`, `ray` and `bbox` on the BRep body.
`blocks/part.py` seeds a `Registry` from `plan_probes(part)` at step 0, re-checks every live
probe after each step, arms plan feature probes by `instance`, and folds the seeded probes
into the step cache key. `step_worker.py` reports `failing_probes` and applies the stuck
rule. Today `plan_probes()` derives probes only from the envelope and from `interfaces[]`
entries whose `type` is in the cut/boss table, so any other request dimension has no check.

Plan probes are evaluated only by step scripts (the `Part` recorder). Legacy part scripts
never see them.

## Goals / Non-Goals

**Goals:**
- Let the planner write probes directly into `BUILD_PLAN.json`, using the existing kinds.
- Treat authored probes exactly like interface-derived plan probes (owner, arming,
  no-retire, cache key, reporting).
- Catch malformed probes at `plan.py validate`, before any build.

**Non-Goals:**
- New probe kinds (concentric, feature-to-feature distance, wall-thickness-along-normal).
  The `solid_at`/`empty_at` bracket covers thickness and height; add relational kinds
  only when point probes demonstrably miss defects.
- Evaluating plan probes for legacy part scripts or in `quality_gate.py`.
- Geometric validation of probe points at plan time (no body exists yet).

## Decisions

- **Reuse `Probe` fields as the JSON shape.** The entry keys (`kind`, `p`, `dir`, `hits`,
  `length`, `lo`, `hi`, `size`, `tol`, `mode`, `label`, `instance`) are the `Probe`
  dataclass fields, so conversion is `Probe(**entry)` with lists turned into tuples.
  Alternative: a separate plan vocabulary (`at`, `axis`, ...) mapped to probes; rejected
  as a second name for every field.
- **Per-kind schema branches (`oneOf` keyed on `kind`, `additionalProperties: false`).**
  Missing `hits` on a `ray` or a stray field fails at validate time with a schema error,
  instead of a `TypeError` or a silently ignored key inside the step loop. `delta` is not
  a branch, so it is rejected.
- **`label` required.** A failing probe's report is only actionable if it says which
  request fact broke; it is also the traceability link the "planner drops request dims"
  gap lacked.
- **`instance` checked in `plan.py._check_instances`.** That function already verifies
  interface `instance` ids against `blocks_needed`; the probe check is the same loop.
- **Authored probes appended after interface probes in `plan_probes()`.** They join the
  seeded list, so `Part.__init__` adds them as `"plan"` owner and the existing cache-key
  hash covers them with no change to `part.py`.

## Risks / Trade-offs

- [Planner places a point in the wrong frame or on a surface, so a correct body fails] ->
  The `label` names the fact; the stuck rule already escalates repeated failures of the
  same probe to `ask_user`. The prompt rule tells the planner to keep points at least
  `MIN_FACE_DIST_MM` (0.1 mm) off any surface and to use the same build-pose frame as
  `interfaces[].position_mm`.
- [Over-probing slows the step loop] -> Point classification is cheap relative to a
  boolean; no cap now. Revisit if step timings show it.
- [Legacy scripts silently skip authored probes] -> Documented as out of scope; step
  scripts are the default authoring path.

## Migration Plan

Additive and optional: existing plans validate unchanged, and an empty or absent
`probes` seeds nothing new. Rollback is reverting the change.

## Open Questions

None.
