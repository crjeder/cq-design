#!/usr/bin/env python3
"""AST-based static pre-flight lint for generated CadQuery part scripts.

Stdlib only (``ast`` + ``json``): no CadQuery import, runs in milliseconds, so the
part loop can catch mechanically-detectable anti-patterns before spending a full
CadQuery subprocess run. Findings share the wrapper's ``{type, message, hint}``
error shape (plus a ``line`` number) so the part loop's correction-prompt
machinery works unchanged.

A step script (one that builds through ``blocks.Part``, or any script under
``--step``) is held to the step form: no CadQuery calls (``raw_cadquery``) and no
dimensions in the script (``script_dimension``: a ``# PARAMETERS`` block or an argument
to ``resize``), since sizes are plan-owned.

Usage:
    python3 script_lint.py <script.py> [--step]

Exit codes: 0 no findings, 1 findings present.
"""

import argparse
import ast
import json
import sys
from dataclasses import asdict, dataclass

# Numeric literals exempt from the magic_number check even outside a named parameter.
_EXEMPT_NUMBERS = {0, 1, -1, 2, 90, 180, 360}

# Calls that permanently shift a workplane's origin, per cq_verify.check_workplane.
_SHIFT_ATTRS = {"center", "hole"}
# Calls that place a new feature relative to the current workplane origin.
_PLACEMENT_ATTRS = {
    "center",
    "hole",
    "moveTo",
    "rect",
    "circle",
    "polygon",
    "cboreHole",
    "cskHole",
    "slot2D",
}


# Workplane/Shape construction and modelling methods a step script must not call.
_CQ_METHODS = {
    "box",
    "rect",
    "extrude",
    "circle",
    "hole",
    "cboreHole",
    "cskHole",
    "polygon",
    "polyline",
    "close",
    "revolve",
    "sweep",
    "loft",
    "sphere",
    "cylinder",
    "workplane",
    "transformed",
    "moveTo",
    "lineTo",
    "threePointArc",
    "slot2D",
    "pushPoints",
    "eachpoint",
    "faces",
    "edges",
    "vertices",
    "fillet",
    "chamfer",
    "shell",
    "union",
    "cut",
    "intersect",
    "fuse",
    "translate",
    "rotate",
    "mirror",
    "twistExtrude",
    "makeBox",
    "makeCylinder",
    "makeCone",
    "makeSphere",
    "makeTorus",
    "split",
    "clean",
}
# Closest step primitive for a raw call, for the fix hint.
_PRIMITIVE_HINT = {
    "box": "box",
    "rect": "box",
    "makeBox": "box",
    "circle": "cylinder",
    "hole": "cylinder",
    "cylinder": "cylinder",
    "makeCylinder": "cylinder",
    "makeCone": "cone",
    "cskHole": "cone",
    "sphere": "sphere",
    "makeSphere": "sphere",
    "polyline": "prism",
    "polygon": "prism",
    "lineTo": "prism",
    "extrude": "box or prism",
    "revolve": "revolve",
    "makeTorus": "torus",
    "cboreHole": "counterbore_hole",
}
_PART_METHODS = {"select", "resize", "place", "param", "positions", "has", "result"}


@dataclass
class Finding:
    type: str
    message: str
    hint: str
    line: int

    def to_dict(self) -> dict:
        return asdict(self)


def _num_value(node: ast.AST) -> int | float | None:
    """Return the numeric value of a Constant or a negated Constant, else None."""
    if (
        isinstance(node, ast.Constant)
        and isinstance(node.value, (int, float))
        and not isinstance(node.value, bool)
    ):
        return node.value
    if (
        isinstance(node, ast.UnaryOp)
        and isinstance(node.op, ast.USub)
        and isinstance(node.operand, ast.Constant)
        and isinstance(node.operand.value, (int, float))
        and not isinstance(node.operand.value, bool)
    ):
        return -node.operand.value
    return None


def _chain_leftmost(node: ast.AST) -> ast.AST:
    """Walk down a fluent method-chain expression to its leftmost object."""
    while True:
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            node = node.func.value
        elif isinstance(node, ast.Attribute):
            node = node.value
        else:
            return node


