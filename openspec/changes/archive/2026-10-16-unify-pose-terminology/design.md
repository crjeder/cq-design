## Context

`CLAUDE.md` ("Three poses") defines build pose, assembly pose and print pose. Everything else drifted:

| Concept | Retired spellings found |
|---|---|
| build pose | "part frame" (SKILL.md, prompts), "authored frame" (src, TODO, README), "build frame" (CLAUDE.md-sense, `skill/phase3_build.md`) |
| assembly pose | "assembled frame" / "assembled-frame" (SKILL.md, prompts, schema, src), "assembled-pose" (already close) |
| print pose | "print frame" (SKILL.md, prompts, `edge_treatment_check.py`, `quality_gate.py`), "build frame" in the print sense (`edge_treatment_check.py`, `quality_gate.py`, `fem_check.py`) |

"build frame" is the hazard: it means the authored frame in some files and the print-oriented frame in others, so it cannot be bulk-replaced.

## Goals / Non-Goals

**Goals:**
- One vocabulary (build / assembly / print pose) in every doc, prompt, schema `description`, docstring, comment, CLI help and user-facing message.
- A grep-able invariant: the retired phrases no longer appear outside history files.

**Non-Goals:**
- Renaming identifiers, JSON keys, CLI flags, typed errors or files (`src/blocks/print_frame.py`, `print_up()`, `coordinate_frame`).
- Any behavior change.
- Rewriting archived changes, `documentation/DONE.md`, or `TODO.md` history entries.

## Decisions

1. **Pose wording wins; no aliases.** `CLAUDE.md` is already the maintainers' reference and the user chose it. Prompts follow it so builders and maintainers read one vocabulary.
2. **Disambiguate "build frame" by hand, per site.** Do the unambiguous phrases (`part frame`, `authored frame`, `assembled frame`, `print frame`) as a scripted replace with a reviewed diff; resolve every `build frame` / `build-frame` hit manually: authored sense -> "build pose", print-oriented sense -> "print pose". Known print-sense sites: `edge_treatment_check.py` (classification is bed-relative), `quality_gate.py` 748/810 (orientation-posed), `fem_check.py` 370/383 (candidate orientation), `TODO.md` C5 entry stays as history.
3. **Grammar follows the noun.** "in the part frame" -> "in build pose"; "the assembled frame" -> "assembly pose"; "print-frame" adjectives -> "print-pose". Compound identifiers stay (`print_frame.py`), but its docstring uses the new words.
4. **Do not touch `coordinate_frame`.** It is the compass-to-axis binding (spec `coordinate-frame`), a different concept; its spec wording keeps "frame" in that name.
5. **Single definition point.** `CLAUDE.md`'s "Three poses" bullet stays the definition; `SKILL.md:52-55` is rewritten to the same three terms, so no third restatement is added elsewhere.
6. **Tests assert strings, so run them.** Grep tests for the old phrases before editing source messages; update expectations in the same commit.
7. **Guard.** A small test (`tests/test_pose_terminology.py`, no CadQuery) scans the tracked doc/prompt/src/spec files for the retired phrases, excluding `openspec/changes/archive/`, `documentation/DONE.md`, `TODO.md`, and its own file. It keeps the vocabulary from drifting back.

## Risks / Trade-offs

- **Prompt text changes**: schema descriptions and `inventory.json` are rendered into builder prompts; a wording-only change could shift builder behavior marginally. Accepted: the intent is the shared vocabulary.
- **Wrong sense of "build frame"**: a mechanical replace would silently mislabel the print-sense hits. Mitigated by decision 2.
- **Guard test false positives**: ordinary phrases such as "part frame" in unrelated prose are unlikely in this repo; the exclusion list is explicit and short.
- **Spec churn**: ~20 specs change wording only; the guard test and `openspec validate --all` confirm they still parse.
