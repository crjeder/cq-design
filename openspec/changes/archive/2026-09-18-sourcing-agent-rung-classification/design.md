## Context

Phase 0 (`skill/phase0_sourcing.md`) already delegates search and license
classification to the Sourcing agent (`prompts/sourcing.md`, commit ecbdcf6). The agent
returns a table with `Kind` (cadquery/build123d/openscad/freecad/step/brep/iges/mesh) and
`Reusable` (license verdict) per candidate. The main session still re-derives which of
the five rungs each candidate fits, even though `Kind` alone determines rungs 1 and 2,
and the agent already read the source page closely enough to judge whether a mesh's
stated dimensions fit the request as-is (rung 3) or need rework (rung 4).

The agent has no Bash or measurement tools — it is a search/browser-only subagent. It
cannot run `measure_stl.py` or the quality gate, so it cannot finalize rung 3, whose
requirement text mandates those checks plus explicit user confirmation before delivery.

## Goals / Non-Goals

**Goals:**
- Stop the main session re-deriving rung 1/2 from `Kind` — trust the agent's `Rung`
  column the same way it already trusts `Reusable`.
- Let the agent's page read produce a first-pass 3-vs-4 split for mesh candidates,
  cutting redundant re-reading of the same Notes text in the main session.
- Shrink `skill/phase0_sourcing.md`'s ladder narrative to what still requires local
  execution or the user checkpoint.

**Non-Goals:**
- Not removing rung 3's local vetting (`measure_stl.py`, quality gate stages) or its
  mandatory user confirmation — those need tools and a channel the agent doesn't have.
- Not changing how a rung, once determined, is handled (reuse/import/rebuild
  instructions in rungs 1/2/3/4 are unchanged).
- Not changing the license `Reusable` verdict or its rules.

## Decisions

**Agent returns `Rung` as `1`, `2`, `3?`, `4?`, or `n/a`; only 1 and 2 are final.**
Kind deterministically implies rung 1 (parametric) or rung 2 (BREP-family) — no judgment
call, no tooling needed, safe to trust outright like `Reusable`. Mesh candidates get a
`?`-suffixed provisional rung so the main session's job is explicitly "confirm/downgrade
via vetting," not "reclassify from scratch." Alternative considered: have the agent
predict a plain `3` or `4` for meshes with no marker. Rejected — the current spec already
allows rung 4 to fall through to `n/a` if `measure_stl.py` finds the discrepancy is
freeform, and an unmarked `4` would read as agent-final when it isn't; the `?` keeps the
distinction visible in the returned table itself, not only in prose the main session has
to remember.

**Phase 0 keeps the rung 3/4 vetting steps and per-rung handling verbatim; only the
rung-1/2 selection narrative is cut.** The removed text (lines ~31-55, ~62-68 of the
current file) was pure kind→rung mapping plus handling instructions; the handling
instructions stay (still needed once a rung is confirmed), only the "how you know it's
rung 1/2" reasoning goes, since the agent now states it directly.

**No new file, no schema.** The `Rung` column is one more Markdown table column in an
existing prompt file, parsed by nothing but the main session's own reading — this is not
worth a JSON contract or a schema file.

## Risks / Trade-offs

- **Agent mis-assigns rung 1/2 from a mis-typed `Kind`.** → `Kind` is already a
  small fixed enum the agent fills today; no new failure surface, and a wrong `Kind`
  would already have caused wrong downstream handling before this change.
- **Agent's provisional 3-vs-4 split is wrong (marks a rework candidate as `3?`).** →
  Unchanged risk profile: rung 3's mandatory `measure_stl.py` cross-check and user
  confirmation already exist specifically to catch this; a wrong `3?` just means that
  step demotes it to rung 4 instead of confirming it, same as today's mis-classification
  path.
- **Prompt drift**: `prompts/sourcing.md` grows another column's worth of instructions.
  → Bounded; the license verdict section is the precedent for size, and this reuses the
  same table the agent already produces.

## Migration Plan

Single-PR change, no data migration: edit `prompts/sourcing.md` (add column + rules),
edit `skill/phase0_sourcing.md` (trim narrative, add trust note), update
`openspec/specs/sourcing-triage/spec.md` via archive. Rollback is a revert of the same
two files.

## Open Questions

None — scope is deliberately bounded to the two prompt/doc files.
