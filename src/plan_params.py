"""Resolve BUILD_PLAN.json instance params that are expressions over parameters.py constants.

A string param such as "BASKET_RIM_OD_MM + GROOVE_CLEARANCE_MM" is evaluated with
numeric literals, constants from the project's parameters.py, + - * / //, unary minus,
parentheses and min/max/round. Anything else is rejected; nothing is ever exec'd.
"""

import ast
import contextlib
import copy
import hashlib
import json
import operator
from collections.abc import Callable
from pathlib import Path
from typing import Any

_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
}
_FUNCS: dict[str, Callable[..., float]] = {"min": min, "max": max, "round": round}


class PlanParamError(ValueError):
    """An expression param is malformed or names an unknown constant."""


def _num(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _eval(node: ast.AST, consts: dict[str, float]) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and _num(node.value):
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in consts:
            raise PlanParamError(f"unknown name {node.id!r}")
        return consts[node.id]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        v = _eval(node.operand, consts)
        return -v if isinstance(node.op, ast.USub) else v
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        return _BINOPS[type(node.op)](_eval(node.left, consts), _eval(node.right, consts))
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in _FUNCS
        and not node.keywords
    ):
        return _FUNCS[node.func.id](*[_eval(a, consts) for a in node.args])
    raise PlanParamError(f"unsupported syntax {type(node).__name__}")


def evaluate(expr: str, consts: dict[str, float]) -> float:
    """Evaluate one whitelisted expression against `consts`."""
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise PlanParamError(f"cannot parse {expr!r}: {exc.msg}") from None
    try:
        return _eval(tree.body, consts)
    except ZeroDivisionError:
        raise PlanParamError(f"division by zero in {expr!r}") from None


def load_constants(path: Path) -> dict[str, float]:
    """Numeric module-level constants of parameters.py, read without importing it."""
    consts: dict[str, float] = {}
    if not path.is_file():
        return consts
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                # not a plain numeric constant (string, tuple, ...) -> skipped
                with contextlib.suppress(PlanParamError):
                    consts[target.id] = _eval(node.value, consts)
    return consts


def _is_enum_word(value: str, consts: dict[str, float]) -> bool:
    """A bare lowercase word such as "auto" is an enum value, not an expression; constants
    are UPPER_CASE, so a lowercase identifier that is not a known constant stays a string."""
    return value.isidentifier() and value not in consts and value != value.upper()


def resolve_plan(plan: dict, consts: dict[str, float]) -> tuple[dict, list[str]]:
    """Copy of `plan` with every string instance param evaluated; plus error strings."""
    out = copy.deepcopy(plan)
    errors: list[str] = []
    for part in out.get("parts", []):
        for block in part.get("blocks_needed", []):
            if not isinstance(block, dict):
                continue
            for name, value in (block.get("params") or {}).items():
                if isinstance(value, str) and not _is_enum_word(value, consts):
                    try:
                        block["params"][name] = evaluate(value, consts)
                    except PlanParamError as exc:
                        errors.append(
                            f"Part '{part.get('id')}' instance '{block.get('id')}' param "
                            f"'{name}': {exc}"
                        )
    return out, errors


def resolved_hashes(resolved_plan: dict) -> dict[str, str]:
    """Part id -> hash of its resolved instance params, for change detection."""
    hashes = {}
    for part in resolved_plan.get("parts", []):
        params = {
            b.get("id", str(i)): b.get("params")
            for i, b in enumerate(part.get("blocks_needed", []))
            if isinstance(b, dict)
        }
        blob = json.dumps(params, sort_keys=True, default=str)
        hashes[part.get("id")] = hashlib.sha256(blob.encode()).hexdigest()[:16]
    return hashes


def changed_parts(old: dict[str, str] | None, new: dict[str, str]) -> list[str]:
    """Parts whose hash differs from `old`; an absent `old` reports nothing."""
    if not old:
        return []
    return sorted(pid for pid, h in new.items() if old.get(pid) != h)
