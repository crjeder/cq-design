#!/usr/bin/env python3
"""AST-based static pre-flight lint for generated CadQuery part scripts.

Stdlib only (``ast`` + ``json``): no CadQuery import, runs in milliseconds, so the
part loop can catch mechanically-detectable anti-patterns before spending a full
CadQuery subprocess run. Findings share the wrapper's ``{type, message, hint}``
error shape (plus a ``line`` number) so the part loop's correction-prompt
machinery works unchanged.

Usage:
    python3 script_lint.py <script.py>

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


def lint_script(path: str) -> list[Finding]:
    """Lint a part script, returning findings (empty if clean). No CadQuery import."""
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
    findings += _find_magic_numbers(tree)
    findings += _find_unanchored_features(tree, parents)
    findings += _find_unguarded_booleans(tree, parents)

    findings.sort(key=lambda f: f.line)
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("script", help="Path to the part script to lint")
    args = parser.parse_args()

    findings = lint_script(args.script)
    result = {"success": len(findings) == 0, "findings": [f.to_dict() for f in findings]}
    print(json.dumps(result, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