def _flatten_chain(node: ast.AST) -> list[tuple[str, ast.Call]]:
    """Return [(attr, call_node), ...] for a fluent chain, first-called to last-called."""
    calls = []
    while isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        calls.append((node.func.attr, node))
        node = node.func.value
    calls.reverse()
    return calls


def _build_parent_map(tree: ast.AST) -> dict:
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[id(child)] = node
    return parents


def _is_chain_final(node: ast.Call, parents: dict) -> bool:
    """True if this call isn't consumed as the object of a further method call."""
    parent = parents.get(id(node))
    if not isinstance(parent, ast.Attribute):
        return True
    grandparent = parents.get(id(parent))
    return not (isinstance(grandparent, ast.Call) and grandparent.func is parent)


def _find_boolean_in_loop(tree: ast.AST) -> list[Finding]:
    findings = []

    def walk(node: ast.AST, depth: int) -> None:
        if isinstance(node, (ast.For, ast.While)):
            depth += 1
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"cut", "union", "intersect"}
            and depth > 0
        ):
            findings.append(
                Finding(
                    "boolean_in_loop",
                    f"`.{node.func.attr}(...)` called inside a loop",
                    "accumulate the boolean outside the loop; a boolean per "
                    "iteration is slow and prone to silent no-ops",
                    node.lineno,
                )
            )
        for child in ast.iter_child_nodes(node):
            walk(child, depth)

    walk(tree, 0)
    return findings


def _find_missing_result(tree: ast.Module) -> list[Finding]:
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name) and target.id == "result":
                    return []
        if (
            isinstance(stmt, ast.AnnAssign)
            and isinstance(stmt.target, ast.Name)
            and stmt.target.id == "result"
        ):
            return []
    return [
        Finding(
            "missing_result",
            "no top-level `result` assignment found",
            "assign the final Workplane (or dict of unions) to a top-level `result` variable",
            tree.body[-1].lineno if tree.body else 1,
        )
    ]


def _find_submodule_imports(tree: ast.AST) -> list[Finding]:
    findings = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("blocks."):
            findings.append(
                Finding(
                    "submodule_import",
                    f"`from {node.module} import ...` imports from a blocks submodule",
                    "import from `blocks` directly, e.g. `from blocks import fillet_box`",
                    node.lineno,
                )
            )
    return findings


def _find_direct_export(tree: ast.AST) -> list[Finding]:
    findings = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "export"
            and isinstance(node.func.value, ast.Attribute)
            and node.func.value.attr == "exporters"
            and isinstance(node.func.value.value, ast.Name)
            and node.func.value.value.id == "cq"
        ):
            findings.append(
                Finding(
                    "direct_export",
                    "direct `cq.exporters.export(...)` call",
                    "remove the export call; run_model_shim.py exports `result` automatically",
                    node.lineno,
                )
            )
    return findings


def _find_shell_after_fillet(tree: ast.AST, parents: dict) -> list[Finding]:
    findings = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "shell"
        ):
            chain = _flatten_chain(node)
            if any(attr == "fillet" for attr, _ in chain[:-1]):
                findings.append(
                    Finding(
                        "shell_after_fillet",
                        "`.shell(...)` called after `.fillet(...)` in the same chain",
                        "shell before filleting, or fillet only the shelled result; "
                        "shelling a filleted body often fails or produces bad geometry",
                        node.lineno,
                    )
                )
    return findings


def _find_fillet_after_chamfer(tree: ast.AST, parents: dict) -> list[Finding]:
    findings = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "fillet"
        ):
            chain = _flatten_chain(node)
            if any(attr == "chamfer" for attr, _ in chain[:-1]):
                findings.append(
                    Finding(
                        "fillet_after_chamfer",
                        "`.fillet(...)` called after `.chamfer(...)` in the same chain",
                        "apply fillets before chamfers in the chain; filleting "
                        "edges a chamfer already split into two is prone to "
                        "BREP_API failures or inconsistent results",
                        node.lineno,
                    )
                )
    return findings


