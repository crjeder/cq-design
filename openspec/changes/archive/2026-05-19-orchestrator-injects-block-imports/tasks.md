## 1. Orchestrator

- [x] 1.1 Add `_prepend_block_imports(code, block_names, inventory)` helper to `orchestrate.py` that builds `from <module> import <function>` lines from inventory and prepends them to the code string
- [x] 1.2 Call `_prepend_block_imports` in the part build loop after `_extract_python(raw_code)`, before writing to `script_path`

## 2. Part Prompt

- [x] 2.1 Remove the `# from blocks import ...  (only if blocks are listed above)` comment from the script structure template in `prompts/part.md`
- [x] 2.2 Add explicit instruction near the Available blocks section: block functions are pre-imported by the runner - do not write import statements for them

## 3. Verification

- [x] 3.1 Run existing tests (`pytest tests/`) and confirm they pass
- [x] 3.2 Manually verify: generate a part with at least one block in `blocks_needed` and confirm the written script file starts with the correct import line(s) and runs without `NameError`
