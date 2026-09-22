## Context

The skill already has every input a stress solve needs except the load case itself.
Geometry is exported as STEP (`src/exporters/step.py`) -- exact B-rep, meshable by
gmsh without the facet-quality problems an STL would bring. `parts[].load` declares
a direction and type. `parts[].interfaces[]` declares named connection points, many
already carrying `position_mm` and a size (`diameter_mm` or `size_mm`) for the
feature-presence check. What is missing is a magnitude, and a statement of which
interfaces receive the load and which hold the part.

`src/FEM.py` is a stub that guesses the last two from the bounding box: fix the
`x_min` face, load the `x_max` face. That is the single most consequential input to
the whole analysis and it is inferred from nothing. It also solves orthotropic with
the weak axis pinned to global Z -- but the weak axis is the build Z of the chosen
*print orientation*, not the authored frame Z. This is the same frame confusion
already fixed once in `quality_gate.py`'s overhang analysis, which now poses the
mesh through the orientation before measuring. And it compares von Mises (an
isotropic criterion) against an interlayer allowable, mixing two incompatible
failure theories.

None of those are reasons not to do FEM. They are the design constraints.

## Goals / Non-Goals

**Goals:**
- A stress number where there is currently a guessed formula, for the two decisions
  named: how the layers should run, and whether a section is thick enough.
- Boundary conditions **declared**, never inferred. No load case, no run.
- Honest failure on ambiguity: a skipped run with a stated reason is a better
  outcome than a run on fabricated BCs.
- A geometry hint that distinguishes "this corner is sharp" from "this section is
  thin", because the fix differs and the raw peak stress cannot tell them apart.
- Zero change to the default install and zero change to any existing gate.

**Non-Goals:**
- Accuracy sufficient to certify a part. This is a screening tool: it moves a
  decision from "the LLM picked a cantilever formula" to "a solve on the real
  geometry says the peak is here and the margin is 2.3x".
- Replacing the snap-fit strain check. A cantilever arm *is* a cantilever; the
  closed form fits and is cheaper.
- Topology optimization, contact, nonlinearity, assembly-level analysis, gating.

## Decisions

### Boundary conditions come from named interfaces, not geometry

`load` gains:

```jsonc
"load": {
  "dir": [0, 0, -1],
  "type": "bending",
  "magnitude_n": 2.6,            // researched mass -> force
  "applied_at": "phone_shelf",   // an interfaces[].name
  "grounded_at": ["wall_screws"] // interfaces[].name list
}
```

Each name resolves to an `interfaces[]` entry; its `position_mm` plus
`diameter_mm`/`size_mm` defines a footprint, and the mesh nodes inside that
footprint become the load set (traction, `magnitude_n * normalize(dir)` distributed
over the set) or the fixed set (all three DOF).

- **Why named interfaces and not a new geometry-selection syntax**: the vocabulary
  exists, is already validated, is already checked to be physically present by
  `feature_presence_check.py`, and is already the thing the planner reasons about.
  A second way to point at a region on the part would be a parallel mechanism for
  one consumer.
- **Why not derive grounds from `interfaces[].type`** (screw_mount/pcb_mount ->
  fixed, everything else free): it silently mis-grounds every part that rests on a
  surface or is held by a clamp rather than a screw, and does so without saying so.
  The whole point of this change is not to guess the BCs.
- **Alternative rejected**: a separate `load_cases[]` array on the part, allowing
  several named cases. Deferred -- one case exercises the machinery; a second case
  is an array wrapper around the same fields whenever a part needs one.

`load` also carries an optional `applied_dir`, overriding `load.dir` for the applied
traction only. A load frequently enters its interface at an angle to the part's principal
direction -- a shelf lip taking weight that also pushes outward, a hook whose strap pulls
off-axis -- and forcing the two to coincide would either misstate the traction or corrupt
`load.dir`, which the orientation optimizer and the rationale trigger both read. Keeping it
a separate flat field rather than replacing `applied_at`'s string with an object avoids a
`oneOf` in the schema for one consumer. `grounded_at` takes no direction: grounds are fully
fixed. If a part ever needs several application points at different angles, `applied_at`
becomes an array of `{name, dir}` objects then, not now.

`magnitude_n` is optional because most parts have no researched mass. Missing it, or
missing either anchor, or an anchor naming an interface without `position_mm`, all
produce the same outcome: a `skipped` result with `reason`, exit 0.

### Magnitude is derived, not stated

The planner never writes a force it made up. `prompts/research.md` gains mass as a
lookup target ("iPhone 15 Pro mass, 187 g, apple.com/specs, confirmed") and its
return table gains a `Unit` column, since the table's header is currently
`Value (mm)` and cannot express grams. The planner then applies, from
`reference/Engineering Design Rules.md`:

