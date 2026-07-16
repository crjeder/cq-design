## Context

Generated part scripts are only checked by running them: `run_cadquery_model.py`
spawns a CadQuery subprocess (seconds per run), and only then do typed errors come
back. A class of mistakes is fully visible in the source text before any run -
booleans in a loop, a missing `result`, submodule block imports, direct exporter
calls. Each one currently costs a run plus a retry round. Improvement plan item 7
calls for an AST-based pre-flight lint that catches these in milliseconds.

## Goals / Non-Goals

**Goals:**
- Catch mechanically checkable anti-patterns before the first CadQuery run.
- Zero heavyweight imports: stdlib `ast` + `json` only, so lint runs even where
  CadQuery is not installed and never adds measurable latency.
- Findings in the same `{type, message, hint}` shape as wrapper errors, so the part
  loop's correction-prompt machinery works unchanged.
- Fast tests (no CadQuery), in the same class as `test_plan_validate.py`.

**Non-Goals:**
- No geometry reasoning (thin walls, overhangs, silent booleans at runtime): those
  stay with the wrapper, `cq_verify`, and the quality gate.
- No auto-fixing; lint reports, the part loop fixes.
- No linting of hand-written project sources (`src/`); scope is generated part
  scripts only.
- Not a replacement for `plan_validate.py` (plan-level) or ruff (style-level).

## Decisions

1. **Standalone module + CLI, not a wrapper stage.** `script_lint.py` is invoked by
   the part loop before `run_cadquery_model.py`, not inside it. Rationale: the whole
   value is skipping the subprocess spin-up when lint fails; embedding it in the
   wrapper would still pay that cost. The wrapper stays untouched, preserving its
   frozen JSON contract. Alternative considered: a `--lint-only` wrapper flag -
   rejected because it couples lint to the wrapper's CadQuery environment.

2. **Pure `ast` visitor over regexes.** Every listed anti-pattern is structural
   (call inside `For`/`While`, import-from targets, attribute chains). A
   `NodeVisitor` gets these exactly; regexes would false-positive on comments and
   strings. Line numbers come free from AST nodes.

3. **Finding contract mirrors the wrapper's `errors` entries.** Each finding is
   `{type, message, hint, line}` with lint-specific `type` values
   (`boolean_in_loop`, `missing_result`, `submodule_import`, `direct_export`,
   `magic_number`, `unanchored_feature`, `unguarded_boolean`, `shell_after_fillet`).
   Output JSON is `{"success": bool, "findings": [...]}`. Rationale: Claude already
   parses this shape inline; a second format would need new prompt plumbing.

4. **Severity: all findings block the first run, none block delivery.** The
   SKILL.md step says "fix findings before the first run". Two checks are heuristic
   (`magic_number`, `unguarded_boolean`) and get conservative rules (see below) so
   the blocking default stays justified; if telemetry (item 8) shows false-positive
   churn, individual types can be demoted to advisory later.

5. **Heuristic checks are scoped narrowly to avoid false positives.**
   - `magic_number`: only numeric literals inside `cq.Workplane` call chains
     (`.box(20, 10, 2)`), outside the PARAMETERS block region (delimited by the
     conventional `# --- PARAMETERS ---` comment or top-level UPPER_CASE
     assignments). Literals 0, 1, -1, 2, 90, 180, 360 are exempt.
   - `unanchored_feature`: flag a `.center(...)` or `.hole(...)` call followed in
     the same fluent chain by another placement call without an intervening
     `.workplane()`/`.center(0, 0)` re-anchor, per the workplane-drift pattern
     `cq_verify.check_workplane` catches at runtime.
   - `unguarded_boolean`: a `.cut(x)`/`.union(x)` whose argument is a Name bound to
     an expression containing arithmetic on parameters (a computed offset) and that
     is not wrapped in `verify_boolean(...)`.

6. **Step 2.5 in SKILL.md, not a new phase.** Lint is one bullet in the existing
   part loop: run lint, fix findings, then proceed to the wrapper. The exit code (0
   clean / 1 findings) lets the loop branch without parsing when it only needs
   pass/fail.

## Risks / Trade-offs

- [False positives on unusual-but-valid scripts] → Narrow heuristics (Decision 5),
  exempt-list for common literals, and advisory demotion path per finding type;
  telemetry from `build/attempts.jsonl` will show if a type blocks good scripts.
- [Lint drift vs. actual failure modes] → Finding catalog is data-informed: item 8's
  telemetry records error types per attempt, so new lint rules are added only for
  patterns that recur at runtime.
- [Duplicate reporting with runtime checks] → Accepted: `unguarded_boolean` overlaps
  `verify_boolean` and `unanchored_feature` overlaps `check_workplane`. The lint
  variant fires earlier and cheaper; the runtime variant remains authoritative.
- [AST cannot see string-built code or exec] → Out of scope; generated scripts are
  plain fluent CadQuery, and anything else already violates the part-prompt rules.

## Migration Plan

Purely additive: new module, new test file, one new SKILL.md step. No rollback
concerns beyond deleting the step; no schema or contract changes.

## Open Questions

- Exact PARAMETERS-block convention to key `magic_number` on: the delimiter comment,
  top-level UPPER_CASE names, or both. Resolve during implementation against the
  scripts `prompts/part.md` actually produces (both is the safe default).
