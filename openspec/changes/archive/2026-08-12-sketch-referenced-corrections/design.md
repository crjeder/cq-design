## Context

`request_log` (see `bound-planning-notes`, `searchable-request-log`) is the pipeline's
sole place for round-by-round build history, keyed by verbatim user text. The C5
Phone-Holder retrospective (`TODO.md`) found that some correction rounds were actually
driven by an attached image, and today that image has no place in the schema -- it sat
in the project root and got referenced ad hoc from `part_notes`, the exact drift
`request_log` exists to prevent.

## Goals / Non-Goals

**Goals:**
- Give an attached sketch a durable, schema-declared home tied to the `request_log`
  entry it motivated.
- Make sure a later attempt, an escalation, or a re-plan can find and re-read that
  sketch the same way it can already search `request_log` text.

**Non-Goals:**
- No OCR, image understanding, or automatic text-to-image matching. The user (or the
  orchestrator acting on the user's attachment) explicitly names the image at the time
  of the correction; nothing infers which sketch belongs to which later feature.
- No change to `request_log_search.py`'s matching semantics (still text/kind only) --
  `images` rides along on whatever entry the existing keyword search already returns.
- No sketch versioning, diffing, or annotation tooling. `sketches/` is a flat drop
  location, not a managed asset store.

## Decisions

**Naming convention: `<slug>-<ts>.<ext>`, not the user's original filename.**
The user's original filename (`ear-placement.png`) collides across sessions and gives
no chronological ordering. Prefixing a short slug derived from the correction's `text`
(or a generic `sketch` if none is obvious) with the `request_log` entry's own `ts`
(colons replaced with `-` for filesystem safety) keeps names stable, sortable, and
traceable back to the entry without needing a separate index file.

**`images` lives on the `request_log` entry, not as a new top-level array.**
An image is meaningless without the correction it illustrates -- it is not an
independent artifact like a preview render. Nesting it under the entry that motivated
it means one lookup (`request_log_search.py`) already returns the image path alongside
the text that explains it, instead of requiring a second join.

**Copy, don't reference the original path.** The source image may live outside the
project (a temp download, a clipboard paste, an external drive) and may not survive
the session. Copying into `sketches/` at record time makes the reference durable the
same way `build/journal.md` and `attempts.jsonl` are durable -- self-contained inside
the project directory.

## Risks / Trade-offs

- Unbounded growth of `sketches/` over a long project -> acceptable; it mirrors
  `build/attempts.jsonl` and preview PNGs, which already accumulate uncapped, and
  sketches are typically few (observed: 3 over a 7-round build).
- No enforcement that a copied file is actually an image (vs. any file) -> acceptable;
  `plan_validate.py` checks the field shape (non-empty path strings), not file content,
  consistent with how it treats every other path-bearing field in the schema.
