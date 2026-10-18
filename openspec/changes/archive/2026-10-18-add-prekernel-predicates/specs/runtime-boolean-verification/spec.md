## ADDED Requirements

### Requirement: In-script helper checks a fillet radius before the kernel

`cq_verify` SHALL provide `check_fillet(body, radius, selector=None, label="")` that
measures the edges of `body` selected by `selector` (all edges when `None`) and raises
a marked `RuntimeError` `[cq-verify:fillet_radius:<label>]` when `radius` is greater
than or equal to the limit set by any adjacent edge. An adjacent edge is any other edge of
`body` that shares a vertex with a selected edge; its limit is its length, halved when
both of its ends touch a selected edge other than itself. The error
detail SHALL report the requested radius, the computed limit, and the selector. On
success the helper SHALL return `body` unchanged without calling the kernel's fillet.

#### Scenario: Radius exceeds the adjacent edge

- **WHEN** a script calls `check_fillet(box(20, 20, 5), 6, ">Z", "lid_edge")`
- **THEN** the helper raises `RuntimeError` marked `fillet_radius` naming `lid_edge`
  and reporting a 5.00 mm limit

#### Scenario: Valid radius passes through

- **WHEN** a script calls `check_fillet(box(20, 20, 5), 2, ">Z", "lid_edge")`
- **THEN** the helper returns the same `body` object

#### Scenario: Edges shared from both ends halve the limit

- **WHEN** a script calls `check_fillet(box(20, 20, 5), 3, "|Z", "corners")`
- **THEN** the helper does not raise, because the 20 mm horizontals give a 10 mm limit
  and the parallel 5 mm verticals are not adjacent edges

---

### Requirement: In-script helper checks a chamfer length before the kernel

`cq_verify` SHALL provide `check_chamfer(body, length, selector=None, label="")`
applying the same adjacent-edge rule as `check_fillet` to a symmetric chamfer length,
raising `[cq-verify:chamfer_size:<label>]` on violation and returning `body` unchanged
on success.

#### Scenario: Chamfer too large

- **WHEN** a script calls `check_chamfer(box(20, 20, 5), 5, ">Z", "top_chamfer")`
- **THEN** the helper raises `RuntimeError` marked `chamfer_size` naming `top_chamfer`

#### Scenario: Chamfer within limit

- **WHEN** a script calls `check_chamfer(box(20, 20, 5), 1, ">Z", "top_chamfer")`
- **THEN** the helper returns the same `body` object

---

### Requirement: In-script helper checks a hole ligament

`cq_verify` SHALL provide `check_ligament(wall_mm, hole_d_mm, min_mm, label="")` that
computes the ligament on each side of a hole centered in a wall as
`(wall_mm - hole_d_mm) / 2` and raises `[cq-verify:thin_ligament:<label>]` when it is
below `min_mm`, reporting the ligament and `min_mm`. On success it SHALL return the
ligament in mm.

#### Scenario: Ligament below minimum

- **WHEN** a script calls `check_ligament(6, 5, 1.2, "m5_boss")`
- **THEN** the helper raises `RuntimeError` marked `thin_ligament` naming `m5_boss`
  and reporting a 0.50 mm ligament

#### Scenario: Ligament sufficient

- **WHEN** a script calls `check_ligament(10, 5, 1.2, "m5_boss")`
- **THEN** the helper returns 2.5

---

### Requirement: Wrapper maps pre-kernel predicate failures to typed errors

`run_cadquery_model.py` SHALL register `fillet_radius`, `chamfer_size`, and
`thin_ligament` in `_VERIFY_HINTS`, so a marked failure becomes an `errors` entry with
that `type`, the `label`, the detail as `message`, and a non-empty `hint`, instead of
an `occ_exception`.

#### Scenario: Over-large fillet in a script

- **WHEN** a part script calls `check_fillet` with a radius above the limit before its
  `.fillet()` call and is run through `run_cadquery_model.py`
- **THEN** the JSON has `success: false` and `errors[0].type == "fillet_radius"` with a
  non-empty `hint`, and no `occ_exception` entry

#### Scenario: Marker strings classify

- **WHEN** stderr ends with `RuntimeError: [cq-verify:<kind>:x] detail` for each of
  the three kinds
- **THEN** `_translate_stderr` returns one entry whose `type` is that kind

---

### Requirement: Generated-script guidance covers the pre-kernel predicates

The "Construction-time verification" section of `prompts/part.md` SHALL show
`check_fillet`, `check_chamfer`, and `check_ligament` in its import example, state the
adjacent-edge rule in one line, and direct the author to call `check_fillet` /
`check_chamfer` before a fillet or chamfer whose size is computed from parameters or
approaches a wall or edge dimension, and `check_ligament` before a hole placed in a
wall sized from a parameter.

#### Scenario: Prompt documents the helpers

- **WHEN** the rendered part prompt is read
- **THEN** its Construction-time verification section names all three helpers, their
  typed error kinds, and the adjacent-edge rule
