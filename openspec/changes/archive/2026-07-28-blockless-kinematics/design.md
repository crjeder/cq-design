## Context

`plan_validate.py`'s `_check_kinematics` (`src/plan_validate.py:228-297`) and
`kinematic_check.py`'s `run_kinematic_check` (`src/kinematic_check.py:159-327`) both
require a `kinematics` entry to name an inventory `block`: the schema marks `block`
required, the validator looks it up and rejects an unknown name, and the runner reads
`dof.mechanical_limit`/`dof.type`/`dof.direction`/`dof.origin` from it unconditionally.
That contract is sound when the joint really is a parametric block (`pin_hinge`,
`dovetail_groove`, ...). It has no answer for a joint hand-built from raw CadQuery
primitives, which is what a custom hinge normally is -- see `proposal.md` for the
C5 Phone-Holder retrospective, where the omission forced seven rounds of a
hand-written, unreliable ad-hoc sweep instead of running `kinematic_check.py` at all.

The sweep itself (`iter_poses`, `_sweep_collision`) already consumes only
`axis_origin_mm`, `axis_dir`, `type`, `required_range`, and `step` -- nothing block
shaped. Only the numeric mechanical-limit check and the plan-validator's joint-contract
arms (type/axis/coaxiality match against the block's `dof`) are block-dependent.

## Goals / Non-Goals

**Goals:**
- `block` becomes optional on a `kinematics` entry: a block-less entry fully specifies
  its own motion (`axis_origin_mm`, `axis_dir`, `type`, `required_range`, `step`) with
  no inventory backing.
- A block-less entry may declare its own `mechanical_limit` so the numeric range check
  still has something to compare against; when it doesn't, the numeric arm is reported
  as not-applicable (not silently skipped) and the sweep still runs.
- `plan_validate.py` skips only the block-dependent contract arms for a block-less
  entry, keeping every check that doesn't need a block (union-id resolution, schema
  shape, nested-entry recursion).
- Planner guidance stops recommending "omit `kinematics`" for a raw-primitive joint.

**Non-Goals:**
- Relaxing the contract for an entry that *does* name a block. That contract catches
  real block/plan misalignment and stays exactly as strict.
- Inferring an axis from geometry. The axis stays author-declared for both block-backed
  and block-less entries.
- Changing `_check_kinematics`'s existing plain-string error style to the structured
  `joint_contract` issue shape described in the `joint-contract` spec. That mismatch
  between spec and implementation predates this change (see Decisions below) and is out
  of scope here.

## Decisions

### Target capability for the contract-scope requirement: `joint-contract`, not `joint-classification`

`proposal.md`'s "Modified Capabilities" section names `joint-classification` for the
"contract applies only when a block is named" requirement. Reading both specs shows
that's the wrong target: `openspec/specs/joint-classification/spec.md` is the
motion/reversible/`carries` taxonomy for inventory entries -- unrelated to whether a
plan's joint contract check runs. The type/axis/coaxiality contract that
`_check_kinematics` implements is `openspec/specs/joint-contract/spec.md`'s
"A declared joint is satisfied only when the block's dof covers it" requirement. This
change's spec delta targets `joint-contract`; `joint-classification` is untouched.

Separately: `joint-contract`'s spec already describes the check as emitting a
structured `joint_contract` issue (`{source, severity, type, message, hint}`).
`_check_kinematics` as it exists today returns plain description strings
(`errors: list[str]`), not structured issues -- `grep` for `joint_contract` in `src/`
finds nothing. That gap predates this change and isn't touched here; the new
block-less branch follows the existing string-error style so the diff doesn't also
carry an unrelated issue-shape migration.

### Schema: drop `block` from `required`, add entry-level `mechanical_limit`

`src/build_plan_schema.json`'s `kinematics_entry`:
- Remove `"block"` from `required`. The property definition stays (now optional);
  its description gains a sentence on the block-less case.