def _find_unanchored_features(tree: ast.AST, parents: dict) -> list[Finding]:
    findings = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and _is_chain_final(node, parents)
        ):
            chain = _flatten_chain(node)
            pending_line = None
            for attr, call_node in chain:
                if attr == "workplane":
                    pending_line = None
                    continue
                if attr == "center" and all(_num_value(a) == 0 for a in call_node.args):
                    pending_line = None
                    continue
                if pending_line is not None and attr in _PLACEMENT_ATTRS:
                    findings.append(
                        Finding(
                            "unanchored_feature",
                            f"`.{attr}(...)` placed on a workplane shifted by an "
                            f"unresolved `.center()`/`.hole()` on line {pending_line}",
                            "re-anchor with `.workplane()` or `.center(0, 0)` before "
                            "placing the next feature, or guard with cq_verify.check_workplane",
                            call_node.lineno,
                        )
                    )
                if attr in _SHIFT_ATTRS:
                    pending_line = call_node.lineno
    return findings


_SIDE_FACES = {"<X", ">X", "<Y", ">Y", "|X", "|Y"}
_SIDE_PLANES = {"XZ", "YZ", "ZX", "ZY"}


def _find_horizontal_round_holes(tree: ast.AST) -> list[Finding]:
    """Advisory: round hole on a side-facing workplane without teardrop_bore in the script."""
    for n in ast.walk(tree):
        if (isinstance(n, ast.Name) and n.id == "teardrop_bore") or (
            isinstance(n, ast.ImportFrom) and any(a.name == "teardrop_bore" for a in n.names)
        ):
            return []
    findings = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        chain = _flatten_chain(node)
        if chain[-1][1] is not node or node.func.attr not in {"hole", "cboreHole", "cskHole"}:
            continue
        side = False
        for attr, call in chain:
            first = call.args[0] if call.args else None
            if (
                attr in {"faces", "workplane", "Workplane"}
                and isinstance(first, ast.Constant)
                and first.value in (_SIDE_FACES | _SIDE_PLANES)
            ):
                side = True
        if side:
            findings.append(
                Finding(
                    "horizontal_round_hole",
                    f"`.{node.func.attr}(...)` on a side-facing workplane; if this axis is "
                    "horizontal at the print pose the hole roof is an overhang",
                    "use blocks.teardrop_bore(..., print_up=print_up()) so the peak follows the "
                    "accepted print pose, or a plain hole if the axis prints vertical",
                    node.lineno,
                )
            )
    return findings


def _collect_computed_names(tree: ast.Module) -> set[str]:
    """Top-level names assigned an expression containing arithmetic (a computed offset)."""
    computed = set()
    for stmt in tree.body:
        if (
            isinstance(stmt, ast.Assign)
            and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Name)
        ):
            has_arith = any(isinstance(n, ast.BinOp) for n in ast.walk(stmt.value))
            if has_arith:
                computed.add(stmt.targets[0].id)
    return computed


def _find_unguarded_booleans(tree: ast.Module, parents: dict) -> list[Finding]:
    computed_names = _collect_computed_names(tree)
    findings = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"cut", "union"}
        ):
            continue
        if (
            not node.args
            or not isinstance(node.args[0], ast.Name)
            or node.args[0].id not in computed_names
        ):
            continue
        parent = parents.get(id(node))
        # Guarded when this call is a direct argument of a verify_boolean(...) call.
        is_guarded = isinstance(parent, ast.Call) and (
            (isinstance(parent.func, ast.Name) and parent.func.id == "verify_boolean")
            or (isinstance(parent.func, ast.Attribute) and parent.func.attr == "verify_boolean")
        )
        if not is_guarded:
            findings.append(
                Finding(
                    "unguarded_boolean",
                    f"`.{node.func.attr}({node.args[0].id})` uses a computed-offset "
                    "tool without a verify_boolean guard",
                    "wrap in `verify_boolean(before, after, op, label)` from cq_verify "
                    "to catch a silent no-op",
                    node.lineno,
                )
            )
    return findings


def _find_magic_numbers(tree: ast.Module) -> list[Finding]:
    workplane_vars: set[str] = set()
    for stmt in tree.body:
        if (
            isinstance(stmt, ast.Assign)
            and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Name)
        ):
            root = _chain_leftmost(stmt.value)
            if isinstance(root, ast.Name) and (root.id == "cq" or root.id in workplane_vars):
                workplane_vars.add(stmt.targets[0].id)

    findings = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        root = _chain_leftmost(node.func.value)
        if not (isinstance(root, ast.Name) and (root.id == "cq" or root.id in workplane_vars)):
            continue
        for arg in list(node.args) + [kw.value for kw in node.keywords]:
            for leaf in ast.walk(arg):
                if not isinstance(leaf, (ast.Constant, ast.UnaryOp)):
                    continue
                value = _num_value(leaf)
                if value is not None and value not in _EXEMPT_NUMBERS:
                    findings.append(
                        Finding(
                            "magic_number",
                            f"magic number {value!r} in `.{node.func.attr}(...)` call",
                            "move this value into the PARAMETERS section as a named variable",
                            leaf.lineno,
                        )
                    )
    return findings


