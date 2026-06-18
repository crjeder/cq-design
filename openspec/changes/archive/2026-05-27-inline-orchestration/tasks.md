## 1. Delete orchestrator files

- [x] 1.1 Delete `src/orchestrate.py`
- [x] 1.2 Delete `tests/test_orchestrate.py`

## 2. Update SKILL.md

- [x] 2.1 Remove the "run orchestrate.py" instruction from phase 3 and replace with the inline part-loop algorithm (read plan, render prompt, Write script, Bash validator, parse JSON, retry up to 3x, conversational failure handling)
- [x] 2.2 Update phase 3 to instruct Claude to write block import statements directly (from `blocks import <function>`) based on `blocks_needed` in the plan -- no post-processing injection
- [x] 2.3 Remove the generated-script rule "Do not write import statements for block functions" (it was written for the injector model)
- [x] 2.4 Update phase 3 to describe assembly phase inline (Claude writes assembly.py, runs validator, checks result)
- [x] 2.5 Update phase 3 to describe quality gate inline (Claude runs quality_gate.py via Bash, reads JSON, reports)
- [x] 2.6 Remove any references to orchestrate.py from the quick-reference file table at the bottom of SKILL.md
- [x] 2.7 Verify the `/plan` command section still correctly scopes to phases 1-2 only (no orchestrator reference)

## 3. Archive obsolete specs

- [x] 3.1 Archive `openspec/specs/orchestration-loop/` (delete or move to archive)
- [x] 3.2 Archive `openspec/specs/robust-claude-subprocess/` (delete or move to archive)

## 4. Verify

- [x] 4.1 Run remaining tests: `uv run pytest tests/` -- confirm only test_orchestrate.py tests are gone, everything else passes
- [x] 4.2 Do a smoke run: invoke `/cq-design` for a simple single-part request and confirm Claude executes the loop inline (writes script, runs validator, reports result) without referencing orchestrate.py
