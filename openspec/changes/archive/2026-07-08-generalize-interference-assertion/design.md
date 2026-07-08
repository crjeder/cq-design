## Context

Two whole-model gate stages ask "do these posed bodies overlap?" with independent copies
of the trimesh + python-fcl machinery:

- `keep_out_check.run_keep_out_check` builds a `CollisionManager` of the foreign unions
  (every union except the zone's declaring part's), then calls
  `manager.in_collision_single(zone_mesh, return_names=True, ...)` **once** and treats any
  `hit` as a violation.
- `kinematic_check._sweep_collision` builds a `CollisionManager` of the fixed unions
  (every union outside the moving subtree) **once**, then per swept pose applies the
  transform to each subtree mesh and calls `manager.in_collision_single(moved, ...)`,
  counting a collision only when the deepest contact `depth` exceeds `penetration_tol_mm`
  (default 0.1).

Both reduce to: one moving mesh vs a prebuilt manager of named fixed objects -> the set of
colliding names. Exclusion (declaring-part unions; subtree unions) is already realized by
each caller simply not adding those objects to its manager. This change extracts that
kernel once (cad-khana's `assert_no_interference`, reimplemented for fluent CadQuery /
trimesh) and refactors both stages onto it, behavior-preserving.

## Goals / Non-Goals

**Goals:**
- One shared interference kernel, independently unit-tested, that both stages call.
- Byte-equivalent findings from `keep_out_check` and the kinematic collision test after
  the refactor (guarded by their existing scenario tests).
- A convenience entry point that honors an exclusion set, so future interference checks
  are a one-call away.

**Non-Goals:**
- Absorbing the kinematic DoF semantics. The `required_range`-vs-`mechanical_limit`
  scalar check and the sweep / `iter_poses` / swept-subtree rigid carry stay in
  `kinematic_check`. The stage is a *consumer* of the kernel, not an instance of keep-out.
- `plate_clearance_check`. It flags pairs that do NOT overlap but sit within one layer
  height -- a proximity/gap measure, the inverse of an overlap test. Untouched.
- Shipping the assembly-clearance placeholder authoring path (reserved result key, export
  exemptions, schema). This change only leaves a documented plug-in point for it.
- Feature presence/placement assertions and any `interfaces[]` schema change -- deferred
  to `plan-feature-assertions`.

## Decisions

### D1: The shared unit is moving-mesh-vs-manager, not zone-vs-zone
The kernel operates on an already-built `CollisionManager`, because the kinematic stage
builds its manager once and reuses it across every swept pose; rebuilding per call would
regress performance. Signature:

```
colliding_names(moving_mesh, manager, penetration_tol_mm: float | None) -> set[str]
```

`keep_out` calls it once; `kinematic` calls it per pose per subtree mesh (unchanged call
pattern, now via the kernel).

### D2: `penetration_tol_mm=None` reproduces keep-out's "any contact" semantics
This is the behavior-preservation trap. Today `keep_out` treats any `hit` as a violation
(a bare touch counts); `kinematic` requires `max(|depth|) > tol`. The kernel takes
`penetration_tol_mm: float | None`:
- `None` -> return the collided names whenever `hit` is true (boolean, any contact) ==
  current keep-out behavior.
- a float -> return names only when the deepest contact depth exceeds it == current
  kinematic behavior (called with `0.1`).

Both stages keep their exact current tolerance semantics; the difference is a parameter,
not a code fork.

### D3: A convenience wrapper carries the exclusion set for static callers
For the static single-subject case, provide:

```
check_interference(subject_mesh, others, *, exclude=frozenset(),
                   penetration_tol_mm=None) -> set[str]
```

which builds a `CollisionManager` over `others` minus `exclude` and calls
`colliding_names` once. `keep_out_check` uses this (exclude = declaring part's unions);
`kinematic_check` uses the lower-level `colliding_names` against its prebuilt,
pose-reused manager. The exclusion-set requirement in the spec is satisfied through this
wrapper.

### D4: Backend loading is centralized; issue wording stays with the caller
The primitive owns the optional-import probe (trimesh + `CollisionManager`) and exposes it
(e.g. `load_backend() -> module handle or None`). Each stage translates a missing backend
into its own `check_skipped` warning, keeping the caller-specific `type`/`message`/`hint`
(the primitive stays agnostic to which check invoked it, per the spec's contract
requirement). No change to the `{source, severity, type, message, hint}` shape either
stage emits today.

### D5: Placeholder is an extension point, not a deliverable
A future assembly-clearance volume is another static single-subject caller: it would pose
a declared PSEUDO volume like a keep-out zone and call `check_interference` with its own
`type`/`hint`. The design names this seam but ships no reserved key, export exemption, or
schema for it. Rationale: that authoring surface is a full slice on its own (it re-treads
the keep-out-zones authoring path), the user's request was the generalization + keep-out
refactor, and gating this change on it would balloon the diff.

## Risks / Trade-offs

- **[This is largely an internal refactor]** -> The user-facing win is the reusable
  primitive and the removed duplication, not new gate behavior. Justified by D5's cheap
  follow-ups and by making the overlap kernel unit-testable in isolation (today it is only
  reachable through two whole-model stages).
- **[Silent behavior drift during extraction]** -> The `penetration_tol_mm=None` vs float
  distinction (D2) is the one place a naive extraction would change keep-out's touch
  semantics. Guarded by keeping every existing `keep_out` and `kinematic` scenario test
  green as the acceptance gate, plus new kernel unit tests that assert the touch-vs-depth
  boundary directly.
- **[python-fcl contact-depth availability]** -> `in_collision_single(..., return_data=True)`
  is already used by both stages; the kernel relies on the same call, so no new backend
  capability is required.
