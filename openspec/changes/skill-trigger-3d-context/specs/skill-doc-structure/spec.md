## ADDED Requirements

### Requirement: Frontmatter description triggers only on 3D-printing context
SKILL.md's frontmatter `description` SHALL lead with "3D-printable part" (or an
equivalent phrase naming 3D printing) and every trigger phrase it enumerates SHALL
carry 3D-printing or CAD context (for example "3D print", "3D-printable", "STL",
"CadQuery", "gridfinity", "print me a", "redesign for printability"). The
`description` SHALL NOT list a generic part noun or verb phrase standalone --
"box", "holder", "stand", "case", "mount", "lid", "enclosure", "bracket",
"design a part", "make a part for" -- such terms MAY appear only when qualified
by print context in the same phrase (e.g. "printable box", "3D-printed mount").

#### Scenario: Generic noun without print context
- **WHEN** the frontmatter `description` is inspected for the quoted trigger phrases
- **THEN** none of "box", "holder", "stand", "case", "mount", "lid", "enclosure",
  "bracket", "design a part", or "make a part for" appears as a standalone quoted
  phrase

#### Scenario: Description leads with 3D-printing context
- **WHEN** the frontmatter `description` is read
- **THEN** its first sentence names 3D-printable parts, and every quoted trigger
  phrase contains a 3D-printing or CAD term (print, printable, STL, CadQuery,
  gridfinity)

#### Scenario: Unrelated request using a generic noun
- **WHEN** a user request uses "mount", "lid", "box", or "case" with no 3D-printing
  or CAD context (e.g. "mount the drive", "the lid of a CSS box")
- **THEN** no phrase in the `description` matches that request on the noun alone