- Add `"mechanical_limit"`: a `[lo, hi]` array, same shape as a block's
  `dof.mechanical_limit`. Meaningful only when `block` is absent (a block-backed
  entry's numeric check is still `dof.mechanical_limit`, unchanged); ignored if both
  are present, since the block's `dof` remains authoritative for anything it backs.

No `additionalProperties` conflict: `mechanical_limit` is a new named property, not a
relaxation of `additionalProperties: false`.

### `plan_validate.py`: branch `_check_kinematics` on presence of `block`

```python
for entry in iter_kinematics_entries(kinematics):
    jid = entry.get("joint_id", "(unknown)")
    ref = entry["moving_union"]
    if ref not in union_part:
        errors.append(f"Kinematics '{jid}': moving_union '{ref}' is not a union id")
    block_name = entry.get("block")
    if block_name is None:
        continue  # block-less: axis is author-declared, nothing to contract-check
    block = get_block(block_name, inventory_path)
    ...  # unchanged from here down
```

`moving_union` resolution runs unconditionally (doesn't need a block). Schema
validation already guarantees `axis_origin_mm`/`axis_dir`/`type`/`required_range`/`step`
are present and well-formed for every entry, block-less or not, and
`iter_kinematics_entries` already recurses into `children` regardless -- so a
block-less entry gets exactly the same non-contract checks as a block-backed one, at
every nesting depth, with no new code path for that part.

### `kinematic_check.py`: source the limit from the block, or the entry, or neither

```python
block = get_block(entry["block"], inventory_path) if entry.get("block") else None
dof = (block or {}).get("dof")
limit = dof["mechanical_limit"] if dof is not None else entry.get("mechanical_limit")

if limit is not None:
    mlo, mhi = limit
    if lo < mlo - 1e-9 or hi > mhi + 1e-9:
        issues.append(make_issue(..., "error", "range_exceeds_limit", ...))
        continue  # mechanically impossible: no mesh, no sweep
else:
    issues.append(
        make_issue(
            "kinematics", "warning", "range_check_not_applicable",
            f"Joint '{jid}' has no mechanical_limit source (block-less entry with none "
            "declared); numeric range check skipped, collision sweep still runs.",
            "Declare 'mechanical_limit' on the entry to enable the numeric check.",
            joint_id=jid,
        )
    )
# sweep runs exactly as today, unconditionally except for the impossible-range `continue` above
```

`range_check_not_applicable` is a new, distinct issue type from `check_skipped`
(reserved for missing backend/STL/manifest) -- this is per-joint and about the
mechanical-limit source, not the whole stage. It's `severity: "warning"`, not
`"error"`: the joint is not invalid, there's simply nothing to compare against, and
`proposal.md` is explicit that this must be a visible result, not a silent no-op.
Everything after this branch (staleness check, mesh loading, `_sweep_collision`) is
unchanged: it already only depends on `subtree_ids`/`fixed_ids`/`entry`, none of which
come from the block.

### Planner guidance: declare the axis directly instead of omitting `kinematics`

`prompts/planning.md` rule 9 and the "Kinematic validation" section of
`skill/phase3_build.md` both currently imply a block is part of declaring a joint.
Each gains one addition (not a rewrite of the surrounding stale-but-unrelated text,
e.g. the pre-existing `unit` field mentions that no longer match the schema -- out of
scope here):
- A sentence in rule 9: a custom/raw-primitive joint omits `block` and declares
  `mechanical_limit` directly if a numeric sanity bound is wanted; never omit the
  whole `kinematics` entry just because no block fits.
- A short block-less example alongside the existing block-backed one in
  `skill/phase3_build.md`, naming the phone-holder retrospective's omitted-entry
  choice as the anti-pattern this removes.

## Risks / Trade-offs

- **A block-less entry with no `mechanical_limit` gets no numeric sanity check** --
  only the sweep. Accepted: the sweep is the authoritative check for a specific
  assembled instance anyway (the docstring for `kinematic_check.py` already says the
  inventory limit is "a nominal sanity bound"); the new `range_check_not_applicable`
  finding makes the gap visible instead of hiding it.
- **Two mechanical_limit sources to reason about** (block `dof` vs. entry field).
  Mitigated by a strict precedence (block wins when present) and the schema
  description stating the entry field is ignored when `block` is present, so there's
  never an ambiguous case.
- **The `joint-contract` capability's spec already diverges from the implementation**
  (structured issue vs. plain string). Not fixed here to keep this change scoped to
  the block-less gap; flagged explicitly above so it isn't mistaken for something this
  change introduced.

## Migration Plan

Purely additive: `block` becomes optional (existing plans that always supplied it are
unaffected), and `mechanical_limit` is a new optional property. No existing plan or
eval case changes behavior -- every block-backed entry validates and sweeps exactly as
before. No data migration, no dependency change.
