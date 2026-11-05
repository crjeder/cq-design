#!/usr/bin/env python3
"""Group commands over a script: the only way an LLM changes a part or edit script.

A script splits into a header, ordered groups and a tail:
- step part script (builds through ``Part``): one group per plan instance, from its
  ``select(..., id=X)`` up to the next ``select`` or the tail (``result = ...``);
- a script with ``# step: <name>`` lines: one group per marked section, no tail;
- anything else: one group, ``whole``.

Usage:
    python3 script_ops.py list    build/plate.py
    python3 script_ops.py show    build/plate.py hole_v
    python3 script_ops.py new     build/plate.py (--template <file> | --code <file>) [--force]
    python3 script_ops.py replace build/plate.py hole_v --code build/plate.op.py
    python3 script_ops.py insert  build/plate.py (--after hole_v | --first) --code <file>
    python3 script_ops.py remove  build/plate.py hole_v
    python3 script_ops.py move    build/plate.py hole_v (--after arm_h | --first)

Every write is preflighted (parse, group identity, scope, def-before-use, planned
instance, lint for step scripts); a refused command leaves the file byte-identical.
Applied commands are recorded in script history. One JSON object out; exit 0 / 1.
"""

import argparse
import ast
import builtins
import hashlib
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import script_history

MARKER = re.compile(r"^# step: (\S+)\s*$")
PART_ID = re.compile(r'Part\("[^"]*"\)')
KNOWN = set(dir(builtins)) | {"__file__", "__name__", "__doc__"}


class OpError(Exception):
    def __init__(self, kind: str, message: str, hint: str):
        super().__init__(message)
        self.error = {"type": kind, "message": message, "hint": hint}


@dataclass
class Layout:
    kind: str  # step | marked | whole
    header: str = ""
    groups: list[tuple[str, str]] = field(default_factory=list)
    tail: str = ""

    def text(self) -> str:
        return self.header + "".join(t for _, t in self.groups) + self.tail

    def ids(self) -> list[str]:
        return [g for g, _ in self.groups]

    def get(self, gid: str) -> str:
        for g, t in self.groups:
            if g == gid:
                return t
        raise OpError("unknown_group", f"no group {gid!r}", f"groups: {self.ids()}")


def _opener(stmt: ast.stmt) -> str | None:
    """Instance id of the first `.select(..., id="X")` call in stmt."""
    for node in ast.walk(stmt):
        if isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "select":
            for kw in node.keywords:
                if kw.arg == "id" and isinstance(kw.value, ast.Constant):
                    return str(kw.value.value)
    return None


def _uses_part(tree: ast.Module) -> bool:
    return any(
        isinstance(n, ast.Call) and getattr(n.func, "id", None) == "Part" for n in ast.walk(tree)
    )


def _parse(text: str, where: str) -> ast.Module:
    try:
        return ast.parse(text)
    except SyntaxError as e:
        raise OpError(
            "parse_error", f"{where}: {e.msg} (line {e.lineno})", "fix the syntax"
        ) from None


def _is_result(stmt: ast.stmt) -> bool:
    return isinstance(stmt, ast.Assign) and any(
        isinstance(t, ast.Name) and t.id == "result" for t in stmt.targets
    )


def layout(text: str) -> Layout:
    """Split script text into header, groups and tail (their concatenation is text)."""
    tree = _parse(text, "script")
    lines = text.splitlines(keepends=True)
    if _uses_part(tree):
        return _step_layout(tree, lines)
    marks = [(i, m.group(1)) for i, line in enumerate(lines) if (m := MARKER.match(line))]
    if not marks:
        return Layout("whole", groups=[("whole", text)])
    out = Layout("marked", header="".join(lines[: marks[0][0]]))
    for k, (i, name) in enumerate(marks):
        end = marks[k + 1][0] if k + 1 < len(marks) else len(lines)
        out.groups.append((name, "".join(lines[i:end])))
    _no_duplicates(out)
    return out


def _step_layout(tree: ast.Module, lines: list[str]) -> Layout:
    body = tree.body
    openers = [i for i, s in enumerate(body) if _opener(s) is not None]
    tail_i = len(body)
    if body and _is_result(body[-1]) and (not openers or openers[-1] < len(body) - 1):
        tail_i = len(body) - 1
    if not openers:
        return Layout("step", header="".join(lines))
    out = Layout("step")
    cut = body[openers[0] - 1].end_lineno if openers[0] else 0
    out.header = "".join(lines[:cut])
    for k, start in enumerate(openers):
        stop = openers[k + 1] if k + 1 < len(openers) else tail_i
        end = body[stop - 1].end_lineno or cut
        out.groups.append((str(_opener(body[start])), "".join(lines[cut:end])))
        cut = end
    out.tail = "".join(lines[cut:])
    _no_duplicates(out)
    return out


