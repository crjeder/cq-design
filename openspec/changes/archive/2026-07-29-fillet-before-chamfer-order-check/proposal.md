## Why

`reference/CadQuery Anti-Patterns.md` warns that a fillet/chamfer can fail or
silently distort geometry when it operates on edges whose topology was already
changed by an earlier fillet/chamfer in the same chain -- `script_lint.py`
already catches one instance of this (`shell_after_fillet`: shelling after
filleting). Mixing `.chamfer(...)` and `.fillet(...)` in the same chain has the
same failure shape and is currently uncaught: a `.fillet(...)` that runs after
a `.chamfer(...)` operates on edges the chamfer already split into two, which
is more prone to BRep failures and inconsistent results than filleting first
and chamfering the (still-simple) result afterward. `TODO.md` tracked this
question and was prematurely marked resolved by a different, already-shipped
rule (`edge_treatment_check.py`'s horizontal-edge=chamfer / vertical-edge=fillet
classification, which governs *which* treatment an edge gets, not the *order*
of calls) -- this change adds the order check that was actually missing.

## What Changes

- Add a new `script_lint.py` finding, `fillet_after_chamfer`: within a single
  fluent chain, a `.fillet(...)` call that follows an earlier `.chamfer(...)`
  call is flagged (mirrors the existing `shell_after_fillet` detector's
  same-chain, call-order approach).
- Wire the new finding into the documented finding catalog (`script-lint`
  spec) and into `skill/phase3_build.md`'s Step 2.5 description.
- Add unit tests in `tests/test_script_lint.py` covering the new finding
  (violation, clean order, and chains with only one of the two calls).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `script-lint`: adds `fillet_after_chamfer` to the anti-pattern finding
  catalog (`Requirement: Anti-pattern finding catalog`).

## Impact

- `src/script_lint.py`: new `_find_fillet_after_chamfer` check, wired into
  `lint_script`.
- `tests/test_script_lint.py`: new test cases.
- `skill/phase3_build.md`: Step 2.5 finding list gains the new type.
- `TODO.md`: un-mark the premature `[x]` and record the real resolution once
  this change ships.
