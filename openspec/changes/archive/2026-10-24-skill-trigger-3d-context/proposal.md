## Why

The `cq-design` frontmatter `description` (SKILL.md:3) lists bare nouns -- "box", "holder", "stand", "case", "mount", "lid" (plus "enclosure", "bracket", "design a part", "make a part for") -- as trigger phrases. None of them carries 3D-printing context, so unrelated requests like "mount the drive", "the lid of a CSS box", or "make a part for the choir" can match and load the skill.

## What Changes

- Rewrite the SKILL.md frontmatter `description` so it leads with "3D-printable part" and every trigger phrase carries 3D-printing / CAD context ("3D print", "3D-printable", "STL", "CadQuery", "gridfinity", "print me a", "redesign for printability").
- Drop the bare generic nouns. Part-category nouns survive only qualified by print context (e.g. "printable box", "3D-printed mount"), never standalone.
- Qualify the generic verb phrases "design a part" / "make a part for" with print context.

## Capabilities

### New Capabilities

### Modified Capabilities
- `skill-doc-structure`: adds a requirement that the frontmatter `description` triggers only on 3D-printing / CAD context and contains no standalone generic part nouns.

## Impact

- `SKILL.md` frontmatter only (one line). No `src/` code, scripts, JSON contracts, or tests change.
- Recall trade-off: a bare "design me a box" with no print context will no longer auto-trigger; users can still say "3D print" / "STL" or invoke `/cq-design:design` directly.