def _no_duplicates(lay: Layout) -> None:
    ids = lay.ids()
    dup = sorted({g for g in ids if ids.count(g) > 1})
    if dup:
        raise OpError(
            "group_identity",
            f"groups {dup} appear more than once",
            "keep each instance's steps (or each `# step:` name) in one contiguous group",
        )


# --- fragments ---------------------------------------------------------------------


def _fragment(kind: str, code: str, gid: str | None) -> tuple[str, str]:
    """Validate replace/insert code as exactly one group; return (group id, text)."""
    code = code.strip("\n") + "\n"
    tree = _parse(code, "code")
    if kind == "step":
        ids = [o for s in tree.body if (o := _opener(s)) is not None]
        first = _opener(tree.body[0]) if tree.body else None
        if not ids or first is None or len(set(ids)) != 1:
            raise OpError(
                "group_identity",
                f"code must be one instance's steps starting at its select; selects: {ids}",
                "put exactly one instance's select/resize/place calls in the code file",
            )
        found = ids[0]
    elif kind == "marked":
        marks = [m.group(1) for line in code.splitlines() if (m := MARKER.match(line))]
        if len(marks) != 1 or not MARKER.match(code.splitlines()[0]):
            raise OpError(
                "group_identity",
                f"code must start with one `# step: <name>` line; found {marks}",
                "begin the code file with its `# step:` marker and add no other",
            )
        found = marks[0]
    else:
        found = "whole"
    if gid is not None and found != gid:
        raise OpError("group_identity", f"code is group {found!r}, not {gid!r}", "address it")
    return found, code


def _leading_blank(text: str) -> str:
    return text[: len(text) - len(text.lstrip("\n"))]


def _placed(kind: str, code: str, lead: str) -> str:
    if kind == "marked":
        return code + "\n"
    return lead + code


# --- preflight -----------------------------------------------------------------------


def _names(tree: ast.AST) -> tuple[set[str], set[str]]:
    stores: set[str] = set()
    loads: set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Name):
            (stores if isinstance(n.ctx, ast.Store) else loads).add(n.id)
        elif isinstance(n, ast.alias):
            stores.add((n.asname or n.name).split(".")[0])
        elif isinstance(n, (ast.FunctionDef, ast.ClassDef)):
            stores.add(n.name)
    return stores, loads


def _check_locals(lay: Layout) -> None:
    defined = set(KNOWN)
    regions = [("header", lay.header), *lay.groups, ("tail", lay.tail)]
    for gid, text in regions:
        stores, loads = _names(_parse(text, gid)) if text.strip() else (set(), set())
        missing = sorted(loads - stores - defined)
        if missing:
            raise OpError(
                "undefined_local",
                f"group {gid!r} reads {missing}, assigned in no earlier group",
                "compute the value inside the group, or keep the group that assigns it first",
            )
        defined |= stores


def _plan_instances(script: Path, header: str) -> set[str] | None:
    m = re.search(r'Part\("([^"]*)"', header)
    path = os.environ.get("CQ_PLAN")
    if not path:
        d = script.parent
        while not (d / "BUILD_PLAN.json").is_file() and d.parent != d:
            d = d.parent
        path = str(d / "BUILD_PLAN.json")
    try:
        plan = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    part = next((p for p in plan.get("parts", []) if m and p.get("id") == m.group(1)), None)
    if part is None:
        return None
    return {b["id"] for b in part.get("blocks_needed", []) if isinstance(b, dict) and "id" in b}


def _check_instances(script: Path, lay: Layout, gids: list[str]) -> None:
    planned = _plan_instances(script, lay.header)
    unknown = [g for g in gids if planned is not None and g not in planned]
    if unknown:
        raise OpError(
            "unknown_instance",
            f"{unknown} are not blocks_needed instances of this part",
            f"planned ids: {sorted(planned or [])}; add the instance to the plan first",
        )


def _lint(text: str) -> None:
    import script_lint

    fd, tmp = tempfile.mkstemp(suffix=".py")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        findings = script_lint.lint_script(tmp, step=True)
    finally:
        os.unlink(tmp)
    if findings:
        f0 = findings[0]
        raise OpError(f0.type, f"line {f0.line}: {f0.message}", f0.hint)


