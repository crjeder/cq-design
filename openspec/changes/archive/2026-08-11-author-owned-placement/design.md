## Context

`parts[].placement` is the single structured source of truth for a union's pose in the
shared assembled frame (`printable-unit-model`). It is written in Phase 2 by the planner
and first consumed at the END of Phase 3 by `model_export.py`, then by the kinematic /
plate-clearance / keep-out stages reading the exported STLs.

The geometry the placement transforms, however, is authored in Phase 3 by a different
agent, in whatever frame that agent chooses. Nothing tells it which frame the planner
assumed. Verified by grep 2026-08-11:

- `prompts/part.md` has no placement or frame content at all; the author receives
  `{{PART_NOTES}}` and no pose field.
- `planning_notes`, where planners currently narrate the convention, is read by nothing
  (`skill/phase3_build.md`, `skill/phase4_deliver.md`, `prompts/part.md`, `src/*.py`:
  zero references).
- The part loop itself reads `placement` zero times. Print-orientation is explicitly
  computed in the AUTHORED frame, "before any `placement`"
  (`skill/phase3_build.md:579`).

So the frame contract is unwritten and unenforced, and the field that tries to carry it
informally has no reader.

The plan already contains the inverted pattern. A part reached through a `joints` mate
chain MUST NOT declare `placement`; its pose is derived from the geometry the author
built, by composing dock frames (`mate_chain.compute_mate_poses`). Two pose mechanisms,
pointing opposite ways.

## Goals / Non-Goals

**Goals:**
- Make the assembled pose an output of authoring, so the frame the author chose and the
  transform that positions it can never disagree.
- Give the planner-to-author pose contract a field with an actual reader.
- Give the human a short pose statement instead of a paragraph of transform prose.
- Keep every existing `placement` consumer untouched.

**Non-Goals:**
- Any new pose representation (matrix, quaternion, named frames). The
  `{rotate, translate_mm}` shape is unchanged.
- Symbolic or structured intent. `pose_intent` is prose for a reader that understands
  prose; the structured form of the pose already exists and is called `placement`.
- Solving the `planning_notes` question generally (see TODO "rationale audit"). This
  change removes one class of content from it and no more.
- Changing `joints` / `mate_chain` derivation, which is already correct.
- Intra-part feature placement (the BOSL2-anchors TODO item); this is about a part's
  pose in the model, not features within a part.

## Decisions

### D1: The author owns `placement`; the planner owns `pose_intent`