```
magnitude_n = mass_g * 9.81 / 1000 * safety_factor
```

with `safety_factor = 2.0` for a static supported load, stated once as a table row
rather than a constant in code, so it sits next to the allowables it is compared
against. No mass researched -> no `magnitude_n` -> no run. This is the same
discipline `research.md` already enforces for dimensions ("Never guess. Every value
needs a source you actually read this run.").

**The derivation is shown at the Phase 2 checkpoint.** Every stress number downstream
scales linearly with `magnitude_n`, and unlike a dimension the user stated, it is a
derivation the planner performed. The plan summary therefore gains a load-cases table
showing the source mass, the safety factor, the resulting force, and the anchors -- the
inputs, not just the output -- so a wrong mass is caught at the one pause that already
exists for exactly this kind of review, rather than propagating into every failure index
in Phase 3. A user correction there re-derives `magnitude_n` and lands in `request_log`
like any other correction.

### Mesh size is the author's, not a default

`--mesh-size` is required. The alternative -- deriving it from `wall_min_mm` or the
bounding box -- would put a convergence decision behind a heuristic, and convergence is the
one thing about an FEM result a reader must be able to interrogate. An author who cannot
see the discretisation has no way to tell a converged number from a coarse one.

So the result echoes the mesh size with the node and element counts, and the workflow is
explicit: if a result looks implausible -- extreme concentration ratio, a failure index far
from what the geometry suggests, a peak somewhere unexpected -- re-run smaller and compare
`fi_p99`. Moves substantially -> the coarse mesh was not converged, do not cite it. Holds
-> the result is mesh-independent at that size. This is the standard convergence check,
made a two-command loop instead of a hidden default, and it costs nothing when the first
result is plausible.

It also pairs with the concentration ratio: `fi_max` at a sharp corner is *expected* to
climb with refinement (the singularity is real, the stress is not), while `fi_p99` is
expected to hold. An author comparing two mesh sizes sees both behaviours and learns which
of the two numbers to trust for which purpose.

### One isotropic solve, N orientation evaluations

Naively, scoring N candidate orientations for strength means N solves. Instead:

```
   STEP -> gmsh tet mesh -> ONE linear-static solve, ISOTROPIC, authored frame
                                      |
                                  sigma(x)
                                      |
                 +--------------------+--------------------+
                 v                    v                    v
          rotate sigma into    rotate sigma into    rotate sigma into
          candidate 1's        candidate 2's        candidate N's
          build frame          build frame          build frame
                 |                    |                    |
                 v                    v                    v
           FI_1 per node        FI_2 per node        FI_N per node
```

The material anisotropy enters at the **criterion**, not the stiffness. Rotating a
solved tensor is arithmetic; re-solving is not.

**Why this is acceptable** (confirmed with the user): FDM stiffness anisotropy here
is `E3/E1 = 1400/1700`, ~18%. The stress field's dependence on that is second-order
next to the first-order uncertainty already present in the BCs and the material
allowables. An advisor that is 18% off on stiffness but points at the right corner
is useful; one that costs N solves to remove that 18% while the BCs carry 2x
uncertainty is not.

**Candidate set**: `fem_check.py` imports `enumerate_candidate_normals` from
`print_orientation.py` rather than re-deriving candidates, so the FI table and the
orientation optimizer index the same list. Duplicating the enumeration would let
them silently drift apart.

### The failure criterion is anisotropic, per orientation

Von Mises assumes isotropy and cannot be compared against an interlayer allowable.
For each candidate, with `z` = that candidate's build direction:

```
FI = max( sigma_zz / S_z ,          delamination: interlayer tension
          tau_z    / S_shear ,      layer slip: interlayer shear
          vm_inplane / S_inplane )  bulk yield in the layer plane
```

`FI >= 1.0` means the allowable is reached; the safety factor is already inside
`magnitude_n`, so the criterion compares against the raw allowable rather than
carrying a second factor. Reporting `FI` rather than a stress in MPa makes the
per-orientation comparison dimensionless and directly usable as
`strength_score = 1 - FI` -- the same 0..1 range `_strength_score` already returns.

### The singularity problem becomes the geometry hint

Any sharp re-entrant corner in a B-rep has unbounded stress: refine the mesh and the
peak rises without limit. A `max(FI)` advisor would therefore flag every unfilleted
internal corner and would move with mesh size.

Rather than suppressing that, use it as the signal:

```
concentration = FI_max / FI_p99

  high (> 3)   -> the peak is a concentration in a tiny neighbourhood.
                  The section is not the problem; the corner is.
                  hint: fillet the concave edge / chamfer the bearing face
                        so the load spreads instead of terminating on an edge

  low  (<= 3)  -> stress is spread over a real volume.
                  hint: the section is genuinely undersized; thicken it
                        (or re-orient: compare FI across the candidate table)
```

Both `FI_max` and `FI_p99` are reported; the orientation strength score uses
`FI_p99`, which is mesh-insensitive, while `FI_max` and the ratio drive the hint.
This is why the tool reports a percentile at all -- not as a fudge, but because the
two numbers together carry information neither has alone.

**Alternative rejected**: requiring fillets everywhere before allowing a run. That
makes the tool unavailable exactly when it has the most to say.

### Advisor, not gate

`fem_check.py` exits 0 on a high `FI`. It adds no `quality_gate.py` stage. The
result reaches the part author (Phase 3 loop) and the user (checkpoint), and the
author decides.

**Why** (confirmed with the user): the BC quality problem is real and does not go
away with a better solver. A gate that blocks delivery on a number derived from two
declared interface footprints would, on the first mis-declared anchor, be a wrong
blocker with a very authoritative-looking justification. An advisory number the
author weighs against the geometry is robust to that failure mode; a gate is not.

This also decides the dependency question: an advisor may be optional, so `gmsh`
(~70 MB wheel) and `scikit-fem` go in a `fem` extra rather than the default install.

### Solver: scikit-fem, not CalculiX

| | mesher | solver | install |
|---|---|---|---|
| `src/FEM.py` stub | gmsh | CalculiX `ccx` binary | manual path (`C:\path\to\ccx.exe`), via FreeCAD or conda |
| **chosen** | gmsh | scikit-fem | pip; numpy + scipy, both already dependencies |
| sfepy | gmsh | sfepy | pip, heavier, more than needed |

Every existing check in this repo (`trimesh`, `python-fcl`, `manifold3d`, `scipy`)
is pip-installable. `ccx` is a native binary with no wheel -- the stub's hardcoded
`CCX = r"C:\path\to\ccx.exe"` is the tell -- and it breaks the install story on the
primary platform. CalculiX buys nonlinearity and contact, neither of which a linear
screening advisor uses. For linear-static tets with a rotated-tensor criterion,
scikit-fem is the smaller correct choice.

### `src/FEM.py` is deleted, not evolved

It is unreferenced: no entry in `reference/scripts.md`, `src/skill_permissions.json`,
any prompt, any spec, or any test. Its three genuinely reusable ideas (gmsh import of
STEP, second-order tets, an orthotropic constants block) are a dozen lines that carry
over into `fem_check.py`. Keeping it alongside would leave two FEM entry points, one
of which guesses its BCs.

## Risks / Trade-offs

- **A mis-declared anchor produces a confident wrong number.** -> Mitigation: the
  result echoes the resolved BC node counts and footprint centroids so the author can
  see what was actually fixed and loaded; advisory-only means a wrong number costs a
  reconsidered decision, not a blocked delivery.
- **Mesh dependence.** -> Mitigation: the orientation score uses `FI_p99`, not
  `FI_max`; the ratio between them is reported rather than hidden.
- **The isotropic-solve approximation is invisible in the output.** -> Mitigation:
  the result carries the assumption explicitly as a field, so a downstream consumer
  (or the user) never reads `FI` as a certified value.
- **gmsh meshing failures on messy B-reps.** -> Mitigation: a mesh failure is a
  `skipped` result with the gmsh error as `reason`, exit 0 -- identical handling to
  a missing load case. The advisor never takes the pipeline down.
- **Two places could drift on material numbers** (the injected Markdown table and the
  solver). -> Mitigation: `src/material_properties.json` is the single source; the
  table in `reference/Engineering Design Rules.md` is generated from it, and a test
  asserts they agree.
- **The candidate-set import couples `fem_check.py` to `print_orientation.py`.** ->
  Accepted: that coupling is the point. The alternative is two enumerations that
  agree until one changes.

## Open Questions

- The concentration-ratio threshold (3.0 in the proposal) is a starting value, not a
  derived one. It needs calibrating against a few real parts during implementation -- a
  filleted corner and an unfilleted one on otherwise identical geometry give the two
  reference points.
- Whether the part author should run the advisor on every load-bearing part that has a
  load case, or only when a decision actually turns on it. Running it always is simpler to
  specify; running it on demand keeps the part loop shorter. Settle in `skill/phase3_build.md`
  once the first real runs show how long a solve takes.
