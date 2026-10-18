## Context

Skill dispatch matches user requests against the SKILL.md frontmatter `description`
only (see the existing skill-doc-structure requirement "SKILL.md body does not
restate frontmatter-owned trigger content"). The current description enumerates
bare part nouns that are common English words outside 3D printing.

## Goals / Non-Goals

**Goals:**
- Every trigger phrase carries 3D-printing / CAD context.
- Keep the description a single line, roughly the same length.

**Non-Goals:**
- Changing `plugin.json` / `marketplace.json` descriptions (they already say "3D-printable").
- Command descriptions under `commands/` (invoked explicitly, not by NL match).
- A trigger-precision eval harness.

## Decisions

- **Qualify, don't just delete, part nouns.** Proposed text:
  `Design or redesign 3D-printable parts as parametric CadQuery models. Use when the user asks to design, model, fix printability of, or generate an STL for a 3D-printed part -- mentions like "3D print", "3D-printable", "STL", "CadQuery", "gridfinity", "print me a", "printable enclosure/bracket/mount/case/holder/box/lid/stand", "design a part to print", "redesign for printability".`
  Alternative: drop the nouns entirely. Rejected because "printable bracket" style phrases are real high-signal requests; the qualifier removes the false-positive surface while keeping them.
- **Also qualify "enclosure", "bracket", "design a part", "make a part for".** Not in the original report but same failure mode ("design a part for the play").

## Risks / Trade-offs

- [Lower recall on context-free requests like "design me a wall mount"] -> The model still sees "design/model ... part" intent plus CadQuery in the description; users can invoke `/cq-design:design` explicitly.
