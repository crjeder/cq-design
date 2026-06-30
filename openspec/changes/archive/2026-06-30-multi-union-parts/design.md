# Design: multi-union-parts

This is the buildable extraction of Option 3 from the `joint-contract` design note: make `union`
first-class, the plan owns the union namespace, the script fulfils it. It does NOT include the joint
contract or annotation geometry.

## Decision 1: The `unions` field shape

A part gains an optional `unions` array of objects:

```json
"unions": [
  { "id": "leafA", "plate": "p1" },
  { "id": "leafB", "plate": "p2" }
]
```

- `id` required, globally unique across the model (shares the namespace with single-union part ids).
- `plate` optional, per union.
- Absent `unions` => the part is one union: id = part id, plate = the part's `plate` (today, unchanged).
- `placement` stays a **part-level** field and applies to every union the part produces (the script
  builds all the part's unions in one shared frame; per-union placement is out of scope).

## Decision 2: The `result` contract accepts a name->Workplane map

A part script's top-level `result` is either:

- a `cq.Workplane` -> one union, id = part id (today), or
- a `dict[str, cq.Workplane]` -> one union per entry, keys exactly the part's declared `unions` ids.

`exporters._load_result` returns `Workplane | dict[str, Workplane]`. A tiny shared helper normalizes
either shape into an ordered `[(union_id, Workplane), ...]` given the part, so every consumer reads
the same structure:

```
   resolve_unions(part, result) -> list[(union_id, Workplane)]
     dict result : [(k, v) for k in part.unions]   (validated: keys == declared)
     plain result: [(part.id, result)]
```

## Decision 3: Plate is resolved per union

```
   plate_of(part, union):  union.get("plate")  or  part.get("plate")  or  union.id
```

The single-union default reproduces today's `part.plate or part.id`. `plate_clearance_check` and
`model_export` plate grouping switch to this per-union resolution.

## Decision 4: Union enumeration is centralized

Several consumers compute "all unions" or "the plate of X" from `parts` today
(`model_export`, `kinematic_check.all_union_ids`, `plate_clearance_check._plate_of`). They are
generalized to iterate the expanded union set via one helper (`iter_unions(plan) -> (part, union_id,
plate)`), so the part->unions expansion lives in exactly one place. The kinematic/plate stages then
need no conceptual change -- they already key off per-union `<id>.stl` and a plate key; the id just
becomes a union id and the fixed set is "every other union" as the spec already states.

## Decision 5: The DFM wrapper validates each union body

`run_cadquery_model` runs a part script in the part loop and checks geometry (watertight, thin walls,
overhang, manifold) on the exported STL. With a `dict` result, each union is a distinct rigid body:
the wrapper validates **each** union (a per-union entry in the JSON `geometry`/`errors`), and
`run_model_shim` auto-exports one `<union_id>.stl` per key (a plain result keeps `<script>.stl`).
This is the trickiest touch point -- the JSON contract gains per-union geometry -- and is kept
backward compatible: a single-Workplane result yields exactly today's single-body report.

## Decision 6: model_export splits instead of compounding

```
   today:   makeCompound(result.vals())            -> ONE named object per part
   change:  for (uid, wp) in resolve_unions(part, result):
              object  = named 3MF object  name=uid (or its description)   plate=plate_of(...)
              placed[uid] = apply_cq(wp, part.placement)
              <uid>.stl   = placed[uid]
            cross-check: dict keys == declared unions  (else a structured error)
```

The named-object 3MF and per-union STL machinery already exists; this feeds it per union rather than
per part.

## Decision 7: Backward compatibility is the safety net

No `unions` field + a plain `Workplane` result = byte-identical to today (id = part id, one object,
one STL, `part.plate or part.id`). Every existing plan, script, and test is unaffected; the new path
is purely additive and opt-in.

## Validation (plan_validate)

- Every part's declared `unions` ids are unique across the whole model (and do not collide with
  single-union part ids).
- `kinematics.moving_union` resolves to a union id in the expanded set (not just a part id).
- Plate references and the `unions[].plate` values are well-formed.
- (Runtime, in `model_export`) a `dict` result's keys equal the part's declared `unions`; mismatch is
  a structured error, not a traceback.

## Open / deferred

- Per-union `placement` (posing a part's unions independently) -- out of scope; one shared part frame.
- Joint contract + satisfaction algebra (`joint-contract` D1) and annotation geometry -- later changes
  that consume this union namespace.
