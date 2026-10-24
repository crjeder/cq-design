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

import importlib
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
        self.body = None
        self.unions: dict[str, Any] = {}
        self.steps: list[dict] = []
        self.registry = pr.Registry()
        seeded, self.unprobed_interfaces = pr.plan_probes(part)
        self.registry.add(seeded, "plan")
        self.placed = False

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
        return handle

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
        tools = []
        for p in points:
            s = handle.shape
            for axis, angle in zip(((1, 0, 0), (0, 1, 0), (0, 0, 1)), rotate, strict=True):
                if angle:
                    s = s.rotate((0, 0, 0), axis, angle)
            tools.append(s.translate(cq.Vector(*p)))
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
        checked, failed = self.registry.check(whole)
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
        if self.unions:
            out = {k: cq.Workplane("XY").newObject([v]) for k, v in self.unions.items()}
            if self.body is not None:
                out[self.id] = cq.Workplane("XY").newObject([self.body])
            return out
        return cq.Workplane("XY").newObject([self.body])