def preflight(script: Path, old: Layout, cand_text: str, target: str | None, order: list[str]):
    """Check the candidate; raise OpError on the first failure."""
    cand = layout(cand_text)
    if cand.kind != old.kind:
        raise OpError("scope_violation", f"script kind changed to {cand.kind}", "keep the form")
    outside = [g for g in old.ids() if g != target]
    if (
        cand.header != old.header
        or cand.tail != old.tail
        or cand.ids() != order
        or any(cand.get(g) != old.get(g) for g in outside if g in order)
    ):
        raise OpError(
            "scope_violation",
            f"the command changed more than group {target!r}",
            "trailing comments in a code file join the next group: end the code with a statement",
        )
    _check_locals(cand)
    if cand.kind == "step":
        if target is not None and target in order:
            _check_instances(script, cand, [target])
        _lint(cand_text)


# --- commands ------------------------------------------------------------------------


def _read(path: str, role: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError as e:
        raise OpError("file_error", f"cannot read {role} {path}: {e}", "check the path") from None


def _write(script: Path, text: str, command: str, group: str | None) -> str:
    tmp = script.with_suffix(".py.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, script)
    return script_history.record_command(script, command, group)


def run(args: argparse.Namespace) -> dict:
    script = Path(args.script).resolve()
    if args.cmd == "new":
        return _new(script, args)
    old = layout(_read(str(script), "script"))
    if args.cmd == "list":
        listing = [
            {"id": g, "lines": t.count("\n"), "hash": hashlib.sha256(t.encode()).hexdigest()[:12]}
            for g, t in old.groups
        ]
        return {"success": True, "kind": old.kind, "groups": listing}
    if args.cmd == "show":
        return {"success": True, "group": args.group, "source": old.get(args.group)}
    groups = list(old.groups)
    ids = old.ids()
    target: str = getattr(args, "group", None) or ""
    if args.cmd in ("replace", "remove", "move"):
        old.get(target)
    if args.cmd == "replace":
        gid, code = _fragment(old.kind, _read(args.code, "code file"), target)
        i = ids.index(gid)
        groups[i] = (gid, _placed(old.kind, code, _leading_blank(groups[i][1])))
    elif args.cmd == "insert":
        target, code = _fragment(old.kind, _read(args.code, "code file"), None)
        if target in ids:
            raise OpError("group_identity", f"group {target!r} exists", "use replace")
        if not args.first:
            old.get(args.after)
        at = 0 if args.first else ids.index(args.after) + 1
        groups.insert(at, (target, _placed(old.kind, code, "\n")))
    elif args.cmd == "remove":
        groups.pop(ids.index(target))
    else:  # move: the group's text, leading blank lines included, travels unchanged
        moved = groups.pop(ids.index(target))
        rest = [g for g, _ in groups]
        if not args.first and args.after not in rest:
            raise OpError("unknown_group", f"no group {args.after!r}", f"groups: {rest}")
        groups.insert(0 if args.first else rest.index(args.after) + 1, moved)
    cand = Layout(old.kind, old.header, groups, old.tail)
    preflight(script, old, cand.text(), target, cand.ids())
    src = _write(script, cand.text(), args.cmd, target)
    return {
        "success": True,
        "command": args.cmd,
        "group": target,
        "changed_groups": [target],
        "src": src,
    }


def _new(script: Path, args: argparse.Namespace) -> dict:
    if script.exists() and not args.force:
        raise OpError("file_exists", f"{script.name} exists", "edit it with replace/insert")
    text = _read(args.template or args.code, "template" if args.template else "code file")
    if args.template:
        text = PART_ID.sub(f'Part("{script.stem}")', text, count=1)
    lay = layout(text)
    _check_locals(lay)
    if lay.kind == "step":
        _check_instances(script, lay, lay.ids())
        _lint(text)
    src = _write(script, text, "new", None)
    return {
        "success": True,
        "command": "new",
        "group": None,
        "changed_groups": lay.ids(),
        "src": src,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("list", "show", "new", "replace", "insert", "remove", "move"):
        p = sub.add_parser(name)
        p.add_argument("script")
        if name in ("show", "replace", "remove", "move"):
            p.add_argument("group")
        if name in ("replace", "insert"):
            p.add_argument("--code", required=True)
        if name in ("insert", "move"):
            where = p.add_mutually_exclusive_group(required=True)
            where.add_argument("--after")
            where.add_argument("--first", action="store_true")
        if name == "new":
            src = p.add_mutually_exclusive_group(required=True)
            src.add_argument("--template")
            src.add_argument("--code")
            p.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)
    try:
        result = run(args)
        result.setdefault("errors", [])
    except OpError as e:
        result = {"success": False, "command": args.cmd, "errors": [e.error]}
    print(json.dumps(result, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
