# Tasks

## 1. Reconcile prompts/part.md
- [x] 1.1 Delete line 51 ("Block functions listed above are pre-imported by the runner ... do not write import statements for them.")
- [x] 1.2 Make line 11 concrete: import `cadquery as cq` and `from blocks import <function>` for each block in the Available blocks list.
- [x] 1.3 Confirm `{{BLOCK_SPECS}}` rendering (SKILL.md render table) needs no module/function field and leave it unchanged.

## 2. Converge SKILL.md on flat imports
- [x] 2.1 Step 2 "Write the part script" (~L422): change the example and instruction from `from blocks.primitives import fillet_box` to flat `from blocks import fillet_box`; drop "look up module and function from the inventory".
- [x] 2.2 Block-library reference line (~L827): change `from blocks.<module> import <function>` to `from blocks import <function>`.
- [x] 2.3 Generated-script rules (~L962): change `from blocks.<module> import <function>` to `from blocks import <function>`; drop the inventory module-lookup clause.

## 3. Rewrite the capability spec
- [x] 3.1 Replace `openspec/specs/block-import-injection/spec.md` content with the flat-import script contract (self-declared flat imports, no runner injection), matching the change's delta spec.

## 4. Guard test (optional but recommended)
- [x] 4.1 Add a test asserting every block name in `blocks/inventory.json` resolves via `from blocks import <name>`.
- [x] 4.2 Add a test asserting the shim performs no import injection (a script calling a block with no import fails with `NameError`).

## 5. Verify convergence
- [x] 5.1 Grep `reference/` and `prompts/planning.md` for any remaining `from blocks.<module>` or "pre-imported" guidance; reconcile any hit to flat.
- [x] 5.2 Grep the repo for `from blocks.` in prose/prompts to confirm only source code (`__init__.py`, tests) uses submodule paths.
- [x] 5.3 Run `uv run pytest tests/` to confirm the suite stays green.
- [x] 5.4 Run `openspec validate flat-block-imports`.
