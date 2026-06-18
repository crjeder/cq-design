## Context

The skill runs user CadQuery scripts in a subprocess and validates the resulting STL. Users currently have no access to standard hardware geometry — they must approximate bolt heads, nut flats, and insert dimensions by hand.

`cq_warehouse` (https://github.com/gumyr/cq_warehouse) is a CadQuery 2.x-native library providing parametric ISO hardware. Unlike `cqparts` (which required FreeCAD), `cq_warehouse` parts are CadQuery `Solid` subclasses that work identically to hand-modelled geometry. No wrappers, no special export hooks needed.

## Goals / Non-Goals

**Goals:**
- Make `cq_warehouse` importable in any model script run by the skill
- Document usage patterns in `SKILL.md` so Claude generates correct import/instantiation code
- Verify the integration with a test that passes through `run_cadquery_model.py`

**Non-Goals:**
- Wrapping `cq_warehouse` API or building adapters
- Adding `cq_warehouse` parts to `blocks/inventory.json` (the inventory is for the skill's own building blocks, not external libraries)
- Pinning an exact version (no PyPI release exists; pin to a commit SHA if stability is required)

## Decisions

### No pipeline changes required

**Decision:** Add `cq_warehouse` to `requirements.txt` only. Zero changes to `run_cadquery_model.py`, `orchestrate.py`, or any other pipeline script.

**Rationale:** `cq_warehouse` parts are `Solid` instances. A script that does `bolt = HexHeadScrew(...); result = cq.Workplane().box(...).add(bolt)` produces a normal CadQuery solid. The existing mtime-based STL discovery, geometry analysis, and DFM checks all work unchanged.

### simple=True default for iteration

**Decision:** Document `simple=True` as the default for all examples.

**Rationale:** Thread geometry adds significant mesh complexity and render time. During the iterate-and-validate loop, thread detail is irrelevant. Final delivery scripts can set `simple=False`.

### Installation from GitHub

**Decision:** Pin as `cq_warehouse @ git+https://github.com/gumyr/cq_warehouse.git` in `requirements.txt`.

**Rationale:** The package has no PyPI release. The git source is the canonical distribution. If a specific commit SHA is needed for reproducibility, update the URL to `...git@<sha>`.

## Risks / Trade-offs

- **No PyPI release**: `pip install` requires network access to GitHub. Mitigation: document the install command; teams with restricted networks can mirror the repo.
- **API instability**: `cq_warehouse` is under active development. The `cq_object` property was deprecated in 0.8.0. Mitigation: document the current API pattern; the `simple=True` path is stable.
- **Build time**: Installing from git source requires building from source, which adds ~60s to fresh environment setup. Acceptable for a once-per-env cost.
