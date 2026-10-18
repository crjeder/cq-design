## 1. Remove the duplicate

- [x] 1.1 In `skill/resume.md` replace the body of "Updating an existing project" (command block + `bundle_project.py` paragraph) with a one-line pointer to `/cq-design:update`; keep the journal paragraph
- [x] 1.2 Check `commands/update.md` mentions that part scripts are untouched and a `blocks` signature change may break `build.py`; add one sentence if missing

## 2. Verify

- [x] 2.1 `grep -rn "path-to-this-repo" SKILL.md skill/ commands/` returns nothing
- [x] 2.2 `uv run pytest tests/test_prose_layer.py` passes
