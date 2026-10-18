## 1. Description rewrite

- [x] 1.1 Replace the SKILL.md frontmatter `description` with the 3D-context-only text from design.md
- [x] 1.2 Confirm no standalone "box", "holder", "stand", "case", "mount", "lid", "enclosure", "bracket", "design a part", "make a part for" remain in the quoted trigger list
- [x] 1.3 Confirm SKILL.md stays under 10 KB and the frontmatter still parses (name + description)

## 2. Verification

- [x] 2.1 Run `openspec validate skill-trigger-3d-context`
- [x] 2.2 Run `uv run pytest tests/test_prose_layer.py` (the only test that reads SKILL.md)