def _raw_finding(name: str, line: int, method: str = "") -> Finding:
    prim = _PRIMITIVE_HINT.get(method or name)
    target = f"the `{prim}` primitive" if prim else "a primitive or block"
    return Finding(
        "raw_cadquery",
        f"`{name}` is raw CadQuery; a step script builds only through `Part` steps",
        f"select {target} with part.select/resize/place instead (add a plan instance for it)",
        line,
    )


def _find_step_violations(tree: ast.Module, source: str) -> list[Finding]:
    """Step-form rules: no CadQuery, no PARAMETERS block, no resize arguments."""
    findings = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(
            a.name.split(".")[0] == "cadquery" for a in node.names
        ):
            findings.append(_raw_finding("import cadquery", node.lineno))
        elif isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "cadquery":
            findings.append(_raw_finding(f"from {node.module} import", node.lineno))
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            attr = node.func.attr
            root = _chain_leftmost(node.func)
            if isinstance(root, ast.Name) and root.id in ("cq", "cadquery"):
                findings.append(_raw_finding(f"{root.id}.{attr}", node.lineno, attr))
            elif attr in _CQ_METHODS and attr not in _PART_METHODS:
                findings.append(_raw_finding(attr, node.lineno))
            elif attr == "resize" and (len(node.args) > 1 or node.keywords):
                findings.append(
                    Finding(
                        "script_dimension",
                        "`resize` takes only the handle; its values come from the plan",
                        "put the values in the instance's `params` in BUILD_PLAN.json",
                        node.lineno,
                    )
                )
    for i, text in enumerate(source.splitlines(), start=1):
        if text.strip().startswith("# PARAMETERS"):
            findings.append(
                Finding(
                    "script_dimension",
                    "a step script has no PARAMETERS block; dimensions are plan-owned",
                    "move each value into a blocks_needed instance's `params` in BUILD_PLAN.json",
                    i,
                )
            )
    # A raw call's chain repeats the same line; report each (type, line, message) once.
    unique = {(f.type, f.line, f.message): f for f in findings}
    return list(unique.values())


def _uses_part(tree: ast.Module) -> bool:
    return any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "Part"
        for n in ast.walk(tree)
    )


def lint_script(path: str, step: bool = False) -> list[Finding]:
    """Lint a part script, returning findings (empty if clean). No CadQuery import.
    Step-form rules apply when `step` is set or the script builds through `Part`."""
    with open(path, encoding="utf-8") as f:
        source = f.read()

    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as e:
        return [
            Finding(
                "syntax_error",
                str(e),
                "fix the Python syntax error before linting can continue",
                e.lineno or 1,
            )
        ]

    parents = _build_parent_map(tree)

    findings: list[Finding] = []
    findings += _find_boolean_in_loop(tree)
    findings += _find_missing_result(tree)
    findings += _find_submodule_imports(tree)
    findings += _find_direct_export(tree)
    findings += _find_shell_after_fillet(tree, parents)
    findings += _find_fillet_after_chamfer(tree, parents)
    findings += _find_unanchored_features(tree, parents)
    findings += _find_unguarded_booleans(tree, parents)
    findings += _find_horizontal_round_holes(tree)
    # A step script's sizes live in the plan, so magic_number's PARAMETERS advice is wrong.
    if step or _uses_part(tree):
        findings += _find_step_violations(tree, source)
    else:
        findings += _find_magic_numbers(tree)

    findings.sort(key=lambda f: f.line)
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("script", help="Path to the part script to lint")
    parser.add_argument(
        "--step", action="store_true", help="enforce the step form even without `Part`"
    )
    args = parser.parse_args()

    findings = lint_script(args.script, step=args.step)
    result = {"success": len(findings) == 0, "findings": [f.to_dict() for f in findings]}
    print(json.dumps(result, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
