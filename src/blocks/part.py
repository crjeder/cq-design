"""Step-list part recorder: ``select`` / ``resize`` / ``place`` over inventory entries.

    from blocks import Part

    part = Part("mounting_plate")
    plate = part.select("box", id="plate")
    part.resize(plate)
    part.place(plate, op="base")
    boss = part.select("screw_boss", id="boss")
    part.resize(boss)
    part.place(boss, at=part.positions("boss"), op="union")
    result = part.result()

Values come from the part's ``blocks_needed`` instances in ``BUILD_PLAN.json`` (found
via ``CQ_PLAN``, else by walking up from the script's directory), so the script holds
no dimensions. Every step runs eagerly and is checked at once: plan binding, the
entry's own probes at ``resize``, then volume sign, solid count and every registry
probe after each ``place``. A failing step raises a marked ``RuntimeError`` that
``run_cadquery_model.py`` maps to a typed error.
"""

import copy
import functools
import hashlib
import importlib
import inspect
import json
import os
import sys
from dataclasses import dataclass, field, replace
from typing import Any

import cadquery as cq

import probes as pr
from blocks.validate import load_inventory

_VOLUME_EPS_MM3 = 1e-3


def _fail(kind: str, label: str, detail: str) -> RuntimeError:
    return RuntimeError(f"[cq-verify:{kind}:{label}] {detail}")


def _moved(shape, at, rotate):
    """shape rotated about X, then Y, then Z (degrees, about the origin), then moved to at."""
    for axis, angle in zip(((1, 0, 0), (0, 1, 0), (0, 0, 1)), rotate, strict=True):
        if angle:
            shape = shape.rotate((0, 0, 0), axis, angle)
    return shape.translate(cq.Vector(*at))


def _on_curves(edge, curves, tol: float = 1e-3) -> bool:
    """True when the edge lies on one of the curves (sampled at three points)."""
    pts = [cq.Vertex.makeVertex(*edge.positionAt(t).toTuple()) for t in (0.1, 0.5, 0.9)]
    return any(all(v.distance(c) <= tol for v in pts) for c in curves)


def _is_horizontal(edge, steps: list) -> bool:
    """True when the edge runs horizontally in print pose (build pose rotated by steps)."""
    from placement import transform_direction

    for t in (0.0, 0.5, 1.0):
        d = transform_direction(edge.tangentAt(t).toTuple(), {"rotate": steps})
        if abs(d[2]) > 0.1:
            return False
    return True


@functools.cache
def _source_hash(module_name: str) -> str:
    """Hash of an entry module's source, so an edited block invalidates cached steps."""
    return hashlib.sha256(
        inspect.getsource(importlib.import_module(module_name)).encode()
    ).hexdigest()


def find_plan(script_file: str | None) -> str:
    """Path of BUILD_PLAN.json: CQ_PLAN, else the nearest one above the script."""
    env = os.environ.get("CQ_PLAN")
    if env:
        return env
    d = os.path.dirname(os.path.abspath(script_file)) if script_file else os.getcwd()
    while True:
        cand = os.path.join(d, "BUILD_PLAN.json")
        if os.path.isfile(cand):
            return cand
        parent = os.path.dirname(d)
        if parent == d:
            raise _fail("step_plan", "plan", f"no BUILD_PLAN.json above {script_file or d}")
        d = parent


@dataclass
class Handle:
    name: str
    id: str
    entry: dict
    instance: dict
    params: dict | None = None
    shape: Any = None
    probes: list = field(default_factory=list)


