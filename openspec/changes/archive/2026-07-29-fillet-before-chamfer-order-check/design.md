## Context

`script_lint.py` is a pure-AST, stdlib-only static lint (no CadQuery import) run
by the part loop's Step 2.5 before the first `run_cadquery_model.py` call. It
already has one order-sensitive detector, `_find_shell_after_fillet`, which
walks a single fluent method-chain and flags `.shell(...)` if `.fillet(...)`
appears earlier in the *same chain*. Real generated part scripts apply both
treatments in one chain (`tests/test_edge_treatment_check.py` fixtures:
`.edges('|Z').fillet(2).edges('|X or |Y').chamfer(1)`), not via separate
top-level reassignment statements -- `blocks/connectors.py` and
`blocks/primitives.py` each use `.chamfer(...)`/`.fillet(...)` singly, never
both in one block, so there's no existing block-level convention to match
beyond the chain pattern already established by `shell_after_fillet`.

## Goals / Non-Goals

**Goals:**
- Catch a `.fillet(...)` operating on edges an earlier `.chamfer(...)` in the
  same chain already split, using the same detection shape as
  `shell_after_fillet` (same file, same AST helpers, same finding contract).

**Non-Goals:**
- Cross-statement / cross-variable tracking (e.g. `body = body.fillet(...)`
  on one line, `body = body.chamfer(...)` on the next). No real part script in
  this repo's fixtures/blocks uses that shape for this pair of calls; adding
  data-flow tracking for a case with zero observed instances is
  over-engineering for a stdlib AST lint.
- Re-litigating the *type* rule (horizontal edge -> chamfer, vertical edge ->
  fillet) -- that's `edge_treatment_check.py`, already shipped, unaffected by
  this change.
- Making the finding advisory/non-blocking. `script-lint`'s existing contract
  treats every finding as blocking (Step 2.5 requires all findings fixed
  before the first CadQuery run); this finding follows the same severity as
  its siblings, including `shell_after_fillet`.

## Decisions

**Direction of the rule: fillet before chamfer, not the reverse.**
A chamfer replaces one edge with two new edges (the chamfer face's top and
bottom boundaries); a later fillet targeting "the same" edge by selector is
now rounding an edge that didn't exist when the script's author reasoned about
it, and is more likely to select the wrong edge, fail (`BREP_API command not
done`, per the Anti-Patterns doc's fillet/chamfer failure section), or produce
a visually inconsistent transition. Filleting first, then chamfering the
still-simple result, avoids this. Finding type name follows the existing
`shell_after_fillet` convention (`<later-call>_after_<earlier-call>`, naming
the call that's out of place): `fillet_after_chamfer`.

**Detection scope: same fluent chain only, via `_flatten_chain`.**
Reuses the exact mechanism `_find_shell_after_fillet` already uses
(`_flatten_chain` walks a chain to `[(attr, call_node), ...]` in call order).
No new AST-walking helper needed.

## Risks / Trade-offs

- [Risk] Same-chain-only detection misses the cross-statement case (fillet and
  chamfer applied to the same body across separate reassignments) →
  Mitigation: no observed case in this repo needs it (see Non-Goals); if the
  eval corpus or a real session later produces one, extend then rather than
  speculatively now.
- [Risk] A script may legitimately need chamfer-then-fillet on edges that
  don't interact (e.g. two disjoint edge groups selected separately) →
  Mitigation: same trade-off `shell_after_fillet` already accepts (it can't
  tell disjoint edge groups apart either); the finding is blocking but the fix
  is trivial (reorder the two calls, or split into two chains against
  `.edges(...)` groups the way the Anti-Patterns doc already recommends for
  the "fillet smaller edges first" case).
