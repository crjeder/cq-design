## Context

`src/model_export.py` builds the assembled 3MF by passing `(part["id"], plate, shape)`
tuples to `write_named_3mf` in `src/exporters/threemf_multi.py`. The writer already
accepts an arbitrary `name` and writes it as the `<object name="...">` attribute, so the
only thing standing between the current terse id (or kernel placeholder) and a readable
name is which string the exporter chooses.

Every part in `BUILD_PLAN.json` already carries a required `description` (min length 5).
That description is the natural, human-readable label, but it is free text: it can be
long and can contain characters (`<`, `>`, `&`, control chars, newlines) that are either
XML-hostile or make for a poor object name in a slicer's object tree.

## Goals / Non-Goals

**Goals:**
- 3MF object names reflect the part `description` so an operator recognizes each union.
- Names are valid in the 3MF XML and reasonable to display (no control chars, bounded
  length).

**Non-Goals:**
- Changing the part `id` role: it stays the stable key for STL filenames, plate
  grouping, and the kinematic check.
- Schema changes. `description` is already required.
- Renaming objects in any STL output (STL has no per-object name).
- Guaranteeing uniqueness of names. 3MF object identity is the `id` attribute; the
  `name` is a display label and duplicates are permitted.

## Decisions

**Derive the name from `description`, sanitized.** A small helper (e.g.
`_object_name(description: str) -> str`) collapses internal whitespace/newlines to single
spaces, strips control characters, and caps length (e.g. 64 chars, trimmed at a word
boundary where practical). `xml.etree.ElementTree` already escapes `<`, `>`, `&` on
write, so the sanitizer focuses on readability (control/whitespace) and length, not XML
safety. Rationale: the description is the only human-authored label available; the id is
a slug intended for filenames.

- Alternative considered: `f"{id}: {description}"`. Rejected as redundant; the id adds
  noise and the operator does not need the slug in the display name.
- Alternative considered: leave the name as `id`. Rejected per the proposal: the id is
  terse and, in the worst case (native kernel export elsewhere), shows as a placeholder.

**Keep the sanitizer in `model_export.py`.** The naming policy is an export-level
concern; `threemf_multi.write_named_3mf` stays a dumb writer of whatever name it is
given. This preserves its single responsibility and keeps the writer reusable.

## Risks / Trade-offs

- [Long or duplicate descriptions yield long or identical object names] → Length is
  capped; duplicates are acceptable because object identity is the `id` attribute, not
  the name.
- [Empty-after-sanitize description (e.g. all control chars)] → Fall back to the part
  `id` so an object always has a non-empty name. The schema's min-length-5 on
  `description` makes this near-impossible, but the fallback removes the edge case.