class Part:
    # Set by the step worker: step key -> cached result, shared across runs of a script.
    cache: dict | None = None
    # The most recently constructed Part, so the worker can read its step report.
    last: "Part | None" = None

    def __init__(self, part_id: str, plan_path: str | None = None):
        script = sys._getframe(1).f_globals.get("__file__")
        path = plan_path or find_plan(script)
        with open(path, encoding="utf-8") as f:
            plan = json.load(f)
        part = next((p for p in plan.get("parts", []) if p.get("id") == part_id), None)
        if part is None:
            raise _fail("step_plan", part_id, f"part {part_id!r} not in {path}")
        self.id = part_id
        self.plan_part = part
        self.instances = {
            b["id"]: b for b in part.get("blocks_needed", []) if isinstance(b, dict) and "id" in b
        }
        self.inventory = {e["name"]: e for e in load_inventory()}
        self.body: Any = None
        self.unions: dict[str, Any] = {}
        self.steps: list[dict] = []
        self.registry = pr.Registry()
        seeded, self.unprobed_interfaces = pr.plan_probes(part)
        self.registry.add(seeded, "plan")
        self.placed = False
        self.armed: set[str] = set()
        self.placements: list[tuple] = []
        # Plan probes are part of every cached state, so they seed the key chain.
        plan_probes = json.dumps([pr.as_dict(p) for p in seeded], sort_keys=True, default=str)
        self.key = hashlib.sha256(f"part:{part_id}|{plan_probes}".encode()).hexdigest()
        self.last_good: dict | None = None
        Part.last = self

    def _chain(self, kind: str, args: dict, module: str = "") -> str:
        """Advance the step key: hash of the previous key, this step's resolved args and its
        entry's source. Equal keys mean equal state after the step."""
        text = json.dumps(args, sort_keys=True, default=str) + (
            _source_hash(module) if module else ""
        )
        self.key = hashlib.sha256(f"{self.key}|{kind}|{text}".encode()).hexdigest()
        return self.key

    def _state(self) -> dict:
        return {
            "body": self.body,
            "unions": dict(self.unions),
            "probes": list(self.registry.probes),
            "retired": list(self.registry.retired),
            "armed": set(self.armed),
            "placements": list(self.placements),
            "placed": self.placed,
        }

    def _restore(self, state: dict) -> None:
        self.body, self.unions, self.placed = state["body"], dict(state["unions"]), state["placed"]
        self.registry.probes, self.registry.retired = list(state["probes"]), list(state["retired"])
        self.armed, self.placements = set(state["armed"]), list(state["placements"])

    def _cached(self, key: str, step: dict):
        """Cached result for key (marking the step cached), or None."""
        hit = Part.cache.get(key) if Part.cache is not None else None
        if hit is not None:
            step.update({k: v for k, v in hit["step"].items() if k != "index"}, cached=True)
        return hit

    def _record(self, kind: str, label: str, **info) -> dict:
        step = {"index": len(self.steps), "kind": kind, "block": label, "ok": True, **info}
        self.steps.append(step)
        return step

    def _error(self, step: dict, kind: str, detail: str) -> RuntimeError:
        step["ok"] = False
        step["error"] = {"type": kind, "message": detail}
        return _fail(kind, f"step{step['index']}:{step['block']}", detail)

    def select(self, name: str, id: str) -> Handle:
        step = self._record("select", name, id=id)
        if name not in self.inventory:
            raise self._error(step, "step_plan", f"no inventory entry {name!r}")
        if id not in self.instances:
            raise self._error(
                step,
                "step_plan",
                f"no blocks_needed instance {id!r} in part {self.id!r}; planned ids: "
                f"{sorted(self.instances)}",
            )
        inst = self.instances[id]
        if inst.get("name") != name:
            raise self._error(
                step,
                "step_plan",
                f"instance {id!r} is planned as {inst.get('name')!r}, not {name!r}",
            )
        key = self._chain("select", {"name": name, "id": id})
        if Part.cache is not None:
            step["cached"] = key in Part.cache
            Part.cache.setdefault(key, {"step": copy.deepcopy(step)})
        return Handle(name, id, self.inventory[name], inst)

    def resize(self, handle: Handle) -> Handle:
        params = dict(self.instances[handle.id].get("params", {}))
        step = self._record("resize", handle.name, id=handle.id, args=params)
        declared = set(handle.entry.get("params", {}))
        unknown = sorted(set(params) - declared)
        missing = sorted(declared - set(handle.entry.get("optional", [])) - set(params))
        if unknown or missing:
            raise self._error(
                step,
                "step_plan",
                f"instance {handle.id!r}: unknown params {unknown}, missing params {missing}; "
                f"{handle.name} declares {sorted(declared)}",
            )
        key = self._chain("resize", {"id": handle.id, "params": params}, handle.entry["module"])
        hit = self._cached(key, step)
        if hit is not None:
            handle.params, handle.shape, handle.probes = hit["handle"]
            return handle
        module = importlib.import_module(handle.entry["module"])
        shape = getattr(module, handle.entry["function"])(**params)
        if isinstance(shape, dict):
            raise self._error(step, "step_plan", f"{handle.name} returns unions; not placeable")
        probe_fn = getattr(module, handle.entry["probes"]) if "probes" in handle.entry else None
        local = probe_fn(**params) if probe_fn else []
        handle.params, handle.shape, handle.probes = params, shape.val(), local
        failed = []
        for p in local:
            if p.kind == "delta":
                continue
            ok, got = pr.evaluate(p, handle.shape)
            if not ok:
                failed.append({**pr.as_dict(p), "got": got})
        step["probes"] = {"checked": len(local), "failed": failed, "retired": []}
        if failed:
            raise self._error(step, "probe_failed", f"{handle.name} own probes failed: {failed}")
        if Part.cache is not None:
            Part.cache[key] = {"step": copy.deepcopy(step), "handle": (params, handle.shape, local)}
        return handle

    def has(self, id: str) -> bool:
        """Whether the plan declares instance `id` (an optional feature of the part)."""
        return id in self.instances

    def param(self, id: str, name: str) -> Any:
        try:
            return self.instances[id]["params"][name]
        except KeyError:
            raise _fail("step_plan", id, f"no param {name!r} on plan instance {id!r}") from None

    def positions(self, id: str) -> list[tuple]:
        """Planned positions of an instance: its interfaces' position_mm, in plan order."""
        return [
            tuple(i["position_mm"])
            for i in self.plan_part.get("interfaces", [])
            if i.get("instance") == id and "position_mm" in i
        ]

    def place(self, handle: Handle, at=None, rotate=(0, 0, 0), op: str = "union", into=None):
        if handle.shape is None:
            raise _fail("step_plan", handle.id, f"place before resize of {handle.id!r}")
        if at is not None and len(at) == 0:
            raise _fail("step_plan", handle.id, f"place of {handle.id!r} at an empty point list")
        points = [(0, 0, 0)] if at is None else [at] if not isinstance(at[0], (list, tuple)) else at
        step = self._record("place", handle.name, id=handle.id, op=op, at=[list(p) for p in points])
        args = {"id": handle.id, "at": points, "rotate": rotate, "op": op, "into": into}
        key = self._chain("place", args, handle.entry["module"])
        hit = self._cached(key, step)
        if hit is not None:
            self._restore(hit["state"])
            self.last_good = hit["state"]
            return handle
        tools = [_moved(handle.shape, p, rotate) for p in points]
        self.placements.append((handle, points, rotate, into))
        tool = tools[0] if len(tools) == 1 else cq.Compound.makeCompound(tools)

        target = into if into is not None else "__body__"
        before = self.unions.get(target) if into is not None else self.body
        if op == "base":
            after = tools[0].fuse(*tools[1:]).clean() if len(tools) > 1 else tool
        elif before is None:
            raise self._error(step, "step_plan", f"{op} into {target!r} before any base place")
        elif op == "union":
            after = before.fuse(tool).clean()
        elif op == "cut":
            after = before.cut(tool).clean()
        else:
            raise self._error(step, "step_plan", f"op must be base, union or cut, not {op!r}")

        dv = after.Volume() - (before.Volume() if before is not None and op != "base" else 0)
        step["volume"], step["delta"] = round(after.Volume(), 3), round(dv, 3)
        if into is not None:
            self.unions[into] = after
        else:
            self.body = after
        self.placed = True

        retired = self.registry.retire_inside(tool, step["index"]) if op != "base" else []
        local = [q for q in handle.probes if q.kind in ("solid_at", "empty_at", "ray")]
        if op == "cut":
            # A cut tool's material is removed; its holes and rays say nothing about the host.
            local = [replace(q, kind="empty_at") for q in local if q.kind == "solid_at"]
        for p in points:
            self.registry.add([pr.transform(q, p, rotate) for q in local], step["index"])
        whole = self._whole()
        solids = [len(b.Solids()) for b in self._bodies()]
        self.armed.add(handle.id)
        checked, failed = self.registry.check(whole, armed=self.armed)
        step["solids"] = solids[0] if len(solids) == 1 else solids
        gone = [pr.as_dict(r) for r in retired]
        step["probes"] = {"checked": checked, "failed": failed, "retired": gone}

        if op == "union" and dv <= _VOLUME_EPS_MM3:
            raise self._error(step, "probe_failed", f"union added no volume ({dv:.3f} mm^3)")
        if op == "cut" and dv >= -_VOLUME_EPS_MM3:
            raise self._error(step, "probe_failed", f"cut removed no volume ({dv:.3f} mm^3)")
        if any(n != 1 for n in solids):
            raise self._error(step, "probe_failed", f"body is {step['solids']} solids, expected 1")
        if failed:
            raise self._error(step, "probe_failed", f"{len(failed)} probe(s) failed: {failed}")
        self.last_good = self._state()
        if Part.cache is not None:
            Part.cache[key] = {"step": copy.deepcopy(step), "state": self.last_good}
        return handle

    def _bodies(self) -> list:
        return list(self.unions.values()) + ([self.body] if self.body is not None else [])

    def _whole(self):
        bodies = self._bodies()
        return bodies[0] if len(bodies) == 1 else cq.Compound.makeCompound(bodies)

    def result(self):
        """The finished body (a Workplane, or dict of unions), with the final envelope check."""
        step = self._record("result", self.id)
        if not self.placed:
            raise self._error(step, "step_plan", "result() before any place")
        checked, failed = self.registry.check(self._whole(), final=True)
        step["probes"] = {"checked": checked, "failed": failed, "retired": []}
        if failed:
            raise self._error(step, "probe_failed", f"{len(failed)} probe(s) failed: {failed}")
        rotate = os.environ.get("CQ_PRINT_ROTATE")
        if rotate:
            self._finish(json.loads(rotate), step)
        if self.unions:
            out = {k: cq.Workplane("XY").newObject([v]) for k, v in self.unions.items()}
            if self.body is not None:
                out[self.id] = cq.Workplane("XY").newObject([self.body])
            return out
        return cq.Workplane("XY").newObject([self.body])

    def _edge_jobs(self) -> list[tuple]:
        """(target, label, size, placed curves) for every plan-declared edge set."""
        jobs = []
        for handle, points, rotate, into in self.placements:
            edges = self.instances[handle.id].get("edges") or {}
            if not edges:
                continue
            module = importlib.import_module(handle.entry["module"])
            sets = getattr(module, f"{handle.entry['function']}_edge_sets")(**handle.params)
            for name, size in edges.items():
                curves = [_moved(c, p, rotate) for c in sets[name] for p in points]
                jobs.append((into or "__body__", f"{handle.id}.{name}", size, curves))
        return jobs

    def _finish(self, steps: list, step: dict) -> None:
        """Print-pose finishing: chamfer horizontal / fillet other edges of each plan edge
        set, then re-check plan probes. Failures are finishing_probe_failed (ask_user)."""
        jobs = self._edge_jobs()
        bodies: dict[str, Any] = dict(self.unions)
        if self.body is not None:
            bodies["__body__"] = self.body
        lost = [
            label
            for into, label, _s, curves in jobs
            if not any(_on_curves(e, curves) for e in bodies[into].Edges())
        ]
        if lost:
            raise self._error(
                step, "finishing_probe_failed", f"edge set(s) {lost} map to no edge of the body"
            )
        treated = []
        for fillet in (True, False):
            for into, label, size, curves in jobs:
                body = bodies[into]
                edges = [
                    e
                    for e in body.Edges()
                    if _on_curves(e, curves) and _is_horizontal(e, steps) != fillet
                ]
                if not edges:
                    continue
                try:
                    body = body.fillet(size, edges) if fillet else body.chamfer(size, None, edges)
                except Exception as exc:
                    raise self._error(
                        step,
                        "finishing_probe_failed",
                        f"{label}: {size} mm treatment failed: {exc}",
                    ) from exc
                bodies[into] = body.clean()
                treated += [(e, size) for e in edges]
        if not treated:
            return
        zone = [
            p
            for p in self.registry.probes
            if p.owner != "plan"
            and p.p is not None
            and any(cq.Vertex.makeVertex(*p.p).distance(e) <= 1.5 * s for e, s in treated)
        ]
        self.registry.probes = [p for p in self.registry.probes if p not in zone]
        self.registry.retired.extend(zone)
        self.body = bodies.pop("__body__", None)
        self.unions.update(bodies)
        checked, failed = self.registry.check(self._whole(), final=True)
        step["finishing"] = {
            "treated_edges": len(treated),
            "checked": checked,
            "retired": [pr.as_dict(p) for p in zone],
        }
        if failed:
            raise self._error(
                step, "finishing_probe_failed", f"edge treatment broke probe(s): {failed}"
            )