The planner states the goal ("stands upright, outward face toward world -Y, at the
tower's NE corner"). The author picks its authoring frame, builds, and writes back the
transform that satisfies the goal.

*Alternative considered:* keep the planner authoring `placement` and simply add the frame
convention as a second field the author reads. Rejected -- it preserves the coupling and
adds a second field that must stay in sync with the first, with no mechanism to detect
divergence. The current bug is exactly a sync failure between an implicit convention and
an explicit transform; two explicit fields would fail the same way, more visibly.

*Alternative considered:* derive everything through `joints` and delete `placement`.
Rejected -- a mate chain requires a single-rooted tree, and real models produce rings
(the HitsterTower 4-panel ring produces conflicting/double-anchored paths, see the
separate TODO item). `placement` is the escape hatch for topologies the tree cannot
express, and must stay.

### D2: `pose_intent` is an optional per-part free-text string

*Alternative considered:* a plan-level authoring convention with per-part override,
mirroring `optimize_for`. Rejected as premature. The shared thing in the HitsterTower
example ("all panels authored lying flat") is an *authoring frame* convention -- and
under D1 the authoring frame is the author's choice, so a plan-level field would be the
planner prescribing exactly what this change hands to the author. What is genuinely
per-part is the goal pose, which differs for every wall. If a shared vocabulary later
proves necessary, it can be added without invalidating per-part intent.

*Alternative considered:* fold it into `description`. Rejected -- `description` is the
part's shape ("north wall panel"), consumed as `{{PART_DESCRIPTION}}`; overloading it
with pose makes both harder to state and gives the author no way to tell which
constraint it is failing.

### D3: The handback rides the existing plan write-back; no new tooling

The part author is an LLM that already edits `BUILD_PLAN.json` mid-Phase-3 for
`dimensions` (`skill/phase3_build.md:552`) and `load` (`:621`, which states the
principle outright: "a corrected understanding belongs in the plan, not just in this one
CLI invocation"). `placement` becomes the third such field.

*Alternative considered:* the script declares a module-level `PLACEMENT` dict and a tool
statically parses it, as `import_params.py` does for `PARAMETERS`. Rejected --
`import_params.parse_parameters` extracts numeric literals only, so this needs a new
parser plus a new reconcile path, for one field, on a route the author already walks by
hand for two other fields.

### D4: Correctness of the returned transform is checked where it already is

A wrong handback is a wrong assembled model, and the model-level stages exist precisely
to catch that: `kinematic_check` (interference through the swept range),
`plate_clearance_check`, `keep_out_check`, plus the whole-model assembled preview
checkpoint the user approves. No new verification stage is introduced.

The one real loss is timing: those stages run after export rather than at Phase 2. That
is inherent to the inversion -- the information does not exist until the part is built.

### D5: The joint-contract axis arm moves to a pre-export re-validation

`plan_validate._check_kinematics` compares a block's `dof.direction` against the plan's
`axis_dir` *after* pushing it through the moving union's `placement`
(`src/plan_validate.py:282-300`). Under D1 that placement is absent at Phase 2, and
`transform_direction(dir, None)` is identity -- so the arm would silently compare in the
wrong frame and pass or fail for the wrong reason.

Decision: run `plan_validate.py` again after the last part's write-back and before
`model_export.py`. That run is the authoritative one for the axis arm. The Phase 2 run
reports, as a non-fatal advisory, which kinematics entries had their axis arm deferred
for want of a placement -- reusing the existing advisory-findings channel that
`check_block_thinness` already prints alongside `BUILD_PLAN OK`
(`src/plan_validate.py:523-527`), not a new output contract.

*Alternative considered:* require the author to write an explicit identity `placement`
so that "absent" becomes unambiguously "not supplied". Rejected -- it contradicts
`printable-unit-model`'s standing requirement that an absent placement means identity,
and would churn every eval-corpus golden for a distinction only one check needs.

Consequence accepted: absent still means identity, so the advisory cannot distinguish
"author has not run yet" from "author chose the assembled frame". The advisory therefore
reads as "deferred or identity", and the pre-export re-run is what makes it moot.

### D6: Existing planner-written placements are proposals, not errors

A plan carrying a planner-written `placement` (every eval golden, every plan on disk)
stays schema-valid and semantically unchanged. The author treats it as a starting
proposal: confirm it if the frame it chose matches, correct it if not. This keeps the
change additive at the data layer and confines it to the prompt/skill layer.

## Risks / Trade-offs

- **A bad handback is caught later than a bad plan was.** → The catching stages
  (kinematic, plate-clearance, keep-out, assembled preview) all already exist and all
  already run before delivery. Feedback moves later within one session; it is not lost.
- **`pose_intent` could bloat exactly as `planning_notes` did.** → It has a reader (the
  part prompt) and a single job (state one pose), which is the property `planning_notes`
  lacks. The spec constrains it to the pose goal; anything else belongs in `part_notes`.
- **The author could omit the write-back and leave a stale or absent placement.** → The
  pre-export re-validation is the gate, and the assembled preview makes a wrong pose
  visible to the user before delivery. An identity placement on a part that needed one
  shows up as parts overlapping at the origin, which the clearance stages flag.
- **A multi-union part has one `placement` for all its unions**
  (`printable-unit-model:100`). → Unchanged by this design: the author writing the part
  is the single agent that built all of those unions in one frame, so it is strictly
  better positioned to supply that one transform than the planner was.
- **`root_part` is "anchored by its own `placement`"** (`prompts/planning.md` rule 7).
  → Still true; the anchor is now author-written. If the root's author supplies nothing,
  identity is a legitimate anchor and the mate chain still resolves.
- **Two agents could disagree about the assembled frame's origin** (e.g. which corner is
  the model origin) when parts are authored independently. → This risk predates the
  change and is what `pose_intent` addresses by naming the goal in shared world terms.

## Migration Plan

1. Schema field added first (optional, additive) -- every existing plan stays valid.
2. Prompt and skill changes land together; a plan produced before them still validates
   and still exports, because a planner-written placement is a valid author proposal
   (D6).
3. No golden regeneration, no data migration, no rollback step beyond reverting the
   prompt/skill edits.

## Open Questions

- Should `pose_intent` eventually become required for any part whose `placement` is not
  identity? Deferred until there is evidence the optional form gets skipped.
- Does the pre-export `plan_validate` re-run belong in Phase 3's export step (where it
  is proposed) or inside `model_export.py` itself? Proposed as a skill step to keep the
  export tool free of plan-policy concerns, but a gate-side call would be harder to
  forget.
- The TODO "rationale audit" may conclude `planning_notes` should be bounded or removed
  entirely. This change removes pose prose from it either way and does not depend on
  that outcome.
