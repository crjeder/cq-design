# Joints, kinematics and anchors -- details

Tasks: [TODO.md](../TODO.md#7-joints-kinematics-and-anchors).

### Kinematic ground plane

Explore adding one simple ground/seating plane (lid-hits-floor checks);
surrounding-geometry questions stay out of scope (external simulation).

### Kinematic articulated chains

Articulated chains (a moving union carries other unions through the sweep).

### Joints multi-DOF

Multi-DOF / coupled simultaneous movements. A joint is a LIST of
single-axis movements (`rotate`/`translate`, each with axis + reference
vector + range); independent movements for now. A spherical/ball joint is
two coupled `rotate` movements sharing a center -- listing them as two
independent entries models a 2-axis gimbal, NOT the ball's coupled cone.
Capture coupling (e.g. helical screw pitch, ball cone) as a later field.

### Blocks assembly placeholder

Assembly placeholder geometry. A block may declare PSEUDO geometry marking
the volume that must stay clear to ASSEMBLE it (e.g. a hinge's pin-insertion
path / leaf-swing-during-assembly envelope). It is exempt from export (not
printed) and from the kinematic sweep (not a moving body), but other geometry
must not intrude into it or assembly is blocked. Pairs with the mating-area
footprint (2D where-to-connect) -- this is the 3D keep-clear-for-assembly
volume. The gate should flag real geometry that violates a declared
placeholder. Distinct from the model's own clearance gaps.

**Implementation note -- suppress support/overhang cost over a declared void
(from [Hitstertower oversupport](todo-case-history.md#hitstertower-oversupport)).** The
`clearance_opening` interface type lands in the plan (`prompts/planning.md`
rule 5a). Two suppressions were planned:
- `quality_gate.py` `_analyze_stl`: DONE 2026-09-15 -- downgrades an
  `overhang_exceeded` finding to advisory (severity `info`) when its
  overhanging faces bound a declared `clearance_opening`, message pointing at
  the interface's load-path note instead of "add chamfers or redesign". Reads
  `interfaces[].position_mm`/`size_mm` directly (a point + radius check), no
  keep-out zone export needed for this half.
- `mesh_io.support_cost` / `print_orientation.py`: still open -- subtract the
  down-facing area whose supporting ray passes through the zone before
  reaching the bed. This one plausibly wants the keep-out-zone route below
  (an actual volume to subtract from the ray-through-zone test, not just a
  point-in-radius check).
The structural half (is 10 mm of wall each side enough for the stated load?)
stays a `parts[].engineering_rationale` `load_path` entry -- no new gate.
Remaining scope question for the `support_cost` half: extend the existing zone
export (`units.resolve_keep_out` -> `keep_out__<name>.stl` -> `keep_out_check.py`)
so a part can emit `result["keep_out"]` tagged as an opening, vs. a distinct
`opening` key (keep-out zones are currently checked for *intrusion by other
parts*; an opening is checked for *nothing* -- it only suppresses).

### Face mount docks

Side-tagged `face_mount` docks so the planner derives union membership and
the world joint axis automatically (interface naming: keep assembly/mating
docks conceptually distinct from kinematic axes even though both live in the
block `interfaces` array).

### BOSL2-style anchors

BOSL2-style attachment/anchor helper for INTRA-part feature placement
(explored 2026-07-22). BOSL2 attachments (BelfrySCAD/BOSL2 wiki
Tutorial-Attachment-Overview) place children on named parent anchors (TOP,
RIGHT+FRONT, ...) instead of hand-computed coordinates. Assessment: the
inter-part half is already covered better by `joints` + block docks +
`mate_chain.py` (typed anchors, exact composed poses, tree-validated) -- do
NOT build a parallel assembly language. The gap is intra-part: part scripts
do coordinate arithmetic by hand (`w_mm/2 - wall - boss_od/2`), which is the
error class `script_lint` (`magic_number`, `unanchored_feature`), `cq_verify`
(`check_workplane`, `verify_feature_bounds`) and `feature_presence_check`
exist to police. Proposed narrow form: a `src/cq_anchor.py` helper importable
like `cq_verify` (`anchor(body, "TOP+RIGHT", inset=...) -> (x,y,z)` resolved
from the body/cavity bbox; maybe `place_at(...)` sugar over the boolean) --
lowers to explicit coordinates at runtime so `feature_presence_check` /
`import_params` keep working. Plus optionally per-archetype named anchor sets
in `templates/` (bbox anchors lie on non-box parts like L-brackets/rings).
Cautions: don't add a 4th positioning concept unless it lowers to the
existing one; plan `interfaces[].position_mm` stays numeric (symbolic
positions in the plan schema = much bigger blast radius, separate decision).
Open questions: (1) quantify via `build/attempts.jsonl` whether placement
arithmetic is actually the top error class; (2) script-only sugar vs
plan-level symbolic positions; (3) archetype anchor sets as shared vocabulary
for visual review. Strategy: reimplement (concept only; BOSL2 is OpenSCAD +
GPL-incompatible, see [Integration strategies](related_projects.md#integration-strategies)).

Concrete failure instance (C5 Phone-Holder session, cradle.py's hinge
knuckle, see [C5 hinge ear center-vs-edge](todo-case-history.md#c5-hinge-ear-center-vs-edge)
above): a connecting box's edge coordinate was set equal to a circle's
CENTER coordinate (reusing the shared pivot variable for both), instead of
offset by the circle's radius to its tangent line. Booleans still succeeded
(watertight), so nothing caught it -- only a rendered preview crop showed the
knuckle as a disc half-buried in a boxy step instead of a free-standing round
ear on a slim neck. `anchor()`/`place_at()` should make "offset to this
body's tangent/edge, not its center" the default so this class of bug can't
be expressed by accident; `script_lint`'s AST-only checks can't catch it
since it requires tracing which named constant plays which geometric role
(center vs. edge) across two different primitives.

### HitsterTower dovetail form

From HitsterTower ("D:\Code\cq-design\debug\session-export-1786431095406.zip"):
"Hinges -> dovetail corner joints. All 4 pin_hinge kinematic joints are gone.
Each corner is now a dovetail_corner_joint (4 pins/tails per corner, 3mm
board thickness, 6mm tooth insertion depth, 0.1mm clearance for separable
fit). The tower no longer folds -- it fully disassembles at all 4 corners
into 4 flat panels + base for storage, and presses back together for use.
Polarity: every wall carries pins on its east edge, tails on its west edge,
so the ring closes consistently (wall_a->wall_c->wall_b->wall_d->wall_a)."
Couldn't express this as a formal top-level `joints` mate-chain (the schema
requires a single-rooted tree; a 4-panel ring produces conflicting/
double-anchored paths) -- so each wall keeps its own explicit placement, and
the dovetail mating is declared through each wall's `interfaces` instead.
Functionally equivalent, just not chained through the schema's joint-tree
mechanism.

Resolved by `openspec/changes/rigid-joint-loops/`: `joints` now accepts loops of rigid
joints (closure-checked). Migrating the tower itself onto `joints` is a follow-up eval case.
